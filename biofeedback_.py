import optitrack as ot
import matplotlib.pyplot as plt
import kineticstoolkit.lab as ktk
import socket
import json
import time

ot.start()

n = 1
last_clear = -1


try:
    while True:
        ts = ot.fetch()
finally:

    ot.stop()

    ktk.save("ts_all_2.ktk.zip", ts)
