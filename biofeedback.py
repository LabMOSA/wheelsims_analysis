import optitrack as ot
import matplotlib.pyplot as plt
import kineticstoolkit.lab as ktk
import socket
import json
import time

ot.start()

n=1
last_clear = -1

def plot_pattern_1(key):
        
        global points
        global events
        
        # Plot 1
        plt.figure()
        times = ts[key].time
        pos = ts[key].data [key][:, 0:3, 3]
        
        t = ts[key].time
        x = ts[key].data [key][:, 0, 3]
        y = ts[key].data [key][:, 1, 3]
        z = ts[key].data [key][:, 2, 3]

        plt.plot(t, x, label='x')
        plt.plot(t, y, label='y')
        plt.plot(t, z, label='z')
        
        plt.legend()
        
        plt.title("ID rigidbody : " + str(key))
        
        points = plt.ginput(6)
        
        events = []
        for point in points:
               # events.append(float(point[0]))
               ts[key] = ts[key].add_event(float(point[0]), "X")
    
        for i in range(5):
            
            ts_crop = ts.copy()
            ts_crop[key] = ts_crop[key].get_ts_between_times(float(points[i][0]), float(points[i+1][0]))
        
            # Plot 2
            plt.figure()
            times = ts_crop[key].time
            pos = ts_crop[key].data[key][:, 0:3, 3]
            
            t = ts_crop[key].time
            x = ts_crop[key].data[key][:, 0, 3]
            y = ts_crop[key].data[key][:, 1, 3]
            z = ts_crop[key].data[key][:, 2, 3]
    
            plt.plot(x, y)
            
            plt.legend()
            
            plt.title("ID rigidbody : " + str(key))
            


try:
    while True:
        ts = ot.fetch()
        
        if 1 in ts:
            n = len(ts[1].time) 
            print(n)
        else:
            continue

finally:
    
    ot.stop()

    ktk.save("ts_all_.ktk.zip", ts)
            

