"""
Main entry point for Godot to launch the Python bridge.

This script acts as a lightweight wrapper that initializes and starts
the UDP receiver loop to handle communication with Godot.
"""

from python_bridge import dispatcher

if __name__ == "__main__":
    dispatcher.start()
