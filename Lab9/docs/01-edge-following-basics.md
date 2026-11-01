# Entry 1: Following the black line by its edge (slow speeds, 20-40 rpm)

Dates: Oct 13-14. Code: `color_sensor.py` (`ba2732d`), `line_follow.py` (first version `6b7f021`).

## Idea

A single TCS34725 colour sensor looks down at the floor. We use its **clear channel** (`color_raw[3]`), which is a brightness count: high on white, low on black.
We do not drive on top of the line. We drive along its **edge**, with the white area on the right of the rover. Over the edge the reading changes smoothly between "white" and "black", so the error `c - SETPOINT` has a sign and a size:

- `error > 0`: too much white, steer left.
- `error < 0`: too much black, steer right.

Following the middle of the line would need left/right decisions on white-black-white. With the sensor on one side we only have black and white, which is easier. The reading can change with the light in the room.

## Hardware and software

- TCS34725 on I2C (`board.I2C()`): SDA and SCL go straight to the Pi, ground and power to the breadboard (as in Lab 2). `i2cdetect -y 1` should show address `0x29`. Integration time 24 ms, gain 4 (later 12 ms, see entry 2).
- Motors through a DRV8833: left forward/backward GPIO 19/26, right 20/16, SLP on GPIO 5.
- Encoders (evdev devices `rotary@6` left, `rotary@12` right). 694 steps per revolution, counter wraps at 100000.
- Python deps from the repo root: `uv sync` (adafruit-circuitpython-tcs34725, evdev, gpiozero, simple-pid).

## Sensor calibration

The sensor readings (seven tests with `color_sensor.py`, channel means, why we use the clear channel C) are in the earlier Lab 9 notebook entry (pp. 145-153, data in `color_sensor_readings/`, commit `0649308`). Here we only use the result: C is about 3900 on white and about 900 on the black line, and white varies between runs, so the setpoint needs trial and error.

We started at `SETPOINT = 2800` (chosen in that entry).

## Controller

Two nested loops, both in `line_follow.py`:

1. **Wheel speed PID** (one per wheel, `simple_pid`, KP=0.01, KI=0.02, KD=0, output 0..1 = motor duty). Input: rpm computed from encoder steps over the loop time `dt`. The gains came from the earlier speed tuning in `../tuning/`.
2. **Steering PI.** `steer = EDGE * (KS*error + KIS*integral(error))`, then
   `left_target = base + steer`, `right_target = base - steer` (rpm). `EDGE = -1` because white is on the right; flip it to `1` if the rover steers away from the edge.
   The output is clamped to `±base` so that neither wheel target goes below 0.

First version (`6b7f021`) was P only, `SETPOINT = 2800`, `KS = 0.01`, loop time 0.05 s.

## What we tried

1. **Setpoint 2800 failed**: the rover just left the line, so we changed the setpoint to **2000**.
2. P-only wobbled/drifted on curves, so we added an I term (`KIS`, commit `22e8fc9`) and a CLI argument for it.
3. A D term (`KDS`, `9dba9d3`) was tried and made it wobble: the sensor jumps about 3000 counts between samples, so the derivative is mostly noise. `KDS = 0`.
4. Sweeps of `KS`/`KIS` at base 20-40 rpm (logs in `follow/`, every log has the settings in its first `#` line; columns `time,c,error,left_target,left_rpm,right_target,right_rpm,...`):

| Base rpm | KS | KIS | Log (mean abs error / max abs error) | Note |
|---|---|---|---|---|
| 20 | 0.008 | 0.004 | 544 / 2193 | 20 s run |
| 25 | 0.008 | 0.004 | 610 / 1650 | |
| 25 | 0.008 | 0.002 | 638 / 2052 | |
| 25 | 0.005 | 0.004 | 511 / 1701 | |
| 25 | 0.004 | 0.005 | 596 / 2214 | |
| 25 | 0.003 | 0.006 | 455 / 3890 | large excursion |
| 25 | 0.0035 | 0.0055 | 430 / 4239 (`_slow`: 492 / 2150) | `_slow` = long run, 178 s |
| 25 | 0.008 | 0 (KDS 0 / 0.0002) | 1005 / 2873, 1002 / 3488 | D tests, worse |
| 30 | 0.003 / 0.005 | 0 (setpoint 2000/2200/2500) | 892..976 / 2243..3168 | setpoint tests, P only |
| 30 | 0.004 / 0.0048 | 0.005 / 0.006 | 519 / 2038, 533 / 2204 | 75 s run |
| 35 | 0.0056 | 0.007 | 583 / 2204 | |
| 40 | 0.0055 | 0.008 | 446..670 / 2033..2270 | **reference tune** |
| 40 | 0.0064 | 0.008 | 612 / 2298 | |
| 40 | 0.005 | 0.0085 | 1113 / 2513 | lost the line (32 s) |

Result: adding I roughly halved the mean error compared with P only (about 900 to about 500). The tune at 40 rpm is `KS_40 = 0.0055`, `KIS_40 = 0.008`. These are the values entry 2 scales from.

The logged `error` is only measured at the sensor; mean abs error around 500 means the sensor stays within about a quarter of the white-black range around the edge.

## Reproduce

```sh
uv sync
# 1. calibrate (on the Pi, sensor held over each surface)
python Lab9/color_sensor.py white
python Lab9/color_sensor.py black_middle
python Lab9/color_sensor.py edge
# 2. drive, white on the right of the rover
cd Lab9
python line_follow.py 40 60 0.0055 2000 0.008     # BASE_RPM SECONDS KS SETPOINT KIS
```

The script waits for Enter, so you can place the rover first. The log goes to `follow/`. If the rover turns away from the edge, set `EDGE = 1`. If it wobbles, lower `KS` first, then `KIS`.
Use `git checkout fed3962 -- Lab9/line_follow.py` (or `22e8fc9`) to see the early, simpler controller.
