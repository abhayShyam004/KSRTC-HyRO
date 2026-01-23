"""
Database module for KSRTC-HyRO
Handles PostgreSQL connection and CRUD operations
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Database URL from environment variable or default
# Reverting to direct host to rule out pooler DNS issues
DATABASE_URL = os.environ.get('DATABASE_URL', 
    'postgresql://neondb_owner:npg_0R7oaXzqeYQK@ep-long-breeze-a1vczx8s.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')

@contextmanager
def get_db_connection():
    """Get a database connection with context manager for auto-cleanup"""
    conn = None
    try:
        # Increased timeout to 30s for slower networks
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
        yield conn
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}")
        if "translate host name" in str(e):
             print("[TIP] DNS FAILURE. Your computer cannot find the database address.")
        raise
    finally:
        if conn:
            conn.close()

def init_database():
    """Initialize database tables if they don't exist"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Bus Stops table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS bus_stops (
                    bus_stop_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    lat DECIMAL(10, 6) NOT NULL,
                    lon DECIMAL(10, 6) NOT NULL,
                    district VARCHAR(100),
                    category VARCHAR(50) DEFAULT 'regular',
                    demand_multiplier DECIMAL(3, 2) DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Users table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'operator',
                    status VARCHAR(20) DEFAULT 'active',
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Settings table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Route History table for analytics
            cur.execute('''
                CREATE TABLE IF NOT EXISTS route_history (
                    route_id SERIAL PRIMARY KEY,
                    stop_ids INTEGER[],
                    distance_km DECIMAL(10, 2),
                    duration_min INTEGER,
                    passengers INTEGER,
                    fuel_cost DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Analytics aggregates table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS analytics_daily (
                    date DATE PRIMARY KEY,
                    total_passengers INTEGER DEFAULT 0,
                    routes_optimized INTEGER DEFAULT 0,
                    fuel_saved DECIMAL(12, 2) DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            print("[OK] Database tables initialized successfully.")

def seed_default_data():
    """Insert default data if tables are empty"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check if bus_stops table is empty
            cur.execute("SELECT COUNT(*) FROM bus_stops")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Insert default bus stops
                default_stops = [
                    ('Thampanoor Central', 8.4875, 76.9520, 'Thiruvananthapuram', 'transport_hub', 2.0),
                    ('Vyttila Mobility Hub', 9.9675, 76.3203, 'Ernakulam', 'transport_hub', 2.0),
                    ('Ernakulam South', 9.9816, 76.2999, 'Ernakulam', 'transport_hub', 1.8),
                    ('Aluva Bus Station', 10.1100, 76.3550, 'Ernakulam', 'transport_hub', 1.7),
                    ('Cochin International Airport', 10.1520, 76.4019, 'Ernakulam', 'airport', 1.9),
                    ('Kozhikode KSRTC', 11.2588, 75.7804, 'Kozhikode', 'transport_hub', 1.8),
                    ('Calicut Cyberpark', 11.3200, 75.9500, 'Kozhikode', 'commercial', 1.5),
                    ('Thrissur Sakthan', 10.5200, 76.2100, 'Thrissur', 'transport_hub', 1.6),
                    ('Kottayam KSRTC', 9.5916, 76.5222, 'Kottayam', 'transport_hub', 1.5),
                    ('Alappuzha Bus Stand', 9.4900, 76.3400, 'Alappuzha', 'tourist', 1.6),
                    ('Kollam KSRTC', 8.8800, 76.5900, 'Kollam', 'transport_hub', 1.5),
                    ('Palakkad KSRTC', 10.7700, 76.6500, 'Palakkad', 'transport_hub', 1.4),
                    ('Kannur City Bus Stand', 11.8700, 75.3500, 'Kannur', 'transport_hub', 1.5),
                    ('Edappally Junction', 10.0261, 76.3125, 'Ernakulam', 'commercial', 1.6),
                    ('Fort Kochi', 9.9639, 76.2424, 'Ernakulam', 'tourist', 1.5),
                    ('Kakkanad InfoPark', 10.0100, 76.3500, 'Ernakulam', 'commercial', 1.4),
                ]
                
                for stop in default_stops:
                    cur.execute('''
                        INSERT INTO bus_stops (name, lat, lon, district, category, demand_multiplier)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', stop)
                
                conn.commit()
                print(f"[OK] Seeded {len(default_stops)} default bus stops.")
            
            # Check if settings table is empty
            cur.execute("SELECT COUNT(*) FROM settings")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Insert default settings
                default_settings = [
                    ('diesel_price', '95.21'),
                    ('empty_mileage', '4.5'),
                    ('full_mileage', '3.5'),
                    ('bus_capacity', '55'),
                    ('peak_morning', '8:00 AM - 10:00 AM'),
                    ('peak_evening', '5:00 PM - 7:00 PM'),
                    ('osrm_server', 'https://router.project-osrm.org'),
                    ('rate_limit', '60'),
                ]
                
                for key, value in default_settings:
                    cur.execute('INSERT INTO settings (key, value) VALUES (%s, %s)', (key, value))
                
                conn.commit()
                print("[OK] Seeded default settings.")
            
            # Check if users table is empty
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Insert default admin user (password: admin123)
                cur.execute('''
                    INSERT INTO users (name, email, password_hash, role, status)
                    VALUES (%s, %s, %s, %s, %s)
                ''', ('Admin User', 'admin@ksrtc.com', 'admin123', 'super_admin', 'active'))
                
                conn.commit()
                print("[OK] Seeded default admin user.")

# ========== BUS STOPS CRUD ==========
def get_all_stops():
    """Get all bus stops"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM bus_stops ORDER BY bus_stop_id')
            return cur.fetchall()

def get_stop_by_id(stop_id):
    """Get a single bus stop by ID"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM bus_stops WHERE bus_stop_id = %s', (stop_id,))
            return cur.fetchone()

def create_stop(name, lat, lon, district, category='regular', demand_multiplier=1.0):
    """Create a new bus stop"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO bus_stops (name, lat, lon, district, category, demand_multiplier)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            ''', (name, lat, lon, district, category, demand_multiplier))
            conn.commit()
            return cur.fetchone()

def update_stop(stop_id, name, lat, lon, district, category, demand_multiplier):
    """Update an existing bus stop"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                UPDATE bus_stops 
                SET name = %s, lat = %s, lon = %s, district = %s, 
                    category = %s, demand_multiplier = %s, updated_at = CURRENT_TIMESTAMP
                WHERE bus_stop_id = %s
                RETURNING *
            ''', (name, lat, lon, district, category, demand_multiplier, stop_id))
            conn.commit()
            return cur.fetchone()

def delete_stop(stop_id):
    """Delete a bus stop"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM bus_stops WHERE bus_stop_id = %s', (stop_id,))
            conn.commit()
            return cur.rowcount > 0

# ========== SETTINGS CRUD ==========
def get_all_settings():
    """Get all settings as a dictionary"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT key, value FROM settings')
            rows = cur.fetchall()
            return {row['key']: row['value'] for row in rows}

def get_setting(key):
    """Get a single setting value"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT value FROM settings WHERE key = %s', (key,))
            row = cur.fetchone()
            return row[0] if row else None

def update_setting(key, value):
    """Update or insert a setting"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
            ''', (key, value, value))
            conn.commit()

# ========== USERS CRUD ==========
def get_all_users():
    """Get all users (excluding password)"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT user_id, name, email, role, status, last_login, created_at FROM users ORDER BY user_id')
            return cur.fetchall()

def create_user(name, email, password, role='operator'):
    """Create a new user"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id, name, email, role, status, created_at
            ''', (name, email, password, role))
            conn.commit()
            return cur.fetchone()

def delete_user(user_id):
    """Delete a user"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
            conn.commit()
            return cur.rowcount > 0

# ========== ANALYTICS ==========
def log_route_optimization(stop_ids, distance_km, duration_min, passengers, fuel_cost):
    """Log a route optimization for analytics"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO route_history (stop_ids, distance_km, duration_min, passengers, fuel_cost)
                VALUES (%s, %s, %s, %s, %s)
            ''', (stop_ids, distance_km, duration_min, passengers, fuel_cost))
            
            # Update daily analytics
            cur.execute('''
                INSERT INTO analytics_daily (date, total_passengers, routes_optimized, fuel_saved)
                VALUES (CURRENT_DATE, %s, 1, %s)
                ON CONFLICT (date) DO UPDATE SET 
                    total_passengers = analytics_daily.total_passengers + %s,
                    routes_optimized = analytics_daily.routes_optimized + 1,
                    fuel_saved = analytics_daily.fuel_saved + %s,
                    updated_at = CURRENT_TIMESTAMP
            ''', (passengers, fuel_cost, passengers, fuel_cost))
            
            conn.commit()

def get_analytics_summary():
    """Get analytics summary for dashboard"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total stats
            cur.execute('''
                SELECT 
                    COALESCE(SUM(total_passengers), 0) as total_passengers,
                    COALESCE(SUM(routes_optimized), 0) as routes_optimized,
                    COALESCE(SUM(fuel_saved), 0) as fuel_saved
                FROM analytics_daily
            ''')
            totals = cur.fetchone()
            
            # Last 7 days trend
            cur.execute('''
                SELECT date, total_passengers, routes_optimized
                FROM analytics_daily
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY date
            ''')
            trends = cur.fetchall()
            
            # Stop count
            cur.execute('SELECT COUNT(*) as count FROM bus_stops')
            stop_count = cur.fetchone()['count']
            
            return {
                'total_passengers': int(totals['total_passengers']),
                'routes_optimized': int(totals['routes_optimized']),
                'fuel_saved': float(totals['fuel_saved']),
                'active_stops': stop_count,
                'trends': trends
            }
