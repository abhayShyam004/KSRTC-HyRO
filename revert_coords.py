
import json
import psycopg2
from src.database import get_db_connection

def revert_coords():
    # Original Airport Coordinates
    kannur_orig = {"lat": 11.9167, "lon": 75.5483} 
    calicut_orig = {"lat": 11.1364, "lon": 75.9546}
    
    updates = [
        ("Kannur International Airport (CNN)", kannur_orig),
        ("Calicut International Airport (CCJ)", calicut_orig)
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
        print("Database reverted to original coordinates.")

        # 2. Update JSON
        path = 'bus_stops.json'
        with open(path, 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        updated = False
        for s in stops:
            if s['name'] == "Kannur International Airport (CNN)":
                s['lat'] = kannur_orig['lat']
                s['lon'] = kannur_orig['lon']
                updated = True
            elif s['name'] == "Calicut International Airport (CCJ)":
                s['lat'] = calicut_orig['lat']
                s['lon'] = calicut_orig['lon']
                updated = True
                
        if updated:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(stops, f, indent=2)
            print("bus_stops.json reverted.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    revert_coords()
