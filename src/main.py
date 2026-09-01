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

Command "close" is reserved for closing the python bridge.

"""

import os
from collections.abc import Callable
from typing import Any

import biofeedback
import biofeedback_pushrim_kinetics as bf_pk
import data_logging
from python_bridge import GODOT_TO_PYTHON_PORT, IP, Receiver, sender

_running_commands: dict[str, dict[str, Any]] = {}


def _send_ready() -> None:
    """Send ready to Godot."""
    sender.send({"command": "ready", "data": []})


def _test(arg1: str, arg2: int) -> None:
    """Answer to test command (used in unit tests)."""
    sender.send(
        {
            "command": "test",
            "data": [arg1, arg2, 1, 2, 3],
        }
    )


COMMAND_MAPPING: dict[str, Callable] = {
    "test": _test,
    "biofeedback_update": biofeedback.biofeedback_update,
    "biofeedback_stop": biofeedback.biofeedback_stop,
    "biofeedback_pushrim_kinetics_connect": bf_pk.connect,
    "biofeedback_pushrim_kinetics_process": bf_pk.process,
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

    stay_in_loop = True
    # Listening Godot requests
    while True:
        # Execute every command in the UDP buffer
        while command_dict := receiver.receive():
            command = command_dict["command"]
            run_mode = command_dict["run_mode"]
            args = command_dict["args"]

            print(f"{run_mode} : {command} {args}")

            if command == "close":
                # Close now
                stay_in_loop = False
                break

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
        if not stay_in_loop:
            break

        # Execute every repeating command
        for command in _running_commands:
            COMMAND_MAPPING[command](**_running_commands[command]["args"])

    # Quit
    os._exit(0)
