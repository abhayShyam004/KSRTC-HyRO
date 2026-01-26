import os
import sys
import pandas as pd
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import FunctionTransformer

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_training_data, get_all_stops, get_db_connection
from ml_utils import TargetEncoder, AtomicModelSaver
from ml_config import (
    SMOOTHING_ALPHA, 
    AUTO_CAT_MIN_SAMPLES, 
    AUTO_CAT_CV_THRESHOLD,
    PROTECTED_TAGS,
    HUB_DEMAND_THRESHOLD,
    COMMERCIAL_DEMAND_THRESHOLD
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'passenger_demand_model.pkl')
LOG_FILE = os.path.join(PROJECT_ROOT, 'category_changes.log')

def update_stop_categories(model, df_train):
    """
    Safely updates stop categories based on learned demand.
    Respects PROTECTED_TAGS and confidence thresholds.
    """
    print("[INFO] Auditing stops for category updates...")
    
    # Calculate stats per stop from training data (Ground Truth)
    stop_stats = df_train.groupby('stop_id')['passenger_count'].agg(['count', 'mean', 'std'])
    
    # Get current stops from DB
    current_stops = {s['bus_stop_id']: s for s in get_all_stops()}
    
    updates = []
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for stop_id, stats in stop_stats.iterrows():
                if stop_id not in current_stops:
                    continue
                    
                s_curr = current_stops[stop_id]
                curr_cat = s_curr.get('category', 'regular')
                
                # 1. Protection Check
                if curr_cat in PROTECTED_TAGS:
                    continue
                
                # 2. Data Sufficiency Check
                if stats['count'] < AUTO_CAT_MIN_SAMPLES:
                    continue
                    
                # 3. Stability Check (Coefficient of Variation)
                # CV = StdDev / Mean. If mean is 0, ignore.
                mean_val = stats['mean']
                if mean_val <= 0.1: 
                    continue
                    
                cv = stats['std'] / mean_val
                if cv > AUTO_CAT_CV_THRESHOLD:
                    # Too volatile (High relative variance)
                    continue
                
                # 4. Threshold Logic (Business Rules)
                new_cat = curr_cat
                
                if mean_val >= HUB_DEMAND_THRESHOLD:
                    new_cat = 'transport_hub'
                elif mean_val >= COMMERCIAL_DEMAND_THRESHOLD:
                    new_cat = 'commercial'
                
                # Only apply if Upgrade (or change from regular)
                if new_cat != curr_cat:
                    msg = f"Stop {stop_id} ({curr_cat}) -> {new_cat} (Avg: {mean_val:.1f}, N={stats['count']}, CV={cv:.2f})"
                    print(f"  [UPDATE] {msg}")
                    updates.append(msg)
                    
                    # Execute DB Update
                    cur.execute(
                        "UPDATE bus_stops SET category = %s WHERE bus_stop_id = %s",
                        (new_cat, int(stop_id))
                    )
            
            if updates and len(updates) > 0:
                 conn.commit()
                 # Audit Log
                 with open(LOG_FILE, 'a') as f:
                     f.write(f"--- Update Run {pd.Timestamp.now()} ---\n")
                     f.write("\n".join(updates) + "\n")
            else:
                print("  No category updates required.")

def train_model():
    print("--- Starting Robust Model Training (V3) ---")
    
    # 1. Fetch Data
    print("[INFO] Fetching training data (this may take a while)...", flush=True)
    raw_data = get_training_data()
    
    if not raw_data:
        print("[ERROR] No training data found.")
        return False
        
    print(f"[INFO] Fetched {len(raw_data)} training records.")
    df = pd.DataFrame(raw_data)
    
    # Features & Target
    # TargetEncoder needs 'stop_id' as a column, not index
    X = df[['stop_id', 'hour_of_day', 'day_of_week', 'is_peak']]
    y = df['passenger_count']
    
    # 2. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 3. Pipeline Construction (Zero-Leakage)
    pipeline = Pipeline([
        ('preprocessor', ColumnTransformer(transformers=[
            ('numerical', 'passthrough', ['hour_of_day', 'day_of_week', 'is_peak']),
            ('categorical', TargetEncoder(cols=['stop_id'], alpha=SMOOTHING_ALPHA), ['stop_id'])
        ])),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1))
    ])
    
    # 4. Cross-Validation (Baseline Check)
    from sklearn.dummy import DummyRegressor
    
    # 4. Cross-Validation (Fair Comparison)
    print("[INFO] Running Cross-Validation...")
    
    # Model CV
    cv_scores = cross_val_score(pipeline, X_train, y_train, scoring='neg_mean_absolute_error', cv=5)
    model_mae = -np.mean(cv_scores)
    print(f"[METRIC] Model CV MAE: {model_mae:.2f}")
    
    # Baseline comparison (Naive Global Mean Predictor)
    baseline_pred = y_train.mean()
    baseline_mae = mean_absolute_error(y_test, [baseline_pred] * len(y_test))
    
    # --- DEBUGGING OUTPUT ---
    print("\n[DEBUG] Data Stats:")
    print(f"  Training Samples: {len(X_train)}")
    print(f"  Target Mean: {y_train.mean():.2f}")
    print(f"  Target Std: {y_train.std():.2f}")
    
    # Check learned encodings from the pipeline
    # The pipeline is not fitted yet, so we can't check 'encoder.maps' from the pipeline *instance* 
    # unless we fit it or inspect the transformer inside the cross_val loop?
    # BUT we can just do a quick peek on the training set:
    debug_enc = TargetEncoder(cols=['stop_id'], alpha=SMOOTHING_ALPHA)
    debug_enc.fit(X_train[['stop_id']], y_train)
    vals = list(debug_enc.maps['stop_id'].values())
    if vals:
        print(f"  Encoded Stop Min: {min(vals):.2f}")
        print(f"  Encoded Stop Max: {max(vals):.2f}")
        print(f"  Encoded Stop Spread: {max(vals) - min(vals):.2f}")
        
        # Check for Collapse
        if (max(vals) - min(vals)) < 0.1:
            print("[CRITICAL] ENCODER COLLAPSED. All stops encoded to global mean.")
            print("  -> Cause: Too few samples per stop OR Alpha too high.")
            
    # Check Signal-to-Noise
    ratio = baseline_mae / y_train.std()
    print(f"  Signal Diagnostic (BaselineMAE / StdDev): {ratio:.2f}")
    if ratio < 0.3:
        print("  -> Interpretation: Baseline is extremely good. Data might be too linear/easy.")
    elif ratio > 0.9:
        print("  -> Interpretation: Baseline is poor, but Model isn't beating it. No extracted signal.")
        
    stop_counts = X_train['stop_id'].value_counts()
    print(f"  Median Samples per Stop: {stop_counts.median()}")
    # ------------------------

    print(f"[BASELINE] Global Mean Predictor MAE: {baseline_mae:.2f}")
    
    # --- NUCLEAR DIAGNOSTIC ---
    with open('nuclear_diagnostic.txt', 'w') as f:
        f.write("--- NUCLEAR DIAGNOSTIC REPORT ---\n")
        
        # 1. Constant Feature Check
        f.write("\n1. FEATURE CARDINALITY (nunique):\n")
        f.write(X_train.nunique().to_string() + "\n")
        
        # 2. CV Starvation Check
        f.write("\n2. PER-STOP SAMPLE STATS:\n")
        stop_counts = X_train['stop_id'].value_counts()
        f.write(stop_counts.describe().to_string() + "\n")
        
        # 3. Linear Signal Check
        from sklearn.linear_model import LinearRegression
        lr = LinearRegression()
        # Need to encode stop_id for LR? No, LR on raw ID is useless. 
        # But user asked for LR check. 
        # If we just pass X_train (with raw stop_id), LR treats it as continuous. Meaningless.
        # But assuming the user wants to see if *Basic* features + Mean have signal.
        # Actually, let's run LR on the *Transformed* features (if possible) OR just run it on numeric features.
        # But simplest Interpretation: If RF (non-linear) can't beat Mean, maybe data is just noise.
        # Let's run LR on the simple numeric columns to see if Time/Day adds ANY linear signal.
        X_simple = X_train[['hour_of_day', 'day_of_week', 'is_peak']]
        lr_scores = cross_val_score(lr, X_simple, y_train, scoring='neg_mean_absolute_error', cv=5)
        lr_mae = -np.mean(lr_scores)
        
        f.write("\n3. LINEAR SIGNAL CHECK (Simple Features Only):\n")
        f.write(f"LinearRegression MAE: {lr_mae:.2f}\n")
        f.write(f"Baseline (Mean) MAE: {baseline_mae:.2f}\n")
        
        ratio = lr_mae / baseline_mae
        f.write(f"LR/Baseline Ratio: {ratio:.2f} (If approx 1.0 -> No linear signal in time features)\n")
    # ------------------------
    # Comparison logic
    if model_mae > baseline_mae:
        print(f"[REJECT] Model MAE ({model_mae:.2f}) > Baseline ({baseline_mae:.2f}). Training rejected.")
        return False
    
    print(f"[PASS] Model ({model_mae:.2f}) beat Baseline ({baseline_mae:.2f}). Proceeding to save.")
    
    # 5. Final Fit
    pipeline.fit(X_train, y_train)
    
    # Test Evaluation
    y_pred = pipeline.predict(X_test)
    test_mae = mean_absolute_error(y_test, y_pred)
    print(f"[RESULT] Test MAE: {test_mae:.2f}")
    
    # 6. Atomic Save
    AtomicModelSaver.save(pipeline, MODEL_PATH)
    
    # NEW: Save Metadata (MAE) for Risk Discounting
    import json
    metadata_path = os.path.join(MODEL_DIR, 'model_metadata.json')
    metadata = {
        'mae': float(model_mae),
        'baseline_mae': float(baseline_mae),
        'last_trained': pd.Timestamp.now().isoformat()
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[INFO] Saved model metadata to {metadata_path}")
    
    # 7. Auto-Categorization (Safety Protected)
    try:
        update_stop_categories(pipeline, df)
    except Exception as e:
        print(f"[WARN] Auto-Categorization failed: {e}")
    
    return True

if __name__ == "__main__":
    train_model()
