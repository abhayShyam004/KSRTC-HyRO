import os
import sys
import hashlib
import json
import logging
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, 'src'))

# Import existing training logic
from train_demand_model import train_model

MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'passenger_demand_model.pkl')
METADATA_PATH = os.path.join(MODELS_DIR, 'model_metadata.json')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    logging.info("--- Starting Offline Model Training ---")
    
    # Ensure models dir exists
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    # 1. Trigger Training
    success = train_model()
    
    if not success:
        logging.error("Training failed!")
        sys.exit(1)
        
    logging.info("Training complete.")
    
    if not os.path.exists(MODEL_PATH):
        logging.error(f"Model file not found at {MODEL_PATH}")
        sys.exit(1)

    # 2. Generate Metadata & Checksum
    file_size = os.path.getsize(MODEL_PATH)
    file_hash = calculate_sha256(MODEL_PATH)
    
    metadata = {
        "version": "1.0", # Increment manually or auto-version if needed
        "trained_at": datetime.utcnow().isoformat(),
        "file_size_bytes": file_size,
        "sha256": file_hash,
        "filename": "passenger_demand_model.pkl"
    }
    
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    logging.info(f"Metadata saved to {METADATA_PATH}")
    logging.info(f"Use this SHA256 for verification: {file_hash}")
    logging.info("--- Offline Training Successful ---")

if __name__ == "__main__":
    main()
