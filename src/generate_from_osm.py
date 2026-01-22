# src/generate_from_osm.py

import pandas as pd
import random
import os
import overpy
import time

def generate_dataset_from_osm(num_records=25000):
    """
    Downloads real bus stop locations for Kochi using the Overpass API (via overpy)
    and simulates passenger data to create the final dataset.
    """
    print("--- Querying OpenStreetMap for real bus stop locations in Kochi ---")
    
    # 1. Query the Overpass API for bus stops in the Kochi area
    api = overpy.Overpass()
    
    # Define a bounding box for the greater Kochi area
    # (South, West, North, East) -> (lat_min, lon_min, lat_max, lon_max)
    kochi_bbox = [9.85, 76.20, 10.15, 76.45]
    
    query = f"""
        [out:json];
        node
          ["highway"="bus_stop"]
          ({kochi_bbox[0]},{kochi_bbox[1]},{kochi_bbox[2]},{kochi_bbox[3]});
        out body;
    """
    
    try:
        result = api.query(query)
        stops_data = result.nodes
        print(f"✅ Successfully downloaded {len(stops_data)} real bus stops in/around Kochi.")
    except Exception as e:
        print(f"❌ Error: Could not download data from Overpass API. {e}")
        return

    # Extract data into a pandas DataFrame
    stops_list = [{'bus_stop_id': node.id, 'lat': float(node.lat), 'lon': float(node.lon)} for node in stops_data]
    stops_df = pd.DataFrame(stops_list)

    # 2. Generate trip records
    records = []
    if len(stops_df) > 0:
        for _ in range(num_records):
            hour = random.randint(5, 22)
            day = random.randint(0, 6)
            is_peak = 1 if (8 <= hour <= 10) or (17 <= hour <= 19) else 0
            
            random_stop_id = random.choice(stops_df['bus_stop_id'])
            
            passengers = random.randint(5, 25)
            if is_peak:
                passengers += random.randint(10, 40)
            
            records.append({
                'hour_of_day': hour,
                'day_of_week': day,
                'is_peak_hour': is_peak,
                'bus_stop_id': random_stop_id,
                'passenger_count': passengers
            })

    records_df = pd.DataFrame(records)
    
    # 3. Merge and Save
    full_df = pd.merge(records_df, stops_df, on='bus_stop_id')
    
    output_dir = 'data'
    file_path = os.path.join(output_dir, 'kochi_overpy_bus_data.csv')
    full_df.to_csv(file_path, index=False)
    print(f"✅ Final dataset saved to {file_path}")

if __name__ == "__main__":
    generate_dataset_from_osm()