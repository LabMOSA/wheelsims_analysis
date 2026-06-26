import kineticstoolkit as ktk
import numpy as np
import matplotlib.pyplot as plt
import time
import optitrack as ot
from matplotlib.patches import Rectangle, Polygon as MplPolygon

results = {
    "run_mode": "stop",
    "data": None,
    "current_window_data": None,
    "cycles": {"left": [], "right": []},
    "new_cycle_log": {"left": 1, "right": 1},
    "new_cycle_send": {"left": 3, "right": 3},
    "ts_full": {"left": None, "right": None},
}


def biofeedback_stop(arg):
    """
    Clear all data.
    Stop the module optitrack and clear the ot data.
    Display the full kinematics and push pattern graphics (by default is commented)
    """

    try:

        # Display full kinematics and push pattern graphics at script termination.
        # Reconstructs the global session dataset (limit_duration=0) and injects
        # the complete accumulated cycle history for both sides.

        plot_sides_kinematics(results)

        plot_side_push_pattern(arg, results, "left")
        plot_side_push_pattern(arg, results, "right")

    except Exception as e:
        print(f"Display full kinematics and push pattern : {e}")

    # ktk.save("results", results)

    results.clear()
    results.update(init_results())

    ot.stop()
    ot.clear()

    print("Biofeedback closed")

    plt.show()


def biofeedback_update(arg):
    """
    Execute a real-time update iteration for the biofeedback.

    Handles the live streaming state machine: initializes the OptiTrack acquisition
    on startup, fetches new tracking frames, extracts and filters side-specific
    kinematics, detects propulsion cycles, logs progress, and streams computed
    metrics to Godot.
    """

    def update_data_cycles(cycles, current_window_data):
        """
        Updates the global cycle history with newly detected propulsion cycles.
        """

        try:
            for side in ["left", "right"]:

                # Skip if no cycles were detected for this side in the current window
                if not current_window_data[side]["cycles"]:
                    continue

                last_cycle = current_window_data[side]["cycles"][-1]

                # If history cycles is empty for this side, safely append the first cycle
                if len(cycles[side]) == 0:
                    cycles[side].append(last_cycle)

                else:
                    in_push_time = float(last_cycle["in_push"]["time"])
                    end_push_time = float(cycles[side][-1]["end_push"]["time"])

                    # Check if a new cycle started after the previous one ended
                    if in_push_time > end_push_time:
                        cycles[side].append(last_cycle)

        except Exception as e:
            print(f"update_data_cycles : {e}")
        return cycles

    def update_ts_full(ts_full, current_window_data):
        """
        Updates the global timeserie of Meta2 with newly detected timeserie.
        """

        try:
            for side in ["left", "right"]:

                ts = current_window_data[side]["ts"]

                # If history timeserie is empty for this side, safely get the first timeserie
                if ts_full[side] is None:
                    ts_full[side] = ts
                else:
                    # Cut the timeserie to merge after the previous one ended
                    ts_to_merge = ts.get_ts_after_time(
                        ts_full[side].time[-1], inclusive=False
                    )

                    ts_full[side].time = np.concatenate(
                        [ts_full[side].time, ts_to_merge.time]
                    )

                    for key in ts_full[side].data:
                        ts_full[side].data[key] = np.concatenate(
                            [ts_full[side].data[key], ts_to_merge.data[key]],
                            axis=0,
                        )

        except Exception as e:
            print(f"update_ts_full : {e}")
        return ts_full

    def send_data_godot(new_cycle_send, cycles):
        """
        Compute and send to Godot the median push frequency and the last 3 normalized push patterns whenever a new cycle is detected
        """

        from python_bridge import send_data

        for side in ["left", "right"]:

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

                label_push_pattern = str(
                    cycles[side][-1]["label_push_pattern"]
                )

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

    def print_log(new_cycle_log, cycles, current_window_data):
        """
        Display push data when a cycle is detected.
        (ex) side : push n°X | execution duration: X.XXXXXX | time windowed: X.XX | push frequency: X.XX | Push Pattern: last [X, Y, Z]
        """

        try:
            for side in ["left", "right"]:

                if len(cycles[side]) == new_cycle_log[side]:

                    push_frequency = cycles[side][-1]["push_frequency"]
                    label_push_pattern = cycles[side][-1]["label_push_pattern"]

                    duration_cycle_analized = (
                        current_window_data[side]["ts"].time[-1]
                        - current_window_data[side]["ts"].time[0]
                    )

                    print(
                        f"{f'{side}':<8} "
                        f" : Push n°{len(cycles[side]):<3} | "
                        f"Time execution: {end - start:<8.6f} s | "
                        f"Time data windowed: {duration_cycle_analized:<4.2f} s | "
                        f"Push frequency: {push_frequency:<4.2f} Pushes per second | "
                        f"Push pattern: {label_push_pattern}"
                    )

                    new_cycle_log[side] += 1

        except Exception as e:
            print(f"print_log : {e}")

        return new_cycle_log

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

        results["current_window_data"] = analyze_current_window(
            results["data"], arg, results["cycles"], limit_duration=5
        )
        results["cycles"] = update_data_cycles(
            results["cycles"], results["current_window_data"]
        )
        results["ts_full"] = update_ts_full(
            results["ts_full"], results["current_window_data"]
        )

        results["new_cycle_send"] = send_data_godot(
            results["new_cycle_send"], results["cycles"]
        )

        results["new_cycle_log"] = print_log(
            results["new_cycle_log"],
            results["cycles"],
            results["current_window_data"],
        )


def analyze_current_window(data, arg, prev_data_cycles, limit_duration=0):
    """
    Extracts kinematics and validated propulsion cycles from the current time window
    """

    def initialize_data_side():
        """
        Initializes and structures calibration coordinates for both sides.
        """

        # Get and convert coordinates to homogeneous arrays [X, Y, Z, 1.0]
        coordinates_left_wheel_center = np.array(
            [arg["coordinates_left_wheel_center"] + [1.0]]
        )
        coordinates_right_wheel_center = np.array(
            [arg["coordinates_right_wheel_center"] + [1.0]]
        )

        coordinates_left_hand = np.array(
            [arg["coordinates_left_hand"] + [1.0]]
        )
        coordinates_right_hand = np.array(
            [arg["coordinates_right_hand"] + [1.0]]
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

    def data_windowed(data, limit_duration):
        """
        Slices the lastest N seconds of the time series to optimize real-time processing
        """

        data_windowed = {}

        if limit_duration == 0:
            return data

        # Iterate through rigid bodies : simulator frame (102), left forearm (201) and right forearm (202)
        for key in ["102", "201", "202"]:

            t_end = data[key].time[-1]
            t_start = max(data[key].time[0], t_end - limit_duration)

            data_windowed[key] = data[key].get_ts_between_times(t_start, t_end)

        return data_windowed

    def compute_local_kinematics(data_windowed, data_side, n):
        """
        Transforms timeseries tracking data into filtered local kinematics for a single side.
        """

        # Extract side-specific configuration and streaming tracking ID
        id_streaming = data_side[n]["id_streaming"]
        side = data_side[n]["side"]

        # Estimate second metacarpal (Meta2) position using the forearm cluster reference frame
        ts = ktk.TimeSeries()
        ts.time = data_windowed[id_streaming].time

        ts.data[f"Meta2{side}"] = ktk.geometry.matmul(
            data_windowed[id_streaming].data[id_streaming],
            data_side[n]["local_meta2"],
        )

        # Find the common overlapping time window and resample the forearm signals onto the simulator frame's timeline
        t_min = max(ts.time[0], data_windowed["102"].time[0])
        t_max = min(ts.time[-1], data_windowed["102"].time[-1])

        ts_data = data_windowed["102"].get_ts_between_times(t_min, t_max)
        ts = ts.get_ts_between_times(t_min, t_max)

        ts = ts.resample(ts_data.time)

        # Transform Meta2 coordinates from the global tracking system to the simulator's local coordinate system
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

    def detect_push_cycles(ts, side, prev_data_cycles):
        """
        Detects voluntary propulsion cycles from position time series based on kinematic and temporal criteria
        """

        def classify_push_pattern(ts, cycles, side, arg):

            def compute_geometric_zones(recovery_phase, push_phase):
                """
                Compute signed areas between recovery and push trajectories by
                segmenting the signal at curve crossings.
                """
                recovery = np.array(recovery_phase)
                push = np.array(push_phase)

                # Sort push curve by anteroposterior for interpolation
                push_sorted = push[np.argsort(push[:, 0])]

                y_push_interpolated = np.interp(
                    recovery[:, 0], push_sorted[:, 0], push_sorted[:, 1]
                )

                # Mask to detect if the hand in the recovery crosses the push line
                above = recovery[:, 1] >= y_push_interpolated

                # Ensure last segment is closed
                extended_mask = np.append(above, not above[-1])

                areas = []
                start_idx = 0
                current_sign = above[0]

                for i in range(1, len(extended_mask)):

                    if extended_mask[i] != current_sign:

                        current_recovery_phase = recovery[start_idx : i + 1]
                        current_push_phase = np.column_stack(
                            (
                                recovery[start_idx : i + 1, 0],
                                y_push_interpolated[start_idx : i + 1],
                            )
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
                            }
                        )

                        start_idx = i
                        current_sign = extended_mask[i]

                return areas

            def compute_A1(
                deviation_max, recovery_phase, push_phase, side, arg
            ):
                """
                Normalized index of recovery-phase deviation relative to push-phase radius.

                A1 compares the hand deviation during recovery to a reference
                threshold (d_max). Values > 1 indicate large deviation.
                """

                push_distances = np.sqrt(
                    (
                        push_phase[:, 0]
                        - arg[f"coordinates_{side}_wheel_center"][0]
                    )
                    ** 2
                    + (
                        push_phase[:, 1]
                        - arg[f"coordinates_{side}_wheel_center"][1]
                    )
                    ** 2
                )
                distance_hand_wheel_center = np.sqrt(
                    (
                        recovery_phase[:, 0]
                        - arg[f"coordinates_{side}_wheel_center"][0]
                    )
                    ** 2
                    + (
                        recovery_phase[:, 1]
                        - arg[f"coordinates_{side}_wheel_center"][1]
                    )
                    ** 2
                )

                min_push_distance = np.min(push_distances)
                deviation = np.sort(
                    np.abs(distance_hand_wheel_center - min_push_distance)
                )

                # Median of the upper quartile (75–100%)
                mean_distance_deviation = np.median(
                    deviation[int(len(deviation) * 0.75) :]
                )

                A1 = mean_distance_deviation / deviation_max

                return A1

            def compute_A2(zones_detectees):
                """
                Symmetry index based on signed areas.

                A2 = (positive areas - negative areas) / total areas
                Range: [-1, 1]
                    +1 --> positive dominance
                    -1 --> negative dominance
                """

                Ap = 0
                An = 0

                for zone in zones_detectees:
                    if zone["sign"] == "positive":
                        Ap += zone["area"]
                    if zone["sign"] == "negative":
                        An += zone["area"]

                A2 = (Ap - An) / (Ap + An)

                return A2

            def classify_stroke_pattern(A1, A2):
                """
                Classify propulsion pattern from A1 and A2.
                """

                if A1 < 1:
                    return "Pumping (PM)"
                elif A2 <= -0.75:
                    return "Semi-Circular (SC)"
                elif A2 >= 0.75:
                    return "Single-Loop (SLOP)"
                elif A2 < 0.75 and A2 > -0.75:
                    return "Double-Loop (DLOP)"
                else:
                    return ""

            # Split the time-series cycle into recovery and push phases
            recovery_phase = ts.get_ts_between_times(
                cycles["recovery"]["time"], cycles["end_push"]["time"]
            ).data[f"Meta2{side}"][:, 0:2]
            push_phase = ts.get_ts_between_times(
                cycles["in_push"]["time"], cycles["recovery"]["time"]
            ).data[f"Meta2{side}"][:, 0:2]

            # Compute A1 and A2 criteria
            areas = compute_geometric_zones(recovery_phase, push_phase)

            A1 = compute_A1(0.1, recovery_phase, push_phase, side, arg)
            A2 = compute_A2(areas)

            # Classify stroke pattern based on A1 and A2 criteria into one of the four common push patterns (PM, SC, SLOP, DLOP)
            label_push_pattern = classify_stroke_pattern(A1, A2)

            return areas, A1, A2, label_push_pattern

        pos_x = ts.data[f"Meta2{side}"][:, 0]
        vel_x = ts.data[f"Meta2{side}_df"]

        # Cycle detection upon velocity zero-crossing with temporal criterion (duration > 0.4 s)
        if np.all(vel_x >= 0) or np.all(vel_x <= 0):
            return []

        try:
            ts_events = ktk.cycles.detect_cycles(
                ts,
                f"Meta2{side}_df",
                thresholds=(0.0, 0.0),
                event_names=["push", "recovery"],
            )
        except:
            return []

        events = [e for e in ts_events.events if e.name != "_"]

        if len(events) < 3:
            return []

        cycles = []

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

                if delta_t > 0.4:

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
                                np.nanmax(vel_x[index_t:index_t2])
                            ),
                            "push_frequency": float(1 / delta_t),
                            "normalised_push_pattern": normalised_push_pattern,
                        }
                    )

        # Kinematic criterion #1: minimum amplitude based on the general amplitude (median) of the last 3 cycles
        filtered_1 = []

        for cycle in cycles:
            if len(prev_data_cycles) <= 3:
                if cycle["velocity_max"] > 0.2:
                    filtered_1.append(cycle)
                continue

            prev_ranges = np.array(
                [
                    prev_data_cycles[-1]["range"],
                    prev_data_cycles[-2]["range"],
                    prev_data_cycles[-3]["range"],
                ]
            )

            if (
                cycle["range"] >= 0.3 * np.median(prev_ranges)
                and cycle["velocity_max"] > 0.2
            ):
                filtered_1.append(cycle)

        cycles = filtered_1

        # Kinematic criterion #2: condition to cross the mean anterior-posterior position computed over the last 3 seconds
        filtered_2 = []
        signal = pos_x

        for r in range(len(cycles)):
            if len(prev_data_cycles) < 3:
                filtered_2.append(cycles[r])
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
                if segment[i] < mean_value and segment[i + 1] >= mean_value:
                    crossed_up = True
                if segment[i] > mean_value and segment[i + 1] <= mean_value:
                    crossed_down = True

                if crossed_up and crossed_down:
                    break

            if crossed_up and crossed_down:
                filtered_2.append(cycles[r])

        for cycle in filtered_2:
            ts = ts.add_event(cycle["in_push"]["time"], "in_push")
            ts = ts.add_event(cycle["end_push"]["time"], "end_push")

        cycles = filtered_2

        # Classify each validated cycle into one of the four common push patterns (PM, SC, SLOP and DLOP)
        cycles_classified = []

        for cycle in cycles:

            areas, A1, A2, label_push_pattern = classify_push_pattern(
                ts, cycle, side, arg
            )

            cycle["areas"] = areas
            cycle["A1"] = float(A1)
            cycle["A2"] = float(A2)
            cycle["label_push_pattern"] = label_push_pattern
            cycles_classified.append(cycle)

        cycles = cycles_classified

        return cycles

    # Initialize the current window data
    current_window_data = {
        "left": {"ts": None, "cycles": None},
        "right": {"ts": None, "cycles": None},
    }

    data_side = initialize_data_side()

    data_windowed = data_windowed(data, limit_duration)

    # Compute kinematics and cycles for left and right sides
    for i in range(2):

        ts, side = compute_local_kinematics(data_windowed, data_side, i)

        cycles = detect_push_cycles(ts, side, prev_data_cycles[side])

        current_window_data[side]["ts"] = ts
        current_window_data[side]["cycles"] = cycles

    return current_window_data


def plot_sides_kinematics(results):
    """
    Plot Position for both side
    """
    plt.figure()
    plt.suptitle("Bilateral kinematics")

    for side in ["left", "right"]:
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
            results["ts_full"][side].time,
            results["ts_full"][side].data[f"Meta2{side}"][:, 0],
            label=f"Meta2{side}",
        )
        plt.xlabel("Time (s)")
        plt.legend()

        plt.tight_layout()


def plot_side_push_pattern(arg, results, side):
    """
    Plot push pattern for a single side
    """

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
            f"push pattern {side} side | Page {page}/{total_pages} | ({num_cycles} cycles total)",
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
                    (zone["recovery_phase"], zone["push_phase"][::-1])
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
            recovery_phase = (
                results["ts_full"][side]
                .get_ts_between_times(
                    cycle["recovery"]["time"], cycle["end_push"]["time"]
                )
                .data[f"Meta2{side}"][:, 0:2]
            )
            push_phase = (
                results["ts_full"][side]
                .get_ts_between_times(
                    cycle["in_push"]["time"], cycle["recovery"]["time"]
                )
                .data[f"Meta2{side}"][:, 0:2]
            )

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
            circle = plt.Circle(
                (
                    arg[f"coordinates_{side}_wheel_center"][0],
                    arg[f"coordinates_{side}_wheel_center"][1],
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
                f"Push n°{global_cycle_number} \n A1 : {A1:.2f}   ¦   A2 : {A2:.2f} \n {cycle['label_push_pattern']}"
            )

        # Create a global legend for all subplots
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(
            dict(zip(labels, handles)).values(),
            dict(zip(labels, handles)).keys(),
        )

        # Adjust subplot spacing
        fig.subplots_adjust(top=0.9, hspace=0.4, wspace=0.3)


def init_results():

    results = {
        "run_mode": "stop",
        "data": None,
        "current_window_data": None,
        "cycles": {"left": [], "right": []},
        "new_cycle_log": {"left": 1, "right": 1},
        "new_cycle_send": {"left": 3, "right": 3},
        "ts_full": {"left": None, "right": None},
    }

    return results


if __name__ == "__main__":

    arg = {
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
