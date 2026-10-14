import csv, sys, time
import board
import adafruit_tcs34725

name = sys.argv[1]
it = int(sys.argv[2]) if len(sys.argv) > 2 else 24   # integration time in ms

sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = it
sensor.gain = 4

with open(f"{name}_it{it}.csv", "a", newline="") as f:   # _it suffix: never mixes with old 24 ms files
    w = csv.writer(f)
    for _ in range(50):
        w.writerow(sensor.color_raw)
        time.sleep(0.05)