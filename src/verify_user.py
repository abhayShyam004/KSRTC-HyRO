import os
import psycopg2
import bcrypt
from psycopg2.extras import RealDictCursor
import sys
import datetime

# Use the pooler URL
DATABASE_URL = 'postgresql://neondb_owner:npg_0R7oaXzqeYQK@ep-long-breeze-a1vczx8s-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

def log(msg):
    with open("verify_log.txt", "a") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")
    print(msg)

def verify_user():
    log("Starting verification...")
    try:
        log("Connecting to database (Timeout 5s)...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        log("✅ Connected!")
        
        # 1. Check if users table exists
        cur.execute("SELECT to_regclass('public.users')")
        if not cur.fetchone()['to_regclass']:
            log("❌ 'users' table does not exist!")
            return

        # 2. Check for admin user
        email = 'admin123' 
        log(f"Checking for user: {email}")
        
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            log(f"❌ User '{email}' not found.")
            
            # Create the user
            log("Creating default admin user...")
            password = 'admin@hyro'
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cur.execute('''
                INSERT INTO users (name, email, password_hash, role, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
            ''', ('Admin User', email, hashed_pw, 'super_admin', 'active'))
            conn.commit()
            log("✅ User created successfully.")
            
        else:
            log(f"✅ User found: ID={user['user_id']}, Role={user['role']}, Status={user['status']}")
            
            # 3. Verify password
            password = 'admin@hyro'
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                log("✅ Password 'admin@hyro' is CORRECT.")
            else:
                log("❌ Password 'admin@hyro' is INCORRECT.")
                
                # Reset password
                log("Resetting password...")
                hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_pw, user['user_id']))
                conn.commit()
                log("✅ Password reset to 'admin@hyro'.")

        conn.close()
        
    except Exception as e:
        log(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_user()
