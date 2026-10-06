import statistics
import time

import board
import busio
import digitalio
from adafruit_mcp3xxx.analog_in import AnalogIn
from adafruit_mcp3xxx.mcp3008 import MCP3008

# measured: voltage rises as the obstacle gets closer; below 10 cm the sensor reads wrong
V = [1.10, 1.39, 1.81, 2.31, 2.60]
CM = [50, 40, 30, 20, 10]

spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.CE0)
mcp = MCP3008(spi, cs)
chan0 = AnalogIn(mcp, 0)


def voltage():
    return statistics.median(chan0.voltage for _ in range(5))  # median drops single-sample spikes


def to_cm(v):
    """Linear interpolation on the table; None outside 10-50 cm."""
    if not V[0] <= v <= V[-1]:
        return None
    for (v0, c0), (v1, c1) in zip(zip(V, CM), zip(V[1:], CM[1:])):
        if v <= v1:
            return c0 + (c1 - c0) * (v - v0) / (v1 - v0)


def fmt(cm):
    return "out of range (<10 or >50 cm)" if cm is None else f"{cm:.1f} cm"


if __name__ == "__main__":
    while True:
        v = voltage()
        print(f"raw={chan0.value:5d}  voltage={v:.3f} V  distance={fmt(to_cm(v))}")
        time.sleep(0.2)
