
import json
import psycopg2
from src.database import get_db_connection

def fix_coords():
    # Safe Coordinates (Entrance/Main Road)
    # Kannur: Near Mattannur Town / Airport Rd junction
    kannur_new = {"lat": 11.9160, "lon": 75.5680} 
    # Calicut: Just outside airport gate on main road
    calicut_new = {"lat": 11.1390, "lon": 75.9520}
    
    updates = [
        ("Kannur International Airport (CNN)", kannur_new),
        ("Calicut International Airport (CCJ)", calicut_new)
    ]
    
    try:
        # 1. Update DB
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for name, coords in updates:
                    cur.execute("""
                        UPDATE bus_stops 
                        SET lat = %s, lon = %s
                        WHERE name = %s
                    """, (coords['lat'], coords['lon'], name))
                conn.commit()
        print("Database updated.")

        # 2. Update JSON
        path = 'bus_stops.json'
        with open(path, 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        updated = False
        for s in stops:
            if s['name'] == "Kannur International Airport (CNN)":
                s['lat'] = kannur_new['lat']
                s['lon'] = kannur_new['lon']
                updated = True
                print("Updated Kannur JSON")
            elif s['name'] == "Calicut International Airport (CCJ)":
                s['lat'] = calicut_new['lat']
                s['lon'] = calicut_new['lon']
                updated = True
                print("Updated Calicut JSON")
                
        if updated:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(stops, f, indent=2)
            print("bus_stops.json saved.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_coords()
