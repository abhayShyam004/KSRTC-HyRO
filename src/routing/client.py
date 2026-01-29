import requests
import time
import threading

class OSRMClient:
    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"
    
    def __init__(self, base_url="https://router.project-osrm.org", failure_threshold=3, cooldown=30):
        self.base_url = base_url
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        
        self.state = self.STATE_CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.sem = threading.Semaphore(20) # Concurrency Cap

    def get_route(self, coords_list, timeout=4):
        # Circuit Check
        if self.state == self.STATE_OPEN:
            if time.time() - self.last_failure_time > self.cooldown:
                self.state = self.STATE_HALF_OPEN
            else:
                raise Exception("Circuit Open: Upstream Unavailable")

        # Prepare URL
        coords_str = ";".join([f"{lon:.5f},{lat:.5f}" for lon, lat in coords_list])
        url = f"{self.base_url}/route/v1/driving/{coords_str}?geometries=geojson&overview=full&steps=true"

        try:
            with self.sem:
                resp = requests.get(url, timeout=timeout)
            
            if resp.status_code >= 500:
                self._record_failure()
                raise Exception(f"OSRM Server Error {resp.status_code}")
                
            self._reset_circuit()
            return resp.json()
            
        except requests.exceptions.RequestException as e:
            self._record_failure()
            raise Exception(f"OSRM Connection Error: {e}")

    def _record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = self.STATE_OPEN
            
    def _reset_circuit(self):
        self.state = self.STATE_CLOSED
        self.failures = 0
