
import json
import psycopg2
from src.database import get_db_connection

def add_trivandrum():
    stop = {
        "bus_stop_id": 9998, # Assign a safe high ID
        "name": "Thiruvananthapuram International Airport (TRV)",
        "lat": 8.4824, 
        "lon": 76.9207,
        "district": "Thiruvananthapuram",
        "category": "airport",
        "demand_multiplier": 5.0
    }
    
    try:
        # Check max ID
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(bus_stop_id) FROM bus_stops")
                max_id = cur.fetchone()[0]
                # Ensure we don't conflict with Calicut (which might be max)
                stop['bus_stop_id'] = max_id + 1
                
                # Insert
                cur.execute("""
                    INSERT INTO bus_stops (bus_stop_id, name, lat, lon, district, category, demand_multiplier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (stop['bus_stop_id'], stop['name'], stop['lat'], stop['lon'], stop['district'], stop['category'], stop['demand_multiplier']))
                conn.commit()
                print(f"Added {stop['name']} to DB with ID {stop['bus_stop_id']}")
                
        # Update JSON
        with open('bus_stops.json', 'r', encoding='utf-8') as f:
            stops = json.load(f)
            stops.append(stop)
            
        with open('bus_stops.json', 'w', encoding='utf-8') as f:
            json.dump(stops, f, indent=2)
        print("Updated JSON.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_trivandrum()
