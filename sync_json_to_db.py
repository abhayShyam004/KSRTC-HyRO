
import json
import psycopg2
from src.database import get_db_connection

def sync_db():
    try:
        # 1. Load JSON (Source of Truth)
        with open('bus_stops.json', 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        print(f"Loaded {len(stops)} stops from JSON.")
        
        # 2. Sync to DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Count before
                cur.execute("SELECT COUNT(*) FROM bus_stops")
                before_count = cur.fetchone()[0]
                print(f"DB Count Before: {before_count}")
                
                updated = 0
                inserted = 0
                
                for s in stops:
                    # Check if exists
                    cur.execute("SELECT bus_stop_id FROM bus_stops WHERE bus_stop_id = %s", (s['bus_stop_id'],))
                    exists = cur.fetchone()
                    
                    if exists:
                        # Update
                        cur.execute("""
                            UPDATE bus_stops 
                            SET name = %s, lat = %s, lon = %s, district = %s, category = %s, demand_multiplier = %s
                            WHERE bus_stop_id = %s
                        """, (s['name'], s['lat'], s['lon'], s['district'], s.get('category', 'regular'), s.get('demand_multiplier', 1.0), s['bus_stop_id']))
                        updated += 1
                    else:
                        # Insert
                        # Note: We force the ID to match JSON
                        cur.execute("""
                            INSERT INTO bus_stops (bus_stop_id, name, lat, lon, district, category, demand_multiplier)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (s['bus_stop_id'], s['name'], s['lat'], s['lon'], s['district'], s.get('category', 'regular'), s.get('demand_multiplier', 1.0)))
                        inserted += 1
                        
                conn.commit()
                print(f"Sync Complete. Inserted: {inserted}, Updated: {updated}")
                
                # Update Sequence
                cur.execute("SELECT setval('bus_stops_bus_stop_id_seq', (SELECT MAX(bus_stop_id) FROM bus_stops))")
                conn.commit()

    except Exception as e:
        print(f"Error syncing DB: {e}")

if __name__ == "__main__":
    sync_db()
