# src/cluster_stops.py

import pandas as pd
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# Import our data loading function
from data_preprocessing import load_data

def perform_clustering():
    """
    Loads bus stop data, clusters them based on location, and visualizes the result.
    """
    print("--- Starting Bus Stop Clustering ---")
    
    # 1. Load data
    df = load_data(is_dummy=True)
    
    # 2. Prepare data for clustering
    # We only need unique bus stop locations
    stop_locations = df[['bus_stop_id', 'lat', 'lon']].drop_duplicates().reset_index(drop=True)
    print("Unique bus stop locations found:")
    print(stop_locations)
    
    # We will cluster based on latitude and longitude
    X = stop_locations[['lat', 'lon']]
    
    # 3. Apply K-Means algorithm
    # Let's say we want to find 3 clusters or 'zones'
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X)
    
    # Get the cluster assignment for each bus stop
    stop_locations['cluster'] = kmeans.labels_
    print("\nBus stops with their assigned clusters:")
    print(stop_locations)
    
    # 4. Visualize the clusters
    print("\n🎨 Generating cluster map...")
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        stop_locations['lon'], 
        stop_locations['lat'], 
        c=stop_locations['cluster'],
        cmap='viridis', # A nice color map
        s=200 # Marker size
    )
    # Add labels for each point
    for i, txt in enumerate(stop_locations['bus_stop_id']):
        plt.annotate(f"Stop {txt}", (stop_locations['lon'][i], stop_locations['lat'][i]), xytext=(5,5), textcoords='offset points')

    plt.title('KSRTC Bus Stop Clusters')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)
    plt.legend(handles=scatter.legend_elements()[0], labels=['Zone 0', 'Zone 1', 'Zone 2'])
    plt.show()
    print("--- Clustering complete ---")

if __name__ == "__main__":
    perform_clustering()