import psycopg2
import os
import sys

# The URL currently used in src/database.py (with -pooler)
DATABASE_URL = 'postgresql://neondb_owner:npg_0R7oaXzqeYQK@ep-long-breeze-a1vczx8s-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

print("--- Database Connection Test ---")
print(f"Target: {DATABASE_URL}")
print("Attempting to connect...")

try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    print("✅ CONNECTION SUCCESSFUL!")
    
    with conn.cursor() as cur:
        print("Attempting to read from bus_stops table...")
        cur.execute("SELECT count(*) FROM bus_stops")
        count = cur.fetchone()[0]
        print(f"✅ READ SUCCESSFUL: Found {count} stops in the remote database.")
        
        # Optional: Check if the 'offline' stop exists (unlikely in this context, but good verify)
        # print("Checking for recently added stops...")
        # cur.execute("SELECT name FROM bus_stops ORDER BY created_at DESC LIMIT 5")
        # stops = cur.fetchall()
        # for s in stops:
        #     print(f" - {s[0]}")
            
    conn.close()
    print("\nCONCLUSION: Your computer CAN connect to the database.")
    print("If your stop is missing, it means the Flask app ran in 'Offline Mode' during that session.")
    sys.exit(0)

except Exception as e:
    print("\n❌ CONNECTION FAILED")
    print(f"Error: {e}")
    print("-" * 50)
    print("Diagnosis:")
    if "could not translate host name" in str(e):
        print("DNS ERROR: Your computer cannot find the 'neon.tech' server.")
        print("Fix attempts:")
        print("1. Flush DNS: 'ipconfig /flushdns'")
        print("2. Set DNS to 8.8.8.8 (Google)")
        print("3. Ensure WARP/VPN is fully active.")
    elif "timeout" in str(e):
        print("TIMEOUT: Firewall or unstable internet is blocking the connection.")
    else:
        print("Unknown network/auth error.")
    sys.exit(1)
