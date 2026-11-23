"""Response shapes, rate definitions and input validation on the project dataset."""
import unittest
from decimal import Decimal

from airport_api import get, rounded


class QueryContracts(unittest.TestCase):
    def success(self, path):
        status, result = get(path)
        self.assertEqual(status, 200, result)
        return result

    def test_search_and_comparison(self):
        flights = self.success("/flights/search?origin=PHL&destination=LAX&date=2025-05-15")
        carriers = self.success("/routes/reliability?origin=PHL&destination=LAX")
        self.assertTrue(flights and carriers)
        for row in flights + carriers:
            self.assertIn("out_delay_rate", row)
            self.assertNotIn("delay_rate", row)
        self.assertTrue(all("in_delay_rate" in row for row in carriers))
        self.assertEqual(get("/flights/search?origin=PHL&destination=LAX&date=2022-05-15")[0], 400)

    def test_airline_details(self):
        code = "AA"
        profile = self.success(f"/airlines/{code}/summary")
        reliability = self.success(f"/airlines/{code}/reliability")
        self.assertIsInstance(profile, dict)
        self.assertIsInstance(reliability, dict)
        self.assertEqual(profile["airline_name"], reliability["airline_name"])
        self.assertNotIn("delay_rate", reliability)
        # Independent 2025 BTS count: 244,989 late arrivals among 973,653 scheduled AA flights.
        self.assertEqual(reliability["total_flights"], 973_653)
        expected_rate = rounded(Decimal(100 * 244_989) / 973_653)
        self.assertEqual(reliability["scheduled_in_delay_rate"], expected_rate)
        for endpoint in ("summary", "reliability"):
            self.assertEqual(get(f"/airlines/ZZZ/{endpoint}")[0], 404)

    def test_rankings_and_lists(self):
        for path in ("/airlines/AA/top-routes", "/airports/PHL/top-routes"):
            rows = self.success(path + "?limit=2")
            self.assertEqual(len(rows), 2)
            self.assertGreaterEqual(rows[0]["number_of_flights"], rows[1]["number_of_flights"])
            for limit in ("-1", "0", "1.5", "", "abc", "2x", "2&limit=3", "9007199254740992"):
                with self.subTest(path=path, limit=limit):
                    self.assertEqual(get(f"{path}?limit={limit}")[0], 400)
            self.assertEqual(self.success(path.replace("AA", "ZZZ").replace("PHL", "ZZZ")), [])
        for path in ("/airlines", "/airports", "/flights/booking-trends"):
            rows = self.success(path)
            self.assertIsInstance(rows, list)
            self.assertTrue(rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
