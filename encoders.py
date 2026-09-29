"""Encoder readers for all three backends: lgpio, pigpio, kernel.
lgpio/pigpio need the rotary-encoder overlays commented out in /boot/firmware/config.txt
(else "GPIO busy"); kernel needs them enabled."""
import fcntl
import glob
import struct
import sys

from gpiozero import Device, RotaryEncoder

BACKENDS = ("lgpio", "pigpio", "kernel")
ROLLOVER = 100000  # must match steps= in config.txt (kernel counter wraps here)
EVIOCGABS_X = 0x80184540  # ioctl: read ABS_X (struct input_absinfo, 6 x int32)


def open_encoder(name):
    """Open the input device the kernel created for one encoder, e.g. 'rotary@6'."""
    for p in glob.glob("/sys/class/input/event*/device/name"):
        with open(p) as f:
            if f.read().strip() == name:
                return open("/dev/input/" + p.split("/")[4], "rb")
    sys.exit(f"No input device '{name}'. Kernel overlays enabled? Check: cat /sys/class/input/event*/device/name")


def read_steps(f):
    """Current position counter of a kernel encoder."""
    return struct.unpack("6i", fcntl.ioctl(f, EVIOCGABS_X, bytes(24)))[0]


def delta(before, after):
    """Steps moved between two readings, either direction, handles the wrap at ROLLOVER."""
    d = (after - before) % ROLLOVER
    return min(d, ROLLOVER - d)


def setup(backend):
    """Set gpiozero's pin factory (also used by Motor) and return (read_motb, read_mota)."""
    try:
        if backend == "pigpio":
            from gpiozero.pins.pigpio import PiGPIOFactory
            Device.pin_factory = PiGPIOFactory()
        elif backend in ("lgpio", "kernel"):  # kernel: lgpio only drives the motors
            from gpiozero.pins.lgpio import LGPIOFactory
            Device.pin_factory = LGPIOFactory()
        else:
            sys.exit(f"Unknown backend '{backend}'. Use one of: {'|'.join(BACKENDS)}")
    except ImportError as e:
        sys.exit(f"{backend} Python package missing ({e}). Try: uv add {backend}")
    except OSError as e:
        sys.exit(f"Can't use {backend}: {e}. For pigpio, start the daemon: sudo pigpiod")

    print("Backend:", backend)
    if backend == "kernel":
        fb, fa = open_encoder("rotary@6"), open_encoder("rotary@12")
        return (lambda: read_steps(fb)), (lambda: read_steps(fa))
    motb = RotaryEncoder(a=6, b=13, max_steps=0)
    mota = RotaryEncoder(a=18, b=12, max_steps=0)
    return (lambda: motb.steps), (lambda: mota.steps)


if __name__ == "__main__":
    assert delta(5, 700) == 695
    assert delta(700, 5) == 695
    assert delta(99990, 10) == 20
    assert delta(10, 99990) == 20
    print("delta ok")
