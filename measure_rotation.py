"""Check counts per wheel turn. Works with any backend:
    uv run measure_rotation.py kernel    # overlays on in config.txt
    uv run measure_rotation.py lgpio     # overlays commented out
    uv run measure_rotation.py pigpio    # overlays commented out + sudo pigpiod
Put a tape mark on each wheel, turn each wheel by hand a known number of
full turns (10 is good), press Ctrl+C, then type how many turns you made."""
import sys
import time

from encoders import delta, report_per_turn, setup

read_b, read_a = setup(sys.argv[1] if len(sys.argv) > 1 else "kernel")
b0, a0 = read_b(), read_a()

print("Turn the wheels by hand. Ctrl+C when done.")
try:
    while True:
        print(f"\rMOTB: {delta(b0, read_b()):6d}   MOTA: {delta(a0, read_a()):6d}", end="", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n")

counts = {"MOTB": delta(b0, read_b()), "MOTA": delta(a0, read_a())}
sys.exit(0 if report_per_turn(counts, default_turns=10) else 1)
