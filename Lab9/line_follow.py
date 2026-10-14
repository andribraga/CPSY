"""
Line follower: edge following with the color sensor + PID speed control per wheel.
Setpoint is a parameter, white area on the RIGHT side of the rover.

Usage: python line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]
KS defaults to the 40 rpm tune scaled by (BASE_RPM/40)**0.6, KIS by (BASE_RPM/40)**0.5.
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
INTEGRATION_MS = 12  # sensor window; 12 halves sensor delay (keep gain 4: 12 ms saturates at 5120 counts)
DT = 0.02 * INTEGRATION_MS / 24   # loop sleep follows the sensor: ~0.025 s loop at 24 ms, ~0.013 s at 12 ms
STEPS_PER_REV = 694
STEPS = 100000
EDGE = -1         # white on the right: too much white -> steer left (flip to 1 if it steers away)
KS_40 = 0.0055    # rpm of steering per count of error, tuned at base 40
KIS_40 = 0.008    # rpm of steering per (count*s) of error, tuned at base 40
KDS = 0      # D made it wobble (sensor jumps ~3000/sample), keep 0
SETPOINT = 2000   # midpoint of white (~3700) and line (~300)
SLOW_ERR = 1500   # error at which speed would hit 0 (before the CORNER_RPM floor); 3000 wobbled in the M (corners too fast)
SLOW_DEAD = 800   # errors below this don't slow down (straight wobble is ~±430, it kept the straights at ~85 rpm); 0 = off
CORNER_RPM = 50   # floor speed in curves, in rpm (not % of BASE_RPM): the M takes ~half the lap at this speed; 40 held, back to 40 if it loses a corner
SLOW_RECOVER = 100 # speed climbs back at most this many rpm per second (stops 40<->95 rpm surging in corners); 99999 = off
SLOW_DROP = 99999 # speed falls at most this many rpm per second; 400 lost the first M corner at 150 (entered at ~130, crossed the line in 0.1 s); 99999 = off
SLOW_TURN = 9999   # steering of SLOW_TURN * BASE_RPM gives the minimum speed (keeps it slow for the whole curve)
MAX_RPM = 220     # motors top out ~225-230 rpm at full duty (tuning/L300_R300)
RESET_ERR = 1200   # clear the steering I term when it fights an error bigger than this (c < 800 or > 3200); 99999 = off
BRAKE_MARGIN = 20 # brake only if a wheel is this many rpm above target (rpm noise is ~±9); 9999 = off

if len(sys.argv) < 2:
    sys.exit("Usage: line_follow.py BASE_RPM [SECONDS [KS [SETPOINT [KIS]]]]")
base_rpm = float(sys.argv[1])
run_time = float(sys.argv[2]) if len(sys.argv) > 2 else 10
# steering grows slower than speed: the sensor-to-wheel delay costs more at speed
# (linear scaling overshot at 100; 0.0095 at 100 vs 0.0055 at 40 fits ^0.6)
KS = KS_40 * (base_rpm / 40) ** 0.6
KIS = KIS_40 * (base_rpm / 40) ** 0.5   # I kept steering past the edge at 100, so it grows slower than P
if len(sys.argv) > 3:
    KS = float(sys.argv[3])
if len(sys.argv) > 4:
    SETPOINT = float(sys.argv[4])
if len(sys.argv) > 5:
    KIS = float(sys.argv[5])

sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = INTEGRATION_MS
sensor.gain = 4
# keep it integrating; otherwise every color_raw powers it on and waits ~2 cycles (~45 ms)
sensor.active = True
# scale counts back to 24 ms so SETPOINT, KS, KIS, RESET_ERR, SLOW_ERR stay valid at any integration time
C_SCALE = 24 / sensor.integration_time

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
log_path = f"follow/base{base_rpm:g}_ks{KS:.3g}_sp{SETPOINT:g}_kis{KIS:.3g}_it{INTEGRATION_MS:g}_{time.strftime('%H%M%S')}.csv"   # time: reruns don't overwrite
log = open(log_path, "w")
log.write(f"# setpoint={SETPOINT:g} ks={KS:g} kis={KIS:g} kds={KDS:g} integration_ms={INTEGRATION_MS:g} slow_err={SLOW_ERR:g} slow_dead={SLOW_DEAD:g} slow_recover={SLOW_RECOVER:g} slow_drop={SLOW_DROP:g} corner_rpm={CORNER_RPM:g}\n")
log.write("time,c,error,left_target,left_rpm,right_target,right_rpm,base,left_out,right_out,i_reset,steer\n")

start = time.monotonic()
last_time = start
steer = 0.0
base = base_rpm

try:
    while time.monotonic() - start < run_time:
        time.sleep(DT)
        now = time.monotonic()
        dt = now - last_time
        last_time = now

        c = round(sensor.color_raw[3] * C_SCALE)
        error = c - SETPOINT                       # > 0: too much white
        # slow down while turning hard (last steer includes I, so it stays slow through the whole curve,
        # also when c passes the setpoint mid-curve) or when far off the edge (overshoot)
        slow = min(1 - abs(steer) / (SLOW_TURN * base_rpm), 1 - max(0, abs(error) - SLOW_DEAD) / (SLOW_ERR - SLOW_DEAD))
        target_base = min(base_rpm, max(CORNER_RPM, base_rpm * slow))   # min: base_rpm below CORNER_RPM still works
        base = max(min(target_base, base + SLOW_RECOVER * dt), base - SLOW_DROP * dt)
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
                  f"{r_target:.1f},{r_rpm:.1f},{base:.1f},{l_out:.3f},{r_out:.3f},{int(i_reset)},{steer:.1f}\n")
finally:
    left.motor.stop()
    right.motor.stop()
    log.close()
    print(f"saved {log_path}")
