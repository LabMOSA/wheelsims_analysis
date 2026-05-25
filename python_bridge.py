"""
Execute python commands with arguments, repeatedly or once.

This script opens a port (PYTHON_PORT) and listens for JSON strings of this
form:
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

import socket
import json
import time
import biofeedback
import create_file
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
    #"biofeedback_update": biofeedback.biofeedback_update,
    #"biofeedback_stop": biofeedback.biofeedback_stop,
    "close": _close,
    "create_file" : create_file.create_files,
    "data_logging" : data_logging.save_data
}


def _init_udp_socket():
    """Initialize the UDP sockets"""
    if _private_vars["sock"] == None:

        _private_vars["sock"] = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )
        _private_vars["sock"].setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        _private_vars["sock"].settimeout(0.0)
        _private_vars["sock"].bind((UDP_IP, PYTHON_PORT))


# Bridge functions UDP : Python to Godot
def send_data(data):
    """Encode data to JSON and send it via UDP."""
    _init_udp_socket()
    message = json.dumps(data).encode("utf-8")
    _private_vars["sock"].sendto(message, (UDP_IP, GODOT_PORT))


if __name__ == "__main__":

    _init_udp_socket()

    # Sending ping request, availables functions to Godot for debug scene
    print("Python connected to Godot...\n")
    time.sleep(1)
    send_data(list(COMMAND_MAPPING.keys()))

    time.sleep(1)

    # Listening Godot requests
    while _private_vars["is_running"]:

        # Execute every command in the UDP buffer
        while True:  # until there's nothing available anymore
            try:
                message, address = _private_vars["sock"].recvfrom(1024)

                command_dict = json.loads(message.decode("utf-8"))
                command = command_dict["command"]
                run_mode = command_dict["run_mode"]
                args = command_dict["args"]

                if run_mode == "start":
                    if command not in _running_commands:
                        _running_commands[command] = {"args": args}

                elif run_mode == "stop":
                    if command in _running_commands:
                        _running_commands.pop(command)

                elif run_mode == "once":
                    COMMAND_MAPPING[command](command_dict["args"])

                else:
                    raise ValueError(
                        "frequency must be 'start', 'stop' or 'once'"
                    )

            except BlockingIOError:
                pass
            except ConnectionResetError:
                pass

        # Execute every repeating command
        for command in _running_commands:
            COMMAND_MAPPING[command](_running_commands[command]["args"])

    # Quit
    _private_vars["sock"].close()