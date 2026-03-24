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
Module that receives a multiple streamed rigid bodies from Optitrack.

This module return the position and orientation of multiple rigid bodies
as Kinetics Toolkit Timeseries.

"""

__author__ = "Laboratoire de recherche en mobilité et systèmes adaptés"
__copyright__ = "Copyright (C) 2024-2026 Laboratoire de recherche en mobilité et systèmes adaptés"
__email__ = "chenier.felix@uqam.ca"
__license__ = "Apache 2.0"

import sys
import time
from .NatNetClient import NatNetClient
import kineticstoolkit.lab as ktk
import numpy as np

# Maximal number of frames to keep in memory
frame_limit = 1000

# Initialize empty lists to store positions, orientations and timestamps
_data = {}
ts = {}

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

    if new_id not in _data:
        _data[new_id] = {"_positions": [], "_orientations": [], "_times": []}

    # Add position, orientation and timestamp
    _data[new_id]["_positions"].append(np.append(position, 1.0))
    _data[new_id]["_orientations"].append(np.append(orientation, 1.0))
    _data[new_id]["_times"].append(relative_time)

    # If frame count exceeds limit, remove oldest frames
    if len(_data[new_id]["_positions"]) > frame_limit:
        _data[new_id]["_positions"].pop(0)
        _data[new_id]["_orientations"].pop(0)
        _data[new_id]["_times"].pop(0)


def fetch() -> ktk.TimeSeries:
    """
    Get the trajectory of all received rigid bodies as TimeSeries of transforms.

    Returns a dictionary of TimeSeries where each key is the ID of the rigid
    body in Motive, and the TimeSeries contains one transform series. The max
    length of these TimeSeries can be changed by changing the frame_limit
    property of this module.

    A dictionary of TimeSeries is returned instead of one TimeSeries because
    each data is received at a different time value. TimeSeries can then be
    merged to a single time vector using the TimeSeries.merge() method.

    Returns
    -------
    dict[str, ktk.TimeSeries]

    """

    for key in _data.keys():

        # Convert lists of times, positions and orientations to numpy arrays
        times_np = np.array(_data[key]["_times"])
        positions_np = np.array(_data[key]["_positions"])[:, 0:3]
        orientations_np = np.array(_data[key]["_orientations"])[:, 0:4]

        # Create the homogeneous transformation matrix
        transforms = ktk.geometry.create_transform_series(
            quaternions=orientations_np, positions=positions_np
        )

        # Create the timeseries
        ts[str(key)] = ktk.TimeSeries(data={str(key): transforms}, time=times_np)

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
    Clear buffer.

    Returns
    -------
    None

    """
    _data.clear()
