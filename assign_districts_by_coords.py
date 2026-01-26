
import json
import math
from src.database import get_db_connection

def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371 # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def assign_districts():
    try:
        # Load all stops
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get everything
                cur.execute("SELECT bus_stop_id, name, lat, lon, district FROM bus_stops")
                rows = cur.fetchall()
                
        stops = []
        for r in rows:
            stops.append({
                "id": r[0], "name": r[1], 
                "lat": float(r[2]), "lon": float(r[3]), 
                "district": r[4]
            })
            
        # Separate into References (Valid) and Targets (Invalid)
        valid_districts = set([s['district'] for s in stops if s['district'] and s['district'] not in ['Kerala', 'Unknown', '']])
        print(f"Valid districts found: {len(valid_districts)}")
        
        references = [s for s in stops if s['district'] in valid_districts]
        targets = [s for s in stops if s['district'] not in valid_districts]
        
        print(f"Stops with valid districts: {len(references)}")
        print(f"Stops to fix (Kerala/Unknown): {len(targets)}")
        
        if not targets:
            print("No stops to fix.")
            return

        updates = []
        for t in targets:
            best_dist = float('inf')
            best_district = None
            
            # Find nearest neighbor
            # Optimization: could use KDTree but simple loop is fine for 2000 stops
            for r in references:
                dist = calculate_distance(t['lat'], t['lon'], r['lat'], r['lon'])
                if dist < best_dist:
                    best_dist = dist
                    best_district = r['district']
            
            if best_district:
                updates.append((best_district, t['id'], t['name']))
                # print(f"Assigning {t['name']} -> {best_district} (Dist: {best_dist:.2f}km)")

        # Apply updates
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Update DB
                for district, bid, name in updates:
                    cur.execute("UPDATE bus_stops SET district = %s WHERE bus_stop_id = %s", (district, bid))
                conn.commit()
                print(f"Updated {len(updates)} stops in Database.")
                
        # Sync JSON from DB state (to keep them in sync)
        # Or just update JSON similarly?
        # Let's update JSON for consistency.
        with open('bus_stops.json', 'r', encoding='utf-8') as f:
            j_stops = json.load(f)
            
        j_updates = 0
        update_map = {u[1]: u[0] for u in updates} # ID -> New District
        
        for s in j_stops:
            if s['bus_stop_id'] in update_map:
                s['district'] = update_map[s['bus_stop_id']]
                j_updates += 1
                
        with open('bus_stops.json', 'w', encoding='utf-8') as f:
            json.dump(j_stops, f, indent=2)
            
        status = f"Updated {len(updates)} stops in Database and JSON based on coordinate proximity."

    except Exception as e:
        status = f"Error: {e}"
        
    with open('assign_status.txt', 'w') as f:
        f.write(status)

if __name__ == "__main__":
    assign_districts()
