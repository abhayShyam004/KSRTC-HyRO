
import os
import sys
import subprocess
import time

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, 'src'))

def run_python_module(module_path, description):
    print(f"\n--- {description} ---")
    try:
        # Run using python -m or direct path
        # We'll use sys.executable to ensure we use the same environment
        cmd = [sys.executable, module_path]
        subprocess.run(cmd, check=True)
        print(f"SUCCESS: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {description} (Error: {e})")
        return False

def main():
    print("🚀 Starting KSRTC-HyRO Build & Bootstrap Process")
    
    # 1. Sync DB from JSON (ensure we have stops)
    # print("[1/3] Preparing Database...")
    # module_populate = os.path.join(PROJECT_ROOT, 'src', 'populate_db_from_json.py')
    # run_python_module(module_populate, "Populating Database from JSON")
    
    # 2. Generate Dummy Historical Data
    # Training needs statistical history. Fresh DBs are empty.
    print("[2/3] Generating Training Data...")
    module_dummy = os.path.join(PROJECT_ROOT, 'src', 'create_dummy_data.py')
    run_python_module(module_dummy, "Generating Dummy Historical Data (Past 30 Days)")
    
    # 3. Train the Model -> SKIPPED (Model is now committed to repo)
    # print("[3/3] Training Demand Model...")
    # module_train = os.path.join(PROJECT_ROOT, 'scripts', 'train_offline.py')
    # run_python_module(module_train, "Training Demand Model")
    print("[3/3] Using Pre-trained Model (Training skipped)")
    
    # Final check
    model_path = os.path.join(PROJECT_ROOT, 'models', 'passenger_demand_model.pkl')
    if os.path.exists(model_path):
        print(f"\n✅ Build Successful! Model created at: {model_path}")
    else:
        print("\n❌ Build Failed: Model file was not generated.")
        sys.exit(1)

if __name__ == "__main__":
    main()
