"""
Real-time wheelchair biofeedback processing and kinematic analysis module.

This module streams and processes raw tracking data from OptiTrack
(Motive software) in real time using a rolling window approach.

It filters local kinematics, extracts and validates voluntary propulsion
cycles, computes geometric metrics (A1, A2, areas), and classifies
push patterns.

The resulting metrics are synchronized and sent to the Godot engine.
"""

import time
from typing import Literal, TypedDict

import kineticstoolkit as ktk
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as MplPolygon

import optitrack as ot

# %% Public variables

# Area ratio thresholds used to discriminate between Semi-Circular (SC),
# Single-Loop (SLOP), and Double-Loop (DLOP) propulsion techniques.
PATTERN_A2_SC_THRESHOLD = 0.75
PATTERN_A2_SLOP_THRESHOLD = 0.75

# Maximum allowed geometric deviation for pattern validation
MAX_DEVIATION_THRESHOLD = 0.1

# Minimum required duration for a valid propulsion cycle (in seconds)
MIN_CYCLE_DURATION = 0.4

# Minimum peak velocity required to filter out parasitic movements (m/s)
MIN_CYCLE_MAX_VELOCITY = 0.2


# %% Typing classes
class Arg(TypedDict):
    """
    Configuration arguments for the biofeedback system.

    coordinates_left_wheel_center :
        3D calibration coordinates (X, Y, Z) for the left wheel center.
    coordinates_right_wheel_center :
        3D calibration coordinates (X, Y, Z) for the right wheel center.
    coordinates_left_hand :
        Initial 3D coordinates (X, Y, Z) of the marker on the left hand.
    coordinates_right_hand :
        Initial 3D coordinates (X, Y, Z) of the marker on the right hand.
    wheel_diameter :
        Diameter of the wheelchair wheels in meters.
    """

    coordinates_left_wheel_center: list[float]
    coordinates_right_wheel_center: list[float]
    coordinates_left_hand: list[float]
    coordinates_right_hand: list[float]
    wheel_diameter: float


class DataSide(TypedDict):
    """
    Side-specific streaming and calibration metadata.

    id_streaming :
        OptiTrack rigid body streaming ID unique to each side.
    local_meta2 :
        Local transformation for kinematic calculations.
    side :
        Label indicating the body side.
    wheel_center :
        3D position vector of the wheel center.
    """

    id_streaming: Literal["201", "202"]
    local_meta2: np.ndarray
    side: Literal["left", "right"]
    wheel_center: np.ndarray


class CycleEvent(TypedDict):
    """
    Temporal and spatial data point marking a propulsion cycle event.

    time :
        Timestamp of the detected event in seconds.
    value :
        Kinematic value associated with the event.
    """

    time: float
    value: float


class Areas(TypedDict):
    """
    Signed geometric areas and trajectories between propulsion phases.

    sign :
        Sign of the deviation between recovery and push curves.
    area : float
        Calculated surface area between the segmented trajectories.
    recovery_phase :
        Array of coordinates representing the recovery path for this segment.
    push_phase :
        Array of coordinates representing the push path for this segment.
    """

    sign: Literal["positive", "negative"]
    area: float
    recovery_phase: np.ndarray
    push_phase: np.ndarray


class PushCycle(TypedDict):
    """
    Calculated metrics and kinematics for a single full propulsion cycle.

    in_push :
        Time and value marking the start of the push phase.
    recovery :
        Time and value marking the start of the recovery phase.
    end_push :
        Time and value marking the end of the push phase.
    range :
        Total linear displacement achieved along the anteroposterior axis
        during the push phase
    velocity_max :
        Maximum velocity reached during the cycle.
    """

    in_push: dict[Literal["time", "value"], float]
    recovery: dict[Literal["time", "value"], float]
    end_push: dict[Literal["time", "value"], float]
    range: float
    velocity_max: float
    push_frequency: float
    normalised_push_pattern: np.ndarray
    areas: list[Areas] | None
    A1: float | None
    A2: float | None
    label_push_pattern: (
        Literal[
            "Pumping (PM)",
            "Semi-Circular (SC)",
            "Single-Loop (SLOP)",
            "Double-Loop (DLOP)",
            "",
        ]
        | None
    )


class KtkDataAndCycles(TypedDict):
    """
    Container for processed time-series kinematics and detected cycles.

    ts :
        Kineticstoolkit TimeSeries object containing side-specific kinematics.
    cycles :
        List of all valid propulsion cycles detected within the time window.
    """

    ts: ktk.TimeSeries | None
    cycles: list[PushCycle] | None


class Results(TypedDict):
    """
    Global state and accumulated processing results for the biofeedback system.

    run_mode :
        Current execution state controlling real-time data acquisition.
    data :
        Raw input data mapping stream names to TimeSeries.
    current_window_data :
        Processed kinematic data and cycles scoped to the active time window.
    cycles :
        Historical or cumulative list of push cycles for each side.
    new_cycle_log :
        Counter or index tracking recently logged cycles for file writing.
    new_cycle_send :
        Counter or index tracking cycles sent to the biofeedback display.
    ts_full :
        Full continuous time-series history aggregated since the session start.
    """

    run_mode: Literal["start", "stop"]
    data: dict[str, ktk.TimeSeries] | None
    current_window_data: (
        dict[Literal["left", "right"], KtkDataAndCycles] | None
    )
    cycles: dict[Literal["left", "right"], list]
    new_cycle_log: dict[Literal["left", "right"], int]
    new_cycle_send: dict[Literal["left", "right"], int]
    ts_full: dict[Literal["left", "right"], ktk.TimeSeries | None]


results: Results = {
    "run_mode": "stop",
    "data": None,
    "current_window_data": None,
    "cycles": {"left": [], "right": []},
    "new_cycle_log": {"left": 1, "right": 1},
    "new_cycle_send": {"left": 3, "right": 3},
    "ts_full": {"left": None, "right": None},
}


# %% Public functions
def biofeedback_stop(arg: Arg) -> None:
    """
    Clear all data.

    Stop the module optitrack and clear the ot data.
    Display the full kinematics and push pattern graphics
    (by default is commented)
    """
    # try:
    #     # Display full kinematics and push pattern graphics at script
    #     # termination.
    #     # Reconstructs the global session dataset (limit_duration=0)
    #     # and injects the complete accumulated cycle history for both sides.

    #     _plot_sides_kinematics(results)

    #     _plot_side_push_pattern(arg, results, "left")
    #     _plot_side_push_pattern(arg, results, "right")

    # except Exception as e:
    #     print(f"Display full kinematics and push pattern : {e}")

    # ktk.save("results", results)

    _init_results()

    ot.stop()
    ot.clear()

    print("Biofeedback closed")

    plt.show()


def biofeedback_update(arg: Arg) -> None:
    """
    Execute a real-time update iteration for the biofeedback.

    Handles the live streaming state machine: initializes the
    OptiTrack acquisition on startup, fetches new tracking frames, extracts
    and filters side-specific kinematics, detects propulsion cycles,
    logs progress, and streams computed metrics to Godot.
    """
    if results["run_mode"] == "stop":
        ot.start()

        time.sleep(1)

        print("Biofeedback started")

        results["run_mode"] = "start"

    elif results["run_mode"] == "start":
        start = time.time()

        try:
            results["data"] = ot.fetch()
        except Exception as e:
            print(e)

        if not results["data"]:
            return

        end = time.time()

        results["current_window_data"] = _analyze_current_window(
            results["data"],
            arg,
            results["cycles"],
            limit_duration=5,
        )

        if results["current_window_data"] is None:
            return

        results["cycles"] = _update_data_cycles(
            results["cycles"],
            results["current_window_data"],
        )
        results["ts_full"] = _update_ts_full(
            results["ts_full"],
            results["current_window_data"],
        )

        results["new_cycle_send"] = _send_data_godot(
            results["new_cycle_send"],
            results["cycles"],
        )

        results["new_cycle_log"] = _print_log(
            results["new_cycle_log"],
            results["cycles"],
            results["current_window_data"],
            end,
            start,
        )


# %% Private functions
def _analyze_current_window(
    data: dict[str, ktk.TimeSeries],
    arg: Arg,
    prev_data_cycles: dict[Literal["left", "right"], list],
    limit_duration: float = 0,
) -> dict[Literal["left", "right"], KtkDataAndCycles]:
    """
    Extract kinematics and validated propulsion cycles.

    Processing is limited to the current real-time data window.
    """

    def initialize_data_side() -> list[DataSide]:
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
        data_side: list[DataSide] = [
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

    def get_windowed_data(
        data: dict[str, ktk.TimeSeries],
        limit_duration: float,
    ) -> dict[str, ktk.TimeSeries]:
        """
        Slice the latest N seconds of the time series.

        This windowing approach is used to optimize real-time processing.
        """
        data_windowed = {}

        if limit_duration == 0:
            return data

        # Iterate through rigid bodies :
        # simulator frame (102),
        # left forearm (201),
        # right forearm (202)
        for key in ["102", "201", "202"]:
            t_end = data[key].time[-1]
            t_start = max(data[key].time[0], t_end - limit_duration)

            data_windowed[key] = data[key].get_ts_between_times(t_start, t_end)

        return data_windowed

    def compute_local_kinematics(
        data_windowed: dict[str, ktk.TimeSeries],
        data_side: list[DataSide],
        n: int,
    ) -> tuple[ktk.TimeSeries, Literal["left", "right"]]:
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
        # signals onto the simulator frame's timeline
        t_min = max(ts.time[0], data_windowed["102"].time[0])
        t_max = min(ts.time[-1], data_windowed["102"].time[-1])

        ts_data = data_windowed["102"].get_ts_between_times(t_min, t_max)
        ts = ts.get_ts_between_times(t_min, t_max)

        ts = ts.resample(ts_data.time)

        # Transform Meta2 coordinates from the global tracking system to the
        # simulator's local coordinate system
        ts.data[f"Meta2{side}"] = ktk.geometry.get_local_coordinates(
            global_coordinates=ts.data[f"Meta2{side}"],
            reference_frames=ts_data.data["102"],
        )

        # Set sample rate constant
        dt = np.median(np.diff(ts.time))
        time_uniform = np.arange(ts.time[0], ts.time[-1], dt)
        ts = ts.resample(time_uniform)

        # Filter butterworth order 4 with cut frequency of 6Hz
        ts = ktk.filters.butter(ts, fc=6, order=4)

        # Add velocity and acceleration timeseries
        ts_df = ktk.filters.deriv(ts, n=1)
        ts_dff = ktk.filters.deriv(ts, n=2)

        ts = ts.get_ts_before_index(len(ts.time) - 1)
        ts.data[f"Meta2{side}_df"] = ts_df.data[f"Meta2{side}"][:, 0]
        ts = ts.get_ts_before_index(len(ts.time) - 1)
        ts.data[f"Meta2{side}_dff"] = ts_dff.data[f"Meta2{side}"][:, 0]

        return ts, side

    def detect_push_cycles(
        ts: ktk.TimeSeries,
        side: Literal["left", "right"],
        prev_data_cycles: list[PushCycle],
    ) -> list[PushCycle]:
        """
        Detect voluntary propulsion cycles from position time series.

        Cycles are identified based on specific kinematic and temporal criteria
        """

        def classify_push_pattern(
            ts: ktk.TimeSeries,
            cycles: PushCycle,
            side: Literal["left", "right"],
            arg: Arg,
        ) -> tuple[
            list[Areas],
            float,
            float,
            Literal[
                "Pumping (PM)",
                "Semi-Circular (SC)",
                "Single-Loop (SLOP)",
                "Double-Loop (DLOP)",
                "",
            ],
        ]:

            def compute_geometric_zones(
                recovery_phase: np.ndarray,
                push_phase: np.ndarray,
            ) -> list[Areas]:
                """
                Compute signed areas between recovery and push trajectories.

                This is achieved by segmenting the signal at curve crossings to
                determine the geometric zones.
                """
                recovery = np.array(recovery_phase)
                push = np.array(push_phase)

                # Sort push curve by anteroposterior for interpolation
                push_sorted = push[np.argsort(push[:, 0])]

                y_push_interpolated = np.interp(
                    recovery[:, 0],
                    push_sorted[:, 0],
                    push_sorted[:, 1],
                )

                # Mask to detect if the hand in the recovery crosses the
                # push line
                above = recovery[:, 1] >= y_push_interpolated

                # Ensure last segment is closed
                extended_mask = np.append(above, not above[-1])

                areas: list[Areas] = []
                start_idx = 0
                current_sign = above[0]

                for i in range(1, len(extended_mask)):
                    if extended_mask[i] != current_sign:
                        current_recovery_phase = recovery[start_idx : i + 1]
                        current_push_phase = np.column_stack(
                            (
                                recovery[start_idx : i + 1, 0],
                                y_push_interpolated[start_idx : i + 1],
                            ),
                        )

                        # Calculating geometric area using the trapezoidal rule
                        dx = (
                            current_recovery_phase[1:, 0]
                            - current_recovery_phase[:-1, 0]
                        )
                        mean_recovery_y = (
                            current_recovery_phase[1:, 1]
                            + current_recovery_phase[:-1, 1]
                        ) / 2.0
                        mean_push_y = (
                            current_push_phase[1:, 1]
                            + current_push_phase[:-1, 1]
                        ) / 2.0

                        area = np.sum((mean_recovery_y - mean_push_y) * dx)

                        areas.append(
                            {
                                "sign": (
                                    "positive" if current_sign else "negative"
                                ),
                                "area": abs(area),
                                "recovery_phase": current_recovery_phase,
                                "push_phase": current_push_phase,
                            },
                        )

                        start_idx = i
                        current_sign = extended_mask[i]

                return areas

            def compute_A1(
                deviation_max: float,
                recovery_phase: np.ndarray,
                push_phase: np.ndarray,
                side: Literal["left", "right"],
                arg: Arg,
            ) -> float:
                """
                Compute the normalized recovery-phase deviation index.

                The index is calculated relative to the push-phase radius.
                A1 compares the hand deviation during recovery to a reference
                threshold (d_max). Values > 1 indicate large deviation.
                """
                if side == "left":
                    coordinates_side_wheel_center = arg[
                        "coordinates_left_wheel_center"
                    ]

                else:
                    coordinates_side_wheel_center = arg[
                        "coordinates_right_wheel_center"
                    ]

                push_distances = np.sqrt(
                    (push_phase[:, 0] - coordinates_side_wheel_center[0]) ** 2
                    + (push_phase[:, 1] - coordinates_side_wheel_center[1])
                    ** 2,
                )
                distance_hand_wheel_center = np.sqrt(
                    (recovery_phase[:, 0] - coordinates_side_wheel_center[0])
                    ** 2
                    + (recovery_phase[:, 1] - coordinates_side_wheel_center[1])
                    ** 2,
                )

                min_push_distance = np.min(push_distances)
                deviation = np.sort(
                    np.abs(distance_hand_wheel_center - min_push_distance),
                )

                # Median of the upper quartile (75–100%)
                mean_distance_deviation = np.median(
                    deviation[int(len(deviation) * 0.75) :],
                )

                A1 = mean_distance_deviation / deviation_max

                return A1

            def compute_A2(zones_detectees: list[Areas]) -> float:
                """
                Symmetry index based on signed areas.

                A2 = (positive areas - negative areas) / total areas
                Range: [-1, 1]
                    +1 --> positive dominance
                    -1 --> negative dominance
                """
                Ap = 0.0
                An = 0.0

                for zone in zones_detectees:
                    if zone["sign"] == "positive":
                        Ap += zone["area"]
                    if zone["sign"] == "negative":
                        An += zone["area"]

                A2 = (Ap - An) / (Ap + An)

                return A2

            def classify_stroke_pattern(
                A1: float,
                A2: float,
            ) -> Literal[
                "Pumping (PM)",
                "Semi-Circular (SC)",
                "Single-Loop (SLOP)",
                "Double-Loop (DLOP)",
                "",
            ]:
                """Classify propulsion pattern from A1 and A2."""
                if A1 < 1:
                    return "Pumping (PM)"
                if A2 <= -PATTERN_A2_SC_THRESHOLD:
                    return "Semi-Circular (SC)"
                if A2 >= PATTERN_A2_SLOP_THRESHOLD:
                    return "Single-Loop (SLOP)"
                if (
                    A2 < PATTERN_A2_SLOP_THRESHOLD
                    and A2 > -PATTERN_A2_SC_THRESHOLD
                ):
                    return "Double-Loop (DLOP)"
                return ""

            # Split the time-series cycle into recovery and push phases
            recovery_phase = ts.get_ts_between_times(
                cycles["recovery"]["time"],
                cycles["end_push"]["time"],
            ).data[f"Meta2{side}"][:, 0:2]
            push_phase = ts.get_ts_between_times(
                cycles["in_push"]["time"],
                cycles["recovery"]["time"],
            ).data[f"Meta2{side}"][:, 0:2]

            # Compute A1 and A2 criteria
            areas = compute_geometric_zones(recovery_phase, push_phase)

            A1 = compute_A1(
                MAX_DEVIATION_THRESHOLD, recovery_phase, push_phase, side, arg
            )
            A2 = compute_A2(areas)

            # Classify stroke pattern based on A1 and A2 criteria into one
            # of the four common push patterns (PM, SC, SLOP, DLOP)
            label_push_pattern = classify_stroke_pattern(A1, A2)

            return areas, A1, A2, label_push_pattern

        def filter_cycles_by_amplitude(
            cycles: list[PushCycle], prev_data_cycles: list[PushCycle]
        ) -> list[PushCycle]:
            """
            Validate propulsion cycles based on kinematic amplitude.

            Applies a minimum amplitude threshold based on the median range
            of the last three historical cycles and filters out low-velocity
            noise.
            """
            cycles_filtered_1 = []

            for cycle in cycles:
                if len(prev_data_cycles) <= 3:
                    if cycle["velocity_max"] > MIN_CYCLE_MAX_VELOCITY:
                        cycles_filtered_1.append(cycle)
                    continue

                prev_ranges = np.array(
                    [
                        prev_data_cycles[-1]["range"],
                        prev_data_cycles[-2]["range"],
                        prev_data_cycles[-3]["range"],
                    ],
                )

                if (
                    cycle["range"] >= 0.3 * np.median(prev_ranges)
                    and cycle["velocity_max"] > MIN_CYCLE_MAX_VELOCITY
                ):
                    cycles_filtered_1.append(cycle)

            return cycles_filtered_1

        def filter_cycles_by_mean_crossing(
            cycles: list[PushCycle],
            prev_data_cycles: list[PushCycle],
            ts: ktk.TimeSeries,
            pos_x: np.ndarray,
            side: Literal["left", "right"],
        ) -> tuple[list[PushCycle], ktk.TimeSeries]:
            """
            Validate propulsion cycles based on mean position crossings.

            Filters cycles to ensure the anterior-posterior signal crosses the
            mean position (computed over the last 3 seconds) both upward and
            downward, then tags validated boundaries within the time series.
            """
            cycles_filtered_2 = []
            signal = pos_x

            for r in range(len(cycles)):
                if len(prev_data_cycles) < 3:
                    cycles_filtered_2.append(cycles[r])
                    continue

                duration_ts = ts.time[-1] - ts.time[0]

                if duration_ts >= 3:
                    mean_value = (
                        ts.get_ts_after_time(ts.time[-1] - 3)
                        .data[f"Meta2{side}"][:, 0]
                        .mean()
                    )
                else:
                    mean_value = ts.data[f"Meta2{side}"][:, 0].mean()

                t0 = ts.get_index_at_time(cycles[r]["in_push"]["time"])
                t2 = ts.get_index_at_time(cycles[r]["end_push"]["time"])

                segment = signal[t0 : t2 + 1]

                crossed_up = False
                crossed_down = False

                for i in range(len(segment) - 1):
                    if (
                        segment[i] < mean_value
                        and segment[i + 1] >= mean_value
                    ):
                        crossed_up = True
                    if (
                        segment[i] > mean_value
                        and segment[i + 1] <= mean_value
                    ):
                        crossed_down = True

                    if crossed_up and crossed_down:
                        break

                if crossed_up and crossed_down:
                    cycles_filtered_2.append(cycles[r])

            for cycle in cycles_filtered_2:
                ts = ts.add_event(cycle["in_push"]["time"], "in_push")
                ts = ts.add_event(cycle["end_push"]["time"], "end_push")

            return cycles_filtered_2, ts

        pos_x = ts.data[f"Meta2{side}"][:, 0]
        vel_x = ts.data[f"Meta2{side}_df"]

        # Cycle detection upon velocity zero-crossing with temporal criterion
        # (duration > MIN_CYCLE_DURATION s)
        if np.all(vel_x >= 0) or np.all(vel_x <= 0):
            return []

        try:
            ts_events = ktk.cycles.detect_cycles(
                ts,
                f"Meta2{side}_df",
                thresholds=(0.0, 0.0),
                event_names=("push", "recovery"),
            )
        except Exception as e:
            print(e)
            return []

        events = [e for e in ts_events.events if e.name != "_"]

        if len(events) < 3:
            return []

        cycles: list[PushCycle] = []

        for i in range(len(events) - 2):
            if (
                events[i].name == "push"
                and events[i + 1].name == "recovery"
                and events[i + 2].name == "push"
            ):
                index_t = ts.get_index_at_time(events[i].time)
                index_t1 = ts.get_index_at_time(events[i + 1].time)
                index_t2 = ts.get_index_at_time(events[i + 2].time)

                t = events[i].time
                t1 = events[i + 1].time
                t2 = events[i + 2].time

                delta_t = events[i + 2].time - events[i].time

                if delta_t > MIN_CYCLE_DURATION:
                    ts_cycle = ts.get_ts_between_times(t, t2)
                    ts_cycle.time = np.linspace(0, 100, len(ts_cycle.time))

                    ts_normalised = ts_cycle.resample(np.linspace(0, 100, 101))

                    normalised_push_pattern = ts_normalised.data[
                        f"Meta2{side}"
                    ][:, 0:3]

                    cycles.append(
                        {
                            "in_push": {
                                "time": float(t),
                                "value": float(pos_x[index_t]),
                            },
                            "recovery": {
                                "time": float(t1),
                                "value": float(pos_x[index_t1]),
                            },
                            "end_push": {
                                "time": float(t2),
                                "value": float(pos_x[index_t2]),
                            },
                            "range": float(pos_x[index_t1] - pos_x[index_t]),
                            "velocity_max": float(
                                np.nanmax(vel_x[index_t:index_t2]),
                            ),
                            "push_frequency": float(1 / delta_t),
                            "normalised_push_pattern": normalised_push_pattern,
                            "areas": None,
                            "A1": None,
                            "A2": None,
                            "label_push_pattern": None,
                        },
                    )

        # Kinematic criterion #1: minimum amplitude based on the general
        # amplitude (median) of the last 3 cycles
        cycles = filter_cycles_by_amplitude(cycles, prev_data_cycles)

        # Kinematic criterion #2: condition to cross the mean
        # anterior-posterior position computed over the last 3 seconds
        cycles, ts = filter_cycles_by_mean_crossing(
            cycles, prev_data_cycles, ts, pos_x, side
        )

        # Classify each validated cycle into one of the four common
        # push patterns (PM, SC, SLOP and DLOP)
        cycles_classified = []

        for cycle in cycles:
            areas, A1, A2, label_push_pattern = classify_push_pattern(
                ts,
                cycle,
                side,
                arg,
            )

            cycle["areas"] = areas
            cycle["A1"] = float(A1)
            cycle["A2"] = float(A2)
            cycle["label_push_pattern"] = label_push_pattern
            cycles_classified.append(cycle)

        cycles = cycles_classified

        return cycles

    # Initialize the current window data
    current_window_data: dict[Literal["left", "right"], KtkDataAndCycles] = {
        "left": {"ts": None, "cycles": None},
        "right": {"ts": None, "cycles": None},
    }

    data_side = initialize_data_side()

    data_windowed = get_windowed_data(data, limit_duration)

    # Compute kinematics and cycles for left and right sides
    for i in range(2):
        ts, side = compute_local_kinematics(data_windowed, data_side, i)

        cycles = detect_push_cycles(ts, side, prev_data_cycles[side])

        current_window_data[side]["ts"] = ts
        current_window_data[side]["cycles"] = cycles

    return current_window_data


def _update_data_cycles(
    cycles: dict[Literal["left", "right"], list[PushCycle]],
    current_window_data: dict[Literal["left", "right"], KtkDataAndCycles],
) -> dict[Literal["left", "right"], list[PushCycle]]:
    """
    Update global cycle history upon cycle detection.

    Appends newly identified propulsion cycles to the continuous historical log
    """
    try:
        sides: tuple[Literal["left", "right"], Literal["left", "right"]] = (
            "left",
            "right",
        )
        for side in sides:
            # Skip if no cycles were detected for this side in the
            # current window
            current_cycles = current_window_data[side]["cycles"]
            if current_cycles is None or not current_cycles:
                continue

            last_cycle = current_cycles[-1]

            # If history cycles is empty for this side, safely append the
            # first cycle
            if len(cycles[side]) == 0:
                cycles[side].append(last_cycle)

            else:
                in_push_time = float(last_cycle["in_push"]["time"])
                end_push_time = float(cycles[side][-1]["end_push"]["time"])

                # Check if a new cycle started after the previous one ended
                if in_push_time > end_push_time:
                    cycles[side].append(last_cycle)

    except Exception as e:
        print(f"_update_data_cycles : {e}")

    return cycles


def _update_ts_full(
    ts_full: dict[Literal["left", "right"], ktk.TimeSeries | None],
    current_window_data: dict[Literal["left", "right"], KtkDataAndCycles],
) -> dict[Literal["left", "right"], ktk.TimeSeries | None]:
    """Update the global timeserie of Meta2 with newly detected timeserie."""
    try:
        sides: tuple[Literal["left", "right"], Literal["left", "right"]] = (
            "left",
            "right",
        )
        for side in sides:
            ts = current_window_data[side]["ts"]

            if ts is None:
                continue

            current_ts = ts_full[side]

            # If history timeserie is empty for this side, safely get the
            # first timeserie
            if current_ts is None:
                ts_full[side] = ts
            else:
                # Cut the timeserie to merge after the previous one ended
                ts_to_merge = ts.get_ts_after_time(
                    current_ts.time[-1], inclusive=False
                )

                current_ts.time = np.concatenate(
                    [current_ts.time, ts_to_merge.time]
                )

                for key in current_ts.data:
                    current_ts.data[key] = np.concatenate(
                        [current_ts.data[key], ts_to_merge.data[key]],
                        axis=0,
                    )
                ts_full[side] = current_ts

    except Exception as e:
        print(f"_update_ts_full : {e}")

    return ts_full


def _send_data_godot(
    new_cycle_send: dict[Literal["left", "right"], int],
    cycles: dict[Literal["left", "right"], list[PushCycle]],
) -> dict[Literal["left", "right"], int]:
    """
    Send computed kinematics metrics to Godot upon cycle detection.

    Computes median push frequency and extracts normalized geometry from the
    last three cycles to stream via python_bridge.
    """
    from python_bridge import send_data

    sides: tuple[Literal["left", "right"], Literal["left", "right"]] = (
        "left",
        "right",
    )

    for side in sides:
        if (
            len(cycles[side]) >= 3
            and len(cycles[side]) == new_cycle_send[side]
        ):
            mean_push_frequency = float(
                np.median(
                    [
                        cycles[side][-1]["push_frequency"],
                        cycles[side][-2]["push_frequency"],
                        cycles[side][-3]["push_frequency"],
                    ]
                )
            )

            last_push_pattern_1 = cycles[side][-1][
                "normalised_push_pattern"
            ].tolist()
            last_push_pattern_2 = cycles[side][-2][
                "normalised_push_pattern"
            ].tolist()
            last_push_pattern_3 = cycles[side][-3][
                "normalised_push_pattern"
            ].tolist()

            label_push_pattern = str(cycles[side][-1]["label_push_pattern"])

            data = {
                side: {
                    "mean_push_frequency": mean_push_frequency,
                    "last_push_pattern_1": last_push_pattern_1,
                    "last_push_pattern_2": last_push_pattern_2,
                    "last_push_pattern_3": last_push_pattern_3,
                    "label_push_pattern": label_push_pattern,
                }
            }

            send_data("biofeedback_update", data)

            new_cycle_send[side] += 1

    return new_cycle_send


def _print_log(
    new_cycle_log: dict[Literal["left", "right"], int],
    cycles: dict[Literal["left", "right"], list[PushCycle]],
    current_window_data: dict[Literal["left", "right"], KtkDataAndCycles],
    end: float,
    start: float,
) -> dict[Literal["left", "right"], int]:
    """
    Display push data when a cycle is detected.

    (ex) side : push n°X |
    execution duration: X.XXXXXX |
    time windowed: X.XX |
    push frequency: X.XX |
    Push Pattern: last [X, Y, Z]
    """
    try:
        sides: tuple[Literal["left", "right"], Literal["left", "right"]] = (
            "left",
            "right",
        )
        for side in sides:
            ts = current_window_data[side]["ts"]

            if ts is None:
                continue

            if len(cycles[side]) == new_cycle_log[side]:
                push_frequency = cycles[side][-1]["push_frequency"]
                label_push_pattern = cycles[side][-1]["label_push_pattern"]

                duration_cycle_analized = ts.time[-1] - ts.time[0]

                print(
                    f"{f'{side}':<8} "
                    f" : Push n°{len(cycles[side]):<3} | "
                    f"Time execution: {end - start:<8.6f} s | "
                    "Time data windowed: "
                    f"{duration_cycle_analized:<4.2f} s | "
                    "Push frequency: "
                    f"{push_frequency:<4.2f} Pushes per second | "
                    f"Push pattern: {label_push_pattern}"
                )

                new_cycle_log[side] += 1

    except Exception as e:
        print(f"print_log : {e}")

    return new_cycle_log


def _plot_sides_kinematics(results: Results) -> None:
    """Plot Position for both side."""
    plt.figure()
    plt.suptitle("Bilateral kinematics")

    sides: tuple[Literal["left", "right"], Literal["left", "right"]] = (
        "left",
        "right",
    )
    for side in sides:
        ts_full = results["ts_full"][side]

        if ts_full is None:
            continue

        if side == "left":
            plt.subplot(2, 1, 1)
        else:
            plt.subplot(2, 1, 2)

        plt.title("Position")
        colors = [(1, 0, 0), (0.5, 0.25, 0.25)]

        for i, cycle in enumerate(results["cycles"][side]):
            start = cycle["in_push"]["time"]
            end = cycle["end_push"]["time"]
            color = colors[i % 2]

            plt.axvspan(start, end, color=color, alpha=0.3)

        plt.plot(
            ts_full.time,
            ts_full.data[f"Meta2{side}"][:, 0],
            label=f"Meta2{side}",
        )
        plt.xlabel("Time (s)")
        plt.legend()

        plt.tight_layout()


def _plot_side_push_pattern(
    arg: Arg,
    results: Results,
    side: Literal["left", "right"],
) -> None:
    """Plot push pattern for a single side."""
    cycles = results["cycles"][side]
    num_cycles = len(cycles)

    if num_cycles == 0:
        print(f"No cycles detected to plot for {side} side.")
        return

    n_cols = 6
    n_rows = 2
    max_cycles_per_page = n_cols * n_rows

    total_pages = int(np.ceil(num_cycles / max_cycles_per_page))

    for page in range(1, total_pages + 1):
        start_idx = (page - 1) * max_cycles_per_page
        end_idx = min(start_idx + max_cycles_per_page, num_cycles)
        page_cycles = cycles[start_idx:end_idx]

        fig = plt.figure()

        plt.suptitle(
            f"\
                push pattern {side} side | Page {page}/{total_pages}\
                | ({num_cycles} cycles total)",
            fontsize=14,
            weight="bold",
            y=0.98,
        )

        for i, cycle in enumerate(page_cycles, start=1):
            ax = plt.subplot(n_rows, n_cols, i)

            # Draw positive and negative areas
            zones = cycle["areas"]
            for zone in zones:
                _points = np.vstack(
                    (zone["recovery_phase"], zone["push_phase"][::-1]),
                )
                _facecolor = "green" if zone["sign"] == "negative" else "red"
                _label = (
                    "negative area"
                    if zone["sign"] == "negative"
                    else "positive area"
                )

                poly_param = MplPolygon(
                    _points,
                    closed=True,
                    fill=True,
                    facecolor=_facecolor,
                    alpha=0.4,
                    label=_label,
                )
                ax.add_patch(poly_param)

            # Split the time-series cycle into recovery and push phases

            ts_full = results["ts_full"][side]

            if ts_full is None:
                continue

            recovery_phase = ts_full.get_ts_between_times(
                cycle["recovery"]["time"],
                cycle["end_push"]["time"],
            ).data[f"Meta2{side}"][:, 0:2]
            push_phase = ts_full.get_ts_between_times(
                cycle["in_push"]["time"],
                cycle["recovery"]["time"],
            ).data[f"Meta2{side}"][:, 0:2]

            # Draw the push phase
            ax.plot(
                push_phase[0, 0],
                push_phase[0, 1],
                color="black",
                marker="o",
                markersize=4,
                linewidth=2,
                zorder=4,
                label="start push phase",
            )
            ax.plot(
                push_phase[:, 0],
                push_phase[:, 1],
                color="black",
                linewidth=1,
                zorder=4,
                label="push phase",
            )

            # # Draw the recovery phase
            ax.plot(
                recovery_phase[:, 0],
                recovery_phase[:, 1],
                color="black",
                linewidth=1,
                zorder=4,
                label="revovery phase",
                linestyle="--",
            )

            # Draw the wheel
            if side == "left":
                coordinates_side_wheel_center = arg[
                    "coordinates_left_wheel_center"
                ]
            if side == "right":
                coordinates_side_wheel_center = arg[
                    "coordinates_right_wheel_center"
                ]

            circle = plt.Circle(
                (
                    coordinates_side_wheel_center[0],
                    coordinates_side_wheel_center[1],
                ),
                arg["wheel_diameter"] / 2,
                fill=False,
                linestyle="dotted",
                label="wheel",
            )
            ax.add_patch(circle)

            ax.set_xlim(-0.5, 0.3)
            ax.set_ylim(0, 1.15)
            ax.set_aspect("equal")
            global_cycle_number = start_idx + i
            A1 = cycle["A1"]
            A2 = cycle["A2"]
            ax.set_title(
                f"\
                    Push n°{global_cycle_number} \n \
                    A1 : {A1:.2f}   ¦   A2 : {A2:.2f} \n \
                    {cycle['label_push_pattern']}",
            )

        # Create a global legend for all subplots
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(
            dict(zip(labels, handles, strict=True)).values(),
            dict(zip(labels, handles, strict=True)).keys(),
        )

        # Adjust subplot spacing
        fig.subplots_adjust(top=0.9, hspace=0.4, wspace=0.3)


def _init_results() -> None:

    results["run_mode"] = "stop"
    results["data"] = None
    results["current_window_data"] = None
    results["cycles"] = {"left": [], "right": []}
    results["new_cycle_log"] = {"left": 1, "right": 1}
    results["new_cycle_send"] = {"left": 3, "right": 3}
    results["ts_full"] = {"left": None, "right": None}


# %% Main
if __name__ == "__main__":
    arg: Arg = {
        "coordinates_left_wheel_center": [
            -0.504,
            0.295,
            -0.779,
        ],
        "coordinates_right_wheel_center": [
            -0.500,
            0.296,
            -0.204,
        ],
        "coordinates_left_hand": [0.081, -0.029, 0.082],
        "coordinates_right_hand": [0.003, -0.145, 0.010],
        "wheel_diameter": 0.54,
    }

    try:
        while True:
            biofeedback_update(arg)
    except KeyboardInterrupt:
        print("Biofeedback closed")
        biofeedback_stop(arg)

    # try:
    #     data = ktk.load("maria")
    #     biofeedback_update(arg)
    #     # biofeedback_stop(arg)
    # except Exception as e:
    #     print(e)
