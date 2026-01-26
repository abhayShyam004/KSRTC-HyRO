
import sys
import os
from database import get_db_connection
import json
import decimal
from collections import Counter
from psycopg2.extras import execute_batch

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def assign_districts():
    print("Connecting to DB...")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all stops
            cur.execute("SELECT bus_stop_id, name, lat, lon FROM bus_stops")
            stops = cur.fetchall()
            print(f"Fetched {len(stops)} stops. Calculating districts...")
            
            updates = []
            
            for stop in stops:
                sid, name, lat, lon = stop
                lat = float(lat)
                lon = float(lon)
                
                district = 'Kerala' # Default
                
                # Approximate Latitude heuristics for Kerala districts (South to North)
                if lat < 8.7:
                     district = 'Thiruvananthapuram'
                elif 8.7 <= lat < 9.15:
                     district = 'Kollam'
                elif 9.15 <= lat < 9.5:
                     # Alappuzha (Coastal) vs Pathanamthitta (Inland)
                     if lon < 76.55:
                         district = 'Alappuzha'
                     else:
                         district = 'Pathanamthitta'
                elif 9.5 <= lat < 9.9:
                     # Alappuzha (North) vs Kottayam vs Idukki
                     if lon < 76.45:
                         district = 'Alappuzha'
                     elif lon > 76.9:
                          district = 'Idukki'
                     else:
                          district = 'Kottayam'
                elif 9.9 <= lat < 10.35:
                     if lon > 76.85:
                         district = 'Idukki'
                     else:
                         district = 'Ernakulam'
                elif 10.35 <= lat < 10.75:
                     district = 'Thrissur'
                elif 10.75 <= lat < 11.25:
                     # Palakkad (Gap/Inland) vs Malappuram
                     # Palakkad lies mostly East
                     if lon > 76.4:
                         district = 'Palakkad'
                     else:
                         district = 'Malappuram'
                elif 11.25 <= lat < 11.75:
                     if lon > 76.0 and lat > 11.5:
                          district = 'Wayanad'
                     else:
                          district = 'Kozhikode'
                elif 11.75 <= lat < 12.15:
                     if lon > 75.8: # Wayanad extends north-east
                          district = 'Wayanad'
                     else:
                          district = 'Kannur'
                elif lat >= 12.15:
                     district = 'Kasaragod'
                     
                updates.append((district, sid))
                
            # Batch Update
            print("Updating database...")
            
            query = "UPDATE bus_stops SET district = %s WHERE bus_stop_id = %s"
            execute_batch(cur, query, updates)
            conn.commit()
            
            # --- SYNC JSON FILE ---
            print("Syncing bus_stops.json...")
            cur.execute("SELECT * FROM bus_stops")
            columns = [desc[0] for desc in cur.description]
            all_stops = [dict(zip(columns, row)) for row in cur.fetchall()]
            
            def default_serializer(obj):
                import datetime
                if isinstance(obj, decimal.Decimal):
                    return float(obj)
                if isinstance(obj, (datetime.date, datetime.datetime)):
                    return obj.isoformat()
                return str(obj)
                
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bus_stops.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(all_stops, f, indent=2, default=default_serializer)
            
            print(f"Success! Database and JSON updated. ({len(all_stops)} stops)")
            
            # Stats
            dists = Counter(u[0] for u in updates)
            print("\nDistrict Distribution:")
            for d, c in dists.most_common():
                print(f"  {d}: {c}")

if __name__ == "__main__":
    assign_districts()
