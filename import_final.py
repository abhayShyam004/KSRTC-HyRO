
import csv
import json
import os

def final_import():
    status = []
    status.append("STARTING IMPORT")
    
    stops = []
    seen_names = set()
    
    # 1. Load "Pre-existing 2000" from Original CSV
    try:
        if os.path.exists('bus_stops.csv'):
            with open('bus_stops.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    if count >= 2000:
                        break
                    
                    name = row.get('name', '') or row.get('stop_name', '')
                    if name and name not in seen_names:
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
            status.append(f"Loaded {len(stops)} base stops from bus_stops.csv (Limit 2000)")
        else:
            status.append("ERROR: bus_stops.csv not found!")
            
    except Exception as e:
        status.append(f"ERROR reading bus_stops.csv: {e}")

    # 2. Add Airports from NEW CSV
    key_file = 'kerala_bus_stops_with_types.csv'
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                airport_count = 0
                
                for row in reader:
                    name = row.get('name', '')
                    if 'airport' in name.lower():
                        if name not in seen_names:
                            sid = len(stops) + 1
                            
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
                            
            status.append(f"Successfully added {airport_count} airports from {key_file}")
        else:
            status.append(f"ERROR: {key_file} not found!")
        
    except Exception as e:
        status.append(f"ERROR reading {key_file}: {e}")

    # 3. Save to JSON
    try:
        with open('bus_stops.json', 'w', encoding='utf-8') as f:
            json.dump(stops, f, indent=2)
        status.append(f"SAVED {len(stops)} total stops to bus_stops.json")
    except Exception as e:
        status.append(f"ERROR writing JSON: {e}")
        
    with open('import_status.txt', 'w') as f:
        f.write('\n'.join(status))

if __name__ == "__main__":
    final_import()
