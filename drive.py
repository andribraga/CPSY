"""
PID speed control for BOTH wheels.

Usage:   python drive.py LEFT_RPM RIGHT_RPM [SECONDS [KP KI KD]]
         negative rpm = that wheel drives backward

Examples:
  python drive.py 50 50        straight ahead
  python drive.py 30 60        curve to the left
  python drive.py 40 -40       turn on the spot (clockwise)
  python drive.py -50 -50      straight backward

  python drive.py 50 50 5 0.005 0.02 0   try these gains

Saves tuning/L<left>_R<right>_kp<kp>_ki<ki>_kd<kd>.csv and prints the mean rpm error
(after the first second) per wheel; lower = better tune.
"""

import os
import sys
import time
import evdev
from evdev import ecodes
from gpiozero import DigitalOutputDevice, Motor
from simple_pid import PID

# ---- settings ----
KP, KI, KD = 0.005, 0.02, 0  # lowered from 0.015/0.05: less wobble at low rpm
DT = 0.05             # loop period (50 ms)
STEPS_PER_REV = 694   # measured: 6940 ticks / 10 turns (both wheels)
STEPS = 100000        # same as steps= in config.txt

left_rpm = float(sys.argv[1])
right_rpm = float(sys.argv[2])
run_time = float(sys.argv[3]) if len(sys.argv) > 3 else 5
if len(sys.argv) == 7:
    KP, KI, KD = (float(x) for x in sys.argv[4:7])
elif len(sys.argv) not in (3, 4):
    sys.exit("Usage: drive.py LEFT_RPM RIGHT_RPM [SECONDS [KP KI KD]]")

devices = {evdev.InputDevice(p).name: evdev.InputDevice(p) for p in evdev.list_devices()}


class Wheel:
    def __init__(self, motor, encoder_name, target_rpm):
        self.motor = motor
        self.enc = devices[encoder_name]
        self.forward = target_rpm >= 0
        # PID works on the speed; direction is chosen by the sign of the target
        self.pid = PID(KP, KI, KD, setpoint=abs(target_rpm))
        self.pid.output_limits = (0, 1)
        self.last_pos = self.position()
        self.total_steps = 0

    def position(self):
        return self.enc.absinfo(ecodes.ABS_X).value

    def update(self, dt):
        pos = self.position()
        d = pos - self.last_pos
        if d > STEPS / 2:
            d -= STEPS
        if d < -STEPS / 2:
            d += STEPS
        self.last_pos = pos
        self.total_steps += abs(d)

        rpm = abs(d) / STEPS_PER_REV / dt * 60
        pwm = self.pid(rpm, dt=dt)
        if self.forward:
            self.motor.forward(pwm)
        else:
            self.motor.backward(pwm)
        return rpm, pwm


left = Wheel(Motor(forward=19, backward=26), "rotary@6", left_rpm)
right = Wheel(Motor(forward=20, backward=16), "rotary@12", right_rpm)
slp = DigitalOutputDevice(5, initial_value=True)  # wake the motor driver

os.makedirs("tuning", exist_ok=True)
log_path = f"tuning/L{left_rpm:g}_R{right_rpm:g}_kp{KP:g}_ki{KI:g}_kd{KD:g}.csv"
log = open(log_path, "w")
errs = {"left": [], "right": []}  # |target - rpm| after the start-up second
log.write("time,left_target,left_rpm,left_pwm,right_target,right_rpm,right_pwm\n")

start = time.monotonic()
last_time = start

try:
    while time.monotonic() - start < run_time:
        time.sleep(DT)
        now = time.monotonic()
        dt = now - last_time
        last_time = now

        l_rpm, l_pwm = left.update(dt)
        r_rpm, r_pwm = right.update(dt)

        t = now - start
        if t > 1:
            errs["left"].append(abs(abs(left_rpm) - l_rpm))
            errs["right"].append(abs(abs(right_rpm) - r_rpm))
        log.write(f"{t:.3f},{left_rpm},{l_rpm:.2f},{l_pwm:.3f},"
                  f"{right_rpm},{r_rpm:.2f},{r_pwm:.3f}\n")
finally:
    left.motor.stop()
    right.motor.stop()
    log.close()
    print(f"left:  {left.total_steps / STEPS_PER_REV:.2f} turns")
    print(f"right: {right.total_steps / STEPS_PER_REV:.2f} turns")
    print(f"Kp={KP:g} Ki={KI:g} Kd={KD:g}")
    for name, e in errs.items():
        if e:
            print(f"{name} mean rpm error: {sum(e) / len(e):.2f}")
    print(f"saved {log_path}")
