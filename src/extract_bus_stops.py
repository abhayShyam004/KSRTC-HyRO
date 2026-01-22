import osmium
import pandas as pd
import json
import os

class BusStopHandler(osmium.SimpleHandler):
    def __init__(self):
        super(BusStopHandler, self).__init__()
        self.bus_stops = []

    def node(self, n):
        # We only want nodes that are tagged as bus stops and have a name
        if 'highway' in n.tags and n.tags['highway'] == 'bus_stop' and 'name' in n.tags:
            self.bus_stops.append({
                'bus_stop_id': n.id,
                'name': n.tags['name'],
                'lat': n.location.lat,
                'lon': n.location.lon
            })

def extract_named_bus_stops():
    """
    Reads the OSM PBF file and extracts all named bus stops, removing duplicates.
    """
    print("--- Reading OSM map file to extract unique named bus stops ---")
    
    pbf_path = os.path.join('osrm_data', 'kerala-latest.osm.pbf')
    handler = BusStopHandler()
    
    try:
        handler.apply_file(pbf_path)
    except FileNotFoundError:
        print(f"❌ Error: {pbf_path} not found. Please ensure the map file is in the 'osrm_data' folder.")
        return

    if not handler.bus_stops:
        print("⚠️  No bus stops found in the PBF file.")
        return

    stops_df = pd.DataFrame(handler.bus_stops)
    print(f"Found {len(stops_df)} total bus stop entries.")

    # --- THIS IS THE FIX: Remove duplicates based on the bus stop name ---
    stops_df.drop_duplicates(subset=['name'], keep='first', inplace=True)
    print(f"✅ Filtered down to {len(stops_df)} unique named bus stops.")

    # Prepare the final JSON file for the web app
    output_dir = os.path.dirname(os.path.abspath(__file__)) # src folder
    root_dir = os.path.dirname(output_dir) # Project root
    output_path = os.path.join(root_dir, 'bus_stops.json')

    # Convert to JSON and save
    stops_list = stops_df.to_dict(orient='records')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stops_list, f, indent=2)

    print(f"✅ Unique bus stops list successfully saved to {output_path}")

if __name__ == "__main__":
    extract_named_bus_stops()
