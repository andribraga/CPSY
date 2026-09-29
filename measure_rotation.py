"""Check counts per wheel turn using the kernel encoder driver.
Put a tape mark on each wheel, turn each wheel by hand a known number of
full turns (10 is good), press Ctrl+C, then type how many turns you made."""
import sys
import time

from kernel_encoder import delta, open_encoder, read_steps

EXPECTED = 700    # counts per wheel turn we expect
TOLERANCE = 0.05  # 5%; a quarter turn off over 10 turns is 2.5%

motb, mota = open_encoder("rotary@6"), open_encoder("rotary@12")
b0, a0 = read_steps(motb), read_steps(mota)

print("Turn the wheels by hand. Ctrl+C when done.")
try:
    while True:
        print(f"\rMOTB: {delta(b0, read_steps(motb)):6d}   MOTA: {delta(a0, read_steps(mota)):6d}",
              end="", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n")

counts = {"MOTB": delta(b0, read_steps(motb)), "MOTA": delta(a0, read_steps(mota))}
all_ok = True
for name, n in counts.items():
    turns = float(input(f"How many full turns did {name} make? [10] ") or 10)
    per_turn = n / turns
    err = (per_turn - EXPECTED) / EXPECTED
    ok = abs(err) <= TOLERANCE
    all_ok &= ok
    print(f"  {name}: {n} counts / {turns:g} turns = {per_turn:.0f} per turn "
          f"({err:+.1%} vs {EXPECTED}) {'PASS' if ok else 'FAIL'}")

sys.exit(0 if all_ok else 1)
