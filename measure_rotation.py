import time
from gpiozero import RotaryEncoder

motb = RotaryEncoder(a=6, b=13, max_steps=0)
mota = RotaryEncoder(a=18, b=12, max_steps=0)

motb.steps = 0
mota.steps = 0
print("Turn the wheels by hand. Ctrl+C when done.")

try:
    while True:
        print(f"\rMOTB: {motb.steps:6d}   MOTA: {mota.steps:6d}", end="", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print(f"\n\nSteps per rotation -> MOTB: {abs(motb.steps)}   MOTA: {abs(mota.steps)}")
