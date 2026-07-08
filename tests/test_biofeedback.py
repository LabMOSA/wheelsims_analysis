"""
Unit tests for the biofeedback processing and kinematic analysis module.

This module validates the integration and correct computation of real-time
wheelchair propulsion metrics using pre-recorded OptiTrack data simulated
in an offline environment.
"""

import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, "src"))
sys.path.append(root_dir)

import kineticstoolkit as ktk

from src import biofeedback


def test_with_udp_data_from_motive():
    """
    Validate the biofeedback update loop using prerecorded OptiTrack data.

    This test simulates an offline real-time stream by incrementally feeding
    time series segments into the `biofeedback_update` pipeline. It ensures
    that the exact number of propulsion cycles and full kinematics timestamps
    are correctly extracted and match historical baseline counts.
    """
    data_path = os.path.join(
        root_dir, "tests", "data", "optitrack_fetch.ktk.zip"
    )
    data = ktk.load(data_path)

    arg_path = os.path.join(
        root_dir,
        "tests",
        "data",
        "godot_argument_for_biofeedback_test.ktk.zip",
    )
    arg = ktk.load(arg_path)

    biofeedback._runtime_state["run_mode"] = "offline"

    try:
        nb_index = min(
            [
                len(data["102"].time),
                len(data["201"].time),
                len(data["202"].time),
            ]
        )
        data_temp = data.copy()

        for i in range(1, nb_index, 40):
            data_temp["102"] = data["102"].get_ts_before_index(i)
            data_temp["201"] = data["201"].get_ts_before_index(i)
            data_temp["202"] = data["202"].get_ts_before_index(i)
            biofeedback._runtime_state["data"] = data_temp
            try:
                biofeedback.biofeedback_update(arg)
            except Exception as e:
                print(e)
        results = biofeedback.kinematics_data.copy()
        biofeedback.biofeedback_stop(arg)

    except Exception as e:
        print(e)

    y = [
        len(results["cycles"]["left"]),
        len(results["cycles"]["right"]),
        len(results["ts_full"]["left"].time),
        len(results["ts_full"]["right"].time),
    ]

    assert [8, 7, 1237, 1237] == y, (
        f"TEST FAILED: Exp: [8,7,1237,1237] | Got: {y} | "
    )


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__])
