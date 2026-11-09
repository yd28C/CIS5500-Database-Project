"""
Download the Kaggle dataset a7madmostafa/us-flight-delays-2025-bts-on-time-performance
and print what is inside (files, sizes, column names, a sample row), without loading
everything into memory.

    py -m pip install kagglehub
    py get_bts_2025.py
"""
import csv
import os
import shutil

import kagglehub

path = kagglehub.dataset_download("a7madmostafa/us-flight-delays-2025-bts-on-time-performance")
dest = os.path.join(os.path.expanduser("~"), "Downloads", "bts_2025")
os.makedirs(dest, exist_ok=True)
print("downloaded to", path)
for root, _, files in os.walk(path):
    for f in sorted(files):
        src = os.path.join(root, f)
        shutil.copy2(src, os.path.join(dest, f))
        print(f"\n{f}  {os.path.getsize(src) / 1e6:,.1f} MB  -> copied to {dest}")
        if f.lower().endswith(".csv"):
            with open(src, encoding="utf-8", errors="replace", newline="") as fh:
                r = csv.reader(fh)
                header = next(r)
                first = next(r, [])
                n = 1 + sum(1 for _ in r)
            print(f"  rows: {n:,}")
            print("  columns:", ", ".join(header))
            print("  first row:", dict(zip(header, first)))
