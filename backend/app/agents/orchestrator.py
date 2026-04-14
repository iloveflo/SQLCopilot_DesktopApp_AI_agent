import operator
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agents.schema_reader import get_optimized_schema
from app.agents.planner import generate_plan
from app.agents.nl2sql import generate_sql
from app.agents.query_runner import execute_safe_query
from app.agents.interpreter import interpret_results
from app.agents.visualizer import generate_chart_config

# 1. Định nghĩa Data Structure truyền giữa các Node (Agents)
class AgentState(TypedDict):
    question: str
    schema: str
    is_approved: bool
    plan_feedback: Optional[str]
    plan: Optional[str]
    needs_approval: bool
    sql_query: str
    sql_error: Optional[str]
    retries: int
    raw_data: Optional[List[Dict[str, Any]]]
    answer: str
    chart_config: Optional[Dict[str, Any]]
    chat_history: Annotated[list[Dict[str, Any]], operator.add]

# 2. Định nghĩa các Node logic
def _format_recent_history(chat_history: list[Dict[str, Any]], max_messages: int = 6) -> str:
    if not chat_history:
        return "Không có lịch sử"
    recent = chat_history[-max_messages:]
    return "\n".join([f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}" for msg in recent])


def node_read_schema(state: AgentState):
    return {"schema": get_optimized_schema(state.get("question", ""))}


def node_plan(state: AgentState):
    history = state.get("chat_history", [])
    formatted_history = _format_recent_history(history, max_messages=6)
    
    plan_text = generate_plan(state["question"], state.get("schema", ""), chat_history=formatted_history)
    return {"plan": plan_text, "needs_approval": True, "answer": "Đã lập xong kế hoạch."}


def node_generate_sql(state: AgentState):
    history = state.get("chat_history", [])
    formatted_history = _format_recent_history(history, max_messages=4)
    
    plan = state.get("plan")
    feedback = state.get("plan_feedback")
    
    combined_plan = ""
    if plan and feedback:
        combined_plan = f"BẢN KẾ HOẠCH GỐC:\n{plan}\n\nYÊU CẦU ĐIỀU CHỈNH TỪ USER:\n{feedback}"
    elif feedback:
        combined_plan = feedback
    elif plan:
        combined_plan = plan

    result = generate_sql(
        question=state["question"], 
        schema=state.get("schema", ""), 
        error_feedback=state.get("sql_error"), 
        chat_history=formatted_history,
        plan_feedback=combined_plan
    )
    return {"sql_query": result.query}

def node_execute(state: AgentState):
    result = execute_safe_query(state["sql_query"])
    if result["success"]:
        return {"raw_data": result["data"], "sql_error": None}
    else:
        # Nếu lỗi, tăng biến đếm retries lên 1
        current_retries = state.get("retries", 0)
        return {"sql_error": result["error"], "retries": current_retries + 1}

def node_interpret(state: AgentState):
    answer = interpret_results(state["question"], state["sql_query"], state["raw_data"])
    chart_config = None
    if state.get("raw_data"):
        chart_config = generate_chart_config(state["question"], state["raw_data"])
        
    new_memory = [
        {"role": "user", "content": state["question"]},
        {
            "role": "assistant", 
            "content": answer,
            "sql_query": state.get("sql_query"),
            "raw_data": state.get("raw_data"),
            "chart_config": chart_config
        }
    ]
        
    return {
        "answer": answer,
        "chart_config": chart_config,
        "needs_approval": False, # Xong chu trình thì gỡ cờ duyệt
        "chat_history": new_memory
    }

# 3. Định nghĩa Conditional Routing
def route_after_reader(state: AgentState) -> str:
    """Nên lập kế hoạch hay quất luôn sinh Code?"""
    if not state.get("is_approved", False):
        return "planner"
    return "sql_coder"

def should_retry(state: AgentState) -> str:
    """Quyết định luồng đi tiếp dựa vào state hiện tại."""
    if state.get("sql_error") is not None:
        if state.get("retries", 0) < 3:
            return "retry" # Quay lại sửa SQL
        else:
            return "fail" # Quá 3 lần, chấp nhận lỗi
    return "success" # Chạy DB thành công

# 4. Compile Graph
workflow = StateGraph(AgentState)

workflow.add_node("reader", node_read_schema)
workflow.add_node("planner", node_plan)
workflow.add_node("sql_coder", node_generate_sql)
workflow.add_node("db_executor", node_execute)
workflow.add_node("data_teller", node_interpret)

workflow.set_entry_point("reader")

workflow.add_conditional_edges("reader", route_after_reader)
workflow.add_edge("planner", END)
workflow.add_edge("sql_coder", "db_executor")

workflow.add_conditional_edges(
    "db_executor",
    should_retry,
    {
        "retry": "sql_coder",
        "success": "data_teller",
        "fail": "data_teller"
    }
)
workflow.add_edge("data_teller", END)

# Khởi tạo kết nối vật lý với file CSDL trên ổ cứng
from pathlib import Path
db_path = Path.home() / ".sqlcopilot_chat.sqlite3"
sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)
memory = SqliteSaver(sqlite_conn)
memory.setup()  # Tạo các bảng nếu chưa có

sql_copilot_app = workflow.compile(checkpointer=memory)

# Hàm Wrapper
def run_copilot(question: str, session_id: str = "default_session", is_approved: bool = False, plan_feedback: str = None) -> dict:
    config = {"configurable": {"thread_id": session_id}}
    
    initial_state = {
        "question": question,
        "is_approved": is_approved,
        "plan_feedback": plan_feedback,
        "retries": 0,
        "sql_error": None,
        "raw_data": [],
        "sql_query": "",
        "chart_config": None
    }
    
    return sql_copilot_app.invoke(initial_state, config=config)

def stream_copilot(question: str, session_id: str = "default_session", is_approved: bool = False, plan_feedback: str = None):
    """Generator truyền các cập nhật trạng thái từ LangGraph (Thought Stream)."""
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "question": question,
        "is_approved": is_approved,
        "plan_feedback": plan_feedback,
        "retries": 0,
        "sql_error": None,
        "raw_data": [],
        "sql_query": "",
        "chart_config": None
    }
    
    # Sử dụng stream_mode="updates" để nhận sự kiện khi mỗi Node chạy xong
    for update in sql_copilot_app.stream(initial_state, config=config, stream_mode="updates"):
        # update là dict: {"node_name": {state_changes}}
        node_name = list(update.keys())[0] if update else "unknown"
        yield {
            "node": node_name,
            "status": "completed",
            "data": update.get(node_name, {})
        }

def clear_session(session_id: str) -> bool:
    """Xóa bỏ triệt để bộ nhớ của một phiên chat khỏi ổ cứng."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (session_id,))
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (session_id,))
        sqlite_conn.commit()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi khi xóa session: {e}")
        return False

def get_session_history(session_id: str) -> list:
    """Tải toàn bộ lịch sử trò chuyện (bao gồm cả chart và data thô) từ ổ cứng."""
    config = {"configurable": {"thread_id": session_id}}
    state_snapshot = sql_copilot_app.get_state(config)
    if state_snapshot and getattr(state_snapshot, 'values', None):
        return state_snapshot.values.get("chat_history", [])
    return []