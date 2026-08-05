"""
UDP Sender (Client).

Provides the 'send_data' utility function, allowing any module in the project
to independently send JSON messages to Godot via UDP.
"""

import json
import socket

UDP_IP = "127.0.0.1"
GODOT_PORT = 4242

_active_socket = [None]


def send_data(command, data):
    """Encode data to JSON and send it via UDP."""
    message = {"command": command, "data": data}
    json_message = json.dumps(message).encode("utf-8")

    if _active_socket[0] is None:
        _active_socket[0] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    _active_socket[0].sendto(json_message, (UDP_IP, GODOT_PORT))
