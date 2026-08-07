"""
Provide NextWheel dummy data, like if we had a real NextWheel.

This is a package mainly for testing. It mimicks a very small subset of the
real NextWheel class so that we can instantiate a wheel, start streaming (in
reality it's always "streaming"), and fetch data.

"""

import os
import time

import nextwheel

this_dir = os.path.dirname(__file__)


class NextWheel:
    """A dummy class that mimics a real NextWheel."""

    def __init__(self):

        # Read dummy data
        self._data = nextwheel.read_dat(
            this_dir + "/sample.dat", this_dir + "/sample_calibration.json"
        )

        # Set the time zero around the middle of this series
        shift = self._data["Analog"].time.mean() + 20
        self._data["Analog"].shift(-shift, in_place=True)
        self._data["IMU"].shift(-shift, in_place=True)
        self._data["Encoder"].shift(-shift, in_place=True)
        self._data["Power"].shift(-shift, in_place=True)

        self._time_start = time.time()

    def start_streaming(self):
        """Do nothing."""
        pass

    def stop_streaming(self):
        """Do nothing."""
        pass

    def fetch(self):
        """Fetch data as if we were connected to a real wheel."""
        time_now = time.time()
        if time_now - self._time_start > self._data["Analog"].time[-1]:
            # We reached the end of the data and should restart at zero.
            self._time_start = time_now

        return {
            "Analog": self._data["Analog"].get_ts_between_times(
                time_now - self._time_start - 60.0, time_now - self._time_start
            ),
            "IMU": self._data["IMU"].get_ts_between_times(
                time_now - self._time_start - 60.0, time_now - self._time_start
            ),
            "Encoder": self._data["Encoder"].get_ts_between_times(
                time_now - self._time_start - 60.0, time_now - self._time_start
            ),
            "Power": self._data["Power"].get_ts_between_times(
                time_now - self._time_start - 60.0, time_now - self._time_start
            ),
        }
