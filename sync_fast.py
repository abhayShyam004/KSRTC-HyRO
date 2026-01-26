
import json
import psycopg2
from psycopg2.extras import execute_values
from src.database import get_db_connection

def sync_fast():
    print("Starting Optimized Sync...")
    try:
        with open('bus_stops.json', 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        print(f"Loaded {len(stops)} stops from JSON.")
        
        # Prepare data for batch insert
        # Columns: bus_stop_id, name, lat, lon, district, category, demand_multiplier
        data = []
        for s in stops:
            cat = s.get('category', 'regular')
            mult = s.get('demand_multiplier', 1.0)
            data.append((
                s['bus_stop_id'], s['name'], s['lat'], s['lon'], 
                s['district'], cat, mult
            ))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Upsert query
                query = """
                    INSERT INTO bus_stops (bus_stop_id, name, lat, lon, district, category, demand_multiplier)
                    VALUES %s
                    ON CONFLICT (bus_stop_id) DO UPDATE 
                    SET name = EXCLUDED.name,
                        lat = EXCLUDED.lat,
                        lon = EXCLUDED.lon,
                        district = EXCLUDED.district,
                        category = EXCLUDED.category,
                        demand_multiplier = EXCLUDED.demand_multiplier
                """
                
                print(f"Executing batch upsert for {len(data)} records...")
                execute_values(cur, query, data)
                conn.commit()
                print("Sync Complete!")
                
                # Update Sequence
                cur.execute("SELECT setval('bus_stops_bus_stop_id_seq', (SELECT MAX(bus_stop_id) FROM bus_stops))")
                conn.commit()

    except Exception as e:
        print(f"Error syncing DB: {e}")

if __name__ == "__main__":
    sync_fast()
