
import os
import sys
from src.database import get_db_connection

def check_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM demand_history;")
        count = cur.fetchone()[0]
        print(f"DEBUG_DB_COUNT: {count}")
        
        cur.execute("SELECT * FROM demand_history LIMIT 5;")
        rows = cur.fetchall()
        print("SAMPLE_ROWS:", rows)
        
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_data()
