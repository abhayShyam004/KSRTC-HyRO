import pandas as pd
import json
import os
import re
import sys

def log(message):
    with open("import_log.txt", "a", encoding="utf-8") as f:
        f.write(str(message) + "\n")
    print(message)

def get_smart_tag(name):
    """
    Assigns a category and demand multiplier based on keywords in the bus stop name.
    """
    name_lower = str(name).lower()
    
    # 1. Transport Hubs (Highest Demand)
    if any(x in name_lower for x in ['bus stand', 'bus station', 'terminal', 'hub', 'depot', 'ksrtc', 'stand', 'railway', 'metro']):
        return 'transport_hub', 2.0
    
    # 2. Airports
    if 'airport' in name_lower:
        return 'airport', 1.8
    
    # 3. Commercial / City Centers
    if any(x in name_lower for x in ['market', 'mall', 'centre', 'plaza', 'junction', 'town', 'city', 'bank', 'hospital', 'college', 'school']):
        return 'commercial', 1.5
        
    # 4. Tourist Spots
    if any(x in name_lower for x in ['beach', 'temple', 'church', 'fort', 'palace', 'falls', 'dam', 'lake', 'view point', 'resort', 'park', 'museum']):
        return 'tourist', 1.3
        
    # 5. Regular Stops (Default)
    return 'regular', 1.0

def import_bus_stops():
    log("--- Starting Bus Stop Import from CSV ---")
    
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    csv_path = os.path.join(project_root, 'bus_stops.csv')
    json_path = os.path.join(project_root, 'bus_stops.json')
    
    if not os.path.exists(csv_path):
        log(f"❌ Error: CSV file not found at {csv_path}")
        return

    try:
        log(f"Reading CSV from {csv_path}...")
        df = pd.read_csv(csv_path, sep='\t')
        
        log(f"Loaded {len(df)} rows from CSV.")
        
        bus_stops = []
        
        for index, row in df.iterrows():
            try:
                # Extract fields
                stop_id = row['@id']
                lat = row['@lat']
                lon = row['@lon']
                name = row['name']
                
                # Skip if name is NaN or empty
                if pd.isna(name) or str(name).strip() == '':
                    continue
                
                # Smart Tagging
                category, multiplier = get_smart_tag(name)
                
                stop_data = {
                    "bus_stop_id": int(stop_id),
                    "name": str(name).strip(),
                    "lat": float(lat),
                    "lon": float(lon),
                    "district": "Kerala", # Defaulting to Kerala as requested
                    "category": category,
                    "demand_multiplier": multiplier
                }
                
                bus_stops.append(stop_data)
                
            except Exception as e:
                # log(f"⚠️ Skipping row {index}: {e}")
                continue
                
        log(f"Processed {len(bus_stops)} valid bus stops.")
        
        # Save to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(bus_stops, f, indent=2)
            
        log(f"✅ Successfully saved bus stops to {json_path}")
        
        # Print some stats
        stats = pd.DataFrame(bus_stops)['category'].value_counts()
        log("\n--- Category Statistics ---")
        log(stats)
        
    except Exception as e:
        log(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    import_bus_stops()
