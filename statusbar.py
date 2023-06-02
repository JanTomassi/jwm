import subprocess
import time
from bluetooth import *
import threading

prev_rx: int = 0
prev_tx: int = 0
is_locking: int = 0
widget_num: int = 0

def run_on_interval_thread(t: int, f, m: list=None, i: int=None):
    e = 0
    while True:
        if (e % t) == 0:
            if m is not None and i is not None:
                m[i] = f()
            elif m is None and i is None:
                f()
        e += 1
        time.sleep(1)


def run_on_interval(t: int, f, m = None):
    global widget_num

    if(m is not None):
        mWidget_num = widget_num
        widget_num += 1

        threading.Thread(
            target=run_on_interval_thread,
            args=(t, f, m, mWidget_num),
        ).start()

    elif(m is None):
        threading.Thread(
            target=run_on_interval_thread,
            args=(t, f),
        ).start()


def get_network():
    global prev_rx
    global prev_tx

    result = subprocess.run(["ip", "route"], capture_output=True, text=True)
    intf = result.stdout.split("\n")[0].split()[4]

    with open("/proc/net/dev", "r") as f:
        next(f)
        next(f)
        for line in f:
            interface, stats = line.split(":", 1)
            if interface.strip() != intf:
                continue
            stats = [int(x) for x in stats.split()]
            res = "%s - %05.2f 󰞒 %05.2f 󰞕" % (
                interface.strip(),
                (stats[0] - prev_rx) * 8 / 1024 / 1024,
                (stats[8] - prev_tx) * 8 / 1024 / 1024,
            )
            prev_rx = stats[0]
            prev_tx = stats[8]
            return res


def get_date():
    res: str = subprocess.run(["date", "+%c"], capture_output=True, text=True).stdout
    return res[:-1]


def get_package_update():
    res_p: str = subprocess.run(["pacman", "-Quq"], capture_output=True, text=True).stdout
    res_y: str = subprocess.run(["yay", "-Quaq"], capture_output=True, text=True).stdout
    n_p = len(res_p.split("\n")[:-1])
    n_y = len(res_y.split("\n")[:-1])
    return f"{n_p} + {n_y} 󰏔"


def get_free_space():
    res_space: str = subprocess.run(
        ["df", "-h", "/"], capture_output=True, text=True
    ).stdout
    res_spaceL: list[str] = res_space.split("\n")
    return res_spaceL[1].split()[4] + " 󰋊"


def get_bluetooth_device() -> bool:
    device_found = lookup_name("AC:3E:B1:73:1B:6A")
    return device_found is not None


def lock_if_no_dev():
    subprocess.run(["i3lock", "-c", b"000000"])


def unlock_if_near():
    subprocess.run(["pkill", "i3lock"])


def manage_bluetooth_locking():
    global is_locking

    is_device = get_bluetooth_device()

    if is_device:
        is_locking = 0
        return " 󰄜"

    elif not (is_device) and (is_locking == 2):
        is_locking += 1
        lock_if_no_dev()
        return " 󰥐"

    elif not (is_device) and (is_locking <= 2):
        is_locking += 1
        subprocess.run(["notify-send", "Phone not found for %d" % is_locking])
        return " 󰥐"

def update_root_window():
    global str_module

    subprocess.run(["xsetroot", "-name", " | ".join(str_module)])


def run_module():
    run_on_interval(15, manage_bluetooth_locking, str_module)
    run_on_interval(1, get_network, str_module)
    run_on_interval(60 * 10, get_free_space, str_module)
    run_on_interval(60 * 60, get_package_update, str_module)
    run_on_interval(1, get_date, str_module)

    run_on_interval(1, update_root_window)


if __name__ == "__main__":
    global str_module

    str_module = [""]*5
    new_name = run_module()
