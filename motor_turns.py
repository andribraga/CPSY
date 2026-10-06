"""Run both motors for 5 seconds; you count the wheel turns (tape mark on each wheel).
Then type the turns and it prints counts per turn vs 700.
    uv run motor_turns.py kernel 0.3     # backend, speed (0-1)
Count until the wheel fully stops: the counts include coasting after the motors stop.
Low speed is easier to count (0.3 ~ 3 turns in 5 s). Try a higher speed to see who drops steps."""
import sys
import time

from gpiozero import DigitalOutputDevice, Motor

from encoders import delta, report_per_turn, setup

RUN_TIME = 5
COAST_TIME = 2  # wait for the wheels to stop before reading

backend = sys.argv[1] if len(sys.argv) > 1 else "kernel"
speed = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
if not 0 < speed <= 1:
    sys.exit("Speed must be between 0 and 1")

read_b, read_a = setup(backend)  # sets pin factory before the motors are created
right = Motor(forward=20, backward=16)
left = Motor(forward=19, backward=26)
slp = DigitalOutputDevice(5, initial_value=True)  # wake the motor driver

input(f"Speed {speed}, {RUN_TIME} s. Lift the robot, press Enter to start...")
for i in (3, 2, 1):
    print(i)
    time.sleep(1)

b0, a0 = read_b(), read_a()
try:
    print("GO - count the turns")
    left.backward(speed)
    right.backward(speed)
    time.sleep(RUN_TIME)
finally:
    left.stop()
    right.stop()
print("STOP - keep counting until the wheels stop")
time.sleep(COAST_TIME)

counts = {"MOTB": delta(b0, read_b()), "MOTA": delta(a0, read_a())}
print(f"Counts: MOTB={counts['MOTB']}  MOTA={counts['MOTA']}\n")
sys.exit(0 if report_per_turn(counts) else 1)
