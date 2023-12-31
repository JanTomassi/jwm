import subprocess
import time
import threading

prev_rx: int = 0
prev_tx: int = 0
is_locking: int = 0
widget_num: int = 0
mutex = threading.Lock()

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
    with mutex:

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
    with mutex:

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
    with mutex:
        res: str = subprocess.run(["date", "+%c"], capture_output=True, text=True).stdout
        return res[:-1]


def get_package_update():
    with mutex:
        res_p: str = subprocess.run(["pacman", "-Quq"], capture_output=True, text=True).stdout
        res_y: str = subprocess.run(["yay", "-Quaq"], capture_output=True, text=True).stdout
        n_p = len(res_p.split("\n")[:-1])
        n_y = len(res_y.split("\n")[:-1])
        return f"{n_p} + {n_y} 󰏔"


def get_free_space():
    with mutex:
        res_space: str = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True
        ).stdout
        res_spaceL: list[str] = res_space.split("\n")
        return res_spaceL[1].split()[4] + " 󰋊"

def get_battery():
    with mutex:
        res = ""
        with open("/sys/class/power_supply/BAT0/capacity") as f:
            res = f.read()
        return f"{res[:-1]} batt"


def update_root_window():
    global str_module
    
    with mutex:
        if str_module is None:
            str_module = [""]*5
        subprocess.run(["xsetroot", "-name", " | ".join(str_module)])


def run_module():
    global str_module

    run_on_interval(5, get_network, str_module)
    run_on_interval(60, get_battery, str_module)
    run_on_interval(60 * 10, get_free_space, str_module)
    run_on_interval(60 * 60, get_package_update, str_module)
    run_on_interval(1, get_date, str_module)

    run_on_interval(1, update_root_window)


if __name__ == "__main__":
    global str_module

    str_module = [""]*5
    new_name = run_module()
