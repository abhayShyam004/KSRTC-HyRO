import requests
import json

def test_route():
    url = "http://127.0.0.1:5001/api/route"
    
    # Kannur -> Calicut Airport -> Cochin -> TVM
    stops = [
        {"name": "Kannur International Airport (CNN)", "lat": 11.9160, "lon": 75.5680},
        {"name": "Calicut International Airport (CCJ)", "lat": 11.1390, "lon": 75.9520},
        {"name": "Cochin International Airport (COK)", "lat": 10.1518, "lon": 76.3930},
        {"name": "Trivandrum International Airport (TRV)", "lat": 8.4821, "lon": 76.9200}
    ]
    
    payload = {"stops": stops}
    
    print(f"Sending request to {url} with {len(stops)} stops...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            routes = data.get('routes', [])
            if routes:
                route = routes[0]
                total_dist = route.get('distance')
                legs = route.get('legs', [])
                print(f"Route Found! Distance: {total_dist} meters")
                print(f"Total Legs: {len(legs)}")
                
                # Check legs details
                for i, leg in enumerate(legs):
                    summary = leg.get('summary', 'No Summary')
                    dist = leg.get('distance', 0)
                    print(f"  Leg {i+1}: {summary} ({dist}m)")
                    
                    # Check start/end of leg
                    steps = leg.get('steps', [])
                    if steps:
                        print(f"    Start: {steps[0].get('name')}")
                        print(f"    End: {steps[-1].get('name')}")
            else:
                print("No routes in response.")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_route()
