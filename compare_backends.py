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

from gpiozero import Device, Motor, RotaryEncoder

from kernel_encoder import delta, open_encoder, read_steps

SPEEDS = [0.3, 0.6, 1.0]
TRIALS = 5
RUN_TIME = 3      # seconds the motors are on
COAST_TIME = 1.5  # wait for the wheels to stop before reading

backend = sys.argv[1] if len(sys.argv) > 1 else "lgpio"
try:
    if backend == "pigpio":
        from gpiozero.pins.pigpio import PiGPIOFactory
        Device.pin_factory = PiGPIOFactory()
    elif backend in ("lgpio", "kernel"):  # kernel: lgpio drives the motors only
        from gpiozero.pins.lgpio import LGPIOFactory
        Device.pin_factory = LGPIOFactory()
    else:
        sys.exit("Usage: uv run compare_backends.py lgpio|pigpio|kernel")
except ImportError as e:
    sys.exit(f"{backend} Python package missing ({e}). Try: uv add {backend}")
except OSError as e:
    sys.exit(f"Can't use {backend}: {e}. For pigpio, start the daemon: sudo pigpiod")


print("Backend:", backend if backend == "kernel" else type(Device.pin_factory).__name__)

right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)

if backend == "kernel":
    fb, fa = open_encoder("rotary@6"), open_encoder("rotary@12")
    read_b, read_a = (lambda: read_steps(fb)), (lambda: read_steps(fa))
else:
    motb = RotaryEncoder(a=6, b=13, max_steps=0)
    mota = RotaryEncoder(a=18, b=12, max_steps=0)
    read_b, read_a = (lambda: motb.steps), (lambda: mota.steps)

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
