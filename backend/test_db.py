from sqlalchemy import create_engine, inspect
import sys
engine = create_engine("mysql+pymysql://root:binh11a10@localhost:3306/")
inspector = inspect(engine)
try:
    dbs = inspector.get_schema_names()
    print("Databases:", dbs)
except Exception as e:
    print(e)
