# src/generate_kochi_dataset.py

import pandas as pd
import numpy as np
import random
import os

def generate_kochi_dataset(num_stops=750, num_records=20000):
    """
    Generates a realistic dummy dataset for Kochi, ensuring stops are on plausible land corridors.
    """
    print(f"--- Generating realistic Kochi dataset with {num_stops} stops ---")

    # Define real-world hubs and simulated road corridors (vectors) radiating from them.
    # A vector of (0.01, 0.005) means stops will be generated along a line going north-east.
    major_hubs = {
        'Vyttila Hub': {'lat': 9.9676, 'lon': 76.3148, 'zone': 'Transport Hub', 'vectors': [(0.01, 0.01), (-0.01, 0.005), (0.005, -0.01)]},
        'Kaloor': {'lat': 9.9958, 'lon': 76.2934, 'zone': 'Commercial', 'vectors': [(0.01, 0.00), (-0.01, 0.00), (0.00, 0.015)]},
        'Fort Kochi': {'lat': 9.9658, 'lon': 76.2416, 'zone': 'Tourist', 'vectors': [(0.00, 0.01), (0.005, 0.005)]}, # Vectors point east and north-east, away from the sea
        'Aluva': {'lat': 10.1084, 'lon': 76.3533, 'zone': 'Residential', 'vectors': [(0.00, -0.01), (-0.01, -0.005), (0.01, 0.00)]},
        'MG Road': {'lat': 9.9790, 'lon': 76.2823, 'zone': 'Commercial', 'vectors': [(0.01, 0.00), (-0.01, 0.00)]},
        'Thripunithura': {'lat': 9.9540, 'lon': 76.3473, 'zone': 'Residential', 'vectors': [(0.00, -0.01), (0.01, 0.005)]}
    }
    
    stops = []
    stop_id_counter = 4000
    
    stops_per_hub = num_stops // len(major_hubs)
    
    for hub_name, details in major_hubs.items():
        for _ in range(stops_per_hub):
            # Choose a random road corridor for this stop
            vec = random.choice(details['vectors'])
            # Choose a random distance along the corridor
            dist = random.uniform(0.1, 1.0)
            
            # Calculate base position along the corridor
            stop_lat = details['lat'] + vec[0] * dist * 3 # Amplify vector
            stop_lon = details['lon'] + vec[1] * dist * 3 # Amplify vector
            
            # Add a small amount of perpendicular "jitter" to simulate stops on either side of the road
            stop_lat += np.random.normal(0, 0.001)
            stop_lon += np.random.normal(0, 0.001)
            
            stops.append({
                'bus_stop_id': stop_id_counter, 
                'lat': stop_lat, 
                'lon': stop_lon,
                'zone': details['zone']
            })
            stop_id_counter += 1
    
    stops_df = pd.DataFrame(stops)

    # (The rest of the script for generating records and saving the file is the same)
    records = []
    for _ in range(num_records):
        hour = random.randint(5, 22)
        day = random.randint(0, 6)
        is_peak = 1 if (8 <= hour <= 10) or (17 <= hour <= 19) else 0
        random_stop = stops_df.sample(1).iloc[0]
        zone = random_stop['zone']
        passengers = random.randint(5, 15)
        if zone == 'Transport Hub': passengers += random.randint(20, 60)
        elif zone == 'Commercial' and is_peak: passengers += random.randint(30, 70)
        elif zone == 'Tourist' and (10 <= hour <= 16): passengers += random.randint(15, 40)
        elif zone == 'Residential' and (is_peak or day > 4): passengers += random.randint(10, 30)
        records.append({'hour_of_day': hour, 'day_of_week': day, 'is_peak_hour': is_peak, 'bus_stop_id': random_stop['bus_stop_id'], 'passenger_count': passengers})

    records_df = pd.DataFrame(records)
    full_df = pd.merge(records_df, stops_df, on='bus_stop_id')
    
    output_dir = 'data'
    file_path = os.path.join(output_dir, 'kochi_real_scale_data_v2.csv')
    full_df.to_csv(file_path, index=False)
    print(f"✅ Geographically corrected Kochi dataset saved to {file_path}")

if __name__ == "__main__":
    generate_kochi_dataset()