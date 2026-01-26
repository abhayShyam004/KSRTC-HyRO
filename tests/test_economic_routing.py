
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

import route_profitability

class TestEconomicRouting(unittest.TestCase):

    def setUp(self):
        # Mock Data
        self.stop_A = {'bus_stop_id': 1, 'name': 'A', 'lat': 10.0, 'lon': 76.0, 'district': 'D1', 'demand_multiplier': 1.0}
        self.stop_B = {'bus_stop_id': 2, 'name': 'B', 'lat': 10.1, 'lon': 76.0, 'district': 'D1', 'demand_multiplier': 1.0}
        
        # Profitable Stop C (Small Detour, High Demand)
        # 10.05, 76.01 -> ~1km detour
        self.stop_C = {'bus_stop_id': 3, 'name': 'C', 'lat': 10.05, 'lon': 76.01, 'district': 'D1', 'demand_multiplier': 5.0}
        
        # Unprofitable Stop D (Large Detour, Low Demand)
        # 10.05, 76.10 -> ~11km detour
        self.stop_D = {'bus_stop_id': 4, 'name': 'D', 'lat': 10.05, 'lon': 76.10, 'district': 'D1', 'demand_multiplier': 1.0}

        self.all_stops = [self.stop_A, self.stop_B, self.stop_C, self.stop_D]

    @patch('route_profitability.demand_model')
    @patch('route_profitability.model_mae', 0.5) # MAE of 0.5
    def test_enrichment_profitable(self, mock_model):
        
        # Mock Prediction: Returns array of demands
        # Order of batch predict in enrichment: candidates list
        # Start with simple Mock that returns [10.0] for C
        mock_model.predict.return_value = [10.0] 
        
        # Conservative Demand = 10.0 - 0.5 = 9.5
        # Revenue = 9.5 * 1.5 (fare) = 14.25 (Wait, logic in code defines 12.0 avg fare)
        # Revenue = 9.5 * 12.0 = 114.0
        
        # Detour Cost ~ 1km
        # Distance A-B ~ 11km
        # Distance A-C + C-B ~ 12km (approx)
        # Detour ~ 1km
        # Fuel = 1km / 4kmpl * 95 = 23.75
        # Time = 2 min * 5 = 10.0
        # Total Cost = 33.75
        
        # Profit = 114 - 33.75 > 0 -> SHOULD ADD
        
        route = [self.stop_A, self.stop_B]
        enriched = route_profitability.enrich_route_economically(route, self.all_stops)
        
        self.assertEqual(len(enriched), 3)
        self.assertEqual(enriched[1]['name'], 'C')
        print("\n[TEST] Successfully enriched profitable detour (Stop C)")

    @patch('route_profitability.demand_model')
    @patch('route_profitability.model_mae', 0.5)
    def test_enrichment_unprofitable(self, mock_model):
        # Mock Prediction for D = 3.0
        mock_model.predict.return_value = [3.0]
        
        # Conservative = 2.5
        # Revenue = 2.5 * 12 = 30.0
        
        # Detour ~ 10km (Large)
        # Cost ~ 200+
        
        route = [self.stop_A, self.stop_B]
        # Only consider D as candidate
        pool = [self.stop_A, self.stop_B, self.stop_D]
        enriched = route_profitability.enrich_route_economically(route, pool)
        
        self.assertEqual(len(enriched), 2)
        print("\n[TEST] Successfully ignored unprofitable detour (Stop D)")

if __name__ == '__main__':
    unittest.main()
