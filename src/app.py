from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd
import datetime
import json
import os

# Import database module
try:
    from database import (
        init_database, seed_default_data, get_all_stops, get_stop_by_id,
        create_stop, update_stop, delete_stop, get_all_settings, update_setting,
        get_all_users, create_user, delete_user, log_route_optimization,
        get_analytics_summary
    )
    DB_AVAILABLE = True
except ImportError:
    print("[WARN] Database module not found. Using JSON fallback.")
    DB_AVAILABLE = False

# Import authentication module
try:
    from auth import register_auth_routes, token_required, admin_required
    AUTH_AVAILABLE = True
except ImportError:
    print("[WARN] Auth module not found. Admin routes unprotected.")
    AUTH_AVAILABLE = False
    # Create dummy decorators
    def token_required(f): return f
    def admin_required(f): return f

# Import route profitability ML model
try:
    from route_profitability import get_route_recommendations, calculate_route_profitability
    ROUTE_ML_AVAILABLE = True
except ImportError:
    print("[WARN] Route profitability model not found.")
    ROUTE_ML_AVAILABLE = False

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

# Initialize database if available
if DB_AVAILABLE:
    try:
        init_database()
        seed_default_data()
        print("[OK] Database connected and initialized.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        DB_AVAILABLE = False

# Register authentication routes
if AUTH_AVAILABLE:
    register_auth_routes(app)
    print("[OK] Authentication routes registered.")

# Load the trained model
try:
    model = joblib.load(MODEL_PATH)
    print("[OK] Passenger demand model loaded successfully.")
except FileNotFoundError:
    print(f"[ERROR] Model not found at {MODEL_PATH}")
    print("Please run 'python src/train_demand_model.py' first.")
    model = None

# Load bus stops (from DB or JSON fallback)
bus_stops_data = {}

def load_bus_stops():
    global bus_stops_data
    if DB_AVAILABLE:
        try:
            stops = get_all_stops()
            bus_stops_data = {stop['bus_stop_id']: dict(stop) for stop in stops}
            print(f"[OK] Loaded {len(bus_stops_data)} bus stops from database.")
            return
        except Exception as e:
            print(f"[WARN] DB load failed, falling back to JSON: {e}")
    
    # JSON fallback
    try:
        with open(BUS_STOPS_PATH, 'r') as f:
            stops = json.load(f)
            for stop in stops:
                bus_stops_data[stop['bus_stop_id']] = stop
        print(f"[OK] Loaded {len(bus_stops_data)} bus stops from JSON.")
    except FileNotFoundError:
        print(f"[WARN] {BUS_STOPS_PATH} not found. Using default multipliers.")

load_bus_stops()


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
            multiplier = float(stop_info.get('demand_multiplier', 1.0))
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
    load_factor = min(1.0, total_passengers / BUS_CAPACITY)
    adjusted_mileage = AVG_BUS_MILEAGE_KMPL - (load_factor * (AVG_BUS_MILEAGE_KMPL - MIN_BUS_MILEAGE_KMPL))
    fuel_needed_litres = distance_km / adjusted_mileage
    fuel_cost = round(fuel_needed_litres * DIESEL_PRICE_PER_LITRE)

    # Log to analytics if DB available
    if DB_AVAILABLE:
        try:
            log_route_optimization(stop_ids, distance_km, int(distance_km / 0.5), total_passengers, fuel_cost)
        except Exception as e:
            print(f"[WARN] Failed to log analytics: {e}")

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


# ========== API: BUS STOPS ==========
@app.route('/api/stops', methods=['GET'])
def api_get_stops():
    """Get all bus stops"""
    if DB_AVAILABLE:
        try:
            stops = get_all_stops()
            # Convert Decimal to float for JSON serialization
            return jsonify([{**dict(s), 'lat': float(s['lat']), 'lon': float(s['lon']), 
                           'demand_multiplier': float(s['demand_multiplier'])} for s in stops])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify(list(bus_stops_data.values()))

# Import demand logic
from demand_logic import calculate_demand_multiplier

@app.route('/api/stops', methods=['POST'])
@token_required
def api_create_stop():
    """Create a new bus stop with auto-calculated demand"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    data = request.get_json()
    
    # Input Validation
    required_fields = ['name', 'lat', 'lon', 'district', 'category']
    missing_fields = [f for f in required_fields if f not in data or not data[f]]
    
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
    try:
        # Calculate demand multiplier automatically
        multiplier = calculate_demand_multiplier(
            data['category'], 
            data['district'], 
            data['lat'], 
            data['lon']
        )
        
        stop = create_stop(
            data['name'], 
            data['lat'], 
            data['lon'], 
            data['district'],
            data['category'], 
            multiplier  # Auto-calculated
        )
        load_bus_stops()  # Refresh cache
        return jsonify({**dict(stop), 'lat': float(stop['lat']), 'lon': float(stop['lon'])}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stops/<int:stop_id>', methods=['PUT'])
@token_required
def api_update_stop(stop_id):
    """Update a bus stop and recalculate demand if needed"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    data = request.get_json()
    try:
        # Recalculate multiplier if category/district changes, else keep existing or auto-calc
        multiplier = calculate_demand_multiplier(
            data.get('category', 'regular'), 
            data.get('district', ''), 
            data.get('lat'), 
            data.get('lon')
        )
        
        stop = update_stop(
            stop_id, 
            data['name'], 
            data['lat'], 
            data['lon'], 
            data['district'],
            data.get('category', 'regular'), 
            multiplier
        )
        )
        if stop:
            load_bus_stops()  # Refresh cache
            return jsonify({**dict(stop), 'lat': float(stop['lat']), 'lon': float(stop['lon'])})
        return jsonify({'error': 'Stop not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stops/<int:stop_id>', methods=['DELETE'])
@token_required
def api_delete_stop(stop_id):
    """Delete a bus stop"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        if delete_stop(stop_id):
            load_bus_stops()  # Refresh cache
            return jsonify({'success': True})
        return jsonify({'error': 'Stop not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== API: SETTINGS ==========
@app.route('/api/settings', methods=['GET'])
@token_required
def api_get_settings():
    """Get all settings"""
    if not DB_AVAILABLE:
        return jsonify({
            'diesel_price': str(DIESEL_PRICE_PER_LITRE),
            'empty_mileage': str(AVG_BUS_MILEAGE_KMPL),
            'full_mileage': str(MIN_BUS_MILEAGE_KMPL),
            'bus_capacity': str(BUS_CAPACITY)
        })
    
    try:
        return jsonify(get_all_settings())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['PUT'])
@token_required
def api_update_settings():
    """Update multiple settings"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    data = request.get_json()
    try:
        for key, value in data.items():
            update_setting(key, str(value))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== API: USERS ==========
@app.route('/api/users', methods=['GET'])
@token_required
def api_get_users():
    """Get all users"""
    if not DB_AVAILABLE:
        return jsonify([])
    
    try:
        users = get_all_users()
        return jsonify([dict(u) for u in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@token_required
def api_create_user():
    """Create a new user"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    data = request.get_json()
    try:
        user = create_user(data['name'], data['email'], data['password'], data.get('role', 'operator'))
        return jsonify(dict(user)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def api_delete_user(user_id):
    """Delete a user"""
    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        if delete_user(user_id):
            return jsonify({'success': True})
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== API: ANALYTICS ==========
@app.route('/api/analytics', methods=['GET'])
@token_required
def api_get_analytics():
    """Get analytics summary"""
    if not DB_AVAILABLE:
        return jsonify({
            'total_passengers': 24892,
            'routes_optimized': 1247,
            'fuel_saved': 320000,
            'active_stops': len(bus_stops_data),
            'trends': []
        })
    
    try:
        return jsonify(get_analytics_summary())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== API: ROUTE RECOMMENDATIONS (ML) ==========
@app.route('/api/route-recommendations', methods=['GET'])
@token_required
def api_route_recommendations():
    """Get ML-powered profitable route recommendations"""
    if not ROUTE_ML_AVAILABLE:
        return jsonify({'error': 'Route profitability model not available'}), 503
    
    try:
        # Get all stops as list for the ML model
        stops_list = list(bus_stops_data.values())
        recommendations = get_route_recommendations(stops_list)
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
