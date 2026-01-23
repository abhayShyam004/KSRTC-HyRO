"""
Route Profitability ML Model for KSRTC-HyRO
Predicts the most effective and profitable routes based on:
- Distance optimization
- Expected passenger demand
- Fuel cost estimation
- Revenue potential
"""
import numpy as np
from itertools import permutations
import datetime

# Constants
TICKET_PRICE_PER_KM = 1.2  # Average ticket price per km in INR
DIESEL_PRICE = 95.21  # INR per litre
EMPTY_MILEAGE = 4.5  # km/L when empty
FULL_MILEAGE = 3.5  # km/L when full load
BUS_CAPACITY = 55


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate approximate distance between two coordinates in km (Haversine)"""
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


def get_time_multiplier():
    """Get demand multiplier based on current time"""
    hour = datetime.datetime.now().hour
    
    # Peak hours have higher demand
    if 8 <= hour <= 10:  # Morning peak
        return 1.5
    elif 17 <= hour <= 19:  # Evening peak
        return 1.4
    elif 6 <= hour <= 8:  # Early morning
        return 1.1
    elif 19 <= hour <= 21:  # Night
        return 1.0
    else:  # Off-peak
        return 0.8


def predict_passengers_for_stop(stop, time_multiplier=1.0):
    """Predict expected passengers at a stop"""
    base_passengers = 8  # Base passengers per stop
    
    # Category multipliers
    category_multipliers = {
        'transport_hub': 2.0,
        'airport': 1.8,
        'commercial': 1.5,
        'tourist': 1.3,
        'regular': 1.0
    }
    
    category = stop.get('category', 'regular')
    demand_mult = float(stop.get('demand_multiplier', 1.0))
    cat_mult = category_multipliers.get(category, 1.0)
    
    return base_passengers * demand_mult * cat_mult * time_multiplier


def calculate_route_profitability(stops, distances_matrix=None):
    """
    Calculate profitability for a given route (ordered list of stops)
    Returns: profit, revenue, fuel_cost, passengers, distance
    """
    if len(stops) < 2:
        return 0, 0, 0, 0, 0
    
    time_mult = get_time_multiplier()
    total_distance = 0
    total_passengers = 0
    
    # Calculate total distance and passengers
    for i in range(len(stops) - 1):
        s1, s2 = stops[i], stops[i + 1]
        
        # Distance between consecutive stops
        dist = calculate_distance(
            float(s1['lat']), float(s1['lon']),
            float(s2['lat']), float(s2['lon'])
        )
        total_distance += dist
        
        # Passengers at each stop
        total_passengers += predict_passengers_for_stop(s1, time_mult)
    
    # Add last stop passengers
    total_passengers += predict_passengers_for_stop(stops[-1], time_mult)
    
    # Cap passengers at bus capacity
    total_passengers = min(total_passengers, BUS_CAPACITY)
    
    # Revenue estimation (passengers × average distance × price per km)
    avg_trip_distance = total_distance * 0.6  # Assume avg passenger travels 60% of route
    revenue = total_passengers * avg_trip_distance * TICKET_PRICE_PER_KM
    
    # Fuel cost calculation with load adjustment
    load_factor = total_passengers / BUS_CAPACITY
    adjusted_mileage = EMPTY_MILEAGE - (load_factor * (EMPTY_MILEAGE - FULL_MILEAGE))
    fuel_litres = total_distance / adjusted_mileage
    fuel_cost = fuel_litres * DIESEL_PRICE
    
    # Profit
    profit = revenue - fuel_cost
    
    return profit, revenue, fuel_cost, total_passengers, total_distance


def optimize_route_order(stops):
    """
    Find the optimal order of stops to maximize profitability
    Uses a greedy nearest-neighbor approach for efficiency
    """
    if len(stops) <= 2:
        return stops, calculate_route_profitability(stops)
    
    # Start with the highest demand stop
    remaining = list(stops)
    remaining.sort(key=lambda s: float(s.get('demand_multiplier', 1.0)), reverse=True)
    
    optimized = [remaining.pop(0)]
    
    # Greedy nearest neighbor with demand weighting
    while remaining:
        last = optimized[-1]
        
        # Score = demand / distance (prefer high demand, close stops)
        best_score = -1
        best_idx = 0
        
        for i, stop in enumerate(remaining):
            dist = calculate_distance(
                float(last['lat']), float(last['lon']),
                float(stop['lat']), float(stop['lon'])
            )
            demand = float(stop.get('demand_multiplier', 1.0))
            
            # Avoid division by zero
            score = demand / max(dist, 0.1)
            
            if score > best_score:
                best_score = score
                best_idx = i
        
        optimized.append(remaining.pop(best_idx))
    
    profit, revenue, fuel_cost, passengers, distance = calculate_route_profitability(optimized)
    
    return optimized, {
        'profit': round(profit, 2),
        'revenue': round(revenue, 2),
        'fuel_cost': round(fuel_cost, 2),
        'passengers': int(passengers),
        'distance_km': round(distance, 2)
    }


def find_most_profitable_routes(all_stops, num_suggestions=5, min_stops=3, max_stops=6):
    """
    Analyze all possible route combinations and find the most profitable ones
    Returns top N most profitable route suggestions
    """
    if len(all_stops) < min_stops:
        return []
    
    suggestions = []
    time_mult = get_time_multiplier()
    
    # Group stops by district for regional routes
    districts = {}
    for stop in all_stops:
        district = stop.get('district', 'Unknown')
        if district not in districts:
            districts[district] = []
        districts[district].append(stop)
    
    # Strategy 1: High-demand hub connections
    hubs = [s for s in all_stops if float(s.get('demand_multiplier', 1.0)) >= 1.5]
    
    if len(hubs) >= 3:
        optimized, metrics = optimize_route_order(hubs[:max_stops])
        if metrics['profit'] > 0:
            suggestions.append({
                'route_name': 'Hub Express',
                'description': 'Connects major transport hubs for maximum passenger pickup',
                'stops': optimized,
                'metrics': metrics,
                'score': metrics['profit'] / max(metrics['distance_km'], 1)  # Profit per km
            })
    
    # Strategy 2: District-wise profitable routes
    for district, stops in districts.items():
        if len(stops) >= min_stops:
            optimized, metrics = optimize_route_order(stops[:max_stops])
            if metrics['profit'] > 0:
                suggestions.append({
                    'route_name': f'{district} Circuit',
                    'description': f'Optimized route within {district} district',
                    'stops': optimized,
                    'metrics': metrics,
                    'score': metrics['profit'] / max(metrics['distance_km'], 1)
                })
    
    # Strategy 3: Airport connector
    airports = [s for s in all_stops if s.get('category') == 'airport']
    if airports:
        # Find nearby high-demand stops to each airport
        for airport in airports:
            nearby = []
            for stop in all_stops:
                if stop['bus_stop_id'] != airport['bus_stop_id']:
                    dist = calculate_distance(
                        float(airport['lat']), float(airport['lon']),
                        float(stop['lat']), float(stop['lon'])
                    )
                    if dist < 50:  # Within 50km
                        nearby.append((stop, dist))
            
            nearby.sort(key=lambda x: x[1])
            route_stops = [airport] + [s[0] for s in nearby[:max_stops-1]]
            
            if len(route_stops) >= min_stops:
                optimized, metrics = optimize_route_order(route_stops)
                if metrics['profit'] > 0:
                    suggestions.append({
                        'route_name': f'{airport["name"]} Shuttle',
                        'description': 'Airport connector with high passenger potential',
                        'stops': optimized,
                        'metrics': metrics,
                        'score': metrics['profit'] / max(metrics['distance_km'], 1) * 1.2  # Boost airport routes
                    })
    
    # Strategy 4: Commercial corridor
    commercial = [s for s in all_stops if s.get('category') in ['commercial', 'transport_hub']]
    if len(commercial) >= min_stops:
        optimized, metrics = optimize_route_order(commercial[:max_stops])
        if metrics['profit'] > 0:
            suggestions.append({
                'route_name': 'Business Express',
                'description': 'Connects major commercial centers and business hubs',
                'stops': optimized,
                'metrics': metrics,
                'score': metrics['profit'] / max(metrics['distance_km'], 1)
            })
    
    # Sort by profitability score and return top N
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    # Clean up output
    for s in suggestions:
        s['stops'] = [{'id': st['bus_stop_id'], 'name': st['name']} for st in s['stops']]
        del s['score']
    
    return suggestions[:num_suggestions]


def get_route_recommendations(all_stops):
    """
    Main function to get route recommendations for the admin dashboard
    """
    return {
        'generated_at': datetime.datetime.now().isoformat(),
        'time_period': 'peak' if get_time_multiplier() > 1.2 else 'off-peak',
        'recommendations': find_most_profitable_routes(all_stops)
    }
