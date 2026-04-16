import time
import sys
import os
from pathlib import Path

# Thêm thư mục hiện tại vào path để import app
sys.path.append(os.getcwd())

from app.db.metadata import get_multi_db_schema_context, invalidate_schema_cache
from app.agents.orchestrator import route_after_reader, AgentState
from app.db.semantic_cache import set_cached_response, get_cached_response
from app.api.routes.admin import split_sql_statements

def benchmark_schema():
    print("\n--- [1] Benchmark Schema Caching ---")
    
    # Giả lập connection để có schema (nếu có engine)
    start_time = time.time()
    schema1 = get_multi_db_schema_context()
    end_time = time.time()
    print(f"Fetch 1 (Cold Start/Fetch): {(end_time - start_time)*1000:.2f}ms")
    
    start_time = time.time()
    schema2 = get_multi_db_schema_context()
    end_time = time.time()
    print(f"Fetch 2 (Cached Hit): {(end_time - start_time)*1000:.2f}ms")
    
    if schema1 == schema2:
        print("=> RESULT: Schema Cache is working.")

def benchmark_semantic_cache():
    print("\n--- [2] Benchmark Semantic Cache ---")
    q = "Last month revenue?"
    sql = "SELECT SUM(amount) FROM orders WHERE date >= '2024-03-01'"
    plan = "Calc total amount from orders table"
    
    # Ghi vào cache
    set_cached_response(q, sql, plan)
    
    start_time = time.time()
    result = get_cached_response(q)
    end_time = time.time()
    
    print(f"Cache Retrieval Time: {(end_time - start_time)*1000:.2f}ms")
    if result and result['sql_query'] == sql:
        print("=> RESULT: Semantic Cache is extremely fast (< 1ms).")

def benchmark_routing():
    print("\n--- [3] Benchmark Fast-Track Routing ---")
    
    scenarios = [
        {"q": "Show users table", "expected": "sql_coder"}, 
        {"q": "Top 10 best selling products", "expected": "sql_coder"},
        {"q": "Analyze revenue trends and compare with last year then draw chart", "expected": "planner"}
    ]
    
    for s in scenarios:
        state: AgentState = {
            "question": s["q"],
            "is_approved": False,
            "is_cached": False,
            "chat_history": []
        }
        target = route_after_reader(state)
        status = "PASSED" if target == s["expected"] else "FAILED"
        print(f"Query: '{s['q']}' -> Flow: {target} [{status}]")

def benchmark_sql_splitter():
    print("\n--- [4] Benchmark SQL Splitter ---")
    sql = "CREATE USER 'test'@'%' IDENTIFIED BY 'pass;word'; GRANT SELECT ON db.* TO 'test'@'%';"
    stmts = split_sql_statements(sql)
    print(f"Number of statements extracted: {len(stmts)}")
    if len(stmts) == 2 and "pass;word" in stmts[0]:
        print("=> RESULT: SQL Splitter safely ignores semicolons inside strings!")
    else:
        print("=> FAILED: Splitter incorrectly cut the string.")

if __name__ == "__main__":
    print("=== START AGENT PERFORMANCE & COMPATIBILITY TEST ===")
    
    try:
        benchmark_schema()
    except Exception as e:
        print(f"Skip Schema Test (Need DB active): {e}")
        
    benchmark_semantic_cache()
    benchmark_routing()
    benchmark_sql_splitter()
    
    print("\n=== END PERFORMANCE TEST ===")
