"""
Route Profitability ML Model for KSRTC-HyRO
Predicts the most effective and profitable routes based on:
- Distance optimization
- Expected passenger demand (Risk Discounted)
- Fuel cost estimation
- Revenue potential vs Cost of Detours
"""
import numpy as np
import joblib
import pandas as pd
import os
import datetime
import json
import math

# Load Traffic Model if available
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
TRAFFIC_MODEL_PATH = os.path.join(MODELS_DIR, 'traffic_model.pkl')
DEMAND_MODEL_PATH = os.path.join(MODELS_DIR, 'passenger_demand_model.pkl')
METADATA_PATH = os.path.join(MODELS_DIR, 'model_metadata.json')

# --- CONFIGURATION ---
BUS_CAPACITY = 55
EMPTY_MILEAGE = 4.5
FULL_MILEAGE = 3.5
DIESEL_PRICE = 95.21
TICKET_PRICE_PER_KM = 1.5  # Avg fare per km
AVG_TRIP_LENGTH_RATIO = 0.6 # Avg passenger travels 60% of route

# ECONOMIC PARAMETERS
TIME_VALUE_PER_MIN = 5.0 # Penalty for delaying the bus (Fuel + Driver + Opportunity Cost)
AVG_TICKET_PRICE_PER_BOARDING = 12.0 # Flat avg revenue per boarding if using boardings count directly

traffic_model = None
demand_model = None
model_mae = 0.0

# --- LOAD MODELS ---
try:
    traffic_model = joblib.load(TRAFFIC_MODEL_PATH)
except:
    pass 

try:
    demand_model = joblib.load(DEMAND_MODEL_PATH)
except:
    pass

try:
    with open(METADATA_PATH, 'r') as f:
        meta = json.load(f)
        model_mae = meta.get('mae', 0.0)
except:
    pass # Default to 0 risk discount if unknown

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine distance in km"""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def predict_duration(distance_km):
    """Predict duration using ML model if available, else fallback to 30kmph"""
    if traffic_model:
        try:
            now = datetime.datetime.now()
            X = pd.DataFrame([{
                'distance_km': distance_km,
                'hour_of_day': now.hour,
                'day_of_week': now.weekday(),
                'is_peak': 1 if (8 <= now.hour <= 10) or (17 <= now.hour <= 19) else 0
            }])
            pred = traffic_model.predict(X)[0]
            return max(5, int(pred)) # Minimum 5 mins
        except Exception:
            pass
            
    # Fallback: 30kmph average speed in city
    return int((distance_km / 30) * 60)

def predict_passengers_for_stops(stops_list, conservative=False):
    """
    Batch predict passengers.
    Args:
        conservative (bool): If True, applies Risk Discount (20% margin).
                             If False, returns raw expectation (for display).
    """
    if not demand_model or not stops_list:
        # Fallback: Multiplier * 15 (boosted base)
        base = 15 
        return [float(s.get('demand_multiplier', 1.0)) * base for s in stops_list]
    
    now = datetime.datetime.now()
    hour = now.hour
    day = now.weekday()
    is_peak = 1 if (8 <= hour <= 10) or (17 <= hour <= 19) else 0
    
    X = pd.DataFrame([{
        'stop_id': s['bus_stop_id'],
        'hour_of_day': hour,
        'day_of_week': day,
        'is_peak': is_peak
    } for s in stops_list])
    
    try:
        preds = demand_model.predict(X)
        
        if conservative:
            # RISK DISCOUNT: 20% margin instead of raw MAE subtraction
            # MAX(0, Pred * 0.8)
            return [max(0, p * 0.8) for p in preds]
        else:
            # RAW DISPLAY: Show full potential (maybe even slightly optimistic?)
            return [max(1, p) for p in preds]
    except:
        return [float(s.get('demand_multiplier', 1.0)) * 15 for s in stops_list]

def calculate_route_profitability(stops):
    """
    Calculate profitability for a given route (ordered list of stops)
    Returns: profit, revenue, fuel_cost, passengers, distance, duration
    """
    if len(stops) < 2:
        return 0, 0, 0, 0, 0, 0
    
    total_distance = 0
    
    # Calculate Distances
    for i in range(len(stops) - 1):
        s1, s2 = stops[i], stops[i + 1]
        dist = calculate_distance(float(s1['lat']), float(s1['lon']), float(s2['lat']), float(s2['lon']))
        total_distance += dist
        
    # Batch Predict Passengers (RAW for Display)
    passenger_counts = predict_passengers_for_stops(stops, conservative=False)
    total_passengers = sum(passenger_counts)
    
    # Cap passengers at bus capacity (Display can show capacity, but revenue capped)
    capped_passengers = min(total_passengers, BUS_CAPACITY)
    
    # Revenue estimation
    revenue = capped_passengers * AVG_TICKET_PRICE_PER_BOARDING
    
    # Fuel cost
    load_factor = capped_passengers / BUS_CAPACITY
    adjusted_mileage = EMPTY_MILEAGE - (load_factor * (EMPTY_MILEAGE - FULL_MILEAGE))
    
    # Avoid zero division
    if adjusted_mileage <= 0: adjusted_mileage = 3.5
    
    fuel_litres = total_distance / adjusted_mileage
    fuel_cost = fuel_litres * DIESEL_PRICE
    
    # Predict Duration (Traffic Aware)
    duration = predict_duration(total_distance)
    
    # Profit (Simple)
    profit = revenue - fuel_cost
    
    return profit, revenue, fuel_cost, total_passengers, total_distance, duration

def enrich_route_economically(current_stops, all_stops_pool, max_additions=3, corridor_radius=3.0):
    """
    Iteratively inserts high-value intermediate stops.
    ECONOMIC LOGIC: Uses CONSERVATIVE predictions for decision making.
    """
    final_route = list(current_stops)
    
    # If pool is empty or route too short, return matching format
    if not all_stops_pool or len(final_route) < 2:
        return final_route
    
    # Filter candidates in "Corridor" (Bounding Box Optimization)
    lats = [float(s['lat']) for s in final_route]
    lons = [float(s['lon']) for s in final_route]
    min_lat, max_lat = min(lats) - 0.05, max(lats) + 0.05
    min_lon, max_lon = min(lons) - 0.05, max(lons) + 0.05
    
    current_ids = {s['bus_stop_id'] for s in final_route}
    candidates = [
        s for s in all_stops_pool 
        if s['bus_stop_id'] not in current_ids
        and min_lat <= float(s['lat']) <= max_lat
        and min_lon <= float(s['lon']) <= max_lon
    ]
    
    if not candidates:
        return final_route
    
    # BATCH PREDICT candidates (CONSERVATIVE for Decision)
    candidate_demands = predict_passengers_for_stops(candidates, conservative=True)
    candidate_map = {c['bus_stop_id']: d for c, d in zip(candidates, candidate_demands)}
    
    # Greedy Insertion Loop
    for _ in range(max_additions):
        best_profit_gain = 0
        best_candidate = None
        best_insert_idx = -1
        
        # Try inserting each candidate at each position
        for cand in candidates:
            if cand['bus_stop_id'] in current_ids:
                continue
                
            pred_demand = candidate_map.get(cand['bus_stop_id'], 0)
            if pred_demand < 1: # Ignore low demand noise
                continue
                
            revenue_gain = pred_demand * AVG_TICKET_PRICE_PER_BOARDING
            
            # Find best insertion point for this candidate to minimize detour
            local_best_detour_cost = float('inf')
            local_best_idx = -1
            
            for i in range(len(final_route) - 1):
                s1 = final_route[i]
                s2 = final_route[i+1]
                
                # Distances
                d1 = calculate_distance(float(s1['lat']), float(s1['lon']), float(cand['lat']), float(cand['lon']))
                d2 = calculate_distance(float(cand['lat']), float(cand['lon']), float(s2['lat']), float(s2['lon']))
                d_orig = calculate_distance(float(s1['lat']), float(s1['lon']), float(s2['lat']), float(s2['lon']))
                
                detour_km = (d1 + d2) - d_orig
                
                # Traffic & Fuel Cost
                # Fuel
                fuel_cost = (detour_km / 4.0) * DIESEL_PRICE
                
                # Time
                # We can approximate time = detour_km / 30kmph * 60 min OR use prediction
                # Using linear approx for speed here to be fast inside double loop
                detour_min = (detour_km / 30) * 60 
                time_cost = detour_min * TIME_VALUE_PER_MIN
                
                total_cost = fuel_cost + time_cost
                
                if total_cost < local_best_detour_cost:
                    local_best_detour_cost = total_cost
                    local_best_idx = i + 1
            
            # Net Benefit
            net_profit_gain = revenue_gain - local_best_detour_cost
            
            if net_profit_gain > best_profit_gain and net_profit_gain > 0:
                best_profit_gain = net_profit_gain
                best_candidate = cand
                best_insert_idx = local_best_idx
        
        # If we found a profitable insertion
        if best_candidate and best_profit_gain > 10: # Minimum ₹10 gain to justify complexity
            final_route.insert(best_insert_idx, best_candidate)
            current_ids.add(best_candidate['bus_stop_id'])
            # print(f"[OPTIMIZER] Added {best_candidate['name']} (+₹{best_profit_gain:.2f})")
        else:
            break # No more profitable additions possible
            
    return final_route

def optimize_route_order(stops, all_stops_pool=None):
    """
    Refined Optimizer:
    1. Basic Greedy Sort (if unordered)
    2. Economic Enrichment (Insert intermediate stops)
    """
    # 1. Start with provided stops
    base_route = list(stops)
    
    # Use passed pool or fallback to empty (prevent DB hit here)
    if all_stops_pool is None:
        all_stops_pool = []
        
    enriched_route = enrich_route_economically(base_route, all_stops_pool)
    
    # Calculate Final Stats
    profit, revenue, fuel_cost, passengers, distance, duration = calculate_route_profitability(enriched_route)
    
    return enriched_route, {
        'profit': round(profit, 2),
        'revenue': round(revenue, 2),
        'fuel_cost': round(fuel_cost, 2),
        'passengers': int(passengers),
        'distance_km': round(distance, 2),
        'duration_min': int(duration)
    }

def get_route_recommendations(all_stops):
    """Admin dashboard recommendations (Stub)"""
    return {'recommendations': []}
