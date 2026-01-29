import sys
import os

# CONFIG: Ensure local modules are found
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import pandas as pd
import datetime
import json
import gc

# Import database module
try:
    from database import (
        init_database, seed_default_data, get_all_stops, get_stop_by_id,
        create_stop, update_stop, delete_stop, get_all_settings, update_setting,
        get_all_users, create_user, delete_user, log_route_optimization,
        get_analytics_summary, get_db_connection
    )
    DB_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Database module not found: {e}. Using JSON fallback.")
    DB_AVAILABLE = False

# Import authentication module
try:
    from auth import register_auth_routes, token_required, admin_required
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Auth module not found: {e}. Admin routes unprotected.")
    AUTH_AVAILABLE = False
    # Create dummy decorators
    def token_required(f): return f
    def admin_required(f): return f

# Import route profitability ML model
try:
    from route_profitability import get_route_recommendations, calculate_route_profitability, optimize_route_order
    ROUTE_ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Route profitability model not found: {e}.")
    ROUTE_ML_AVAILABLE = False

# Import Routing Engine (v6)
try:
    from routing.engine import RoutingEngine
    routing_engine = RoutingEngine()
    print("[OK] Routing Engine v6 initialized.")
except ImportError as e:
    print(f"[ERROR] Routing Engine load failed: {e}")
    routing_engine = None
except Exception as e:
    print(f"[ERROR] Routing Engine init failed: {e}")
    routing_engine = None

# --- CONFIGURATION ---
# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # One level up from src/

MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', 'passenger_demand_model.pkl')
BUS_STOPS_PATH = os.path.join(PROJECT_ROOT, 'bus_stops.json')
STATIC_FOLDER = PROJECT_ROOT  # Serve HTML from project root

# Default Configuration (Fallbacks if DB settings missing)
AVG_BUS_MILEAGE_KMPL = 4.5
MIN_BUS_MILEAGE_KMPL = 3.5
BUS_CAPACITY = 55
DIESEL_PRICE_PER_LITRE = 95.21

def get_current_settings():
    """Fetch current technical settings from DB or use defaults"""
    defaults = {
        'empty_mileage': AVG_BUS_MILEAGE_KMPL,
        'full_mileage': MIN_BUS_MILEAGE_KMPL,
        'bus_capacity': BUS_CAPACITY,
        'diesel_price': DIESEL_PRICE_PER_LITRE
    }
    
    if DB_AVAILABLE:
        try:
            db_settings = get_all_settings()
            return {
                'empty_mileage': float(db_settings.get('empty_mileage', defaults['empty_mileage'])),
                'full_mileage': float(db_settings.get('full_mileage', defaults['full_mileage'])),
                'bus_capacity': int(db_settings.get('bus_capacity', defaults['bus_capacity'])),
                'diesel_price': float(db_settings.get('diesel_price', defaults['diesel_price']))
            }
        except Exception as e:
            print(f"[WARN] Failed to fetch settings: {e}")
            return defaults
    return defaults

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

# --- ROUTING API (v6) ---
@app.route('/api/route', methods=['POST'])
def get_safe_route():
    if not routing_engine:
        return jsonify({"error": "Routing Engine Unavailable"}), 503
        
    try:
        data = request.json
        stops = data.get('stops', [])
        if not stops:
            return jsonify({"error": "No stops provided"}), 400
            
        route_geo = routing_engine.get_optimized_route(stops)
        return jsonify(route_geo)
        
    except Exception as e:
        print(f"[ROUTE ERROR] {e}")
        # Determine error code based on message
        msg = str(e)
        if "Circuit Open" in msg:
            return jsonify({"error": "Routing Service Temporarily Unavailable (Upstream Limit)"}), 503
        elif "Restricted" in msg or "Violation" in msg:
             return jsonify({"error": msg}), 422
        else:
             return jsonify({"error": msg}), 500


# Load the trained model
# Load the trained model (Strict Mode)
try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file missing at {MODEL_PATH}")
        
    model = joblib.load(MODEL_PATH)
    print(f"[OK] Passenger demand model loaded successfully.")
    
    # Log metadata if available
    metadata_path = os.path.join(PROJECT_ROOT, 'models', 'model_metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            meta = json.load(f)
            print(f"[MODEL] Version: {meta.get('version', 'unknown')} | SHA256: {meta.get('sha256', 'unknown')[:8]}...")
            
    # Free up memory used during load
    gc.collect()
            
except Exception as e:
    print(f"[CRITICAL] Failed to load model: {e}")
    # In production, we want to fail fast.
    print("-" * 50)
    print("DEPLOYMENT TIP: The model file is missing. This usually happens because 'models/' is in .gitignore.")
    print("Ensure your Render build command includes: python scripts/render_build.py")
    print("-" * 50)
    print("Application cannot start without prediction model.")
    sys.exit(1)

# Load bus stops (from DB or JSON fallback)
bus_stops_data = {}

def load_bus_stops():
    global bus_stops_data
    bus_stops_data = {}
    
    # 1. Load from Database (Primary Source)
    if DB_AVAILABLE:
        try:
            # Use global import
            stops = get_all_stops()
            
            # --- DEBUG: verify DB connection and count ---
            from database import DATABASE_URL
            print(f"[DEBUG] DB URL: {DATABASE_URL}")
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM bus_stops")
                    print(f"[DEBUG] Raw DB Count: {cur.fetchone()[0]}")
            # ---------------------------------------------
            
            if stops:
                bus_stops_data = {stop['bus_stop_id']: dict(stop) for stop in stops}
                print(f"[OK] Loaded {len(bus_stops_data)} bus stops from database (Primary).")
                return
        except Exception as e:
            print(f"[WARN] DB load failed, falling back to JSON: {e}")
            
    # 2. JSON Fallback
    if os.path.exists(BUS_STOPS_PATH):
        try:
            with open(BUS_STOPS_PATH, 'r', encoding='utf-8') as f:
                stops_list = json.load(f)
                
            bus_stops_data = {s['bus_stop_id']: s for s in stops_list}
            print(f"[OK] Loaded {len(bus_stops_data)} bus stops from JSON (Fallback).")
        except Exception as e:
            print(f"[ERROR] Failed to load JSON stops: {e}") 
            
    if not bus_stops_data:
        print("[CRITICAL] No bus stops loaded! Application will be empty.")

load_bus_stops()

@app.route('/api/stops', methods=['GET'])
def get_stops():
    # Return list of stops
    return jsonify(list(bus_stops_data.values()))

@app.route('/bus_stops.json')
def serve_stops_json():
    return send_from_directory(PROJECT_ROOT, 'bus_stops.json')

@app.route('/predict', methods=['POST'])
def predict():
    import traceback
    try:
        if model is None:
            print("[ERROR] Predict called but model is None")
            return jsonify({"error": "Model not loaded"}), 500

        data = request.get_json()
        print(f"[DEBUG] Predict request data: {data}")
        
        distance_km = data.get('distance_km')
        num_stops = data.get('num_stops')
        stop_ids = data.get('stop_ids', [])
        
        # 1. Calculate Stats for ORIGINAL Route
        # -------------------------------------
        if not distance_km or not num_stops:
            if not stop_ids:
                 return jsonify({"error": "Missing 'distance_km' or 'stop_ids'"}), 400

        # [DEMO FIX] Force prediction time to Monday 10:00 AM
        # This ensures meaningful passenger numbers during off-hours demo/testing
        # now = datetime.datetime.now()
        # hour = now.hour
        # day_of_week = now.weekday()
        
        hour = 10         # 10 AM
        day_of_week = 0   # Monday
        is_peak = 1       # 10 AM is peak
        
        # is_peak logic (redundant due to override, but kept for reference)
        # is_peak = 1 if (8 <= hour <= 10) or (17 <= hour <= 19) else 0
        
        # Still need 'now' for response formatting
        now = datetime.datetime.now()
        
        is_weekend = 1 if day_of_week >= 5 else 0

        unique_stop_ids = list(set(stop_ids))
        if unique_stop_ids:
            X_pred = pd.DataFrame([{
                'stop_id': s_id,
                'hour_of_day': hour,
                'day_of_week': day_of_week,
                'is_peak': is_peak
            } for s_id in unique_stop_ids])
            
            try:
                preds = model.predict(X_pred)
                stop_predictions = dict(zip(unique_stop_ids, preds))
            except Exception as e:
                print(f"[WARN] Model prediction failed: {e}")
                # Fallback
                try:
                    # Check if it's the ColumnTransformer mismatch
                    X_v1 = pd.DataFrame([{
                        'hour_of_day': hour, 
                        'day_of_week': day_of_week, 
                        'is_peak': is_peak
                    }])
                    base_pred = model.predict(X_v1)[0]
                    stop_predictions = {sid: base_pred * float(bus_stops_data.get(sid, {}).get('demand_multiplier', 1.0)) for sid in unique_stop_ids}
                except Exception as e2:
                    print(f"[ERROR] V1 Fallback also failed: {e2}")
                    stop_predictions = {sid: 5 for sid in unique_stop_ids}
        else:
            stop_predictions = {}
        
        # Fetch dynamic settings for this calculation
        settings = get_current_settings()
        sim_capacity = settings['bus_capacity']
        sim_empty_mileage = settings['empty_mileage']
        sim_full_mileage = settings['full_mileage']
        sim_diesel_price = settings['diesel_price']

        def calculate_stats(current_stop_ids, dist_km):
            total_pass = 0
            h_stops = []
            if current_stop_ids:
                for s_id in current_stop_ids:
                    s_info = bus_stops_data.get(s_id, {})
                    cat = s_info.get('category', 'regular')
                    s_name = s_info.get('name', f'Stop {s_id}')
                    s_pass = stop_predictions.get(s_id, 0)
                    s_pass = max(0, float(s_pass))
                    total_pass += s_pass
                    if s_pass >= 15:
                        h_stops.append({'name': s_name, 'category': cat, 'multiplier': 1.0})
            
            # [DEBUG] Log predictions
            print(f"[DEBUG] Stop IDs: {current_stop_ids}")
            print(f"[DEBUG] Predictions: {stop_predictions}")
            print(f"[DEBUG] Total Passengers: {total_pass}")

            total_pass = round(total_pass)
            # Load Factor capped at 1.0 (Full) or higher? Standard practice cap at 1.2 (standing)?
            # Keeping 1.0 for conservative fuel calc, but showing overflow is fine.
            l_factor = min(1.0, total_pass / sim_capacity)
            
            if dist_km > 0:
                adj_mileage = sim_empty_mileage - (l_factor * (sim_empty_mileage - sim_full_mileage))
                f_cost = round((dist_km / adj_mileage) * sim_diesel_price)
                mileage = adj_mileage
            else:
                f_cost = 0
                mileage = sim_empty_mileage
                
            return total_pass, f_cost, l_factor, mileage, h_stops

        orig_pass, orig_cost, orig_load, orig_mileage, orig_high_stops = calculate_stats(stop_ids, distance_km or 0)

        optimized_result = None
        if ROUTE_ML_AVAILABLE and stop_ids and len(stop_ids) > 2:
            try:
                current_stops_objs = [bus_stops_data.get(sid) for sid in stop_ids if sid in bus_stops_data]
                all_stops_cache = list(bus_stops_data.values())
                opt_stops, opt_metrics = optimize_route_order(current_stops_objs, all_stops_cache)
                opt_stop_ids = [s['bus_stop_id'] for s in opt_stops]
                
                if opt_stop_ids != stop_ids:
                    from math import radians, cos, sin, asin, sqrt
                    def haversine(lon1, lat1, lon2, lat2):
                        lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
                        dlon = lon2 - lon1
                        dlat = lat2 - lat1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        return 6371 * c
                    
                    def calculate_path_length(stops_sequence):
                        dist = 0
                        for i in range(len(stops_sequence)-1):
                            s1, s2 = stops_sequence[i], stops_sequence[i+1]
                            dist += haversine(s1['lon'], s1['lat'], s2['lon'], s2['lat'])
                        return dist

                    orig_haversine = calculate_path_length(current_stops_objs)
                    new_haversine = calculate_path_length(opt_stops)
                    road_factor = (distance_km / orig_haversine) if orig_haversine > 0 else 1.2
                    est_opt_distance_km = new_haversine * road_factor
                    
                    opt_pass, opt_cost, opt_load, opt_mileage, opt_high = calculate_stats(opt_stop_ids, est_opt_distance_km)
                    
                    optimized_result = {
                        'stop_ids': opt_stop_ids,
                        'stop_names': [s['name'] for s in opt_stops],
                        'estimated_distance_km': round(est_opt_distance_km, 2),
                        'expected_passengers': int(opt_pass),
                        'estimated_fuel_cost_inr': int(opt_cost),
                        'savings_inr': int(orig_cost - opt_cost)
                    }
            except Exception as e:
                print(f"[WARN] Optimization step failed: {e}")
                traceback.print_exc()

        # Calculate actual fuel savings (difference between original and optimized route)
        actual_fuel_saved = 0
        if optimized_result and optimized_result.get('savings_inr', 0) > 0:
            actual_fuel_saved = optimized_result['savings_inr']
        
        if DB_AVAILABLE:
            try:
                log_route_optimization(stop_ids, distance_km or 0, int((distance_km or 0) / 0.5), orig_pass, actual_fuel_saved)
            except Exception as e:
                print(f"[WARN] Failed to log analytics: {e}")

        return jsonify({
            'expected_passengers': int(orig_pass),
            'estimated_fuel_cost_inr': int(orig_cost),
            'load_factor_percent': round(orig_load * 100),
            'adjusted_mileage_kmpl': round(orig_mileage, 2),
            'high_demand_stops': orig_high_stops,
            'calculation_time': now.strftime('%H:%M'),
            'is_peak_hour': bool(is_peak),
            'optimized_route': optimized_result
        })
    except Exception as e:
        err_msg = f"INTERNAL ERROR: {str(e)}"
        print(f"[CRITICAL] {err_msg}")
        traceback.print_exc()
        return jsonify({"error": err_msg, "traceback": traceback.format_exc()}), 500



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
try:
    from demand_logic import calculate_demand_multiplier
    DEMAND_LOGIC_AVAILABLE = True
except ImportError:
    print("[WARN] Demand logic module not found. Using fallback.")
    DEMAND_LOGIC_AVAILABLE = False
    def calculate_demand_multiplier(cat, dist, lat, lon): return 1.0

@app.route('/api/stops', methods=['POST'])
@token_required
def api_create_stop():
    """Create a new bus stop with auto-calculated demand"""
    data = request.get_json()
    
    # Input Validation
    required_fields = ['name', 'lat', 'lon', 'district', 'category']
    missing_fields = [f for f in required_fields if f not in data or not data[f]]
    
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

    # Offline/JSON Fallback Mode
    if not DB_AVAILABLE:
        try:
            # Generate new ID (max + 1)
            new_id = max([int(k) for k in bus_stops_data.keys()] or [0]) + 1
            
            # Calculate multiplier
            multiplier = calculate_demand_multiplier(
                data['category'], data['district'], data['lat'], data['lon']
            )
            
            new_stop = {
                'bus_stop_id': new_id,
                'name': data['name'],
                'lat': data['lat'],
                'lon': data['lon'],
                'district': data['district'],
                'category': data['category'],
                'demand_multiplier': multiplier
            }
            
            # Update cache and save to file
            bus_stops_data[new_id] = new_stop
            with open(BUS_STOPS_PATH, 'w') as f:
                json.dump(list(bus_stops_data.values()), f, indent=2)
                
            print(f"[INFO] New stop added to JSON (Offline Mode): {new_stop['name']}")
            return jsonify(new_stop), 201
        except Exception as e:
            return jsonify({'error': f"Offline save failed: {str(e)}"}), 500

    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    # DB Mode continues...
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
    data = request.get_json()
    
    # Offline/JSON Fallback Mode
    if not DB_AVAILABLE:
        if stop_id not in bus_stops_data:
            return jsonify({'error': 'Stop not found'}), 404
            
        try:
            stop = bus_stops_data[stop_id]
            multiplier = calculate_demand_multiplier(
                data.get('category', stop['category']), 
                data.get('district', stop['district']), 
                data.get('lat', stop['lat']), 
                data.get('lon', stop['lon'])
            )
            
            stop['name'] = data['name']
            stop['lat'] = data['lat']
            stop['lon'] = data['lon']
            stop['district'] = data['district']
            stop['category'] = data.get('category', stop['category'])
            stop['demand_multiplier'] = multiplier
            
            # Save to file
            with open(BUS_STOPS_PATH, 'w') as f:
                json.dump(list(bus_stops_data.values()), f, indent=2)
                
            return jsonify(stop)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if not DB_AVAILABLE:
        return jsonify({'error': 'Database not available'}), 503
    
    # DB Mode continues...
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
    # Offline/JSON Fallback Mode
    if not DB_AVAILABLE:
        if stop_id in bus_stops_data:
            del bus_stops_data[stop_id]
            try:
                with open(BUS_STOPS_PATH, 'w') as f:
                    json.dump(list(bus_stops_data.values()), f, indent=2)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        return jsonify({'error': 'Stop not found'}), 404

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



# ========== API: SYSTEM STATUS ==========
@app.route('/api/status', methods=['GET'])
def api_status():
    """Check system status"""
    return jsonify({
        'status': 'online',
        'db_available': DB_AVAILABLE,
        'mode': 'cloud' if DB_AVAILABLE else 'offline_fallback'
    })

# ========== API: USERS ==========
@app.route('/api/users', methods=['GET'])
@token_required
def api_get_users():
    """Get all users"""
    if not DB_AVAILABLE:
        try:
            users_path = os.path.join(PROJECT_ROOT, 'users.json')
            if os.path.exists(users_path):
                with open(users_path, 'r') as f:
                    users = json.load(f)
                    return jsonify(users)
            return jsonify([])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
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
            'total_passengers': 0,
            'routes_optimized': 0,
            'fuel_saved': 0,
            'active_stops': len(bus_stops_data),
            'trends': []
        })
    
    try:
        data = get_analytics_summary()
        # Fix date serialization for JSON
        if 'trends' in data:
            for item in data['trends']:
                if isinstance(item.get('date'), (datetime.date, datetime.datetime)):
                    item['date'] = item['date'].isoformat()
        return jsonify(data)
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

# ========== API: ADMIN ==========
@app.route('/api/admin/retrain', methods=['POST'])
@token_required
def api_retrain_model():
    """Trigger ASYNC model retraining on latest DB data"""
    try:
        from training_manager import TrainingManager
        manager = TrainingManager()
        
        success, msg = manager.start_training_async()
        
        if success:
            return jsonify({'success': True, 'message': msg}), 202
        else:
            return jsonify({'error': msg}), 409 # Conflict (already running)

    except Exception as e:
        return jsonify({'error': f"Retraining initiation error: {str(e)}"}), 500

@app.route('/api/admin/training-status', methods=['GET'])
@token_required
def api_training_status():
    """Poll status of background training"""
    try:
        from training_manager import TrainingManager
        manager = TrainingManager()
        return jsonify(manager.get_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/rollback', methods=['POST'])
@token_required
def api_rollback_model():
    """Rollback model to previous version"""
    data = request.get_json() or {}
    model_type = data.get('model', 'demand') # demand or traffic
    
    try:
        from training_manager import TrainingManager
        manager = TrainingManager()
        
        success, msg = manager.rollback(model_type)
        
        if success:
             # Reload model in memory if it's the demand model
            if model_type == 'demand':
                global model
                try:
                    model = joblib.load(MODEL_PATH)
                except:
                    pass
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'error': msg}), 400
            
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
    app.run(host='0.0.0.0', port=5001, debug=True)
