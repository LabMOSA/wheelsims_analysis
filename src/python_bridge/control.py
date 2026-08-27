"""Control signals for python bridge."""

from python_bridge import sender


def send_ready() -> None:
    """Send ready to Godot."""
    sender.send({"command": "ready", "args": {}, "data": []})


def test(arg1: str, arg2: int) -> None:
    """Answer to test command (used in unit tests)."""
    sender.send(
        {
            "command": "test",
            "data": [arg1, arg2, 1, 2, 3],
        }
    )
