import sys, unittest
from pathlib import Path
from fractions import Fraction as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bounds_model import endpoint, classify, completion
from cut_certificate import verify_allocation


class OutsideBounds(unittest.TestCase):
    def setUp(self):
        self.s = {"1": 5}
        self.r = {("1", "2"): 3, ("1", "3"): 3}
        self.d = {"2": 3, "3": 3}
        self.res = {"2": 2, "3": 2}

    def solve(self, gamma):
        return endpoint(self.s, self.r, self.d, self.res, gamma)

    def test_zero_endpoint_attains_lower(self):
        self.assertEqual(self.solve("0")[3], 5)

    def test_half_endpoint_attains_upper(self):
        self.assertEqual(self.solve("1/2")[3], 6)

    def test_full_endpoint_bounded_by_demand(self):
        self.assertEqual(self.solve("1")[3], 6)

    def test_monotonic(self):
        self.assertEqual([self.solve(g)[3] for g in ["0", "1/2", "1"]], [5, 6, 6])

    def test_shared_double_claim(self):
        self.assertEqual(sum(self.solve("0")[6].values()), 6)

    def test_exact_fraction(self):
        self.res = {"2": F(1, 3), "3": F(1, 3)}
        self.assertEqual(self.solve("1/2")[3], F(16, 3))

    def test_cut_certificates_all_endpoints(self):
        for g in ["0", "1/2", "1"]:
            s, r, d, total, flows, a, claims = self.solve(g)
            n, cuts = verify_allocation(s, r, d, total, flows)
            self.assertEqual(len(cuts), 4)

    def test_no_residual_narrows_to_known(self):
        self.res = {"2": 0, "3": 0}
        self.assertEqual(self.solve("1")[3], 5)

    def test_negative_residual_stops(self):
        self.res["2"] = -1
        self.assertRaises(ValueError, self.solve, "1")

    def test_missing_residual_stops(self):
        del self.res["2"]
        self.assertRaises(ValueError, self.solve, "1")

    def test_reserved_identity_stops(self):
        self.s["999999"] = 1
        self.assertRaises(ValueError, self.solve, "1")

    def test_outside_grid_stops(self):
        self.assertRaises(ValueError, self.solve, "2")

    def test_negative_gamma_stops(self):
        self.assertRaises(ValueError, self.solve, "-1/2")

    def test_zero_loss_class(self):
        self.assertEqual(classify(F(), F(), F()), "ZERO_MODELED_LOSS")

    def test_known_sufficient_class(self):
        self.assertEqual(classify(F(5), F(5), F(5)), "KNOWN_NETWORK_SUFFICIENT")

    def test_conditional_shortfall_class(self):
        self.assertEqual(classify(F(6), F(3), F(5)), "CONDITIONAL_SHORTFALL")

    def test_unresolved_class(self):
        self.assertEqual(
            classify(F(6), F(5), F(6)), "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY"
        )

    def test_invalid_interval_stops(self):
        self.assertRaises(AssertionError, classify, F(6), F(6), F(5))

    def test_disconnected_known_with_conditional_outside(self):
        s, r, d, total, flows, a, c = endpoint({"1": 0}, {}, {"2": 10}, {"2": 3}, "1")
        self.assertEqual(total, 3)
        self.assertEqual(classify(F(10), F(), total), "CONDITIONAL_SHORTFALL")

    def test_outside_route_not_unrestricted(self):
        self.res = {"2": 0, "3": 10}
        self.assertEqual(self.solve("1")[3], 6)


if __name__ == "__main__":
    unittest.main()
