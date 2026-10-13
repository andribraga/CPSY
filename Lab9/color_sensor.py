import csv, sys, time
import board
import adafruit_tcs34725

name = sys.argv[1]

sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = 24
sensor.gain = 4

with open(f"{name}.csv", "a", newline="") as f:
    w = csv.writer(f)
    for _ in range(50):
        w.writerow(sensor.color_raw)
        time.sleep(0.05)