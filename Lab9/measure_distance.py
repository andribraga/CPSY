"""Usage: uv run Lab9/measure_distance.py <true_cm>  -- appends one row per run to calibration.csv"""
import csv, statistics, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "Lab8"))
from distance_sensor import voltage, to_cm, fmt

N = 50  # readings per run, 0.1 s apart

if len(sys.argv) != 2:
    sys.exit("usage: measure_distance.py <true_cm>")
true_cm = float(sys.argv[1])

vs = []
for _ in range(N):
    vs.append(voltage())
    time.sleep(0.1)

med = statistics.median(vs)
pred = to_cm(med)
print(f"mean={statistics.mean(vs):.3f} median={med:.3f} stdev={statistics.stdev(vs):.3f} "
      f"min={min(vs):.3f} max={max(vs):.3f} V")
print(f"true={true_cm:g} cm, table predicts {fmt(pred)}")

path = Path(__file__).parent / "calibration.csv"
with open(path, "a", newline="") as f:  # append: repeated runs at the same cm all kept
    csv.writer(f).writerow([true_cm, round(med, 4), "" if pred is None else round(pred, 1),
                            datetime.now().isoformat(timespec="seconds")])

with open(path) as f:  # mean of medians per distance = value to paste into V/CM
    by_cm = {}
    for cm, v, *_ in csv.reader(f):
        by_cm.setdefault(float(cm), []).append(float(v))
n = len(by_cm[true_cm])
print(f"{true_cm:g} cm -> {statistics.mean(by_cm[true_cm]):.3f} V  ({n} run{'s' * (n > 1)})")
