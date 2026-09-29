"""Read encoder counts from the kernel rotary-encoder driver.
Needs the dtoverlay=rotary-encoder lines enabled in /boot/firmware/config.txt."""
import fcntl
import glob
import struct
import sys

ROLLOVER = 100000  # must match steps= in config.txt (counter wraps here)
EVIOCGABS_X = 0x80184540  # ioctl: read ABS_X (struct input_absinfo, 6 x int32)


def open_encoder(name):
    """Open the input device the kernel created for one encoder, e.g. 'rotary@6'."""
    for p in glob.glob("/sys/class/input/event*/device/name"):
        with open(p) as f:
            if f.read().strip() == name:
                return open("/dev/input/" + p.split("/")[4], "rb")
    sys.exit(f"No input device '{name}'. Check: cat /sys/class/input/event*/device/name")


def read_steps(f):
    """Current position counter of the encoder."""
    return struct.unpack("6i", fcntl.ioctl(f, EVIOCGABS_X, bytes(24)))[0]


def delta(before, after):
    """Steps moved between two readings, either direction, handles the wrap at ROLLOVER."""
    d = (after - before) % ROLLOVER
    return min(d, ROLLOVER - d)


if __name__ == "__main__":
    assert delta(5, 700) == 695
    assert delta(700, 5) == 695
    assert delta(99990, 10) == 20
    assert delta(10, 99990) == 20
    print("delta ok")
