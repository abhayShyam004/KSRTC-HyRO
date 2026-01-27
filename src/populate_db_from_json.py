import json
import os
import psycopg2
import psycopg2.extras
import random
import math
from database import get_db_connection

# District Capitals of Kerala (Lat, Lon)
DISTRICT_CAPITALS = {
    'Thiruvananthapuram': (8.5241, 76.9366),
    'Kollam': (8.8932, 76.6141),
    'Pathanamthitta': (9.2648, 76.7870),
    'Alappuzha': (9.4981, 76.3388),
    'Kottayam': (9.5916, 76.5222),
    'Idukki': (9.8494, 76.9809),
    'Ernakulam': (9.9312, 76.2673),
    'Thrissur': (10.5276, 76.2144),
    'Palakkad': (10.7867, 76.6548),
    'Malappuram': (11.0510, 76.0711),
    'Kozhikode': (11.2588, 75.7804),
    'Wayanad': (11.6103, 76.0830),
    'Kannur': (11.8745, 75.3704),
    'Kasaragod': (12.5102, 74.9852)
}

def get_nearest_district(lat, lon):
    """Find the nearest district capital to the given coordinates."""
    min_dist = float('inf')
    nearest_district = 'Kerala'
    
    for district, (d_lat, d_lon) in DISTRICT_CAPITALS.items():
        # Euclidean distance is sufficient for this scale/purpose
        dist = math.sqrt((lat - d_lat)**2 + (lon - d_lon)**2)
        if dist < min_dist:
            min_dist = dist
            nearest_district = district
            
    return nearest_district

# Default stops from database.py (Original 17)
DEFAULT_STOPS = [
    (1, 'Thampanoor Central', 8.4875, 76.9520, 'Thiruvananthapuram', 'transport_hub', 2.0),
    (2, 'Vyttila Mobility Hub', 9.9675, 76.3203, 'Ernakulam', 'transport_hub', 2.0),
    (3, 'Ernakulam South', 9.9816, 76.2999, 'Ernakulam', 'transport_hub', 1.8),
    (4, 'Aluva Bus Station', 10.1100, 76.3550, 'Ernakulam', 'transport_hub', 1.7),
    (5, 'Cochin International Airport', 10.1520, 76.4019, 'Ernakulam', 'airport', 1.9),
    (6, 'Kozhikode KSRTC', 11.2588, 75.7804, 'Kozhikode', 'transport_hub', 1.8),
    (7, 'Calicut Cyberpark', 11.3200, 75.9500, 'Kozhikode', 'commercial', 1.5),
    (8, 'Thrissur Sakthan', 10.5200, 76.2100, 'Thrissur', 'transport_hub', 1.6),
    (9, 'Kottayam KSRTC', 9.5916, 76.5222, 'Kottayam', 'transport_hub', 1.5),
    (10, 'Alappuzha Bus Stand', 9.4900, 76.3400, 'Alappuzha', 'tourist', 1.6),
    (11, 'Kollam KSRTC', 8.8800, 76.5900, 'Kollam', 'transport_hub', 1.5),
    (12, 'Palakkad KSRTC', 10.7700, 76.6500, 'Palakkad', 'transport_hub', 1.4),
    (13, 'Kannur City Bus Stand', 11.8700, 75.3500, 'Kannur', 'transport_hub', 1.5),
    (14, 'Edappally Junction', 10.0261, 76.3125, 'Ernakulam', 'commercial', 1.6),
    (15, 'Fort Kochi', 9.9639, 76.2424, 'Ernakulam', 'tourist', 1.5),
    (16, 'Kakkanad InfoPark', 10.0100, 76.3500, 'Ernakulam', 'commercial', 1.4),
    # Adding the 17th stop manually as it was in the original JSON but not in database.py seed
    (17, 'vadagara New bus stand', 11.608495, 75.5917092, 'Kozhikode', 'transport_hub', 2.0)
]

def populate_db():
    print("--- Starting Database Population from JSON (All Stops + Districts + Restore Defaults) ---")
    
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    json_path = os.path.join(project_root, 'bus_stops.json')
    
    if not os.path.exists(json_path):
        print(f"[ERROR] JSON file not found at {json_path}")
        return

    try:
        # Load JSON
        print(f"Reading JSON from {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            stops_data = json.load(f)
            
        total_stops = len(stops_data)
        print(f"Loaded {total_stops} stops from JSON.")
        
        # NOTE: WE DO NOT SCALE DOWN HERE. WE LOAD ALL STOPS.
            
        # ALWAYS Restore original default stops to the list
        print("Restoring original default stops to the list...")
        for stop in DEFAULT_STOPS:
            stop_dict = {
                "bus_stop_id": stop[0],
                "name": stop[1],
                "lat": stop[2],
                "lon": stop[3],
                "district": stop[4],
                "category": stop[5],
                "demand_multiplier": stop[6]
            }
            # Ensure we don't have duplicates by ID (remove if exists)
            stops_data = [s for s in stops_data if s['bus_stop_id'] != stop[0]]
            stops_data.append(stop_dict)
        
        # Prepare data for insertion
        # Schema: bus_stop_id, name, lat, lon, district, category, demand_multiplier
        values = []
        for stop in stops_data:
            lat = stop['lat']
            lon = stop['lon']
            district = get_nearest_district(lat, lon)
            
            # If it's one of the default stops, keep its original district
            # Check if ID is in default IDs
            is_default = any(d[0] == stop['bus_stop_id'] for d in DEFAULT_STOPS)
            if is_default:
                district = stop['district'] # Keep original
            
            stop['district'] = district
            
            values.append((
                stop['bus_stop_id'],
                stop['name'],
                lat,
                lon,
                district,
                stop.get('category', 'regular'),
                stop.get('demand_multiplier', 1.0)
            ))
            
        print(f"Overwriting {json_path} with the final list (including defaults & districts)...")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stops_data, f, indent=2)
        print("[OK] bus_stops.json updated.")
            
        print("Connecting to database...")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("Checking and fixing schema for large IDs...")
                # Fix schema for large IDs
                try:
                    cur.execute("ALTER TABLE bus_stops ALTER COLUMN bus_stop_id TYPE BIGINT;")
                    cur.execute("ALTER TABLE route_history ALTER COLUMN stop_ids TYPE BIGINT[];")
                    cur.execute("ALTER TABLE demand_history ALTER COLUMN stop_id TYPE BIGINT;")
                    conn.commit()
                    print("[OK] Schema updated to support BIGINT IDs.")
                except Exception as e:
                    conn.rollback()
                    print(f"[WARN] Schema update skipped or failed (might already be BIGINT): {e}")

                # Clear ALL data to ensure clean state with defaults
                print("Clearing ALL previous data to restore defaults + random stops...")
                cur.execute("DELETE FROM bus_stops;")
                conn.commit()

                print("Executing bulk insert...")
                
                # Use execute_values for efficiency
                query = '''
                    INSERT INTO bus_stops (bus_stop_id, name, lat, lon, district, category, demand_multiplier)
                    VALUES %s
                    ON CONFLICT (bus_stop_id) DO UPDATE 
                    SET name = EXCLUDED.name,
                        lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon,
                        district = EXCLUDED.district,
                        category = EXCLUDED.category,
                        demand_multiplier = EXCLUDED.demand_multiplier,
                        updated_at = CURRENT_TIMESTAMP
                '''
                
                psycopg2.extras.execute_values(
                    cur,
                    query,
                    values,
                    template='(%s, %s, %s, %s, %s, %s, %s)',
                    page_size=1000
                )
                
                conn.commit()
                print(f"[OK] Successfully inserted/updated {len(values)} records in the database.")
                
                # Verify count
                cur.execute("SELECT COUNT(*) FROM bus_stops")
                count = cur.fetchone()[0]
                print(f"[INFO] Total stops in database now: {count}")

    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    populate_db()
