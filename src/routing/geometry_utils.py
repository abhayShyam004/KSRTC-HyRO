import math

def point_in_polygon(point, polygon):
    """
    Ray-casting algorithm to check if point is in polygon.
    point: (lat, lon)
    polygon: List of (lat, lon) vertices
    """
    lat, lon = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        intersect = ((yi > lon) != (yj > lon)) and \
                    (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside

def segments_intersect(p1, p2, p3, p4):
    """
    Check if line segment p1-p2 intersects with segment p3-p4.
    p: (lat, lon)
    """
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def route_intersects_polygon(route_coords, polygon):
    """
    Check if any segment of the route intersects with any edge of the polygon.
    route_coords: List of [lon, lat] (OSRM format) -> converted to (lat, lon)
    polygon: List of [lat, lon]
    """
    # Convert OSRM [lon, lat] to [lat, lon] match polygon format
    route_points = [(p[1], p[0]) for p in route_coords]
    
    # Check 1: Any point inside?
    for pt in route_points:
        if point_in_polygon(pt, polygon):
            return True
            
    # Check 2: Any intersection?
    poly_len = len(polygon)
    for i in range(len(route_points) - 1):
        r1 = route_points[i]
        r2 = route_points[i+1]
        
        for j in range(poly_len):
            p1 = polygon[j]
            p2 = polygon[(j + 1) % poly_len]
            
            if segments_intersect(r1, r2, p1, p2):
                return True
                
    return False

# --- v9 BBox Utilities ---

def get_bbox(points):
    """
    Returns (min_lat, min_lon, max_lat, max_lon) for a list of (lat, lon) points.
    """
    if not points:
        return (0, 0, 0, 0)
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return (min(lats), min(lons), max(lats), max(lons))

def bbox_intersects(box1, box2):
    """
    Check if two BBoxes intersect.
    Box: (min_lat, min_lon, max_lat, max_lon)
    """
    # Check for disjoint
    if (box1[2] < box2[0] or box2[2] < box1[0] or # Lat disjoint
        box1[3] < box2[1] or box2[3] < box1[1]):  # Lon disjoint
        return False
    return True

def point_in_bbox(point, bbox):
    """
    Check if point (lat, lon) is inside bbox (min_lat, min_lon, max_lat, max_lon).
    """
    lat, lon = point
    return bbox[0] <= lat <= bbox[2] and bbox[1] <= lon <= bbox[3]
