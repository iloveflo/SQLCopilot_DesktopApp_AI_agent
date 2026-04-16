import sqlite3
from pathlib import Path

db_path = Path.home() / '.sqlcopilot_chat.sqlite3'
if not db_path.exists():
    print(f"Database file {db_path} does not exist yet. Running setup...")
    # Triggering setup by importing the module
    import sys
    import os
    sys.path.append(os.getcwd())
    from app.db import session_store
    
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")
print(f"pinned_metrics exists: {'pinned_metrics' in tables}")
conn.close()
