"""Test the nextwheel_dummy package."""

import os
import sys
import pytest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, "src"))
sys.path.append(root_dir)

import nextwheel_dummy


def test_nextwheel_dummy():
    """Simply test the constructor."""
    # It's difficult to test more than that since the rest of the class is
    # time-dependent. At least, we check that the constructor works, which
    # also means that the data is loaded.
    nextwheel_dummy.NextWheel()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
