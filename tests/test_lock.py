import threading
import time

from clayutil.futil import filelock


@filelock
def main(*args):
    print("thread {} started at {}".format(threading.current_thread().name, time.perf_counter()))
    time.sleep(1)
    print("thread {} ended at {}".format(threading.current_thread().name, time.perf_counter()))


def test():
    t1 = threading.Thread(target=main, name="t1", args=[0])
    t2 = threading.Thread(target=main, name="t2", args=[0])
    t3 = threading.Thread(target=main, name="t3", args=[1])
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()
