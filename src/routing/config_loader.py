import json
import os
import hashlib

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')

class ConfigLoader:
    def __init__(self):
        self.zones = self._load_json('zones.json')
        self.portals = self._load_json('portals.json')
        self.config_hash = self._compute_hash()

    def _load_json(self, filename):
        path = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(path):
            print(f"Config missing: {path}")
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Config load error {filename}: {e}")
            return {}

    def _compute_hash(self):
        s = json.dumps(self.zones, sort_keys=True) + json.dumps(self.portals, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()

    def get_zones(self):
        return self.zones.get('zones', [])

    def get_portals(self):
        return self.portals.get('portals', {})
