"""Control signals for python bridge."""

from python_bridge import sender


def send_ready() -> None:
    """Send ready to Godot."""
    sender.send({"command": "ready", "args": {}, "data": []})


def test(arg1: str, arg2: int) -> None:
    sender.send(
        {
            "command": "test",
            "args": {"arg1": arg1, "arg2": arg2},
            "data": [1, 2, 3],
        }
    )
