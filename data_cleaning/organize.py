"""
Fill this folder with the data, from the files already in your Downloads folder.
Run once from this folder:   py organize.py

Copies the small files, MOVES the big cleaned CSVs here from ..\\cis5500_cleaning\\output
(same drive, so it is instant and does not double the disk space), and writes small
samples of every file that is too big for GitHub (GitHub refuses files over 100 MB).
"""
import gzip
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.dirname(HERE)                       # the Downloads folder
OUT = os.path.join(DL, "cis5500_cleaning", "output")
SAMPLE_ROWS = 10_000

TABLES = ["airport", "airline", "route", "flight_operation", "delayed_flight",
          "weather_station", "weather_observation", "itinerary", "segment", "fare_quote", "books"]
BIG = {"itinerary", "segment", "fare_quote", "books", "flight_operation"}   # not pushed to GitHub, samples are
REPORTS = ["report_bts.md", "report_ghcn.md", "report_itineraries.md",
           "report_itineraries_recovered.md", "report_integration.md",
           "bts_rejects.csv", "ghcn_rejects.csv", "d1_rejects_recovered.csv"]


def p(*parts):
    path = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def head(src, dst, n=SAMPLE_ROWS):
    with open(src, encoding="utf-8", newline="") as f, open(dst, "w", encoding="utf-8", newline="") as g:
        for i, line in enumerate(f):
            if i > n:
                break
            g.write(line)
    print(f"  sample  {os.path.relpath(dst, HERE)}  ({n:,} rows)")


def main():
    # ---- raw data ----
    print("raw data:")
    src = os.path.join(DL, "ghcn_raw_2025.csv")
    shutil.copy2(src, p("data", "raw", "ghcn_raw_2025.csv"))
    print("  copied  data/raw/ghcn_raw_2025.csv")
    src = os.path.join(DL, "flight_delays_2025_01.csv")
    with open(src, "rb") as f, gzip.open(p("data", "raw", "flight_delays_2025_01.csv.gz"), "wb", 9) as g:
        shutil.copyfileobj(f, g)
    print("  gzipped data/raw/flight_delays_2025_01.csv.gz (the .csv is 107 MB, over GitHub's limit)")
    head(os.path.join(DL, "itineraries-dataset1.csv"), p("data", "raw", "itineraries_sample.csv"))

    # ---- cleaned tables ----
    print("cleaned tables:")
    for t in TABLES:
        src, dst = os.path.join(OUT, f"{t}.csv"), p("data", "cleaned", f"{t}.csv")
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"  moved   data/cleaned/{t}.csv")
        elif not os.path.exists(dst):
            print(f"  MISSING {t}.csv (not in {OUT})")
            continue
        if t in BIG:
            head(dst, p("data", "cleaned", "samples", f"{t}_sample.csv"))

    # ---- reports ----
    print("reports:")
    for r in REPORTS:
        src = os.path.join(OUT, r)
        if os.path.exists(src):
            shutil.copy2(src, p("reports", r))
            print(f"  copied  reports/{r}")

    # ---- GitHub size check ----
    ignored = {os.path.normpath(os.path.join("data", "cleaned", f"{t}.csv")) for t in BIG}
    too_big = []
    for root, _, files in os.walk(HERE):
        if ".git" in root.split(os.sep):
            continue
        for f in files:
            rel = os.path.normpath(os.path.relpath(os.path.join(root, f), HERE))
            if rel not in ignored and os.path.getsize(os.path.join(root, f)) > 95 * 1024 * 1024:
                too_big.append(rel)
    print("\nfiles over GitHub's 100 MB limit that are NOT in .gitignore:", too_big or "none")
    print("\nDone. You can now delete ..\\cis5500_cleaning\\output\\d1_rejects.csv and _d1_work.sqlite (3.7 GB).")


if __name__ == "__main__":
    main()
