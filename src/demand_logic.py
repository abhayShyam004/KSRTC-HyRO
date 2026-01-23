"""
Custom Demand Logic Model for KSRTC-HyRO.
Calculates demand multiplier based on stop characteristics effectively replacing manual input.
"""

def calculate_demand_multiplier(category, district, lat=None, lon=None):
    """
    Calculate demand multiplier based on stop metadata.
    
    Base Multiplier: 1.0
    
    Category Boosts:
    - Transport Hub: +0.8
    - Airport: +1.0
    - Commercial: +0.5
    - Tourist: +0.4
    - Regular: +0.0
    
    District Factors (based on population density/activity):
    - Ernakulam, Thiruvananthapuram, Kozhikode: +0.2 (High density)
    - Thrissur, Kollam, Kannur: +0.1 (Medium density)
    - Others: +0.0
    
    Returns:
        float: Calculated demand multiplier (rounded to 2 decimal places)
    """
    base_multiplier = 1.0
    
    # 1. Category Factor
    category_boosts = {
        'transport_hub': 0.8,
        'airport': 1.0,
        'commercial': 0.5,
        'tourist': 0.4,
        'regular': 0.0
    }
    
    # Normalize category input
    cat_key = category.lower().replace(' ', '_') if category else 'regular'
    base_multiplier += category_boosts.get(cat_key, 0.0)
    
    # 2. District Factor
    high_density = ['ernakulam', 'thiruvananthapuram', 'kozhikode']
    medium_density = ['thrissur', 'kollam', 'kannur', 'alappuzha', 'kottayam', 'palakkad', 'malappuram']
    
    dist_key = district.lower() if district else ''
    
    if dist_key in high_density:
        base_multiplier += 0.2
    elif dist_key in medium_density:
        base_multiplier += 0.1
        
    # 3. Location Heuristics (Placeholder for future geo-spatial features)
    # For now, we assume lat/lon might adjust scores if near specific coordinates,
    # but we'll keep it simple for this version.
    
    return round(base_multiplier, 2)
