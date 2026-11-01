# Entry 2: Making the line follower fast (60-200 rpm)

Date: Oct 14, evening (18:30 to about 21:50). All changes are in `Lab9/line_follow.py`. Starting point: entry 1, tuned at 40 rpm.

## Problem

The controller from entry 1 loses the line when the base speed goes up. At 100 rpm the sensor reaches the line before the wheels can react, and the corners (an "M" shape takes about half the lap) are taken too fast. Each fix below was added one after another and checked with a run.

## Steps

1. **Scale the gains with speed** (`58a98e0`, `8a209d0`).
   Linear scaling overshot at 100 rpm. The fitted rule is
   `KS = 0.0055 * (base/40)**0.6`, `KIS = 0.008 * (base/40)**0.5`
   (0.0095 at 100 vs 0.0055 at 40 fits the exponent 0.6; I grows slower because it kept steering past the edge). They can still be overridden on the command line.
2. **Short brake** (`ee51213`, `b5df1ef`). Coasting at duty 0 is too slow to shed speed. If a wheel is more than `BRAKE_MARGIN = 20` rpm above its target, both DRV8833 inputs are set high (short brake). rpm noise is about ±9, so 20 avoids false braking. On/off only.
3. **Faster sensor** (`9e4f068`, `23a0504`, `a8e8224`). Integration time 24 ms to 12 ms halves the sensor delay, and the loop time follows it (`DT = 0.02*ms/24`, about 13 ms). Gain stays 4 because 12 ms saturates at 5120 counts. Counts are multiplied by `C_SCALE = 24/integration_ms`, so `SETPOINT = 2000`, `KS`, `KIS` and the thresholds below still mean the same. `sensor.active = True` keeps it integrating; otherwise every read waits about 45 ms for power-up. 12 ms readings (`*_it12.csv`, mean C): white 2049, black middle 195, edge 801 (these are unscaled).
4. **Slow down in corners** (`1fdb21f`, `9de65db`, `47388e6` and the SLOW_DEAD commits).
   `slow = min(1 - |steer|/(SLOW_TURN*base), 1 - max(0,|error| - SLOW_DEAD)/(SLOW_ERR - SLOW_DEAD))`
   `target_base = min(base_rpm, max(CORNER_RPM, base_rpm*slow))`
   - `SLOW_ERR = 1500`: error where speed would reach 0 (3000 made the M wobble).
   - `SLOW_DEAD = 600`: errors below it do not slow down. Straight-line wobble is about ±430, and a lower value kept the straights at about 85 rpm. Tuned over 7 commits (`438ed66` to `647734b`).
   - `CORNER_RPM = 50`: floor speed in rpm, not a fraction of base. We tried several values (`7a7791f`..`bd67831`); 40 held, 50 is the final value.
   - `SLOW_TURN = 9999`: steering-based slowdown effectively off (`ffb1a44`).
5. **Rate limits** (`ef9b707`, `2245c95`, `a48de1c`). `SLOW_RECOVER = 100` rpm/s: speed climbs back slowly, which stops 40<->95 rpm surging in corners. `SLOW_DROP` was tried at 400 and lost the first M corner at 150 rpm (entered at about 130, crossed the line in 0.1 s), so it is off (99999).
6. **Clear the I term** (`aba0aa1`). `RESET_ERR = 1200`: if |error| is above it and the integral pushes against the error, the integral is reset. Without it the I term kept steering past the edge after a corner.
7. **Wheel limit** (`MAX_RPM = 220`). Motors top out at about 225-230 rpm. If one target exceeds it, both are lowered by the excess, so the speed difference (the turn) stays.
8. `KDS` stays 0 (`78c8b48` only added it to the log header).

## Runs (from `follow/`)

Each row is a run's total log time; a run is 22 s if it completed the track (about 22 s for the full course at 12 ms) and shorter if we stopped it or it lost the line. I could not tell from the log alone which short runs were stops and which were losses, so short runs are marked "short".

| Base | KS | KIS | Integration | Runs | Typical outcome |
|---|---|---|---|---|---|
| 60 | 0.00825 | 0.012 | 24 | 2 | 35 s with brake, mean error 434 |
| 80 | 0.011 | 0.016 | 24 | 2 | 28.7 s with brake, 566 |
| 100 | 0.0095-0.011 | 0.01-0.016 | 24/12 | 13 | 12 ms: 5 of 6 runs go 23-29 s, mean error 550-680 |
| 120 | 0.0106 | 0.0139 | 24 | 1 | short (5.8 s) |
| 150 | 0.011 / 0.013 | 0.01 | 12 | 6 | 4 of 6 completed, 24-27 s, mean error about 650 |
| 180 | 0.013 | 0.01 (0.007 failed, 4-6 s) | 12 | 14 | about 6 completed at 21-24 s, mean error 720-790; the rest short |
| 200 | 0.013 / 0.014 | 0.01 | 12 | 9 | 5 completed at 21-22 s, mean error 745-790; the rest short |

Observations:

- 180 and 200 rpm give the same lap time (about 21-22 s) because of the corner floor; the average rpm is about 80, as the straights are short.
- KIS 0.007 at 180 lost the line in 4-6 s, 0.01 works. So lowering I was the wrong direction.
- The 100 rpm runs that finished take 23-29 s, no faster than 180/200.
- Max error stays near 2000-2500 in the good runs. Max above 3500 means the sensor left the line.
- Gains were not re-tuned between 150 and 200: the same KS 0.013 / KIS 0.01 worked.

## Best 180 rpm run

`follow/base180_ks0.013_sp2000_kis0.01_it12_213458.csv`: 21.1 s (shortest of the six full-length 180 runs), mean abs error 778, max 1918, SLOW_DEAD 600, SLOW_RECOVER 100. It ran on commit `438ed66`; the current `HEAD` differs only in whitespace and an extra `kds=0` in the log header, so the behaviour is the same.
Rerun (from `Lab9/`, rover placed at the start, press Enter): `python line_follow.py 180 25 0.013 2000 0.01`. Results vary with battery and lighting (the 180 runs ranged 21.1-24.2 s).

## Final settings (`647734b`)

```
KP, KI, KD = 0.01, 0.02, 0     INTEGRATION_MS = 12   gain 4   SETPOINT = 2000   EDGE = -1
KS_40 = 0.0055  KIS_40 = 0.008  KDS = 0
SLOW_ERR = 1500  SLOW_DEAD = 600  CORNER_RPM = 50  SLOW_RECOVER = 100  SLOW_DROP = 99999  SLOW_TURN = 9999
MAX_RPM = 220  RESET_ERR = 1200  BRAKE_MARGIN = 20
```

## Reproduce

```sh
cd Lab9
python line_follow.py 200 25 0.013 2000 0.01   # BASE_RPM SECONDS KS SETPOINT KIS
```

The log is written to `follow/base<rpm>_ks<..>_sp<..>_kis<..>_it<ms>_<HHMMSS>.csv`; the first line holds all settings, and the columns are
`time,c,error,left_target,left_rpm,right_target,right_rpm,base,left_out,right_out,i_reset,steer`.
To tune: start at 40 with the entry 1 values, raise the base in steps (60, 100, 150, 200), watch `error` and the `base` column in the log. Increase `KS` if it drifts off, lower it if it oscillates. If it loses a corner, lower `SLOW_ERR` or `SLOW_DEAD` (slow down earlier) before touching `CORNER_RPM`.
To test the sensor: `python color_sensor.py NAME 12` and compare against the table in entry 1.
