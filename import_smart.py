
import csv
import json
import os

def smart_import():
    stops = []
    seen_names = set()
    
    # 1. Load "Pre-existing 2000" from Original CSV
    # Assuming bus_stops.csv is the original source
    try:
        with open('bus_stops.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count >= 2000:
                    break
                
                name = row.get('name', '') or row.get('stop_name', '')
                if name and name not in seen_names:
                    # Construct ID (simple incremental)
                    sid = len(stops) + 1
                    
                    stop = {
                        "bus_stop_id": sid,
                        "name": name,
                        "lat": float(row.get('lat', 0) or row.get('latitude', 0)),
                        "lon": float(row.get('lon', 0) or row.get('longitude', 0)),
                        "district": row.get('district', 'Unknown'),
                        "category": "regular",
                        "demand_multiplier": 1.0
                    }
                    stops.append(stop)
                    seen_names.add(name)
                    count += 1
                    
        print(f"Loaded {len(stops)} base stops (limit 2000).")
            
    except Exception as e:
        print(f"Error reading bus_stops.csv: {e}")
        # Fallback: keep existing JSON?
        pass

    # 2. Add Airports from NEW CSV
    try:
        with open('kerala_bus_stops_with_types.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            airport_count = 0
            
            for row in reader:
                name = row.get('name', '')
                # Check for Airport
                if 'airport' in name.lower():
                    if name not in seen_names:
                        sid = len(stops) + 1
                         
                        district = 'Unknown'
                        # CSV does not seem to have 'district' column in preview?
                        # Header: name,bus_type,lat,lon,is_station
                        # No district. We can infer or leave Unknown.
                        
                        stop = {
                            "bus_stop_id": sid,
                            "name": name,
                            "lat": float(row['lat']),
                            "lon": float(row['lon']),
                            "district": "Kerala", # Default
                            "category": "airport",
                            "demand_multiplier": 5.0 
                        }
                        stops.append(stop)
                        seen_names.add(name)
                        airport_count += 1
                        print(f"Added Airport: {name}")
                        
        print(f"Added {airport_count} airports from new CSV.")
        
    except Exception as e:
        print(f"Error reading kerala_bus_stops_with_types.csv: {e}")

    # 3. Save to JSON
    with open('bus_stops.json', 'w', encoding='utf-8') as f:
        json.dump(stops, f, indent=2)
    print(f"Saved {len(stops)} total stops to bus_stops.json")

if __name__ == "__main__":
    smart_import()
