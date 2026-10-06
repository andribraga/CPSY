"""Drive forward forever. While an obstacle is 30-50 cm away, pull SLP (GPIO5) low to stop;
closer than 30 cm or farther than 50 cm, SLP is high and the robot drives. Ctrl+C to quit.
    uv run Lab8/emergency_stop.py 0.3     # speed (0-1)
Start more than 50 cm from any obstacle (sensor reads wrong under 10 cm)."""
import sys
import time

from gpiozero import DigitalOutputDevice, Motor

from distance_sensor import fmt, to_cm, voltage

BAND_LO_V = 1.10  # 50 cm
BAND_HI_V = 1.81  # 30 cm

speed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
if not 0 < speed <= 1:
    sys.exit("Speed must be between 0 and 1")

slp = DigitalOutputDevice(5, initial_value=True)  # high = motor driver awake
right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)

input(f"Speed {speed}. Place robot >50 cm from obstacles, press Enter to start (Ctrl+C to quit)...")
try:
    left.forward(speed)
    right.forward(speed)
    while True:
        v = voltage()
        in_band = BAND_LO_V <= v <= BAND_HI_V  # obstacle 30-50 cm away
        if slp.value and in_band:
            slp.off()  # emergency stop
            print(f"{v:.3f} V ({fmt(to_cm(v))}) -> STOP")
        elif not slp.value and not in_band:
            slp.on()
            print(f"{v:.3f} V ({fmt(to_cm(v))}) -> DRIVE")
        time.sleep(0.02)
except KeyboardInterrupt:
    pass
finally:
    slp.off()
    left.stop()
    right.stop()
