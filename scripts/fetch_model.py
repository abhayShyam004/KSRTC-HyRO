import os
import sys
import hashlib
import json
import logging
import time
import requests
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FETCHER] %(levelname)s - %(message)s')

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'passenger_demand_model.pkl')
METADATA_PATH = os.path.join(MODELS_DIR, 'model_metadata.json')

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def download_file(url, target_path, retries=3, timeout=30):
    for attempt in range(retries):
        try:
            logging.info(f"Downloading model from {url} (Attempt {attempt + 1}/{retries})...")
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logging.info("Download complete.")
            return True
        except requests.exceptions.RequestException as e:
            logging.warning(f"Download failed: {e}")
            if attempt < retries - 1:
                sleep_time = (attempt + 1) * 2
                logging.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logging.error("Max retries reached.")
                return False

def main():
    # 1. Configuration from Env Vars
    model_url = os.environ.get('MODEL_DOWNLOAD_URL')
    expected_sha256 = os.environ.get('MODEL_SHA256')

    if not model_url:
        logging.info("MODEL_DOWNLOAD_URL not set. Creating dummy/fallback for build if strictly required, or skipping.")
        # In a real rigorous setup, we might fail here. 
        # But for now, if no URL is provided, we assume the user might have copied it manually or is running locally.
        # Check if file exists locally
        if os.path.exists(MODEL_PATH):
             logging.info(f"Found local model at {MODEL_PATH}. Skipping download.")
             # Validate Hash if provided
             if expected_sha256:
                 current_hash = calculate_sha256(MODEL_PATH)
                 if current_hash != expected_sha256:
                     logging.error(f"[SECURITY] Local hash mismatch! Expected: {expected_sha256}, Got: {current_hash}")
                     sys.exit(1)
                 else:
                     logging.info("Local model verified successfully.")
             return
        else:
            logging.error("MODEL_DOWNLOAD_URL not set and no local model found. Build cannot proceed.")
            sys.exit(1)

    # Ensure directory exists
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)

    # 2. Download
    if not download_file(model_url, MODEL_PATH):
        logging.error("Failed to download model artifact.")
        sys.exit(1)

    # 3. Verification
    if expected_sha256:
        logging.info("Verifying checksum...")
        current_hash = calculate_sha256(MODEL_PATH)
        if current_hash != expected_sha256:
            logging.error(f"[CRITICAL] Checksum mismatch!")
            logging.error(f"  Expected: {expected_sha256}")
            logging.error(f"  Received: {current_hash}")
            logging.error("Deleting corrupted file...")
            os.remove(MODEL_PATH)
            sys.exit(1)
        logging.info("Checksum verified ✅")
    else:
        logging.warning("No MODEL_SHA256 provided. Skipping verification (Not Recommended for Prod).")

    # 4. Generate/Update Basic Metadata (if not downloaded)
    # Ideally, metadata is valid from source.
    if os.path.exists(METADATA_PATH):
        logging.info(f"Metadata file present at {METADATA_PATH}")
    else:
        logging.info("Generating minimal metadata for downloaded artifact...")
        meta = {
            "source": model_url,
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256": expected_sha256 or "unknown"
        }
        with open(METADATA_PATH, 'w') as f:
            json.dump(meta, f, indent=2)

    logging.info("Model setup complete.")

if __name__ == "__main__":
    main()
