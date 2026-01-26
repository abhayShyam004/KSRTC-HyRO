
import json
import os

def add_airports():
    try:
        path = 'bus_stops.json'
        if not os.path.exists(path):
            print("bus_stops.json not found!")
            return

        with open(path, 'r', encoding='utf-8') as f:
            stops = json.load(f)
            
        print(f"Current stops count: {len(stops)}")
        
        # Max ID logic
        max_id = max([s.get('bus_stop_id', 0) for s in stops]) if stops else 0
        print(f"Max ID: {max_id}")

        # List of missing airports to check
        # Name, District, Lat, Lon
        airports_to_add = [
            ("Cochin International Airport (COK)", "Ernakulam", 10.1518, 76.3930),
            ("Trivandrum International Airport (TRV)", "Thiruvananthapuram", 8.4821, 76.9200),
            ("Calicut International Airport (CCJ)", "Malappuram", 11.1364, 75.9546),
            ("Kannur International Airport (CNN)", "Kannur", 11.9167, 75.5483)
        ]
        
        added_count = 0
        
        for name, district, lat, lon in airports_to_add:
            # Check if exists by name (fuzzy) or coords
            exists = False
            for s in stops:
                if 'airport' in s['name'].lower() and district.lower() in s['district'].lower():
                    print(f"Found existing: {s['name']} in {s['district']}")
                    exists = True
                    break
            
            if not exists:
                max_id += 1
                new_stop = {
                    "bus_stop_id": max_id,
                    "name": name,
                    "lat": lat,
                    "lon": lon,
                    "district": district,
                    "category": "airport",
                    "demand_multiplier": 2.0
                }
                stops.append(new_stop)
                print(f"Added: {name}")
                added_count += 1
                
        if added_count > 0:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(stops, f, indent=2)
            print(f"Successfully added {added_count} airports.")
        else:
            print("All airports already exist.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_airports()
