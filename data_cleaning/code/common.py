"""Shared helpers for the Milestone 2 cleaning scripts."""
import re

import pandas as pd

AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
AIRLINE_RE = re.compile(r"^[A-Z0-9]{2,3}$")

# BTS reports carrier codes only, so names come from this list (and from Expedia
# segmentsAirlineName when those rows exist).
BTS_AIRLINE_NAMES = {
    "AA": "American Airlines", "AS": "Alaska Airlines", "B6": "JetBlue Airways",
    "DL": "Delta Air Lines", "F9": "Frontier Airlines", "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines", "MQ": "Envoy Air", "NK": "Spirit Airlines",
    "OH": "PSA Airlines", "OO": "SkyWest Airlines", "UA": "United Airlines",
    "WN": "Southwest Airlines", "YX": "Republic Airways", "9E": "Endeavor Air",
    "QX": "Horizon Air", "ZW": "Air Wisconsin", "C5": "CommuteAir", "G7": "GoJet Airlines",
    "PT": "Piedmont Airlines", "EV": "ExpressJet Airlines", "YV": "Mesa Airlines",
    "SY": "Sun Country Airlines", "MX": "Breeze Airways",
}


def std_code(s: pd.Series) -> pd.Series:
    """Trim and upper-case an airport or airline code column; blanks become null."""
    s = s.astype("string").str.strip().str.upper()
    return s.mask(s == "")


class Report:
    """Collects check results and writes them as a Markdown file."""

    def __init__(self, title):
        self.lines = [f"# {title}", ""]

    def section(self, name):
        self.lines += ["", f"## {name}", ""]

    def add(self, label, value=None):
        if value is None:
            self.lines.append(f"- {label}")
        else:
            if isinstance(value, (int,)) or (hasattr(value, "dtype") and str(value).isdigit()):
                value = f"{int(value):,}"
            self.lines.append(f"- {label}: {value}")
        print(self.lines[-1])

    def table(self, df: pd.DataFrame):
        cols = [str(c) for c in df.columns]
        rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        rows += ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |"
                 for r in df.itertuples(index=False)]
        self.lines += [""] + rows + [""]

    def write(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print(f"\nreport written to {path}")
