# src/run_full_pipeline.py

import os
import pandas as pd
from sklearn.cluster import KMeans
import configparser
import folium
import requests
import json

from optimize_route import solve_tsp_with_roads as solve_tsp
from data_preprocessing import load_data

def get_route_geometry(route_coords):
    """
    Queries the OSRM route service to get the actual road network geometry
    for a given sequence of coordinates.
    """
    locations_str = ";".join([f"{lon:.6f},{lat:.6f}" for lat, lon in route_coords])
    url = f"http://localhost:5000/route/v1/driving/{locations_str}?geometries=geojson"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # The geometry is returned in [lon, lat] format
        route_geometry = data['routes'][0]['geometry']['coordinates']
        # We need to flip it to [lat, lon] for Folium
        return [[coord[1], coord[0]] for coord in route_geometry]
    except Exception as e:
        print(f"❌ Could not fetch route geometry from OSRM: {e}")
        return None

def run_integrated_pipeline():
    """
    Runs the full pipeline and plots the true road-network route on the map.
    """
    print("--- 🚀 Starting KSRTC-HyRO Integrated Pipeline ---")

    config = configparser.ConfigParser()
    script_dir = os.path.dirname(__file__)
    config_path = os.path.join(script_dir, '..', 'config.ini')
    config.read(config_path)

    n_clusters = config.getint('CLUSTERING', 'n_clusters')
    cluster_to_optimize = config.getint('OPTIMIZATION', 'cluster_to_optimize')
    sample_size = config.getint('OPTIMIZATION', 'sample_size')

    print(f"Configuration: n_clusters={n_clusters}, optimizing_zone={cluster_to_optimize}, sample_size={sample_size}")
    
    os.makedirs('output', exist_ok=True)
    
    df = load_data(is_dummy=True)
    if df is None: return
    stop_locations_df = df[['bus_stop_id', 'lat', 'lon']].drop_duplicates().set_index('bus_stop_id')

    print("\n--- 🗺️  Performing Bus Stop Clustering ---")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    stop_locations_df['cluster'] = kmeans.fit_predict(stop_locations_df[['lat', 'lon']])
    stop_locations_df.to_csv('output/bus_stop_clusters.csv')
    print("✅ Cluster assignments saved.")

    target_cluster = stop_locations_df[stop_locations_df['cluster'] == cluster_to_optimize]
    
    if target_cluster.empty:
        print(f"❌ Error: No bus stops found for Zone {cluster_to_optimize}.")
        return

    if len(target_cluster) > sample_size:
        print(f"\n⚠️  Cluster is too large. Taking a random sample of {sample_size}.")
        target_cluster = target_cluster.sample(n=sample_size, random_state=42)

    stops_to_optimize = {f"Stop_{idx}": (row['lat'], row['lon']) for idx, row in target_cluster.iterrows()}
    
    optimized_route_names = solve_tsp(stops_to_optimize)

    if optimized_route_names is None:
        print("❌ Route optimization failed. Halting pipeline.")
        return

    route_df = pd.DataFrame({'step': range(1, len(optimized_route_names) + 1), 'stop_name': optimized_route_names})
    route_df.to_csv(f'output/optimized_route_for_zone_{cluster_to_optimize}.csv', index=False)
    print("✅ Optimized route saved.")

    print("\n--- 🗺️  Generating Final Interactive Map with Real Route ---")
    map_center = [9.9312, 76.2673]
    m = folium.Map(location=map_center, zoom_start=11)
    colors = ['blue', 'green', 'red', 'purple', 'orange', 'darkred', 'cadetblue']
    
    for idx, row in stop_locations_df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']], radius=4,
            color=colors[int(row['cluster'])], fill=True, fill_color=colors[int(row['cluster'])],
            tooltip=f"Stop ID: {idx}<br>Zone: {row['cluster']}"
        ).add_to(m)

    # Get the coordinates in the optimized order
    optimized_route_coords = [stops_to_optimize[name] for name in optimized_route_names]
    
    # --- NEW: Get the detailed road path from OSRM ---
    road_network_path = get_route_geometry(optimized_route_coords)
    
    if road_network_path:
        folium.PolyLine(
            locations=road_network_path,
            color='black', weight=4, opacity=0.8,
            tooltip=f'Optimized Route for Zone {cluster_to_optimize}'
        ).add_to(m)

    map_path = 'output/kochi_final_road_route_map.html'
    m.save(map_path)
    print(f"✅ Final interactive map saved to {map_path}")

if __name__ == "__main__":
    run_integrated_pipeline()