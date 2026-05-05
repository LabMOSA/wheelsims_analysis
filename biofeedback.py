import kineticstoolkit as ktk
import numpy as np
import matplotlib.pyplot as plt


def biofeedback(data, arg):

    data_biofeedback = {
        "left": {
            "cycle_count": None,
            "mean_trajectory_meta2": [],
            "mean_push_frequency": None,
        },
        "right": {
            "cycle_count": None,
            "mean_trajectory_meta2": [],
            "mean_push_frequency": None,
        },
    }

    data_cycles = {
        "left": {
            "ts": None,
            "cycles": None,
        },
        "right": {
            "ts": None,
            "cycles": None,
        },
    }

    def initialize_data():

        coordinates_left_wheel_center = np.array([arg["coordinates_left_wheel_center"] + [1.0]])
        coordinates_right_wheel_center = np.array([arg["coordinates_right_wheel_center"] + [1.0]])

        coordinates_left_hand = np.array([arg["coordinates_left_hand"] + [1.0]])
        coordinates_right_hand = np.array([arg["coordinates_right_hand"] + [1.0]])

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

    def process_signals(data_side, n):

        id_streaming = data_side[n]["id_streaming"]
        side = data_side[n]["side"]

        ts = ktk.TimeSeries()
        ts.time = data[id_streaming].time

        ts.data[f"Meta2{side}"] = ktk.geometry.matmul(data[id_streaming].data[id_streaming], data_side[n]["local_meta2"])

        t_min = max(ts.time[0], data["102"].time[0])
        t_max = min(ts.time[-1], data["102"].time[-1])

        ts_data = data["102"].get_ts_between_times(t_min, t_max)
        ts = ts.get_ts_between_times(t_min, t_max)

        ts = ts.resample(ts_data.time)

        ts.data[f"Meta2{side}"] = ktk.geometry.get_local_coordinates(global_coordinates=ts.data[f"Meta2{side}"], reference_frames=ts_data.data["102"])

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

    def detect_push_cycles(ts, side):

        pos_x = ts.data[f"Meta2{side}"][:, 0]

        # Creation des cycles lorsque la direction change --> v = 0 avec critere temporel : durée cycle supérieur à 0.4 s        
        ts_events = ktk.cycles.detect_cycles(ts, f"Meta2{side}_df", thresholds=(0.0, 0.0), event_names=["push", "recovery"])        
        events = [e for e in ts_events.events if e.name != "_"]

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

                delta_t = events[i + 2].time - events[i].time

                if delta_t > 0.4:
                    cycles.append(
                        {
                            "in_push": {
                            "time": events[i].time,
                            "value": pos_x[index_t],
                            },
                            "recovery": {
                            "time": events[i + 1].time,
                            "value": pos_x[index_t1],
                            },
                            "end_push": {
                            "time": events[i + 2].time,
                            "value": pos_x[index_t2],
                            },
                            "range": pos_x[index_t1] - pos_x[index_t],
                            "push_frequency": 1 / delta_t,
                        }
                    )

        # Critère cinématique n°1 : amplitude minimale fonction de l'amplitude générale (médiane) des 3 derniers cycles
        filtered = []

        for cycle in cycles:
            if len(filtered) < 3:
                filtered.append(cycle)
                continue

            prev_ranges = np.array(
                [
                    filtered[-1]["range"],
                    filtered[-2]["range"],
                    filtered[-3]["range"],
                ]
            )

            if cycle["range"] >= 0.3 * np.median(prev_ranges):
                filtered.append(cycle)

        cycles = filtered

        # Critère cinématique n°2 : condition de traverser le point milieu entre la position la plus antérieure et la plus postérieure générale des 3 derniers cycles
        filtered = []
        signal = pos_x

        for r in range(len(cycles)):
            if r < 3:
                filtered.append(cycles[r])
                continue

            prev_values = [
                (cycles[r - 1]["recovery"]["value"]
                 + cycles[r - 1]["in_push"]["value"]) / 2,
                (cycles[r - 2]["recovery"]["value"]
                 + cycles[r - 2]["in_push"]["value"]) / 2,
                (cycles[r - 3]["recovery"]["value"]
                 + cycles[r - 3]["in_push"]["value"]) / 2,
            ]

            median_val = sorted(prev_values)[1]

            t0 = ts.get_index_at_time(cycles[r]["in_push"]["time"])
            t2 = ts.get_index_at_time(cycles[r]["end_push"]["time"])

            segment = signal[t0 : t2 + 1]

            crossed_up = False
            crossed_down = False

            for i in range(len(segment) - 1):
                if segment[i] < median_val and segment[i + 1] >= median_val:
                    crossed_up = True
                if segment[i] > median_val and segment[i + 1] <= median_val:
                    crossed_down = True

                if crossed_up and crossed_down:
                    break

            if crossed_up and crossed_down:
                filtered.append(cycles[r])

        cycles = filtered

        for cycle in cycles:
            ts = ts.add_event(cycle["in_push"]["time"], "in_push")
            ts = ts.add_event(cycle["end_push"]["time"], "end_push")

        return cycles

    def caculate_mean_three_last_push_frequency(cycles):
        # list push frequency and mean
        push_frequency = []
        for i in range(3):
            push_frequency.append(cycles[-i-1]["push_frequency"])
            # print(str(i), " ", str(cycles[i]["push_frequency"]))
        mean_push_frequency = np.mean(push_frequency)

        return mean_push_frequency



    data_side = initialize_data()

    for i in range(2):
        ts, side = process_signals(data_side, i)
        cycles = detect_push_cycles(ts, side)

        data_cycles[side]["ts"] = ts
        data_cycles[side]["cycles"] = cycles
        
        mean_push_frequency = caculate_mean_three_last_push_frequency(cycles)
        data_biofeedback[side]["mean_push_frequency"] = float(mean_push_frequency)
    
        data_biofeedback[side]["cycle_count"] = len(cycles)

    return data_biofeedback, data_cycles



def plot_sides_kinematics(data_cycles):
    
    # Plot Position and velocity
    plt.figure()
    plt.suptitle("Bilateral kinematics")

    for side in ["left", "right"]:
        if side == "left":
            plt.subplot(2, 1, 1)
        else:
            plt.subplot(2, 1, 2)
            
        plt.title("Position")
        colors = [(1, 0, 0), (0.5, 0.25, 0.25)]

        for i, cycle in enumerate(data_cycles[side]["cycles"]):
            start = cycle["in_push"]["time"]
            end = cycle["end_push"]["time"]
            color = colors[i % 2]
        
            plt.axvspan(start, end, color=color, alpha=0.3)
        
        plt.plot(data_cycles[side]["ts"].time, data_cycles[side]["ts"].data[f"Meta2{side}"][:, 0], label = f"Meta2{side}")
        plt.xlabel("Time (s)")
        plt.legend()
        
        plt.tight_layout()
        plt.show()

def plot_side_kinematics(data_cycles, side):
    
    # Plot Position and velocity
    plt.figure()
    plt.suptitle(f"Kinematics {side} side")
    plt.subplot(3, 1, 1)
    plt.title("Position")
    colors = [(1, 0, 0), (0.5, 0.25, 0.25)]
    
    for i, cycle in enumerate(data_cycles[side]["cycles"]):
        start = cycle["in_push"]["time"]
        end = cycle["end_push"]["time"]
        color = colors[i % 2]
    
        plt.axvspan(start, end, color=color, alpha=0.3)
    
    plt.plot(data_cycles[side]["ts"].time, data_cycles[side]["ts"].data[f"Meta2{side}"][:, 0], label = f"Meta2{side}")
    plt.xlabel("Time (s)")
    plt.legend()
    plt.subplot(3, 1, 2)
    plt.title("Velocity")
    data_cycles[side]["ts"].plot(f"Meta2{side}_df")
    plt.subplot(3, 1, 3)
    plt.title("Acceleration")
    data_cycles[side]["ts"].plot(f"Meta2{side}_dff")
    
    plt.tight_layout()
    plt.show()

def plot_side_push_pattern(arg, data_cycles, side):
    # Plot single pattern push
    i = 1

    plt.figure(figsize=(8, 8))
    
    plt.suptitle(f"push pattern {side} side")
    
    for cycle in data_cycles[side]["cycles"]:
        ax = plt.subplot(6, 7, i)
    
        circle = plt.Circle(
            (
                arg[f"coordinates_{side}_wheel_center"][0],
                arg[f"coordinates_{side}_wheel_center"][1],
            ),
            arg["wheel_diameter"] / 2,
            fill=False,
            linestyle="--",
        )
        ax.add_patch(circle)
    
        ts = data_cycles[side]["ts"].get_ts_between_times(cycle["in_push"]["time"], cycle["end_push"]["time"])
        ax.plot(ts.data[f"Meta2{side}"][:, 0], ts.data[f"Meta2{side}"][:, 1])
    
        ax.set_xlim(-0.8, 0.2)
        ax.set_ylim(0, 1.15)
    
        ax.set_aspect("equal")
    
        i += 1

    plt.tight_layout()
    plt.show()



# data = ktk.load("ts_all_.ktk.zip")
# arg = {
#        "coordinates_left_wheel_center": [-0.214146345853806-0.29, 0.295335084199905, -0.779305219650269],
#        "coordinates_right_wheel_center": [-0.210078418254852-0.29, 0.296095550060272, -0.204232186079025],
#        "coordinates_left_hand": [0.0819698944687843, -0.029034435749054, 0.082910031080246],
#        "coordinates_right_hand": [0.00322970747947693, -0.145348995923996, 0.0109105035662651],
#        "wheel_diameter": 0.54,
#        }


# data_biofeedback, data_cycles = biofeedback(data, arg)


# plt.close()

# plot_sides_kinematics(data_cycles)

# plot_side_kinematics(data_cycles, "left")
# plot_side_kinematics(data_cycles, "right")

# plot_side_push_pattern(arg, data_cycles, "left")
# plot_side_push_pattern(arg, data_cycles, "right")


def biofeedback_godot(data, arg):
    
    data_biofeedback, data_cycles = biofeedback(data, arg)
    
    
    # plt.close()
    
    # plot_sides_kinematics(data_cycles)
    
    # plot_side_kinematics(data_cycles, "left")
    # plot_side_kinematics(data_cycles, "right")
    
    # plot_side_push_pattern(arg, data_cycles, "left")
    # plot_side_push_pattern(arg, data_cycles, "right")
    
    return data_biofeedback
