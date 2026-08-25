"""Just a script for now, will become a proper unit test later."""

import matplotlib.pyplot as plt
import pytest
import os
import sys


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, "src"))
sys.path.append(root_dir)


import biofeedback_pushrim_kinetics



biofeedback_pushrim_kinetics.init()
while True:
    biofeedback_pushrim_kinetics.process()
    plt.pause(0.1)
    plt.cla()
