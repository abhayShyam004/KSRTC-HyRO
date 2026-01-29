import hashlib
import json
import time

from .config_loader import ConfigLoader
from .client import OSRMClient
from .cache import LTRUCache
from .validator import RouteValidator

from .geometry_utils import point_in_polygon, get_bbox, bbox_intersects, point_in_bbox

class RoutingEngine:
    STRATEGY_PORTALS_ONLY = "PORTALS_ONLY"
    STRATEGY_PLUS_CITY = "PORTALS_PLUS_CITY"
    STRATEGY_PLUS_HIGHWAY = "PORTALS_PLUS_HIGHWAY"
    
    def __init__(self):
        self.config = ConfigLoader()
        self.client = OSRMClient()
        self.cache = LTRUCache(capacity=200)
        self.validator = RouteValidator(self.config)
        self.portals = self.config.get_portals()
        self.zones = self.config.get_zones()

    def _get_cache_key(self, stops, strategy):
        # Hash(Stops + Strategy + ConfigHash)
        s = json.dumps(stops, sort_keys=True) + strategy + self.config.config_hash
        return hashlib.md5(s.encode()).hexdigest()

    def _validate_stops_access(self, stops):
        """
        v8 Strict Zone Guard:
        Ensure no stop is physically inside a restricted zone without a defined Portal Rule.
        """
        # Find Beach Road Zone
        beach_zone = next((z for z in self.zones if z['id'] == 'ZONE_BEACH_RD'), None)
        if not beach_zone:
            return # Zone config missing, skip check

        polygon = beach_zone['geometry']

        for stop in stops:
            name = stop.get('name', '')
            
            # 1. Check if allowed (Portal Rule Exists)
            is_allowed = False
            for p_name in self.portals:
                if p_name.lower() in name.lower():
                    is_allowed = True
                    break
            
            if is_allowed:
                continue

            # 2. Check Geometry
            # Using tuple (lat, lon) for point_in_polygon
            pt = (float(stop['lat']), float(stop['lon']))
            if point_in_polygon(pt, polygon):
                raise Exception(
                    f"CRITICAL CONFIG ERROR: Stop '{name}' is physically inside the Restricted Beach Road Zone "
                    f"but has no Access Rule defined in portals.json. Please configure a Portal for this stop."
                )

    def _inject_portals(self, stops, strategy):
        # Deep copy to avoid mutating original
        # We transform coordinates based on Operational Logic
        transformed_coords = []
        
        print(f"[ENGINE] Injecting Portals for {len(stops)} stops. Strategy: {strategy}")

        for i, stop in enumerate(stops):
            name = stop.get('name')
            is_origin = (i == 0)
            is_dest = (i == len(stops) - 1)
            
            lat, lon = stop['lat'], stop['lon']
            
            # Fuzzy Match Portal Config
            portal = None
            for p_name, p_config in self.portals.items():
                if p_name.lower() in name.lower():
                    portal = p_config
                    break
            
            # Check Portal Config
            if portal:
                is_access_controlled = (portal.get('type') == 'ACCESS_CONTROLLED_STOP')
                
                # CASE 1: ORIGIN (Start)
                if is_origin:
                    if is_access_controlled:
                        gate = portal.get('exit_gate')
                        lat, lon = gate['lat'], gate['lon']
                    transformed_coords.append(f"{lon:.5f},{lat:.5f}")
                    
                # CASE 2: DESTINATION (End)
                elif is_dest:
                    if is_access_controlled:
                        gate = portal.get('entry_gate')
                        lat, lon = gate['lat'], gate['lon']
                    transformed_coords.append(f"{lon:.5f},{lat:.5f}")
                    
                # CASE 3: INTERMEDIATE
                else:
                    if is_access_controlled:
                        gate = portal.get('entry_gate')
                        transformed_coords.append(f"{gate['lon']:.5f},{gate['lat']:.5f}")
                        print(f"[ENGINE] 🔄 Intermediate Switch: {name} -> Road Gate")
                    else:
                        # Standard Portal (Via points sandwich)
                        entry = portal.get('entry_gate')
                        exit_gate = portal.get('exit_gate')
                        
                        transformed_coords.append(f"{entry['lon']:.5f},{entry['lat']:.5f}") # Enter
                        transformed_coords.append(f"{lon:.5f},{lat:.5f}")           # Stop (Physical)
                        transformed_coords.append(f"{exit_gate['lon']:.5f},{exit_gate['lat']:.5f}") # Exit

            else:
                # Standard Stop (No Portal)
                transformed_coords.append(f"{lon:.5f},{lat:.5f}")

        # 2. Strategy Augmentation (Via Points)
        # Insert into middle of the list
        if strategy == self.STRATEGY_PLUS_CITY:
            mid = max(1, len(transformed_coords) // 2)
            transformed_coords.insert(mid, "75.78800,11.25200") # Palayam
            print(f"[ENGINE] Strategy Insert: Palayam at index {mid}")
            
        elif strategy == self.STRATEGY_PLUS_HIGHWAY:
             mid = max(1, len(transformed_coords) // 2)
             transformed_coords.insert(mid, "75.82000,11.27000") # Bypass
             print(f"[ENGINE] Strategy Insert: Bypass at index {mid}")

        # Helper to parse string "lon,lat" back to float tuple
        final_list = []
        for s in transformed_coords:
             parts = s.split(',')
             final_list.append((float(parts[0]), float(parts[1])))
        
        print(f"[ENGINE] Final Coord Count: {len(final_list)}. Sent to OSRM.")
        return final_list

    def get_optimized_route(self, stops_payload):
        """
        Orchestrates the routing request.
        stops_payload: List of {name, lat, lon}
        """
        # v9.3: Sort stops North-to-South (by latitude, descending)
        # This ensures consistent route direction and can help avoid certain road issues
        stops_payload = sorted(stops_payload, key=lambda s: float(s['lat']), reverse=True)
        print(f"[ENGINE] Stops sorted N→S: {[s['name'] for s in stops_payload]}")
        
        # v8: Audit Stops before Routing
        self._validate_stops_access(stops_payload)

        # v9: Zone-Scoped Strategies
        # Default: Pure OSRM (Portals Only) - Safe for all regions
        strategies = [self.STRATEGY_PORTALS_ONLY]

        # Context Check: Calicut Beach Zone
        beach_zone = next((z for z in self.zones if z['id'] == 'ZONE_BEACH_RD'), None)
        
        if beach_zone:
            stops_pts = [(s['lat'], s['lon']) for s in stops_payload]
            stops_bbox = get_bbox(stops_pts)
            
            # Using zone geometry to compute its approximate bbox
            zone_pts = beach_zone['geometry']
            zone_bbox = get_bbox(zone_pts)
            
            # 1. Fast Filter: BBox Intersection
            if bbox_intersects(stops_bbox, zone_bbox):
                # 2. Relaxed Check: If the route area overlaps the zone, we trigger the strategies.
                # This covers cases where stops straddle the zone (e.g. North/South) but aren't inside.
                print("[ENGINE] 🏙️ Calicut Context Detected: Enabling City/Highway Strategies")
                # Prioritize HIGHWAY then CITY, then default
                strategies = [self.STRATEGY_PLUS_HIGHWAY, self.STRATEGY_PLUS_CITY] + strategies


        last_error = "Unknown Error"
        start_time = time.time()
        TIME_BUDGET = 8.0 # 8 Seconds Total

        for strategy in strategies:
            # Timeout Guard
            if time.time() - start_time > TIME_BUDGET:
                raise Exception(f"Routing Timeout: Exceeded {TIME_BUDGET}s budget")

            cache_key = self._get_cache_key(stops_payload, strategy)
            
            # Check Cache
            cached = self.cache.get(cache_key, self.config.config_hash)
            if cached:
                if 'error' in cached: continue # Negative cache hit
                return cached['data']

            # Build Request
            coords = self._inject_portals(stops_payload, strategy)
            
            try:
                # Call OSRM
                route_data = self.client.get_route(coords)
                
                # Validate
                is_valid, reason = self.validator.validate(route_data)
                
                if is_valid:
                    self.cache.set(cache_key, {'data': route_data}, self.config.config_hash)
                    
                    # DEBUG: Log route details
                    if route_data.get('routes'):
                        r = route_data['routes'][0]
                        leg_count = len(r.get('legs', []))
                        dist = r.get('distance', 0)
                        print(f"[ENGINE] SUCCESS. Legs: {leg_count}, Dist: {dist}m")
                        
                        # Log Geometry Start/End
                        coords = r.get('geometry', {}).get('coordinates', [])
                        if coords:
                            print(f"[ENGINE] Route Start: {coords[0]}")
                            print(f"[ENGINE] Route End: {coords[-1]}")
                        
                        # Log Waypoints (Snapping)
                        waypoints = r.get('waypoints', [])
                        if waypoints:
                             print(f"[ENGINE] OSRM Waypoints: {len(waypoints)}")
                             for i, wp in enumerate(waypoints):
                                 print(f"  [{i}] Snapped To: {wp.get('name')} ({wp.get('location')})")

                        if leg_count > 0:
                            print(f"[ENGINE] First Step: {r['legs'][0]['steps'][0].get('name')}")
                            print(f"[ENGINE] Last Step: {r['legs'][-1]['steps'][-1].get('name')}")
                            
                    return route_data
                else:
                    print(f"Strategy {strategy} Failed: {reason}")
                    self.cache.set(cache_key, {'error': reason}, self.config.config_hash, ttl=30) # Negative Cache
                    last_error = reason
                    
            except Exception as e:
                print(f"Strategy {strategy} Exception: {e}")
                last_error = str(e)
                # Don't cache transient exceptions unless we want to debounce
 
        raise Exception(f"All strategies failed. Last error: {last_error}")
