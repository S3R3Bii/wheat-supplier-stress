import sys
import unittest
from fractions import Fraction as Q
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from flow import maximum_flow, separate_country_claims


class FiniteFlowTests(unittest.TestCase):
    def test_shared_capacity_is_not_three_separate_pools(self):
        supplies = {1: 5}
        routes = {(1, 2): 5, (1, 3): 5, (1, 4): 5}
        demands = {2: 5, 3: 5, 4: 5}
        self.assertEqual(
            sum(separate_country_claims(supplies, routes, demands).values()), 15
        )
        self.assertEqual(maximum_flow(supplies, routes, demands)[0], 5)

    def test_reverse_path_reroutes_earlier_flow(self):
        supplies = {1: 1, 2: 1}
        routes = {(1, 10): 1, (1, 20): 1, (2, 10): 1}
        demands = {10: 1, 20: 1}
        total, flows, n = maximum_flow(supplies, routes, demands)
        self.assertEqual(total, 2)
        self.assertEqual(flows["origin:1", "importer:20"], 1)
        self.assertEqual(flows["origin:2", "importer:10"], 1)

    def test_disconnected_demand_is_unmet(self):
        self.assertEqual(maximum_flow({1: 5}, {}, {2: 5})[0], 0)

    def test_zero_source(self):
        self.assertEqual(maximum_flow({1: 0}, {(1, 2): 5}, {2: 5})[0], 0)

    def test_zero_demand(self):
        self.assertEqual(maximum_flow({1: 5}, {(1, 2): 5}, {2: 0})[0], 0)

    def test_route_limits_supply(self):
        self.assertEqual(maximum_flow({1: 100}, {(1, 2): 3}, {2: 100})[0], 3)

    def test_demand_limits_supply(self):
        self.assertEqual(maximum_flow({1: 100}, {(1, 2): 100}, {2: 3})[0], 3)

    def test_empty_origins(self):
        self.assertEqual(maximum_flow({}, {}, {2: 3})[0], 0)

    def test_empty_importers(self):
        self.assertEqual(maximum_flow({1: 3}, {}, {})[0], 0)

    def test_fractional_capacity_has_no_float_tolerance(self):
        self.assertEqual(
            maximum_flow({1: Q(1, 3)}, {(1, 2): Q(1, 2)}, {2: 1})[0], Q(1, 3)
        )

    def test_native_decimal_string(self):
        self.assertEqual(
            maximum_flow({1: "0.1"}, {(1, 2): "0.2"}, {2: "0.3"})[0], Q(1, 10)
        )

    def test_negative_supply_rejected(self):
        with self.assertRaises(ValueError):
            maximum_flow({1: -1}, {}, {2: 1})

    def test_negative_route_rejected(self):
        with self.assertRaises(ValueError):
            maximum_flow({1: 1}, {(1, 2): -1}, {2: 1})

    def test_negative_demand_rejected(self):
        with self.assertRaises(ValueError):
            maximum_flow({1: 1}, {}, {2: -1})

    def test_tied_total_preserves_exact_conservation(self):
        total, flows, n = maximum_flow({1: 5}, {(1, 2): 5, (1, 3): 5}, {2: 5, 3: 5})
        self.assertEqual(total, 5)
        self.assertEqual(
            flows["source", "origin:1"],
            flows["origin:1", "importer:2"] + flows["origin:1", "importer:3"],
        )


if __name__ == "__main__":
    unittest.main()
