import subprocess
import os
import time

cwd = os.getcwd()
data_path = os.path.join(cwd, 'osrm_data')

# Commands to run
# 1. OSRM Server
# We use --algorithm mld or ch? Default is usually fine if contracted.
cmd_osrm = f'docker run -t -i -p 5000:5000 -v "{data_path}:/data" osrm/osrm-backend osrm-routed /data/kerala-latest.osrm'

# 2. Flask Backend
cmd_flask = 'python src/app.py'

# 3. Frontend
cmd_frontend = 'python -m http.server'

print("Starting OSRM Server in new window...")
subprocess.Popen(f'start "OSRM Server (Port 5000)" cmd /k {cmd_osrm}', shell=True)

print("Waiting 5 seconds for OSRM to initialize...")
time.sleep(5)

print("Starting Flask Backend in new window...")
subprocess.Popen(f'start "Flask Backend (Port 5001)" cmd /k {cmd_flask}', shell=True)

print("Starting Frontend Server in new window...")
subprocess.Popen(f'start "Frontend (Port 8000)" cmd /k {cmd_frontend}', shell=True)

print("All services launched! Check the popped-up terminal windows.")
print("Access the app at: http://localhost:8000/ksrtc_driver_app.html")
