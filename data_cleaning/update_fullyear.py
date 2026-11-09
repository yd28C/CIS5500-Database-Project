"""
One-off step after the full-year BTS run. Run from this folder:   py update_fullyear.py
Writes a sample of flight_operation.csv (too big for GitHub), copies the new reports
into reports/, and lists any file over GitHub's 100 MB limit that is not in .gitignore.
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(HERE, "data", "cleaned")
IGNORED = {"itinerary.csv", "segment.csv", "fare_quote.csv", "books.csv", "flight_operation.csv", "d1_rejects.csv"}

os.makedirs(os.path.join(CLEAN, "samples"), exist_ok=True)
with open(os.path.join(CLEAN, "flight_operation.csv"), encoding="utf-8", newline="") as f, \
     open(os.path.join(CLEAN, "samples", "flight_operation_sample.csv"), "w", encoding="utf-8", newline="") as g:
    for i, line in enumerate(f):
        if i > 10_000:
            break
        g.write(line)
print("wrote data/cleaned/samples/flight_operation_sample.csv (10,000 rows)")

os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
for r in ["report_bts.md", "report_integration.md", "bts_rejects.csv"]:
    src = os.path.join(CLEAN, r)
    if os.path.exists(src):
        shutil.move(src, os.path.join(HERE, "reports", r))
        print(f"moved {r} -> reports/")

too_big = []
for root, dirs, files in os.walk(HERE):
    dirs[:] = [d for d in dirs if d != ".git"]
    for f in files:
        full = os.path.join(root, f)
        if f.endswith(".zip") or (root == CLEAN and f in IGNORED):
            continue
        if os.path.getsize(full) > 95 * 1024 * 1024:
            too_big.append(os.path.relpath(full, HERE))
print("files over 100 MB that are NOT in .gitignore:", too_big or "none")
