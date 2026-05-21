import socket
import json
import time
import biofeedback

UDP_IP = "127.0.0.1"
PYTHON_PORT = 4243
GODOT_PORT = 4242

is_running = [True]
running_commands = {}


def _close():
    """Close the Python app."""
    print("\nClose Python app...")
    time.sleep(2)
    is_running[0] = False


COMMAND_MAPPING = {
    "biofeedback_godot": biofeedback.biofeedback_godot,
    "close": _close,
}


def send_data(data):
    """Encode data to JSON and send it via UDP."""
    message = json.dumps(data).encode("utf-8")
    sock.sendto(message, (UDP_IP, GODOT_PORT))


if __name__ == "__main__":

    # Init UDP sockets
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.0)
    sock.bind((UDP_IP, PYTHON_PORT))

    # Sending ping request, availables functions to Godot for debug scene
    print("Python connected to Godot...\n")
    time.sleep(1)
    send_data(list(COMMAND_MAPPING.keys()))

    time.sleep(1)

    # Listening Godot requests
    while is_running[0]:

        # Execute every command in the UDP buffer
        while True:  # until there's nothing available anymore
            try:
                message, address = sock.recvfrom(1024)

                command_dict = json.loads(message.decode("utf-8"))
                command = command_dict["command"]
                run_mode = command_dict["run_mode"]
                args = command_dict["args"]

                if run_mode == "start":
                    if command not in running_commands:
                        running_commands[command] = {"args": args}

                elif run_mode == "stop":
                    if command in running_commands:
                        running_commands.pop(command)

                elif run_mode == "once":
                    command_dict["command"](command_dict["args"])

                else:
                    raise ValueError("frequency must be 'start', 'stop' or 'once'")

            except socket.timeout:
                break

        # Execute every repeating command
        for command in running_commands:
            command(running_commands[command]["args"])

    # Quit
    sock.close()
