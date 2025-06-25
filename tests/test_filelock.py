import threading
import time

from clayutil.futil import filelock

l = [0.0, 0.0, 0.0]


@filelock(0)
def main(*args):
    l[args[1]] = time.perf_counter()
    time.sleep(1)


if __name__ == "__main__":
    t1 = threading.Thread(target=main, name="t1", args=(0, 0))
    t2 = threading.Thread(target=main, name="t2", args=(0, 1))
    t3 = threading.Thread(target=main, name="t3", args=(1, 2))
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()
    print(l)
    assert l[1] - l[0] >= 1
