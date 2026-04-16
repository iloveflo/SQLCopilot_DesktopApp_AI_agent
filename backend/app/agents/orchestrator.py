import operator
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agents.schema_reader import get_optimized_schema
from app.agents.nl2sql import generate_sql
from app.agents.query_runner import execute_safe_query
from app.agents.interpreter import interpret_and_visualize

# 1. Định nghĩa Data Structure
class AgentState(TypedDict):
    question: str
    schema: str
    plan: str
    plan_feedback: Optional[str]
    sql_query: str
    sql_error: Optional[str]
    raw_data: List[Dict[str, Any]]
    answer: str
    is_approved: bool
    retries: int
    chart_config: Optional[Dict[str, Any]]
    chat_history: Annotated[list[Dict[str, Any]], operator.add]
    session_id: str
    cached_sql: Optional[str]
    cached_plan: Optional[str]

# 2. Định nghĩa các Node logic
def _format_recent_history(chat_history: list[Dict[str, Any]], max_messages: int = 6) -> str:
    if not chat_history:
        return "Không có lịch sử"
    recent = chat_history[-max_messages:]
    return "\n".join([f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}" for msg in recent])

def node_read_schema(state: AgentState):
    from app.db.semantic_cache import get_cached_response
    cache_hit = get_cached_response(state["question"])
    return {
        "schema": get_optimized_schema(state["question"]),
        "cached_sql": cache_hit["sql_query"] if cache_hit else None,
        "cached_plan": cache_hit["plan"] if cache_hit else None
    }

def node_generate_sql(state: AgentState):
    """Xử lý chính (Pillar 2 + Speed patch): Gộp Plan và SQL."""
    history = state.get("chat_history", [])
    formatted_history = _format_recent_history(history, max_messages=4)
    
    # Nếu đã được duyệt (HITL) và KHÔNG có góp ý mới, sử dụng ngay SQL cũ
    if state.get("is_approved") and state.get("sql_query") and not state.get("plan_feedback"):
        return {"sql_query": state["sql_query"], "needs_approval": False}

    result = generate_sql(
        question=state["question"], 
        schema=state.get("schema", ""), 
        error_feedback=state.get("sql_error"), 
        chat_history=formatted_history,
        plan_feedback=state.get("plan_feedback")
    )
    
    return {
        "sql_query": result.query, 
        "plan": result.plan or "Đã lập kế hoạch tự động.",
        "answer": "Đã chuẩn bị kế hoạch và câu lệnh SQL.",
        # Nếu có feedback bám kèm is_approved=True, vẫn cần chạy execute sau node này
        # nhưng node này bản thân nó 'xong' nhiệm vụ generate.
        "needs_approval": not state.get("is_approved", False)
    }

def node_execute(state: AgentState):
    result = execute_safe_query(
        sql=state["sql_query"], 
        session_id=state.get("session_id", "unknown"), 
        question=state.get("question", "")
    )
    if result["success"]:
        return {"raw_data": result["data"], "sql_error": None, "plan_feedback": None} # Xóa feedback sau khi đã dùng
    else:
        current_retries = state.get("retries", 0)
        return {"sql_error": result["error"], "retries": current_retries + 1}

def node_interpret(state: AgentState):
    """Gộp Báo cáo và Biểu đồ (Pillar 3 + Speed patch)."""
    res = interpret_and_visualize(state["question"], state["sql_query"], state["raw_data"])
    
    new_memory = [
        {"role": "user", "content": state["question"]},
        {
            "role": "assistant", 
            "content": res["answer"],
            "sql_query": state.get("sql_query"),
            "raw_data": state.get("raw_data"),
            "chart_config": res["chart_config"]
        }
    ]
    
    if state.get("raw_data") and state.get("sql_query"):
        from app.db.semantic_cache import set_cached_response
        set_cached_response(state["question"], state["sql_query"], state.get("plan"))

    return {
        "answer": res["answer"],
        "chart_config": res["chart_config"],
        "is_approved": False,
        "raw_data": state.get("raw_data"), # Trả về để Frontend cập nhật stream đồng bộ
        "chat_history": new_memory
    }

def route_after_reader(state: AgentState) -> str:
    if state.get("cached_sql"): return "cache"
    return "sql_coder"

def route_after_sql(state: AgentState) -> str:
    """Quyết định dừng lại chờ duyệt (HITL) hay chạy luôn."""
    if state.get("is_approved"): return "execute"
    return "wait_for_user"

def should_retry(state: AgentState) -> str:
    if state.get("sql_error") is not None and state.get("retries", 0) < 3:
        return "retry"
    return "finalize"

# 4. Compile Graph
workflow = StateGraph(AgentState)
workflow.add_node("reader", node_read_schema)
workflow.add_node("sql_coder", node_generate_sql)
workflow.add_node("db_executor", node_execute)
workflow.add_node("data_teller", node_interpret)

workflow.set_entry_point("reader")
workflow.add_conditional_edges("reader", route_after_reader, {"cache": "db_executor", "sql_coder": "sql_coder"})
workflow.add_conditional_edges("sql_coder", route_after_sql, {"execute": "db_executor", "wait_for_user": END})

workflow.add_conditional_edges("db_executor", should_retry, {"retry": "sql_coder", "finalize": "data_teller"})
workflow.add_edge("data_teller", END)

# Persistent DB checkpointer
from pathlib import Path
db_path = Path.home() / ".sqlcopilot_chat.sqlite3"
sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10)
sqlite_conn.execute("PRAGMA journal_mode=WAL;")
memory = SqliteSaver(sqlite_conn)
memory.setup()
sql_copilot_app = workflow.compile(checkpointer=memory)

# Functions
def run_copilot(*args, **kwargs): return sql_copilot_app.invoke(*args, **kwargs)
def stream_copilot(question: str, session_id: str = "default_session", is_approved: bool = False, plan_feedback: str = None):
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "question": question, "session_id": session_id, "is_approved": is_approved,
        "plan_feedback": plan_feedback, "retries": 0, "sql_error": None,
        "raw_data": [], "sql_query": "", "chart_config": None, "chat_history": []
    }
    for update in sql_copilot_app.stream(initial_state, config=config, stream_mode="updates"):
        node_name = list(update.keys())[0] if update else "unknown"
        yield {"node": node_name, "status": "completed", "data": update.get(node_name, {})}

def clear_session(sid):
    try:
        sqlite_conn.execute("DELETE FROM writes WHERE thread_id = ?", (sid,))
        sqlite_conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (sid,))
        sqlite_conn.commit()
        return True
    except: return False

def get_session_history(sid):
    config = {"configurable": {"thread_id": sid}}
    state = sql_copilot_app.get_state(config)
    return state.values.get("chat_history", []) if state and getattr(state, 'values', None) else []