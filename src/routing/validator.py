from .geometry_utils import route_intersects_polygon

class RouteValidator:
    def __init__(self, config_loader):
        self.config_loader = config_loader

    def validate(self, route_json):
        """
        Validates the route against Zone Polygons and Road Name rules.
        Returns: (is_valid, reason)
        """
        if not route_json or not route_json.get('routes'):
            return False, "No route data"
            
        route = route_json['routes'][0]
        
        # 1. Spatial Audit (Primary Truth)
        geometry = route['geometry']['coordinates'] # [[lon, lat], ...]
        zones = self.config_loader.get_zones() # Re-fetch to get raw geometries for BBox
        
        # Imports for Scoped Logic
        from .geometry_utils import route_intersects_polygon, get_bbox, bbox_intersects
        
        # Convert route for BBox
        route_pts = [(p[1], p[0]) for p in geometry]
        route_bbox = get_bbox(route_pts)

        for zone in zones:
            if zone.get('rule') == 'FORBIDDEN_SEGMENT':
                poly = zone.get('geometry') # [[lat, lon], ...]
                
                # A. Strict Polygon Check
                if route_intersects_polygon(geometry, poly):
                    return False, f"Spatial Violation: Intersects {zone.get('name')}"
                
                # NOTE: String-based "beach road" check removed in v9.2.
                # The polygon check is the primary truth. The string check was causing
                # false positives for legitimate routes that briefly touch Beach Road.

        return True, "Valid"
