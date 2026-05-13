import socket
import json
import time
import importlib
import sys
import threading
import biofeedback
import optitrack as ot

UDP_IP = "127.0.0.1"
PYTHON_PORT = 4243
GODOT_PORT = 4242

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

sock.settimeout(1.0)

sock.bind((UDP_IP, PYTHON_PORT))

running = True


# basics functions
def biofeedback_godot(arg):
    print("biofeedback_godot")
    biofeedback.biofeedback_godot(arg)


def plot_biofeedback_godot(arg):
    print("plot_biofeedback_godot")


# Close this Python app
def close():
    global running
    print("\nClose Python app...")
    time.sleep(2)
    running = False


# functions to call anything command : Godot to Python
command = {
    "biofeedback_godot": biofeedback_godot,
    "plot_biofeedback_godot": plot_biofeedback_godot,
    "close": close,
}


def call_command(_json):

    _command = _json.get("command")
    _arg = _json.get("arg")

    try:
        func = command[_command]
        if _arg is not None:
            func(_arg)
        else:
            func()
        print("request received : ", _command)
    except:
        print("error call command")
        True


# Bridge functions UDP : Python to Godot
def _send_data(data):

    try:
        message = json.dumps(data).encode("utf-8")
        sock.sendto(message, (UDP_IP, GODOT_PORT))

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    try:

        # Sending ping request, availables functions to Godot for debug scene
        print("Python connected to Godot...\n")
        time.sleep(1)
        _send_data(list(command.keys()))

        time.sleep(1)

        # Listening Godot requests
        while running:
            try:

                message, address = sock.recvfrom(1024)
                commande = message.decode("utf-8")
                commande = json.loads(commande)

                call_command(commande)

            except socket.timeout:
                continue
    except:
        pass
    finally:
        sock.close()
