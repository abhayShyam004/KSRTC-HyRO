
import csv
import os
import sys

# Ensure src is in path to import database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bus_stops.csv')

def categorize_stop(name, bus_type, is_station_str):
    name_lower = name.lower()
    bus_type_lower = bus_type.lower()
    is_station = is_station_str.strip().lower() == 'true'

    # Priority 1: Airports
    if 'airport' in name_lower:
        return 'airport', 2.5

    # Priority 2: Transport Hubs (Major Stations)
    # If explicitly marked as station OR contains key terms with KSRTC
    if is_station:
        return 'transport_hub', 2.0
    
    if 'ksrtc' in bus_type_lower and any(x in name_lower for x in ['stand', 'station', 'depot', 'terminal']):
        return 'transport_hub', 2.0

    # Priority 3: Commercial / Municipal
    if 'municipal' in bus_type_lower or 'private' in bus_type_lower:
        return 'commercial', 1.5

    # Priority 4: Tourist (Simple keyword check)
    if any(x in name_lower for x in ['beach', 'dam', 'falls', 'view point', 'resort', 'tourist']):
        return 'tourist', 1.8

    # Default
    return 'regular', 1.0

def log(msg):
    with open('import_log.txt', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)

def import_stops():
    try:
        if os.path.exists('import_log.txt'):
             os.remove('import_log.txt')
    except: pass
    
    log(f"Starting import from {CSV_PATH}...")
    
    stops_to_insert = []
    
    try:
        if not os.path.exists(CSV_PATH):
            log(f"CRITICAL ERROR: File not found at {CSV_PATH}")
            # Try looking in current dir
            alt_path = 'bus_stops.csv'
            if os.path.exists(alt_path):
                log(f"Found in current dir: {alt_path}")
                # Update global for reader
            else:
                return

        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                name = row['name']
                bus_type = row['bus_type']
                lat = float(row['lat'])
                lon = float(row['lon'])
                is_station = row['is_station']
                
                category, multiplier = categorize_stop(name, bus_type, is_station)
                district = 'Kerala'
                
                stops_to_insert.append((name, lat, lon, district, category, multiplier))
                
        log(f"Parsed {len(stops_to_insert)} stops.")
        
        if not stops_to_insert:
            log("No stops found in CSV.")
            return

        log("Connecting to DB...")
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                log("Truncating table...")
                cur.execute("TRUNCATE TABLE bus_stops RESTART IDENTITY CASCADE;")
                
                log("Inserting rows...")
                # Batch insert
                # psycopg2.extras.execute_values is cleaner but direct mogrify works too
                args_str = ','.join(cur.mogrify("(%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in stops_to_insert)
                cur.execute("INSERT INTO bus_stops (name, lat, lon, district, category, demand_multiplier) VALUES " + args_str)
                
                conn.commit()
                log("Success! Database populated.")
                
                # Print stats
                from collections import Counter
                cats = Counter(s[4] for s in stops_to_insert)
                log("Category Distribution:")
                for c, count in cats.items():
                    log(f"  {c}: {count}")

    except Exception as e:
        log(f"Error parsing/inserting: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    import_stops()
