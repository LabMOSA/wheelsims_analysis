"""
Main entry point for Godot to launch the Python bridge.

This script acts as a lightweight wrapper that initializes and starts
the UDP receiver loop to handle communication with Godot.
"""

<<<<<<< HEAD
import json
import os
import socket
import time

import biofeedback
import data_logging

UDP_IP = "127.0.0.1"
PYTHON_PORT = 4243
GODOT_PORT = 4242

_private_vars = {
    "is_running": True,
    "sock": None,
}

_running_commands = {}


def _close(args=None):
    """Close the Python app."""
    print("\nClose Python app...")
    time.sleep(2)
    _private_vars["is_running"] = False


COMMAND_MAPPING = {
    "biofeedback_update": biofeedback.biofeedback_update,
    "biofeedback_stop": biofeedback.biofeedback_stop,
    "close": _close,
    "start_logging": data_logging.start_log,
    "create_trial": data_logging.create_trial,
    "data_logging": data_logging.save_data,
    "end_trial": data_logging.end_trial,
    "end_logging": data_logging.end_log,
}


def _init_udp_socket():
    """Initialize the UDP sockets."""
    if _private_vars["sock"] == None:
        _private_vars["sock"] = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )
        _private_vars["sock"].setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        _private_vars["sock"].settimeout(0.0)
        _private_vars["sock"].bind((UDP_IP, PYTHON_PORT))


def send_data(command, data):
    """Encode data to JSON and send it via UDP."""
    _init_udp_socket()

    message = {"command": command, "data": data}

    json_message = json.dumps(message).encode("utf-8")
    _private_vars["sock"].sendto(json_message, (UDP_IP, GODOT_PORT))

=======
from bridge_package import receiver
>>>>>>> main

if __name__ == "__main__":
    receiver.start()
