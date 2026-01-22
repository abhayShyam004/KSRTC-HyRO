# src/generate_large_dataset.py

import pandas as pd
import numpy as np
import random

def generate_large_dataset(num_stops=1000, num_records=10000, file_path='data/ksrtc_large_dummy_data.csv'):
    """
    Generates a large, realistic dummy dataset for KSRTC and saves it as a CSV.
    """
    print(f"--- Generating large dataset with {num_stops} stops and {num_records} records ---")

    # 1. Generate realistic bus stop locations clustered around major Kerala cities
    city_centers = {
        'Thiruvananthapuram': (8.5241, 76.9366),
        'Kochi': (9.9312, 76.2673),
        'Kozhikode': (11.2588, 75.7804),
        'Thrissur': (10.5276, 76.2144)
    }
    
    stops = []
    for i in range(num_stops):
        city_name, (lat, lon) = random.choice(list(city_centers.items()))
        # Add random noise to create clusters
        stop_lat = lat + np.random.normal(0, 0.05)
        stop_lon = lon + np.random.normal(0, 0.05)
        stops.append({'bus_stop_id': 1000 + i, 'lat': stop_lat, 'lon': stop_lon})
    
    stops_df = pd.DataFrame(stops)

    # 2. Generate trip records
    records = []
    for _ in range(num_records):
        hour = random.randint(5, 22)
        day = random.randint(0, 6) # 0=Sunday
        is_peak = 1 if (7 <= hour <= 10) or (16 <= hour <= 19) else 0
        
        # Base passenger count
        passengers = random.randint(5, 20)
        if is_peak:
            passengers += random.randint(20, 50) # Peak hour rush
        if day in [5, 6]: # Friday/Saturday
            passengers += random.randint(5, 15)
        
        record = {
            'hour_of_day': hour,
            'day_of_week': day,
            'is_peak_hour': is_peak,
            'bus_stop_id': random.choice(stops_df['bus_stop_id']),
            'passenger_count': passengers
        }
        records.append(record)

    records_df = pd.DataFrame(records)
    
    # 3. Merge and Save
    full_df = pd.merge(records_df, stops_df, on='bus_stop_id')
    
    # Reorder columns for clarity
    column_order = ['bus_stop_id', 'lat', 'lon', 'hour_of_day', 'day_of_week', 'is_peak_hour', 'passenger_count']
    full_df = full_df[column_order]

    full_df.to_csv(file_path, index=False)
    print(f"✅ Dataset successfully saved to {file_path}")

if __name__ == "__main__":
    # Make sure you have a /data folder in your project root
    generate_large_dataset()