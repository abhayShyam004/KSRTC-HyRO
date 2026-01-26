
import os

files_to_delete = [
    "add_airports.py",
    "add_calicut_airport.py",
    "add_trivandrum_airport.py",
    "analyze_beach_stops.py",
    "assign_districts_by_coords.py",
    "check_airports.py",
    "check_calicut.py",
    "check_db_airports.py",
    "check_pbf.py",
    "db_test_fast.py",
    "debug_import.py",
    "fallback_extract.py",
    "fix_airport_districts.py",
    "fix_beach_stop.py",
    "force_fix.py",
    "import_final.py",
    "import_log.txt",
    "import_smart.py",
    "import_status.txt",
    "list_airports.py",
    "nuclear_diagnostic.txt",
    "rename_airports.py",
    "rename_status.txt",
    "restore_from_csv.py",
    "sync_airports_only.py",
    "sync_fast.py",
    "sync_json_to_db.py",
    "sync_status.txt",
    "test_io.py",
    "beach_debug.txt",
    "debug_output.txt",
    "sync_output.txt",
    "restore_log.txt",
    "sync_airports_log.txt",
    "assign_log.txt",
    "db_result.txt",
    "test_py.txt",
    "test_canary.txt",
    "test_console.txt",
    "import_status.txt", # already listed
    "beach_debug.txt", # already listed
    "sync_airports_log.txt", # already listed
    "assign_log.txt", # already listed
    "import_log.txt", # already listed
    "db_result.txt", # already listed
    "test_py.txt", # already listed
    "test_canary.txt", # already listed
    "test_console.txt" # already listed
]

for f in set(files_to_delete):
    if os.path.exists(f):
        try:
            os.remove(f)
            print(f"Deleted: {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")
    else:
        # print(f"Not found: {f}")
        pass

print("Cleanup script finished.")
