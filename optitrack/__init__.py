#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2024-2026 Laboratoire de recherche en mobilité et systèmes adaptés

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module that receives a single streamed rigid body from Optitrack.

In the future, this module will be configurable and will return the position and
orientation of multiple rigid bodies as Kinetics Toolkit Timeseries.

"""

__author__ = "Laboratoire de recherche en mobilité et systèmes adaptés"
__copyright__ = (
    "Copyright (C) 2024-2026 Laboratoire de recherche en mobilité et systèmes adaptés"
)
__email__ = "chenier.felix@uqam.ca"
__license__ = "Apache 2.0"

import sys
import time
from NatNetClient import NatNetClient
import kineticstoolkit.lab as ktk
import numpy as np

# Maximal number of frames to keep in memory
frame_limit = 1000

# Initialize empty lists to store positions and timestamps
_positions = []  # Initialize empty lists to store positions
_times = []  # and timestamps

# Initial system time (to calculate time stamps relative to import time)
_initial_system_time = time.time()

# Global variable for the NatNet client
_streaming_client = NatNetClient()


def receive_rigid_body_frame(
    new_id: int, position: np.ndarray, orientation: np.ndarray
) -> None:  # ignore: D401
    """
    Add a new received rigid body data (used as callback).

    Parameters
    ----------
    new_id
        The ID of the rigid body.
    position
        The position of the rigid body as a NumPy array.
    orientation
        The orientation of the rigid body as a NumPy array.

    Returns
    -------
    None

    """
    # Calculate elapsed time since the first frame
    relative_time = time.time() - _initial_system_time

    # Add position and timestamp
    _positions.append(np.append(position, 1.0))
    _times.append(relative_time)

    # If frame count exceeds limit, remove oldest frames
    if len(_positions) > frame_limit:
        _positions.pop(0)
        _times.pop(0)


def fetch() -> ktk.TimeSeries:
    """
    Get a TimeSeries from the current position and time lists.

    Returns
    -------
    ktk.TimeSeries
        A time series object containing the position of the rigid bodies over
        time.

    """
    # Convert lists of times and positions to numpy arrays
    times_np = np.array(_times)
    positions_np = np.array(_positions)

    # Create the timeseries
    ts = ktk.TimeSeries(data={"Position": positions_np}, time=times_np)

    return ts


def start() -> None:
    """
    Start receiving data from NatNet.

    Returns
    -------
    None

    """
    # Configure client to receive rigid body data
    _streaming_client.rigid_body_listener = receive_rigid_body_frame

    # Start NatNet client
    is_running = _streaming_client.run()
    if not is_running:
        print(
            "ERROR: Could not start streaming client."
        )  # Indicates an error if the streaming client fails to start
        sys.exit(1)

    # Wait for client to connect
    while not _streaming_client.connected():
        time.sleep(1)

    print(
        "Connected to the server. Receiving data..."
    )  # Indicates successful connection to the NatNet server


def stop() -> None:
    """
    Stop receiving data from NatNet.

    Returns
    -------
    None

    """
    # Stop NatNet client
    _streaming_client.shutdown()


def clear() -> None:
    """
    Clear positions and times lists.

    Returns
    -------
    None

    """
    _positions.clear()
    _times.clear()
