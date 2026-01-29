import time

class LTRUCache:
    def __init__(self, capacity=100, default_ttl=300):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self.cache = {} # Key -> (ConfigHash, Value, ExpiryTime)
        self.order = [] # LRU order

    def get(self, key, config_hash):
        if key in self.cache:
            stored_hash, value, expiry = self.cache[key]
            if time.time() > expiry:
                self._remove(key)
                return None
            if stored_hash != config_hash:
                self._remove(key)
                return None
            
            # Refresh LRU
            self.order.remove(key)
            self.order.append(key)
            return value
        return None

    def set(self, key, value, config_hash, ttl=None):
        ttl = ttl or self.default_ttl
        self.cache[key] = (config_hash, value, time.time() + ttl)
        if key in self.order:
            self.order.remove(key)
        self.order.append(key)
        
        if len(self.order) > self.capacity:
            lru = self.order.pop(0)
            del self.cache[lru]
            
    def _remove(self, key):
        if key in self.cache:
            del self.cache[key]
        if key in self.order:
            self.order.remove(key)
