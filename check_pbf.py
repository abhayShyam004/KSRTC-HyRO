import os

path = 'osrm_data/kerala-latest.osm.pbf'
if os.path.exists(path):
    size = os.path.getsize(path)
    print(f"File exists. Size: {size / (1024*1024):.2f} MB")
else:
    print("File DOES NOT exist.")
