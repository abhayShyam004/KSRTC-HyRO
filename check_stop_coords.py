import psycopg2
from src.database import get_db_connection

def check_coords():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("Checking Airport Coordinates in DB...")
                cur.execute("SELECT name, lat, lon FROM bus_stops WHERE name ILIKE '%Airport%' OR name ILIKE '%Beach%'")
                rows = cur.fetchall()
                for row in rows:
                    name, lat, lon = row
                    lat = float(lat)
                    lon = float(lon)
                    print(f"Stop: {name}, Lat: {lat}, Lon: {lon}")
                    
                    if "Kannur" in name and "Airport" in name:
                        if abs(lat - 11.9) > 0.1:
                            print("  WARNING: Suspicious Kannur Lat!")
                    
                    if "Calicut" in name and "Airport" in name:
                        if abs(lat - 11.13) > 0.1:
                             print("  WARNING: Suspicious Calicut Lat!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_coords()
