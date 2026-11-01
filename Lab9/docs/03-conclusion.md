# Entry 3: Conclusion and reflection

## Conclusion

A single TCS34725 clear-channel reading was enough to follow the edge of the black line. The controller has two layers: a PID for each wheel's speed, and a PI loop that steers from the sensor error. Adding the I term roughly halved the mean error compared with P only, from about 900 to about 500. The D term only added noise, so `KDS = 0`. The 40 rpm tune (`KS = 0.0055`, `KIS = 0.008`) was the base for going faster. Speed came from several changes together:

- scaling the gains with speed
- short braking
- a 12 ms sensor integration time
- slowing down in corners
- rate limits
- resetting the I term after large errors

The rover finished the track at 180 and 200 rpm in about 21-22 s, with a mean error of about 750.

## Reflection

- **Sensor delay:** The sensor, not the motors, was the main limit. Halving the integration time helped more than any gain change.
- **Corner floor:** Going above about 180 rpm gave no gain, because the corner floor (`CORNER_RPM = 50`) and the short straights set the lap time.
- **Reliability:** About half of the fast runs failed or were stopped, and the logs didn't say which. Lighting and battery level also changed the results.
- **Lowering I was the wrong move:** KIS 0.007 at 180 rpm lost the line, while 0.01 worked.

## What we will change

**For this run (180 rpm, same track):**

1. Lower `CORNER_RPM` from 50 to 40 and `SLOW_ERR` from 1500 to 1300. *Measure:* lap time under 20 s (best so far 21.1 s) and max error under 2500.
2. Do 5 repeat runs with the same settings and a fully charged battery. *Measure:* at least 4 of 5 finish, with lap times within ±1 s.

**In the future:**

1. Add an `outcome` field (`finished`, `lost_line`, or `stopped`) to the CSV header. *Measure:* 100% of runs in `follow/` have an outcome.
2. Improve reliability at 180-200 rpm. *Measure:* at least 9 of 10 consecutive runs finish (now about 6 of 14).
3. Reduce the wobble on the straights. *Measure:* mean abs error under 600 (now 720-790).
4. Recalibrate the white level before each session. *Measure:* the white C value stays within ±10% between sessions.
