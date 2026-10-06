"""Drive forward until the wall is within 50 cm, then pull SLP (GPIO5) low to stop.
Passes if the robot comes to rest between 30 and 50 cm.
    uv run Lab8/emergency_stop.py 0.3     # speed (0-1)
Start more than 50 cm from the wall (sensor reads wrong under 10 cm)."""
import sys
import time

import board
import busio
import digitalio
from adafruit_mcp3xxx.analog_in import AnalogIn
from adafruit_mcp3xxx.mcp3008 import MCP3008
from gpiozero import DigitalOutputDevice, Motor

FAR_V, NEAR_V = 1.16, 1.8  # 50 cm, 30 cm; voltage rises as the wall gets closer

speed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
if not 0 < speed <= 1:
    sys.exit("Speed must be between 0 and 1")

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
sensor = AnalogIn(MCP3008(spi, digitalio.DigitalInOut(board.CE0)), 0)
slp = DigitalOutputDevice(5)  # high = motor driver awake
right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)

input(f"Speed {speed}. Place robot >50 cm from the wall, press Enter to start...")
try:
    slp.on()
    left.backward(speed)  # backward = robot forward, same as motor_turns.py
    right.backward(speed)
    while (v := sensor.voltage) < FAR_V:
        print(f"{v:.3f} V")
        time.sleep(0.02)
    slp.off()  # emergency stop: put the driver to sleep
    print(f"SLP low at {v:.3f} V")
    time.sleep(0.5)  # let it roll to a stop
    v = sensor.voltage
finally:
    slp.off()
    left.stop()
    right.stop()

ok = FAR_V <= v <= NEAR_V
print(f"Stopped at {v:.3f} V -> {'PASS' if ok else 'FAIL'} (30-50 cm = {FAR_V}-{NEAR_V} V)")
sys.exit(0 if ok else 1)
