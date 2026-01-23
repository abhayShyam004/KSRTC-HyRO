
import os
import sys
import random
from datetime import datetime, timedelta

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import get_all_stops, log_demand_batch, init_database
except ImportError:
    print("Database module not found. Run this from the project root.")
    sys.exit(1)

def generate_historical_data(days=30):
    print(f"Generating data for past {days} days...")
    
    # Ensure tables exist
    init_database()
    
    stops = get_all_stops()
    if not stops:
        print("No stops found! Seed the database first.")
        return

    history_data = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date
    while current_date <= end_date:
        dow = current_date.weekday() # 0=Mon, 6=Sun
        is_weekend = dow >= 5
        
        for hour in range(6, 22): # Operates 6 AM to 10 PM mainly
            is_peak = (8 <= hour <= 10) or (17 <= hour <= 19)
            
            for stop in stops:
                # Base Demand
                demand = 5 # Minimum
                
                # Factors
                if is_peak:
                    demand += random.randint(15, 25)
                elif 11 <= hour <= 16: # Mid-day
                    demand += random.randint(5, 10)
                
                # Stop Category Impact
                cat = stop.get('category', 'regular')
                if cat == 'transport_hub':
                    demand *= 2.0
                elif cat == 'commercial':
                    demand *= 1.5
                elif cat == 'airport':
                    demand *= 1.2
                
                # Weekend reduction for commercial/regular, increase for tourist
                if is_weekend:
                    if cat == 'commercial': demand *= 0.6
                    elif cat == 'tourist': demand *= 1.5
                    else: demand *= 0.8
                
                # Random Noise
                demand = int(demand * random.uniform(0.8, 1.2))
                
                # Add to batch
                # (stop_id, timestamp, dow, hour, is_peak, count)
                ts = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                history_data.append((
                    stop['bus_stop_id'],
                    ts,
                    dow,
                    hour,
                    is_peak,
                    max(0, demand)
                ))
        
        current_date += timedelta(days=1)
        
    print(f"Generated {len(history_data)} records. Inserting into DB...")
    
    # Insert in chunks likely? psycopg2 execute_values handles large batches well usually, 
    # but let's chunk it to be safe (e.g. 5000 rows)
    chunk_size = 5000
    for i in range(0, len(history_data), chunk_size):
        chunk = history_data[i:i + chunk_size]
        log_demand_batch(chunk)
        print(f"Inserted batch {i}/{len(history_data)}")
        
    print("Done!")

if __name__ == "__main__":
    generate_historical_data()
