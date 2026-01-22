# src/optimize_route.py

import random
import numpy as np
import requests
from deap import base, creator, tools, algorithms

def get_travel_time_matrix(bus_stops_data):
    """
    Queries the local OSRM server to get a matrix of real-world travel times,
    with robust URL formatting and error checking.
    """
    if not bus_stops_data:
        print("❌ Error: bus_stops_data is empty. Cannot query OSRM.")
        return None, None

    stop_names = list(bus_stops_data.keys())
    coords = [bus_stops_data[name] for name in stop_names]
    
    # Ensure coords are in (lat, lon) format and are valid numbers
    if not all(isinstance(lat, (int, float)) and isinstance(lon, (int, float)) for lat, lon in coords):
        print("❌ Error: Invalid coordinate data found.")
        return None, None

    # Format coordinates for OSRM API call: {longitude},{latitude}
    # Use repr() to ensure decimal points are periods, regardless of system locale
    locations_str = ";".join([f"{lon:.6f},{lat:.6f}" for lat, lon in coords])
    
    url = f"http://localhost:5000/table/v1/driving/{locations_str}?annotations=duration"
    
    # --- ADDED DEBUGGING PRINT ---
    print(f"--- Querying OSRM with URL: {url} ---")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'durations' not in data:
            print(f"❌ OSRM Error: 'durations' not found in response. Response: {data}")
            return None, None

        time_matrix = np.array(data['durations'])
        return time_matrix, stop_names
    except requests.exceptions.RequestException as e:
        print(f"❌ OSRM API Error: {e}")
        print("Please ensure the OSRM Docker server is running correctly.")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None


# The 'solve_tsp_with_roads' function remains exactly the same as before.
def solve_tsp_with_roads(bus_stops_data):
    """Solves the TSP using real road network travel times from OSRM."""
    time_matrix, stop_names = get_travel_time_matrix(bus_stops_data)
    if time_matrix is None:
        return None
    
    num_stops = len(stop_names)

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)
    toolbox = base.Toolbox()
    toolbox.register("indices", random.sample, range(num_stops), num_stops)
    toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def evaluate_route_time(individual):
        total_time = sum(time_matrix[individual[i], individual[i+1]] for i in range(num_stops - 1))
        total_time += time_matrix[individual[-1], individual[0]]
        return (total_time,)

    toolbox.register("evaluate", evaluate_route_time)
    toolbox.register("mate", tools.cxOrdered)
    toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.05)
    toolbox.register("select", tools.selTournament, tournsize=3)

    print(f"\n--- 🧬 Optimizing route for {num_stops} stops using real road network ---")
    population = toolbox.population(n=50)
    hof = tools.HallOfFame(1)
    algorithms.eaSimple(population, toolbox, cxpb=0.7, mutpb=0.2, ngen=150, halloffame=hof, verbose=False)
    
    best_route_indices = hof[0]
    best_route = [stop_names[i] for i in best_route_indices]
    
    print("--- 🏆 Optimization Complete ---")
    return best_route