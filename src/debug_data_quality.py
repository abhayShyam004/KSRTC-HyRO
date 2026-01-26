
import os
import sys
import pandas as pd
import numpy as np
from database import get_db_connection, get_training_data
from ml_utils import TargetEncoder
from ml_config import SMOOTHING_ALPHA

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def inspect_data():
    with open('debug_report.txt', 'w') as f:
        f.write("--- DATA QUALITY INSPECTION ---\n")
        
        # 1. Row Count
        raw_data = get_training_data()
        row_count = len(raw_data)
        f.write(f"[METRIC] Total Rows: {row_count}\n")
        
        if row_count < 500:
            f.write("[FAIL] Row count < 500. Data starvation.\n")
            return

        df = pd.DataFrame(raw_data)
        
        # 2. Distribution Sanity
        mean_demand = df['passenger_count'].mean()
        std_demand = df['passenger_count'].std()
        f.write(f"[METRIC] Global Mean: {mean_demand:.2f}\n")
        f.write(f"[METRIC] Global Std Dev: {std_demand:.2f}\n")
        
        if std_demand < (0.2 * mean_demand):
             f.write("[WARN] Low Variance. Signal might be weak.\n")
        
        # 3. Per-Stop Counts
        stop_counts = df['stop_id'].value_counts()
        f.write(f"[METRIC] Unique Stops: {len(stop_counts)}\n")
        f.write(f"[METRIC] Median Samples per Stop: {stop_counts.median()}\n")
        f.write(f"[METRIC] Min Samples per Stop: {stop_counts.min()}\n")
        
        if stop_counts.median() < 20:
            f.write("[WARN] Median samples < 20. Target Encoding will collapse to global mean.\n")
            
        # 4. Encoding Separation Check
        f.write(f"\n[CHECK] Target Encoding Separation (Alpha={SMOOTHING_ALPHA})\n")
        encoder = TargetEncoder(cols=['stop_id'], alpha=SMOOTHING_ALPHA)
        # Fit on ALL data just to see the spread
        encoder.fit(df[['stop_id']], df['passenger_count'])
        
        # Get the learned map
        learned_map = encoder.maps['stop_id']
        
        # Sort by value
        sorted_stops = sorted(learned_map.items(), key=lambda x: x[1], reverse=True)
        
        f.write("Top 5 Highest Demand Stops (Encoded):\n")
        for stop, val in sorted_stops[:5]:
            f.write(f"  Stop {stop}: {val:.2f}\n")
            
        f.write("Bottom 5 Lowest Demand Stops (Encoded):\n")
        for stop, val in sorted_stops[-5:]:
            f.write(f"  Stop {stop}: {val:.2f}\n")
            
        # Check spread
        max_enc = sorted_stops[0][1]
        min_enc = sorted_stops[-1][1]
        spread = max_enc - min_enc
        f.write(f"[METRIC] Encoding Spread: {spread:.2f}\n")
        
        if spread < 1.0:
            f.write("[FAIL] Encoding collapsed. All stops look the same to the model.\n")
        else:
            f.write("[PASS] Stops are distinguishable.\n")

if __name__ == "__main__":
    inspect_data()
