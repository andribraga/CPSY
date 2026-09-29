"""Compare encoder counts with lgpio vs pigpio vs the kernel rotary-encoder driver.
Lift the robot so the wheels spin freely, then run once per backend:
    uv run compare_backends.py lgpio
    uv run compare_backends.py pigpio    # needs: sudo pigpiod (not on Pi 5)
    uv run compare_backends.py kernel    # needs: rotary-encoder overlays enabled in config.txt
lgpio/pigpio need the overlays commented out (else "GPIO busy"); kernel needs them on.
"""
import sys
import time
from statistics import mean, stdev

from gpiozero import Motor

from encoders import delta, setup

SPEEDS = [0.3, 0.6, 1.0]
TRIALS = 5
RUN_TIME = 3      # seconds the motors are on
COAST_TIME = 1.5  # wait for the wheels to stop before reading

read_b, read_a = setup(sys.argv[1] if len(sys.argv) > 1 else "lgpio")  # sets pin factory first
right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)

print(f"{'speed':>5} | {'MOTB avg':>8} {'±':>4} | {'MOTA avg':>8} {'±':>4} | raw counts")
try:
    for speed in SPEEDS:
        b_counts, a_counts = [], []
        for _ in range(TRIALS):
            b0, a0 = read_b(), read_a()
            left.backward(speed)
            right.backward(speed)
            time.sleep(RUN_TIME)
            left.stop()
            right.stop()
            time.sleep(COAST_TIME)  # ponytail: counts include coasting; read before sleep to exclude it
            b_counts.append(delta(b0, read_b()))
            a_counts.append(delta(a0, read_a()))
        print(f"{speed:5.1f} | {mean(b_counts):8.0f} {stdev(b_counts):4.0f} | "
              f"{mean(a_counts):8.0f} {stdev(a_counts):4.0f} | B={b_counts} A={a_counts}")
finally:
    left.stop()
    right.stop()
