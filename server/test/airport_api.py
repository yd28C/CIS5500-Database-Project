"""HTTP integration tests for the airport endpoints using project data."""
import csv
import json
import os
import unittest
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

BASE = os.getenv("AIRPORT_API_URL", "http://localhost:8080").rstrip("/")
DATA = Path(__file__).resolve().parents[2] / "data_cleaning/data/cleaned"


@lru_cache(maxsize=None)
def get(path):
    try:
        with urlopen(BASE + path, timeout=75) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        with error:
            return error.code, json.load(error)


def rounded(value):
    return float(value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))


class AirportAPI(unittest.TestCase):
    def success(self, path):
        status, body = get(path)
        self.assertEqual(status, 200, body)
        return body

    def test_summary_and_monthly_totals(self):
        overview = self.success("/airports/phl/overview")
        annual = self.success("/airports/PHL/efficiency?year=2025")
        months = self.success("/airports/PHL/weather-reliability")
        self.assertEqual((overview["airport_code"], overview["year"]), ("PHL", 2025))
        self.assertEqual(overview["total_departures"], annual["total_departures"])
        self.assertEqual(overview["total_arrivals"], annual["total_arrivals"])
        self.assertEqual(overview["total_scheduled_operations"], annual["total_departures"] + annual["total_arrivals"])
        self.assertEqual([m["month"] for m in months], list(range(1, 13)))
        for key in ("total_departures", "departures_with_delay_data", "delayed_departures", "cancelled_departures"):
            self.assertEqual(sum(m[key] for m in months), annual[key])
        for rate, numerator, denominator in [
            ("out_delay_rate", "delayed_departures", "departures_with_delay_data"),
            ("cancellation_rate", "cancelled_departures", "total_departures"),
        ]:
            expected = rounded(Decimal(100 * annual[numerator]) / annual[denominator])
            self.assertEqual(annual[rate], expected)

    def test_january_flights_against_bts(self):
        counts = Counter()
        with (DATA / "flight_operation.csv").open(newline="") as source:
            for row in csv.DictReader(source):
                if row["origin_code"] != "PHL" or not row["flight_date"].startswith("2025-01-"):
                    continue
                counts["total_departures"] += 1
                if row["dep_delay_min"]:
                    counts["departures_with_delay_data"] += 1
                    counts["delayed_departures"] += int(row["dep_delay_min"]) >= 15
                counts["cancelled_departures"] += bool(row["cancellation_code"].strip())
        self.assertGreater(counts["total_departures"], 0)
        jan = self.success("/airports/PHL/weather-reliability")[0]
        for field, expected in counts.items():
            self.assertEqual(jan[field], expected, field)

    def test_weather_against_ghcn(self):
        with (DATA / "weather_station.csv").open(newline="") as source:
            station = next(r["station_id"] for r in csv.DictReader(source) if r["airport_code"] == "PHL")
        obs = defaultdict(list)
        with (DATA / "weather_observation.csv").open(newline="") as source:
            for row in csv.DictReader(source):
                day = row["observation_date"]
                if row["station_id"] == station and day.startswith("2025-"):
                    obs[int(day[5:7]), row["element_code"]].append(Decimal(row["raw_value"]))
        for month in self.success("/airports/PHL/weather-reliability"):
            self.assertEqual(month["weather_station_id"], station)
            for element, field, days in [
                ("TMAX", "monthly_max_temp_f", "tmax_days"),
                ("TMIN", "monthly_min_temp_f", "tmin_days"),
                ("PRCP", "precipitation_inches", "precipitation_days"),
                ("SNOW", "snowfall_inches", "snowfall_days"),
            ]:
                values = [v for v in obs[month["month"], element] if v != -9999]
                self.assertEqual(month[days], len(values))
                if not values:
                    self.assertIsNone(month[field])
                    continue
                if element in ("TMAX", "TMIN"):
                    extreme = max(values) if element == "TMAX" else min(values)
                    expected = extreme / 10 * 9 / 5 + 32
                else:
                    expected = sum(values) / (254 if element == "PRCP" else Decimal("25.4"))
                self.assertEqual(month[field], rounded(expected), (month["month"], field))

    def test_airport_without_station(self):
        months = self.success("/airports/ABE/weather-reliability")
        self.assertEqual(len(months), 12)
        self.assertTrue(any(m["total_departures"] > 0 for m in months))
        for m in months:
            self.assertIsNone(m["weather_station_id"])
            self.assertIsNone(m["monthly_max_temp_f"])
            self.assertIsNone(m["monthly_min_temp_f"])
            self.assertEqual((m["tmax_days"], m["tmin_days"]), (0, 0))
            self.assertIsNone(m["precipitation_inches"])
            self.assertIsNone(m["snowfall_inches"])

    def test_supported_year(self):
        for endpoint in ("overview", "efficiency", "weather-reliability", "top-routes"):
            path = f"/airports/PHL/{endpoint}"
            self.assertEqual(self.success(path), self.success(path + "?year=2025"))
            for year in ("2022", "2024", "2026", "2025abc", "2025&year=2025"):
                with self.subTest(endpoint=endpoint, year=year):
                    self.assertEqual(get(path + "?year=" + year)[0], 400)

    def test_errors(self):
        for suffix in ("overview", "efficiency", "weather-reliability"):
            for url, expected in [
                (f"/airports/ZZZ/{suffix}", 404), (f"/airports/PH/{suffix}", 400),
                (f"/airports/PHL/{suffix}?year=", 400), (f"/airports/PHL/{suffix}?year=2025x", 400),
                (f"/airports/PHL/{suffix}?year=2024&year=2025", 400),
            ]:
                with self.subTest(url=url):
                    status, result = get(url)
                    self.assertEqual(status, expected)
                    self.assertIsInstance(result["error"], str)

    def test_b_routes_remain_available(self):
        options = self.success("/airports")
        self.assertTrue(any(a["airport_code"] == "PHL" for a in options))
        top = self.success("/airports/PHL/top-routes?limit=2&year=2025")
        self.assertEqual(len(top), 2)
        self.assertGreaterEqual(top[0]["number_of_flights"], top[1]["number_of_flights"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
