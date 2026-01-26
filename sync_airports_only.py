
import json
import psycopg2
from src.database import get_db_connection

def sync_airports():
    try:
        # 1. Load JSON (Source of Truth)
        with open('bus_stops.json', 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        # Filter for airports
        airports = [s for s in stops if s.get('category') == 'airport']
        print(f"Found {len(airports)} airports in JSON to sync.")
        
        if not airports:
            print("No airports found in JSON!")
            return

        # 2. Sync to DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                synced_count = 0
                for s in airports:
                    # Upsert Logic
                    cur.execute("""
                        INSERT INTO bus_stops (bus_stop_id, name, lat, lon, district, category, demand_multiplier)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (bus_stop_id) DO UPDATE 
                        SET name = EXCLUDED.name,
                            lat = EXCLUDED.lat,
                            lon = EXCLUDED.lon,
                            district = EXCLUDED.district,
                            category = EXCLUDED.category,
                            demand_multiplier = EXCLUDED.demand_multiplier
                    """, (s['bus_stop_id'], s['name'], s['lat'], s['lon'], s['district'], s['category'], s.get('demand_multiplier', 5.0)))
                    synced_count += 1
                    
                conn.commit()
                status = f"Successfully synced {synced_count} airports to NeonDB."
                
                # Update Sequence just in case
                cur.execute("SELECT setval('bus_stops_bus_stop_id_seq', (SELECT MAX(bus_stop_id) FROM bus_stops))")
                conn.commit()

    except Exception as e:
        status = f"Error syncing DB: {e}"
        
    with open('sync_status.txt', 'w') as f:
        f.write(status)

if __name__ == "__main__":
    sync_airports()
