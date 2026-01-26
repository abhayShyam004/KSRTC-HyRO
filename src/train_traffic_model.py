
import os
import sys
import pandas as pd
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from psycopg2.extras import RealDictCursor

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection
from ml_utils import TargetEncoder, AtomicModelSaver
from ml_config import TRAFFIC_FREQ_CUTOFF, SMOOTHING_ALPHA

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'traffic_model.pkl')

def get_traffic_data():
    """Fetch route history for training"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # We want to learn: Given Route + Distance + Time -> What is Duration?
            # We assume route_history has start/end stops or we infer them (simplification for now: dummy 'route_id' logic)
            # Since current schema might not have start_stop_id/end_stop_id, we'll try to use 'stop_ids' array if available
            # or just rely on distance for generic model if route info missing.
            
            # Checking if columns exist (robustness)
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'route_history'")
            cols = [row['column_name'] for row in cur.fetchall()]
            
            if 'stop_ids' in cols:
                query = '''
                    SELECT distance_km, duration_min, created_at, stop_ids
                    FROM route_history
                    WHERE duration_min > 0 AND distance_km > 0
                '''
            else:
                # If no stop_ids, we can't do route signatures, fallback to generic
                query = '''
                    SELECT distance_km, duration_min, created_at, NULL as stop_ids
                    FROM route_history
                    WHERE duration_min > 0 AND distance_km > 0
                '''
            
            cur.execute(query)
            return cur.fetchall()

def train_traffic_model():
    print("--- Starting Traffic Model Training (V3: Route Aware) ---")
    
    # 1. Fetch Data
    raw_data = get_traffic_data()
    
    if not raw_data:
        print("[WARN] No traffic data found in 'route_history'.")
        return False
        
    print(f"[INFO] Fetched {len(raw_data)} route records.")
    df = pd.DataFrame(raw_data)
    
    # 2. Feature Engineering
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['hour_of_day'] = df['created_at'].dt.hour
    df['day_of_week'] = df['created_at'].dt.dayofweek
    df['is_peak'] = df['hour_of_day'].apply(lambda h: 1 if (8 <= h <= 10) or (17 <= h <= 19) else 0)
    
    # Route Signature Generation
    def get_route_sig(row):
        if row.get('stop_ids') and len(row['stop_ids']) >= 2:
            try:
                # Extract Start-End (simplest signature)
                # Ensure ids are integers/strings consistent
                s_id = str(row['stop_ids'][0])
                e_id = str(row['stop_ids'][-1])
                return f"{s_id}-{e_id}"
            except:
                return "UNKNOWN_ROUTE"
        return "UNKNOWN_ROUTE"

    if 'stop_ids' in df.columns:
        df['route_signature'] = df.apply(get_route_sig, axis=1)
    else:
        df['route_signature'] = "UNKNOWN_ROUTE"
        
    # Frequency Cutoff (Handling Rare Routes)
    # If a route appears less than CUTOFF times, treat it as UNKNOWN (generic)
    # This prevents the model from overfitting to 1-2 samples of a rare trip
    sig_counts = df['route_signature'].value_counts()
    valid_sigs = sig_counts[sig_counts >= TRAFFIC_FREQ_CUTOFF].index
    
    df['route_signature'] = df['route_signature'].apply(lambda x: x if x in valid_sigs else "UNKNOWN_ROUTE")
    
    print(f"[INFO] Route Signatures: {len(valid_sigs)} frequent routes identified.")
    
    # Features & Target
    X = df[['distance_km', 'hour_of_day', 'day_of_week', 'is_peak', 'route_signature']]
    y = df['duration_min']
    
    if len(df) < 5:
        print("[WARN] Not enough data points to train.")
        return False

    # 3. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Pipeline Construction
    # We use TargetEncoder for route_signature. 
    # 'UNKNOWN_ROUTE' will just get average duration (which is essentially distance-based).
    pipeline = Pipeline([
        ('preprocessor', ColumnTransformer(transformers=[
            ('numerical', 'passthrough', ['distance_km', 'hour_of_day', 'day_of_week', 'is_peak']),
            ('categorical', TargetEncoder(cols=['route_signature'], alpha=SMOOTHING_ALPHA), ['route_signature'])
        ])),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
    ])
    
    # 5. Cross-Validation
    print("[INFO] Running Cross-Validation...")
    cv_scores = cross_val_score(pipeline, X_train, y_train, scoring='neg_mean_absolute_error', cv=5)
    print(f"[METRIC] CV MAE: {-np.mean(cv_scores):.2f} min")
    
    # 6. Fit & Save
    pipeline.fit(X_train, y_train)
    
    if len(X_test) > 0:
        y_pred = pipeline.predict(X_test)
        test_mae = mean_absolute_error(y_test, y_pred)
        print(f"[RESULT] Test MAE: {test_mae:.2f} min")
    
    AtomicModelSaver.save(pipeline, MODEL_PATH)
    return True

if __name__ == "__main__":
    train_traffic_model()
