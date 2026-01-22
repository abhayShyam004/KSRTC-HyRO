# src/data_preprocessing.py

import pandas as pd

def load_data(is_dummy=True, file_path='data/kochi_overpy_bus_data.csv'):
    """
    Loads KSRTC data. If is_dummy=True, it reads from the large generated CSV.
    """
    if is_dummy:
        print(f"Loading large dummy dataset from {file_path}...")
        try:
            df = pd.read_csv(file_path)
            return df
        except FileNotFoundError:
            print(f"❌ Error: Data file not found at {file_path}")
            print("Please run 'python src/generate_large_dataset.py' first to create it.")
            return None
    else:
        # This part will be for the final, real dataset
        raise NotImplementedError("Real data loading is not yet implemented.")

# The rest of the file (preprocess_data function) remains the same

def preprocess_data(df):
    """
    Prepares the data for passenger demand modeling.
    """
    print("Preprocessing passenger demand data...")
    
    # We drop lat/lon here as they are not needed for demand prediction
    X = df.drop(['passenger_count', 'bus_stop_id', 'lat', 'lon'], axis=1)
    y = df['passenger_count']
    
    print("Preprocessing complete.")
    return X, y