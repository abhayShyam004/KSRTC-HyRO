import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# CONFIG: Ensure local modules are found
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import DATABASE_URL

def debug_users():
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, name, email, role, status FROM users")
            users = cur.fetchall()
            print(f"\nFOUND {len(users)} USERS:")
            for u in users:
                print(f"- ID: {u['user_id']} | Name: {u['name']} | Email/User: '{u['email']}' | Role: {u['role']}")
            
            if not users:
                print("No users found in database.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    debug_users()
