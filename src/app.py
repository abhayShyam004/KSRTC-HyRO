from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd
import datetime
import json
import os

# --- CONFIGURATION ---
# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # One level up from src/

MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', 'passenger_demand_model.pkl')
BUS_STOPS_PATH = os.path.join(PROJECT_ROOT, 'bus_stops.json')
STATIC_FOLDER = PROJECT_ROOT  # Serve HTML from project root

AVG_BUS_MILEAGE_KMPL = 4.5  # Base mileage for empty bus
MIN_BUS_MILEAGE_KMPL = 3.5  # Mileage when fully loaded
BUS_CAPACITY = 55  # Standard KSRTC bus capacity
DIESEL_PRICE_PER_LITRE = 95.21  # Current price in Kerala

# --- INITIALIZATION ---
app = Flask(__name__, static_folder=STATIC_FOLDER)
CORS(app)

# Load the trained model
try:
    model = joblib.load(MODEL_PATH)
    print("✅ Passenger demand model loaded successfully.")
except FileNotFoundError:
    print(f"❌ Error: Model not found at {MODEL_PATH}")
    print("Please run 'python src/train_demand_model.py' first.")
    model = None

# Load bus stops with demand multipliers
bus_stops_data = {}
try:
    with open(BUS_STOPS_PATH, 'r') as f:
        stops = json.load(f)
        for stop in stops:
            bus_stops_data[stop['bus_stop_id']] = stop
    print(f"✅ Loaded {len(bus_stops_data)} bus stops with demand data.")
except FileNotFoundError:
    print(f"⚠️ Warning: {BUS_STOPS_PATH} not found. Using default multipliers.")


@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500

    data = request.get_json()
    distance_km = data.get('distance_km')
    num_stops = data.get('num_stops')
    stop_ids = data.get('stop_ids', [])  # NEW: Accept stop IDs

    if not distance_km or not num_stops:
        return jsonify({"error": "Missing 'distance_km' or 'num_stops'"}), 400

    # --- 1. Get Current Time Features ---
    now = datetime.datetime.now()
    hour = now.hour
    day_of_week = now.weekday()
    is_peak = 1 if (8 <= hour <= 10) or (17 <= hour <= 19) else 0
    is_weekend = 1 if day_of_week >= 5 else 0

    features = pd.DataFrame([{
        'hour_of_day': hour,
        'day_of_week': day_of_week,
        'is_peak_hour': is_peak
    }])
    
    # --- 2. Calculate Weighted Passenger Demand ---
    base_passengers_per_stop = model.predict(features)[0]
    
    total_passengers = 0
    high_demand_stops = []
    
    if stop_ids and len(stop_ids) > 0:
        # Use stop-specific demand multipliers
        for stop_id in stop_ids:
            stop_info = bus_stops_data.get(stop_id, {})
            multiplier = stop_info.get('demand_multiplier', 1.0)
            category = stop_info.get('category', 'regular')
            stop_name = stop_info.get('name', f'Stop {stop_id}')
            
            stop_passengers = base_passengers_per_stop * multiplier
            total_passengers += stop_passengers
            
            # Track high-demand stops (multiplier > 1.5)
            if multiplier >= 1.5:
                high_demand_stops.append({
                    'name': stop_name,
                    'category': category,
                    'multiplier': multiplier
                })
    else:
        # Fallback: simple calculation
        total_passengers = base_passengers_per_stop * num_stops
    
    total_passengers = round(total_passengers)

    # --- 3. Calculate Load-Adjusted Fuel Cost ---
    # More passengers = heavier bus = worse fuel efficiency
    load_factor = min(1.0, total_passengers / BUS_CAPACITY)
    
    # Mileage decreases from 4.5 (empty) to 3.5 (full) based on load
    adjusted_mileage = AVG_BUS_MILEAGE_KMPL - (load_factor * (AVG_BUS_MILEAGE_KMPL - MIN_BUS_MILEAGE_KMPL))
    
    fuel_needed_litres = distance_km / adjusted_mileage
    fuel_cost = round(fuel_needed_litres * DIESEL_PRICE_PER_LITRE)

    return jsonify({
        'expected_passengers': int(total_passengers),
        'estimated_fuel_cost_inr': int(fuel_cost),
        'load_factor_percent': round(load_factor * 100),
        'adjusted_mileage_kmpl': round(adjusted_mileage, 2),
        'high_demand_stops': high_demand_stops,
        'calculation_time': now.strftime('%H:%M'),
        'is_peak_hour': bool(is_peak),
        'is_weekend': bool(is_weekend)
    })


# Serve static files (HTML, CSS, JS)
@app.route('/')
def serve_app():
    return send_from_directory(STATIC_FOLDER, 'ksrtc_driver_app.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_FOLDER, path)


if __name__ == '__main__':
    # For local development
    app.run(port=5001, debug=True)

