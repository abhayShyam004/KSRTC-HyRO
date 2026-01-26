
import threading
import time
import os
import shutil
import glob
import json
from database import get_db_connection

# Import training functions lazily or at top if no circle deps
# We'll import them inside the thread to be safe and clear

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

class TrainingManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TrainingManager, cls).__new__(cls)
                    cls._instance.status = "idle" # idle, training, completed, failed
                    cls._instance.progress = 0
                    cls._instance.message = ""
                    cls._instance.last_run = None
                    cls._instance.thread = None
        return cls._instance

    def start_training_async(self):
        """Starts training in a background thread if not already running."""
        with self._lock:
            if self.status == "training":
                return False, "Training already in progress."
            
            self.status = "training"
            self.progress = 0
            self.message = "Starting training sequence..."
            self.thread = threading.Thread(target=self._run_training_sequence)
            self.thread.start()
            return True, "Training started in background."

    def get_status(self):
        return {
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "last_run": self.last_run
        }

    def _run_training_sequence(self):
        try:
            # 1. Versioning
            self.progress = 5
            timestamp = int(time.time())
            self._backup_models(timestamp)
            
            self.message = "Training Demand Model..."
            self.progress = 10
            
            # Import here to ensure fresh code/db connection context
            from train_demand_model import train_model as train_demand
            
            # We can't easily hook into the function without modifying it to accept a callback
            # For now, we'll just update before/after.
            success_demand = train_demand()
            
            if not success_demand:
                raise Exception("Demand model rejected (worse than baseline) or failed.")
            
            self.progress = 50
            self.message = "Training Traffic Model..."
            from train_traffic_model import train_traffic_model as train_traffic
            success_traffic = train_traffic()
            
            if not success_traffic:
                self.message = "Traffic model missing data (Warning), but Demand model OK."
            
            self.progress = 90
            # Save Sync Metadata
            self._save_metadata(timestamp, success_demand, success_traffic)
            
            self.progress = 100
            self.status = "completed"
            self.message = "Training successfully completed."
            self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            self.status = "failed"
            self.message = f"Error: {str(e)}"
            print(f"[TrainingManager] Failed: {e}")

    def _save_metadata(self, timestamp, demand_ok, traffic_ok):
        meta = {
            "timestamp": timestamp,
            "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "demand_model_updated": demand_ok,
            "traffic_model_updated": traffic_ok,
            "models": {
                "demand": f"passenger_demand_model_v{timestamp}.pkl" if demand_ok else None,
                "traffic": f"traffic_model_v{timestamp}.pkl" if traffic_ok else None
            }
        }
        with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def _backup_models(self, timestamp):
        """Creates copies of current .pkl files with timestamp."""
        for name in ['passenger_demand_model.pkl', 'traffic_model.pkl']:
            path = os.path.join(MODEL_DIR, name)
            if os.path.exists(path):
                backup_name = f"{name.replace('.pkl', '')}_v{timestamp}.pkl"
                backup_path = os.path.join(MODEL_DIR, backup_name)
                shutil.copy2(path, backup_path)
                print(f"[Backup] Saved {backup_name}")

    def rollback(self, model_type='demand'):
        """
        Rolls back to the previous version.
        Simple logic: Find latest _vTIMESTAMP file and restore it.
        """
        with self._lock:
            if self.status == "training":
                return False, "Cannot rollback while training."
                
            prefix = "passenger_demand_model" if model_type == 'demand' else "traffic_model"
            current_path = os.path.join(MODEL_DIR, f"{prefix}.pkl")
            
            # Find backups
            pattern = os.path.join(MODEL_DIR, f"{prefix}_v*.pkl")
            backups = sorted(glob.glob(pattern), reverse=True)
            
            if not backups:
                return False, "No backup versions found."
                
            latest_backup = backups[0] # The most recent backup (which was the state before LAST training)
            
            try:
                shutil.copy2(latest_backup, current_path)
                self.message = f"Rolled back {model_type} to {os.path.basename(latest_backup)}"
                return True, self.message
            except Exception as e:
                return False, f"Rollback failed: {e}"
