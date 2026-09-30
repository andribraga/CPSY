"""
PID speed control for ONE wheel.

Usage:   python pid_one_wheel.py KP KI KD
Example: python pid_one_wheel.py 0.005 0 0

Runs for RUN_TIME seconds, prints rpm/pwm and saves pid_log.csv.
"""

import sys
import time
import evdev
from evdev import ecodes
from gpiozero import Motor
from simple_pid import PID

# ---- settings ----
TARGET_RPM = 50
RUN_TIME = 5          # seconds
DT = 0.05             # loop period (50 ms)
STEPS_PER_REV = 694
STEPS = 100000        # same as steps= in config.txt

motor = Motor(forward=19, backward=26)   # left motor
ENCODER_NAME = "rotary@6"               # change to "rotary@6" if it's the other wheel

# ---- gains from the command line ----
kp, ki, kd = (float(x) for x in sys.argv[1:4]) if len(sys.argv) == 4 else (0.005, 0, 0)

pid = PID(kp, ki, kd, setpoint=TARGET_RPM)
pid.output_limits = (0, 1)

# ---- find the encoder ----
enc = next(evdev.InputDevice(p) for p in evdev.list_devices()
           if evdev.InputDevice(p).name == ENCODER_NAME)

def position():
    return enc.absinfo(ecodes.ABS_X).value

def steps_since(last, now):
    d = now - last
    if d > STEPS / 2:
        d -= STEPS
    if d < -STEPS / 2:
        d += STEPS
    return abs(d)     # forward only for now

# ---- control loop ----
log = open("pid_log.csv", "w")
log.write("time,rpm,pwm\n")

start = time.monotonic()
last_time = start
last_pos = position()

try:
    while time.monotonic() - start < RUN_TIME:
        time.sleep(DT)

        now = time.monotonic()
        pos = position()
        dt = now - last_time
        rpm = steps_since(last_pos, pos) / STEPS_PER_REV / dt * 60
        last_time, last_pos = now, pos

        pwm = pid(rpm, dt=dt)
        motor.forward(pwm)

        t = now - start
        print(f"t={t:4.2f}  rpm={rpm:5.1f}  pwm={pwm:.2f}")
        log.write(f"{t:.3f},{rpm:.2f},{pwm:.3f}\n")
finally:
    motor.stop()
    log.close()
    print(f"\nKp={kp} Ki={ki} Kd={kd}  -> saved pid_log.csv")