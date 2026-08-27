"""
Main entry point to launch commands from Godot.

This script listens for JSON strings of this form:
    {
        "command": str,
        "args": any
        "run_mode": "once", "start" or "stop"
    }

For run_mode == "once", the function listed in COMMAND_MAPPING[command] is
executed once.

For run_mode == "start", the function listed in COMMAND_MAPPING[command] starts
being executed continuously. Many functions can be started at the same time;
in this case they are executed one after the other, continuously.

For run_mode == "stop", the function listed in COMMAND_MAPPING[command] stops
being executed consinuously.
"""

import os
from typing import Any

import biofeedback
import data_logging
from python_bridge import GODOT_TO_PYTHON_PORT, IP, Receiver, sender


class PrivateVariables:
    """Keep track of private variables."""

    is_running: bool = True


_private_vars = PrivateVariables
_running_commands: dict[str, dict[str, Any]] = {}


def _close(args=None):
    """Close the Python app."""
    print("\nClose Python app...")
    _private_vars.is_running = False


def _send_ready() -> None:
    """Send ready to Godot."""
    sender.send({"command": "ready", "args": {}, "data": []})


def _test(arg1: str, arg2: int) -> None:
    """Answer to test command (used in unit tests)."""
    sender.send(
        {
            "command": "test",
            "data": [arg1, arg2, 1, 2, 3],
        }
    )



COMMAND_MAPPING = {
    "test": _test,
    "biofeedback_update": biofeedback.biofeedback_update,
    "biofeedback_stop": biofeedback.biofeedback_stop,
    "close": _close,
    "start_logging": data_logging.start_log,
    "create_trial": data_logging.create_trial,
    "data_logging": data_logging.save_data,
    "end_trial": data_logging.end_trial,
    "end_logging": data_logging.end_log,
}


if __name__ == "__main__":
    # Create the receiver
    receiver = Receiver(ip=IP, port=GODOT_TO_PYTHON_PORT, timeout=0.0)
    # Send "ready" to Godot
    _send_ready()

    # Listening Godot requests
    while _private_vars.is_running:
        # Execute every command in the UDP buffer
        while command_dict := receiver.receive():
            command = command_dict["command"]
            run_mode = command_dict["run_mode"]
            args = command_dict["args"]

            print(f"{run_mode} : {command} {args}")

            if run_mode == "start":
                if command not in _running_commands:
                    _running_commands[command] = {"args": args}

            elif run_mode == "stop":
                if command in _running_commands:
                    _running_commands.pop(command)

            elif run_mode == "once":
                COMMAND_MAPPING[command](**command_dict["args"])

            else:
                raise ValueError("frequency must be 'start', 'stop' or 'once'")

        # Do not execute repeating commands after shutdown request
        if not _private_vars.is_running:
            break

        # Execute every repeating command
        for command in _running_commands:
            COMMAND_MAPPING[command](**_running_commands[command]["args"])

    # Quit
    os._exit(0)
