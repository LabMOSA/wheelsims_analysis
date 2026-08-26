"""
Integration and unit tests for the propulsion_patterns module.

Main functionalities tested:
    - Geometric zone and score computations
      --> (_compute_a1_score,_compute_a2_score)
    - Cycle filtering by velocity, amplitude, and mean crossing
    - Propulsion cycle detection and segmentation
    - Cycle phase extraction and push pattern classification
      --> (PM, SLOP, SC, DLOP)
    - Unilateral and bilateral propulsion data visualization
"""

import pytest

import os
import sys
import numpy as np

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, "src"))
sys.path.append(root_dir)

import kineticstoolkit as ktk
from src import propulsion_patterns


# %% Unit tests
def test_compute_geometric_zones(_push_pattern_cycles_data):
    """
    Test _compute_geometric_zones.

    Verifies the calculation of geometric zones defining the spatial
    boundaries between the push and recovery phases.
    """

    dict_push_pattern_cycle = _push_pattern_cycles_data

    push_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            0,
            87,
        )
        .data["Meta2left"][:, 0:2]
    )

    recovery_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            87,
            125,
        )
        .data["Meta2left"][:, 0:2]
    )

    propulsion_patterns._compute_geometric_zones(push_phase, recovery_phase)

    return


def test_compute_a1_score(_push_pattern_cycles_data):
    """
    Test _compute_a1_score.

    Verifies the calculation of the A1 score, which quantifies the main area
    enclosed by the push and recovery trajectory loop.
    """

    dict_push_pattern_cycle = _push_pattern_cycles_data

    push_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            0,
            87,
        )
        .data["Meta2left"][:, 0:2]
    )

    recovery_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            87,
            125,
        )
        .data["Meta2left"][:, 0:2]
    )

    propulsion_patterns._compute_a1_score(push_phase, recovery_phase)

    return


def test_compute_a2_score(_push_pattern_cycles_data):
    """
    Test _compute_a2_score.

    Verifies the computation of the A2 score based on signed sub-areas
    formed by crossing loops during the propulsion cycle.
    """

    signed_areas = []

    signed_areas.append(
        {
            "sign": "positive",
            "area": 0.5,
            "recovery_phase": None,
            "push_phase": None,
        }
    )

    signed_areas.append(
        {
            "sign": "negative",
            "area": 0.5,
            "recovery_phase": None,
            "push_phase": None,
        }
    )

    propulsion_patterns._compute_a2_score(signed_areas)

    return


def test_filter_cycles_by_velocity_and_amplitude(
    _unfiltered__cycles_metrics_data,
):
    """
    Test _filter_cycles_by_velocity_and_amplitude.

    Ensures that detected cycles below specified velocity or amplitude
    thresholds are properly filtered out (expected: 8 valid cycles retained).
    """

    unfiltered_cycles_metrics = _unfiltered__cycles_metrics_data

    (
        filtered_cycles
    ) = propulsion_patterns._filter_cycles_by_velocity_and_amplitude(
        unfiltered_cycles_metrics
    )

    assert 8 == len(filtered_cycles), (
        f"Exp: 8 cycles detected | Got: {len(filtered_cycles)}"
    )

    return


def test_filter_cycles_by_mean_crossing(
    _unfiltered__cycles_metrics_data,
    _bilateral_ts_propulsion_data,
):
    """
    Test _filter_cycles_by_mean_crossing.

    Verifies cycle filtering based on baseline/mean position crossing rules
    (expected: 8 valid cycles retained).
    """

    unfiltered_cycles_metrics = _unfiltered__cycles_metrics_data

    bilateral_ts_propulsion = _bilateral_ts_propulsion_data
    ts_propulsion = bilateral_ts_propulsion["left"]

    filtered_cycles = propulsion_patterns._filter_cycles_by_mean_crossing(
        unfiltered_cycles_metrics, ts_propulsion
    )

    assert 8 == len(filtered_cycles), (
        f"Exp: 8 cycles detected | Got: {len(filtered_cycles)}"
    )

    return


def test_plot_bilateral_cycles(
    _bilateral_ts_propulsion_data, _cycles_metrics_data
):
    """
    Test detect_propulsion_cycles.

    Verifies that the bilateral cycle visualization function executes
    without errors given valid left and right side TimeSeries and metrics.
    """

    bilateral_ts_propulsion = _bilateral_ts_propulsion_data

    cycles_metrics = _cycles_metrics_data

    bilateral_cycles_metrics = {
        "left": cycles_metrics,
        "right": cycles_metrics,
    }

    propulsion_patterns.plot_bilateral_cycles(
        bilateral_ts_propulsion,
        bilateral_cycles_metrics,
    )

    return


def test_plot_unilateral_push_patterns(
    _bilateral_ts_propulsion_data, _push_pattern_cycles_data
):
    """
    Test detect_propulsion_cycles.

    Verifies that single-side propulsion trajectory plots
    (including push/recovery phases and pattern labels) render properly
    without throwing exceptions.
    """

    bilateral_ts_propulsion = _bilateral_ts_propulsion_data
    ts_propulsion = bilateral_ts_propulsion["left"]

    dict_push_pattern_cycle = _push_pattern_cycles_data

    push_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            0,
            87,
        )
        .data["Meta2left"][:, 0:2]
    )

    recovery_phase = (
        dict_push_pattern_cycle["Pumping (PM)"]
        .get_ts_between_indexes(
            87,
            125,
        )
        .data["Meta2left"][:, 0:2]
    )

    cycles = []

    signed_areas = []

    signed_areas.append(
        {
            "sign": "positive",
            "area": 0.5,
            "recovery_phase": recovery_phase,
            "push_phase": push_phase,
        }
    )

    cycles.append(
        {
            "in_push": {"time": 0.57, "value": -0.13},
            "recovery": {"time": 1.50, "value": -0.14},
            "end_push": {"time": 2.36, "value": -0.16},
            "range": 0.36,
            "velocity_max": 0.73,
            "push_frequency": None,
            "normalised_push_pattern": None,
            "areas": signed_areas,
            "A1": -1.00,
            "A2": 0.50,
            "label_push_pattern": "Pumping (PM)",
        }
    )

    propulsion_patterns.plot_unilateral_push_patterns(
        ts_propulsion,
        cycles,
    )

    return


def test_segment_propulsion_cycles(
    _bilateral_ts_propulsion_data, _cycles_metrics_data
):
    """
    Test detect_propulsion_cycles.

    Verifies that continuous TimeSeries data is correctly sliced into
    individual TimeSeries cycles based on cycle metrics
    (expected: 8 extracted cycle TimeSeries).
    """
    bilateral_ts_propulsion = _bilateral_ts_propulsion_data
    ts_propulsion = bilateral_ts_propulsion["left"]

    cycles_metrics = _cycles_metrics_data

    cycles_ts_list = propulsion_patterns.segment_propulsion_cycles(
        ts_propulsion, cycles_metrics
    )

    assert 8 == len(cycles_ts_list), (
        f"TEST FAILED: Exp: 8 cycles detected | Got: {len(cycles_ts_list)}"
    )

    return


def test_extract_propulsion_phases(_push_pattern_cycles_data):
    """
    Test detect_propulsion_cycles.

    Verifies that a single cycle TimeSeries is properly split into its
    respective push and recovery spatial trajectories.
    """

    dict_push_pattern_cycle = _push_pattern_cycles_data

    push_phase, recovery_phase = propulsion_patterns.extract_propulsion_phases(
        dict_push_pattern_cycle[next(iter(dict_push_pattern_cycle))]
    )

    return


# %% Integration tests public functions
def test_detect_propulsion_cycles(_bilateral_ts_propulsion_data):
    """
    Test detect_propulsion_cycles.

    Tests the end-to-end detection pipeline on raw kinematics to ensure it
    correctly identifies propulsion cycle boundaries
    (expected: 8 cycles detected).
    """
    bilateral_ts_propulsion = _bilateral_ts_propulsion_data

    ts_propulsion = bilateral_ts_propulsion["left"]

    cycles_metrics = propulsion_patterns.detect_propulsion_cycles(
        ts_propulsion
    )

    assert 8 == len(cycles_metrics), (
        f"TEST FAILED: Exp: 8 cycles detected | Got: {len(cycles_metrics)}"
    )

    return


def test_analyse_propulsion_cycle(_push_pattern_cycles_data):
    """
    Test detect_propulsion_cycles.

    Verifies the complete analysis pipeline for a single cycle, calculating
    metrics, areas, scores (A1, A2), and pattern classification.
    """

    dict_push_pattern_cycle = _push_pattern_cycles_data

    cycle_analyzed = propulsion_patterns.analyse_propulsion_cycle(
        dict_push_pattern_cycle[next(iter(dict_push_pattern_cycle))]
    )

    assert np.all(np.isfinite(cycle_analyzed["normalised_push_pattern"])), (
        "normalised_push_pattern contains NaN or Inf"
    )

    return


def test_classify_push_pattern(_push_pattern_cycles_data):
    """
    Test detect_propulsion_cycles.

    Ensures that known propulsion cycles (Pumping, Single-Loop, Semi-Circular,
    Double-Loop) are correctly classified into their expected pattern labels
    based on geometry.
    """

    dict_push_pattern_cycle = _push_pattern_cycles_data

    for push_pattern in dict_push_pattern_cycle:
        (label_push_pattern, A1, A2, signed_areas) = (
            propulsion_patterns.classify_push_pattern(
                dict_push_pattern_cycle[push_pattern]
            )
        )

        assert label_push_pattern == push_pattern, (
            f"Exp: {push_pattern} cycles detected | Got: {label_push_pattern}"
        )

    return


# %% Fixtures for loading and processing test data
@pytest.fixture
def _bilateral_ts_propulsion_data():
    """
    Load and preprocess raw bilateral hand propulsion TimeSeries data.

    Synchronizes time vectors and centers hand coordinates onto left and right
    wheel centers.
    """

    # Load data
    data_path = os.path.join(
        root_dir, "tests", "data", "optitrack_fetch.ktk.zip"
    )
    data = ktk.load(data_path)

    # Load arg
    arg_path = os.path.join(
        root_dir,
        "tests",
        "data",
        "godot_argument_for_biofeedback_test.ktk.zip",
    )
    arg = ktk.load(arg_path)

    # Synchronize the time vectors so that t=0 corresponds to the first sample
    data["201"].time = data["201"].time - data["201"].time[0]
    data["202"].time = data["202"].time - data["202"].time[0]
    data["102"].time = data["102"].time - data["102"].time[0]

    # Initialize calibration data from the input arguments
    data_side = _initialize_data_side(arg)

    # Dictionaries used to store left and right side results
    # for bilateral visualization
    bilateral_ts_propulsion = {}

    # Process the left side (i=0, "201") and the right side (i=1, "202")
    for i in range(2):
        # Compute local kinematics (already filtered and expressed in the
        # simulator "102" reference frame)
        ts_xxx, side = _compute_local_kinematics(data, data_side, i)
        key_data = f"Meta2{side}"

        # Extract the 3D coordinates (X, Y, Z) from array
        coords_hand_local = ts_xxx.data[key_data][:, :3]

        # Retrieve the wheel center coordinates [X, Y, Z] for the current side
        wheel_center_local = data_side[i]["wheel_center"][0, :3]

        # Create the TimeSeries centered on the wheel center (0, 0, 0)
        # for the current side
        ts_propulsion_cycles = ktk.TimeSeries()
        ts_propulsion_cycles.time = ts_xxx.time

        # Center the hand coordinates by subtracting the calibrated wheel
        # center position
        ts_propulsion_cycles.data[key_data] = np.zeros_like(coords_hand_local)
        ts_propulsion_cycles.data[key_data][:, 0] = (
            coords_hand_local[:, 0] - wheel_center_local[0]
        )  # X
        ts_propulsion_cycles.data[key_data][:, 1] = (
            coords_hand_local[:, 1] - wheel_center_local[1]
        )  # Y
        ts_propulsion_cycles.data[key_data][:, 2] = (
            coords_hand_local[:, 2] - wheel_center_local[2]
        )  # Z

        bilateral_ts_propulsion[side] = ts_propulsion_cycles

    return bilateral_ts_propulsion


@pytest.fixture
def _cycles_metrics_data():
    """
    Provide temporal boundary metrics for segmented propulsion cycles.

    Contains start and end push timestamps used to isolate valid cycle
    intervals.
    """

    cycles_metrics = []

    cycles_metrics.append(
        {
            "in_push": {"time": 0.57, "value": -0.13},
            "end_push": {"time": 2.36, "value": -0.16},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 2.36, "value": -0.16},
            "end_push": {"time": 3.92, "value": -0.13},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 3.92, "value": -0.13},
            "end_push": {"time": 5.59, "value": -0.14},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 5.59, "value": -0.14},
            "end_push": {"time": 7.28, "value": -0.15},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 7.28, "value": -0.15},
            "end_push": {"time": 8.47, "value": -0.24},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 8.47, "value": -0.24},
            "end_push": {"time": 9.95, "value": -0.23},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 9.95, "value": -0.23},
            "end_push": {"time": 11.93, "value": -0.19},
        }
    )

    cycles_metrics.append(
        {
            "in_push": {"time": 11.93, "value": -0.19},
            "end_push": {"time": 14.01, "value": -0.16},
        }
    )

    return cycles_metrics


@pytest.fixture
def _push_pattern_cycles_data(
    _bilateral_ts_propulsion_data, _cycles_metrics_data
):
    """
    Generate representative TimeSeries samples for each propulsion pattern.

    Extracts isolated cycle signals for Pumping (PM), Single-Loop (SLOP),
    Semi-Circular (SC), and Double-Loop (DLOP) patterns.
    """

    bilateral_ts_propulsion = _bilateral_ts_propulsion_data
    ts_propulsion = bilateral_ts_propulsion["left"]

    cycles_metrics = _cycles_metrics_data

    dict_push_pattern_cycle = {}

    for i in [0, 2, 4, 6]:
        cycle = cycles_metrics[i]

        t_start = cycle["in_push"]["time"]
        t_end = cycle["end_push"]["time"]

        if i == 0:
            dict_push_pattern_cycle["Pumping (PM)"] = (
                ts_propulsion.get_ts_between_times(t_start, t_end)
            )
        if i == 2:
            dict_push_pattern_cycle["Single-Loop (SLOP)"] = (
                ts_propulsion.get_ts_between_times(t_start, t_end)
            )
        if i == 4:
            dict_push_pattern_cycle["Semi-Circular (SC)"] = (
                ts_propulsion.get_ts_between_times(t_start, t_end)
            )
        if i == 6:
            dict_push_pattern_cycle["Double-Loop (DLOP)"] = (
                ts_propulsion.get_ts_between_times(t_start, t_end)
            )

    return dict_push_pattern_cycle


@pytest.fixture
def _unfiltered__cycles_metrics_data():
    """
    Provide raw, unfiltered cycle metrics.

    Includes both valid and invalid movements with amplitude and peak velocity
    values used to test cycle filtering functions.
    """

    unfiltered_cycles_metrics = []

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 0.57, "value": -0.13},
            "end_push": {"time": 2.36, "value": -0.16},
            "value": -0.16,
            "range": 0.36,
            "velocity_max": 0.73,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 2.36, "value": -0.16},
            "end_push": {"time": 3.92, "value": -0.13},
            "value": -0.13,
            "range": 0.39,
            "velocity_max": 0.86,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 3.92, "value": -0.13},
            "end_push": {"time": 5.59, "value": -0.14},
            "value": -0.14,
            "range": 0.55,
            "velocity_max": 1.23,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 5.59, "value": -0.14},
            "end_push": {"time": 7.28, "value": -0.15},
            "value": -0.15,
            "range": 0.56,
            "velocity_max": 1.42,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 7.28, "value": -0.15},
            "end_push": {"time": 8.47, "value": -0.24},
            "value": -0.24,
            "range": 0.34,
            "velocity_max": 1.65,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 8.47, "value": -0.24},
            "end_push": {"time": 9.95, "value": -0.23},
            "value": -0.23,
            "range": 0.46,
            "velocity_max": 1.31,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 9.95, "value": -0.23},
            "end_push": {"time": 11.93, "value": -0.19},
            "value": -0.19,
            "range": 0.77,
            "velocity_max": 1.80,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 11.93, "value": -0.19},
            "end_push": {"time": 14.01, "value": -0.16},
            "value": -0.16,
            "range": 0.71,
            "velocity_max": 1.30,
        }
    )

    unfiltered_cycles_metrics.append(
        {
            "in_push": {"time": 14.31, "value": -0.12},
            "end_push": {"time": 14.89, "value": -0.12},
            "value": -0.12,
            "range": 0.006,
            "velocity_max": 0.024,
        }
    )

    return unfiltered_cycles_metrics


def _initialize_data_side(arg):
    """Initialize and structures calibration coordinates for both sides."""
    # Get and convert coordinates to homogeneous arrays [X, Y, Z, 1.0]
    coordinates_left_wheel_center = np.array(
        [list(arg["coordinates_left_wheel_center"]) + [1.0]],
    )

    coordinates_right_wheel_center = np.array(
        [list(arg["coordinates_right_wheel_center"]) + [1.0]],
    )

    coordinates_left_hand = np.array(
        [list(arg["coordinates_left_hand"]) + [1.0]],
    )
    coordinates_right_hand = np.array(
        [list(arg["coordinates_right_hand"]) + [1.0]],
    )

    # Set a dictionnary of side-specific metadata and tracking IDs
    data_side = [
        {
            "id_streaming": "201",
            "local_meta2": coordinates_left_hand,
            "side": "left",
            "wheel_center": coordinates_left_wheel_center,
        },
        {
            "id_streaming": "202",
            "local_meta2": coordinates_right_hand,
            "side": "right",
            "wheel_center": coordinates_right_wheel_center,
        },
    ]

    return data_side


def _compute_local_kinematics(
    data_windowed: dict[str, ktk.TimeSeries],
    data_side,
    n: int,
):
    """
    Transform tracking data into local kinematics.

    Filters and processes timeseries data for a single wheelchair side.
    """
    # Extract side-specific configuration and streaming tracking ID
    id_streaming = data_side[n]["id_streaming"]
    side = data_side[n]["side"]

    # Estimate second metacarpal (Meta2) position using the forearm
    # cluster reference frame
    ts = ktk.TimeSeries()
    ts.time = data_windowed[id_streaming].time

    ts.data[f"Meta2{side}"] = ktk.geometry.matmul(
        data_windowed[id_streaming].data[id_streaming],
        data_side[n]["local_meta2"],
    )

    # Find the common overlapping time window and resample the forearm
    # signals onto the simulator frame"s timeline
    t_min = max(ts.time[0], data_windowed["102"].time[0])
    t_max = min(ts.time[-1], data_windowed["102"].time[-1])

    ts_data = data_windowed["102"].get_ts_between_times(t_min, t_max)
    ts = ts.get_ts_between_times(t_min, t_max)

    # Transform Meta2 coordinates from the global tracking system to the
    # simulator"s local coordinate system
    ts.data[f"Meta2{side}"] = ktk.geometry.get_local_coordinates(
        global_coordinates=ts.data[f"Meta2{side}"],
        reference_frames=ts_data.data["102"],
    )

    return ts, side


# %% Main
if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
