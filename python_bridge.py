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
ts = None


def start_optitrack():
    ot.start()


# basics functions
def push_frequency(arg):
    global ts
    mean_push_frequency = biofeedback.push_frequency(ts, arg)
    _send_data({"type": "response", "data": str(mean_push_frequency)})


def clear_data_optitrack():
    ot.clear()


# Close this Python app
def close():
    global running
    print("\nClose Python app...")
    time.sleep(2)
    running = False


# functions to call anything command : Godot to Python
command = {
    "clear_data_optitrack": clear_data_optitrack,
    "push_frequency": push_frequency,
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
        print("la fonction n'existe pas")


# Bridge functions UDP : Python to Godot
def _send_data(data):

    try:
        message = json.dumps(data).encode("utf-8")
        sock.sendto(message, (UDP_IP, GODOT_PORT))

    except KeyboardInterrupt:
        pass


# Main
try:

    # Sending ping request, availables functions to Godot for debug scene
    print("Python connected to Godot...\n")
    time.sleep(1)
    _send_data(list(command.keys()))

    ot_thread = threading.Thread(target=start_optitrack, daemon=True)
    ot_thread.start()

    time.sleep(1)

    # Listening Godot requests
    while running:
        try:

            ts = ot.fetch()

            message, address = sock.recvfrom(1024)
            commande = message.decode("utf-8")
            commande = json.loads(commande)

            call_command(commande)

        except socket.timeout:
            continue
except KeyboardInterrupt:
    pass
finally:
    sock.close()
    ot.stop()
