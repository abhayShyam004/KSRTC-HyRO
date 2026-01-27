import requests
import json
import time

def test_predict_counts():
    url = "http://localhost:5001/predict"
    
    # Use IDs of known hubs from seed data:
    # 8.4875, 'Thiruvananthapuram' -> Thampanoor Central -> ID likely 1
    # 9.9675, 'Ernakulam' -> Vyttila Mobility Hub -> ID likely 2
    # 10.1520, 'Ernakulam' -> Cochin International Airport -> ID likely 5
    
    # We can fetch /api/stops first to be sure, or just guess based on seed order.
    # The user mentioned "12 stops" gave 34 passengers.
    # Let's try sending 5 stops including hubs.
    
    payload = {
        "distance_km": 15.5,
        "num_stops": 5,
        "stop_ids": [4, 8, 11, 155, 156] # Mix of regular and potential hubs
    }
    
    print(f"Sending payload: {payload}")
    
    try:
        start = time.time()
        response = requests.post(url, json=payload)
        duration = time.time() - start
        
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print("\nResponse Summary:")
            print(f"  Total Passengers: {data.get('expected_passengers')}")
            print(f"  Total Revenue (Est): INR {data.get('expected_passengers', 0) * 20}") # Avg ticket price guess
            print(f"  High Demand Stops: {len(data.get('high_demand_stops', []))}")
            for stop in data.get('high_demand_stops', []):
                print(f"    - {stop['name']} ({stop['category']})")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_predict_counts()
