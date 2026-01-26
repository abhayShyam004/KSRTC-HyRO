
import json
from src.database import get_db_connection

def list_airports():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, district FROM bus_stops WHERE category='airport' OR name ILIKE '%Airport%'")
                rows = cur.fetchall()
                print(f"Found {len(rows)} airports:")
                for name, district in rows:
                    print(f"- {name} (District: {district})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_airports()
