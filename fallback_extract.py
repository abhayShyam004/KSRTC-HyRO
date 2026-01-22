import os
import json
import subprocess
import sys

def create_dummy_data():
    print(" Creating DUMMY bus_stops.json...")
    stops = [
        {"bus_stop_id": 1, "name": "Aluva Stand", "lat": 10.10, "lon": 76.35},
        {"bus_stop_id": 2, "name": "Edappally", "lat": 10.02, "lon": 76.30},
        {"bus_stop_id": 3, "name": "Kaloor", "lat": 9.99, "lon": 76.29},
        {"bus_stop_id": 4, "name": "Vyttila Hub", "lat": 9.96, "lon": 76.32},
        {"bus_stop_id": 5, "name": "Fort Kochi", "lat": 9.96, "lon": 76.24}
    ]
    with open('bus_stops.json', 'w') as f:
        json.dump(stops, f, indent=2)
    print("Dummy data created.")

pbf_path = 'osrm_data/kerala-latest.osm.pbf'

if not os.path.exists(pbf_path):
    print(f"PBF file {pbf_path} not found!")
    create_dummy_data()
    sys.exit(0)

print(f"PBF file found. Size: {os.path.getsize(pbf_path)} bytes.")

try:
    print("Running extract_bus_stops.py...")
    subprocess.run(['python', 'src/extract_bus_stops.py'], check=True, timeout=60)
    if os.path.exists('bus_stops.json'):
        print("Success! bus_stops.json created.")
    else:
        print("Script finished but no JSON file found.")
        create_dummy_data()
except Exception as e:
    print(f"Extraction failed: {e}")
    create_dummy_data()
