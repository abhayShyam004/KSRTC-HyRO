import json

def analyze():
    with open('bus_stops.json', 'r', encoding='utf-8') as f:
        stops = json.load(f)
    
    beach_stops = [s for s in stops if 'Kozhikode' in s.get('district', '') and 'Beach' in s.get('name', '')]
    
    print(f"Found {len(beach_stops)} beach stops in Kozhikode:")
    for s in beach_stops:
        print(f"ID: {s['bus_stop_id']}, Name: {s['name']}, Lat: {s['lat']}, Lon: {s['lon']}")

if __name__ == "__main__":
    analyze()
