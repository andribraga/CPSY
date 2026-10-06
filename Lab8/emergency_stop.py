"""Drive forward forever. When the wall/obstacle is within 50 cm, pull SLP (GPIO5) low to stop;
when it's gone, SLP goes high again and the robot drives on. Ctrl+C to quit.
    uv run Lab8/emergency_stop.py 0.3     # speed (0-1)
Start more than 50 cm from any obstacle (sensor reads wrong under 10 cm)."""
import sys
import time

import board
import busio
import digitalio
from adafruit_mcp3xxx.analog_in import AnalogIn
from adafruit_mcp3xxx.mcp3008 import MCP3008
from gpiozero import DigitalOutputDevice, Motor

FAR_V = 1.16  # 50 cm; voltage rises as the obstacle gets closer (1.8 V = 30 cm)

speed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
if not 0 < speed <= 1:
    sys.exit("Speed must be between 0 and 1")

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
sensor = AnalogIn(MCP3008(spi, digitalio.DigitalInOut(board.CE0)), 0)
slp = DigitalOutputDevice(5)  # high = motor driver awake
right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)

input(f"Speed {speed}. Place robot >50 cm from obstacles, press Enter to start (Ctrl+C to quit)...")
try:
    left.backward(speed)  # backward = robot forward, same as motor_turns.py
    right.backward(speed)
    # ponytail: no hysteresis; add a lower resume voltage if it stutters at the 50 cm edge
    while True:
        v = sensor.voltage
        clear = v < FAR_V
        if clear != slp.value:
            slp.value = clear  # SLP low = emergency stop, high = drive on
            print(f"{v:.3f} V -> {'DRIVE' if clear else 'STOP'}")
        time.sleep(0.02)
except KeyboardInterrupt:
    pass
finally:
    slp.off()
    left.stop()
    right.stop()
