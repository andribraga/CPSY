"""
Line follower: edge following with the color sensor + PID speed control per wheel.
Setpoint is a parameter, white area on the RIGHT side of the rover.

Usage: python line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]
KS and KIS default to the 40 rpm tune scaled by BASE_RPM/40.
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
DT = 0.02         # sensor runs continuously (new value every 24 ms), so the loop is ~0.025 s
STEPS_PER_REV = 694
STEPS = 100000
EDGE = -1         # white on the right: too much white -> steer left (flip to 1 if it steers away)
KS_40 = 0.0055    # rpm of steering per count of error, tuned at base 40
KIS_40 = 0.008    # rpm of steering per (count*s) of error, tuned at base 40
KDS = 0           # D made it wobble (sensor jumps ~3000/sample), keep 0
SETPOINT = 2000   # midpoint of white (~3700) and line (~300)
SLOW_ERR = 3000   # error at which speed would hit 0 (before the SLOW_MIN floor)
SLOW_MIN = 0.4    # never go below 40% of BASE_RPM in curves
MAX_RPM = 220     # motors top out ~225-230 rpm at full duty (tuning/L300_R300)
RESET_ERR = 1200  # clear the steering I term when it fights an error bigger than this (c < 800 or > 3200); 99999 = off
BRAKE_MARGIN = 20 # brake only if a wheel is this many rpm above target (rpm noise is ~±9); 9999 = off

if len(sys.argv) < 2:
    sys.exit("Usage: line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]")
base_rpm = float(sys.argv[1])
run_time = float(sys.argv[2]) if len(sys.argv) > 2 else 10
# steering in rpm must scale with speed to keep the same curve radius
KS = KS_40 * base_rpm / 40
KIS = KIS_40 * base_rpm / 40
if len(sys.argv) > 3:
    KS = float(sys.argv[3])
if len(sys.argv) > 4:
    SETPOINT = float(sys.argv[4])
if len(sys.argv) > 5:
    KIS = float(sys.argv[5])

sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = 24
sensor.gain = 4
# keep it integrating; otherwise every color_raw powers it on and waits ~2 cycles (~45 ms)
sensor.active = True

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
        out = self.pid(rpm, dt=dt)
        if rpm > target_rpm + BRAKE_MARGIN:
            # wheel clearly too fast: DRV8833 short brake (IN1 = IN2 = high); coasting at 0 duty is too slow
            # ponytail: on/off brake, make it proportional if it chatters
            self.motor.forward_device.on()
            self.motor.backward_device.on()
            out = -1
        else:
            self.motor.forward(out)
        return rpm, out


left = Wheel(Motor(forward=19, backward=26), "rotary@6")
right = Wheel(Motor(forward=20, backward=16), "rotary@12")
slp = DigitalOutputDevice(5, initial_value=True)

# steering PI; simple_pid uses setpoint - c, so -EDGE keeps the same direction as EDGE * (c - SETPOINT)
steer_pid = PID(KS, KIS, KDS, setpoint=SETPOINT)
steer_pid.output_limits = (-base_rpm, base_rpm)   # keep both wheels >= 0, also caps the integral

os.makedirs("follow", exist_ok=True)
log_path = f"follow/base{base_rpm:g}_ks{KS:g}_sp{SETPOINT:g}_kis{KIS:g}_brake.csv"
log = open(log_path, "w")
log.write(f"# setpoint={SETPOINT:g} ks={KS:g} kis={KIS:g}\n")
log.write("time,c,error,left_target,left_rpm,right_target,right_rpm,base,left_out,right_out,i_reset\n")

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
        # slow down when far from the edge (sharp curve / overshoot), full speed when on it
        base = base_rpm * max(SLOW_MIN, 1 - abs(error) / SLOW_ERR)
        steer_pid.output_limits = (-base, base)    # keep both wheels >= 0
        # I term is stored as KIS * (SETPOINT - c), so i * error > 0 means it steers against the sensor
        _, i_term, _ = steer_pid.components
        i_reset = abs(error) > RESET_ERR and i_term * error > 0
        if i_reset:
            steer_pid.reset()
        steer = -EDGE * steer_pid(c, dt=dt)
        l_target = base + steer
        r_target = base - steer
        # outer wheel can't go past MAX_RPM: shift both down so the speed difference (the turn) is kept
        excess = max(l_target, r_target) - MAX_RPM
        if excess > 0:
            l_target -= excess
            r_target -= excess

        l_rpm, l_out = left.update(dt, l_target)
        r_rpm, r_out = right.update(dt, r_target)
        log.write(f"{now - start:.3f},{c},{error:.0f},{l_target:.1f},{l_rpm:.1f},"
                  f"{r_target:.1f},{r_rpm:.1f},{base:.1f},{l_out:.3f},{r_out:.3f},{int(i_reset)}\n")
finally:
    left.motor.stop()
    right.motor.stop()
    log.close()
    print(f"saved {log_path}")
