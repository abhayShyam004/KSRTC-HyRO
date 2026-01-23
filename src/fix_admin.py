import os
import sys
import bcrypt

# CONFIG: Ensure local modules are found
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import get_db_connection

def fix_admin():
    hashed_pw = bcrypt.hashpw('admin@hyro'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if admin exists
            cur.execute("SELECT * FROM users WHERE email = %s", ('admin',))
            user = cur.fetchone()
            
            if user:
                print("Updating existing admin user...")
                cur.execute("UPDATE users SET password_hash = %s WHERE email = %s", (hashed_pw, 'admin'))
            else:
                print("Admin user not found, inserting...")
                cur.execute('''
                    INSERT INTO users (name, email, password_hash, role, status)
                    VALUES (%s, %s, %s, %s, %s)
                ''', ('Admin User', 'admin', hashed_pw, 'super_admin', 'active'))
            
            conn.commit()
            print("[OK] Admin user fixed (Username: admin, Password: admin@hyro).")

if __name__ == "__main__":
    fix_admin()
