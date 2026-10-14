"""
Line follower: edge following with the color sensor + PID speed control per wheel.
Setpoint is a parameter, white area on the RIGHT side of the rover.

Usage: python line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]
"""

import os
import sys
import time
import board
import adafruit_tcs34725
import evdev
from evdev import ecodes
from gpiozero import DigitalOutputDevice, Motor
from simple_pid import PID

# ---- settings ----
KP, KI, KD = 0.01, 0.02, 0   # wheel speed PID (best from tuning/)
DT = 0.01          # extra sleep; sensor read adds ~0.05 s, so the loop is ~0.06 s
STEPS_PER_REV = 694
STEPS = 100000
EDGE = -1         # white on the right: too much white -> steer left (flip to 1 if it steers away)
KS = 0.005        # rpm of steering per count of error
KIS = 0           # rpm of steering per (count*s) of error, tightens long turns like the U
KDS = 0           # D made it wobble (sensor jumps ~3000/sample), keep 0
SETPOINT = 2000   # midpoint of white (~3700) and line (~300)

if len(sys.argv) < 2:
    sys.exit("Usage: line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]")
base_rpm = float(sys.argv[1])
run_time = float(sys.argv[2]) if len(sys.argv) > 2 else 10
if len(sys.argv) > 3:
    KS = float(sys.argv[3])
if len(sys.argv) > 4:
    SETPOINT = float(sys.argv[4])
if len(sys.argv) > 5:
    KIS = float(sys.argv[5])

sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = 24
sensor.gain = 4

input("Put the rover at the start, press Enter to drive")

# ---- wheels (created after the prompt so moving it by hand isn't counted) ----
devices = {evdev.InputDevice(p).name: evdev.InputDevice(p) for p in evdev.list_devices()}


class Wheel:
    def __init__(self, motor, encoder_name):
        self.motor = motor
        self.enc = devices[encoder_name]
        self.pid = PID(KP, KI, KD, setpoint=0)
        self.pid.output_limits = (0, 1)
        self.last_pos = self.position()

    def position(self):
        return self.enc.absinfo(ecodes.ABS_X).value

    def update(self, dt, target_rpm):
        self.pid.setpoint = max(0, target_rpm)
        pos = self.position()
        d = pos - self.last_pos
        if d > STEPS / 2:
            d -= STEPS
        if d < -STEPS / 2:
            d += STEPS
        self.last_pos = pos
        rpm = abs(d) / STEPS_PER_REV / dt * 60
        self.motor.forward(self.pid(rpm, dt=dt))
        return rpm


left = Wheel(Motor(forward=19, backward=26), "rotary@6")
right = Wheel(Motor(forward=20, backward=16), "rotary@12")
slp = DigitalOutputDevice(5, initial_value=True)

# steering PI; simple_pid uses setpoint - c, so -EDGE keeps the same direction as EDGE * (c - SETPOINT)
steer_pid = PID(KS, KIS, KDS, setpoint=SETPOINT)
steer_pid.output_limits = (-base_rpm, base_rpm)   # keep both wheels >= 0, also caps the integral

os.makedirs("follow", exist_ok=True)
log_path = f"follow/base{base_rpm:g}_ks{KS:g}_sp{SETPOINT:g}_kis{KIS:g}.csv"
log = open(log_path, "w")
log.write(f"# setpoint={SETPOINT:g} ks={KS:g} kis={KIS:g}\n")
log.write("time,c,error,left_target,left_rpm,right_target,right_rpm\n")

start = time.monotonic()
last_time = start

try:
    while time.monotonic() - start < run_time:
        time.sleep(DT)
        now = time.monotonic()
        dt = now - last_time
        last_time = now

        c = sensor.color_raw[3]
        error = c - SETPOINT                       # > 0: too much white
        steer = -EDGE * steer_pid(c, dt=dt)
        l_target = base_rpm + steer
        r_target = base_rpm - steer

        l_rpm = left.update(dt, l_target)
        r_rpm = right.update(dt, r_target)
        log.write(f"{now - start:.3f},{c},{error:.0f},{l_target:.1f},{l_rpm:.1f},"
                  f"{r_target:.1f},{r_rpm:.1f}\n")
finally:
    left.motor.stop()
    right.motor.stop()
    log.close()
    print(f"saved {log_path}")
