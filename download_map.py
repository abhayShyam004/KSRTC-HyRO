import requests
import os

url = "https://download.geofabrik.de/asia/india/kerala-latest.osm.pbf"
output_path = "osrm_data/kerala-latest.osm.pbf"

if not os.path.exists("osrm_data"):
    os.makedirs("osrm_data")

print(f"Downloading {url} to {output_path}...")
try:
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")
except Exception as e:
    print(f"Error: {e}")
