
import os
import sys
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import get_training_data, get_all_stops
except ImportError:
    print("Database module not found. Run this from the project root.")
    sys.exit(1)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'passenger_demand_model.pkl')

def train_model():
    print("--- Starting Model Training ---")
    
    # 1. Fetch Data
    raw_data = get_training_data()
    stops = get_all_stops()
    
    if not raw_data:
        print("[ERROR] No training data found in 'demand_history'.")
        print("Run 'python src/create_dummy_data.py' to generate initial dataset.")
        return False
        
    print(f"[INFO] Fetched {len(raw_data)} training records.")

    # 2. Data Preprocessing
    df = pd.DataFrame(raw_data)
    
    # Stop Multiplier Mapping
    stop_mult = {s['bus_stop_id']: float(s.get('demand_multiplier', 1.0)) for s in stops}
    
    # Normalize Target: We want base_demand = actual / multiplier
    # This removes the bias of the specific stop, allowing the model to learn General Time Patterns
    def normalize_demand(row):
        mult = stop_mult.get(row['stop_id'], 1.0)
        return row['passenger_count'] / mult if mult > 0 else 0

    df['base_demand'] = df.apply(normalize_demand, axis=1)
    
    # Features & Target
    # We drop stop_id, passenger_count. We keep time features.
    X = df[['hour_of_day', 'day_of_week', 'is_peak']]
    y = df['base_demand']
    
    # 3. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Model Training
    print("[INFO] Training RandomForestRegressor...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. Evaluation
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"[RESULT] Model Performance:")
    print(f"  - MAE: {mae:.2f} (Average error in base passengers)")
    print(f"  - R2 Score: {r2:.2f}")
    
    # 6. Save Model
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        
    joblib.dump(model, MODEL_PATH)
    print(f"[SUCCESS] Model saved to {MODEL_PATH}")
    return True

if __name__ == "__main__":
    train_model()
