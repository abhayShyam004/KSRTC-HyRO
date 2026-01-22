import subprocess
import os
import sys

# Get absolute path to osrm_data
cwd = os.getcwd()
data_path = os.path.join(cwd, 'osrm_data')

print(f"Data path: {data_path}")

# Docker commands
cmds = [
    f'docker run -t -v "{data_path}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/kerala-latest.osm.pbf',
    f'docker run -t -v "{data_path}:/data" osrm/osrm-backend osrm-contract /data/kerala-latest.osrm'
]

for cmd in cmds:
    print(f"Executing: {cmd}")
    try:
        # We use shell=True but Python handles the string passing to cmd better than manual typing
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

print("OSRM processing complete.")
