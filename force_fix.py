import os
import sys
import bcrypt
import psycopg2

# CONFIG: Ensure local modules are found
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import DATABASE_URL

def force_fix_admin():
    print("Connecting to DB...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    hashed_pw = bcrypt.hashpw('admin@hyro'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Delete any existing admin or admin@Hyro to be sure
    cur.execute("DELETE FROM users WHERE email IN ('admin', 'admin@Hyro', 'admin@ksrtc.com')")
    
    # Insert fresh
    cur.execute('''
        INSERT INTO users (name, email, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s)
    ''', ('Admin User', 'admin', hashed_pw, 'super_admin', 'active'))
    
    conn.commit()
    print("SUCCESS: Admin user recreated.")
    print("Username: admin")
    print("Password: admin@hyro")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    force_fix_admin()
