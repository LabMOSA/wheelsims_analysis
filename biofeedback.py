def push_frequency(data, arg):

    import kineticstoolkit as ktk
    import numpy as np
    import matplotlib.pyplot as plt

    coordinates_left_wheel_center = np.array(
        [arg["coordinates_left_wheel_center"] + [1.0]]
    )
    coordinates_right_wheel_center = np.array(
        [arg["coordinates_right_wheel_center"] + [1.0]]
    )

    coordinates_left_hand = np.array([arg["coordinates_left_hand"] + [1.0]])
    coordinates_right_hand = np.array([arg["coordinates_right_hand"] + [1.0]])

    data_side = [
        {
            "id_streaming": "201",
            "local_meta2": coordinates_left_hand,
            "side": "L",
            "wheel_center": coordinates_left_wheel_center,
        },
        {
            "id_streaming": "202",
            "local_meta2": coordinates_right_hand,
            "side": "R",
            "wheel_center": coordinates_right_wheel_center,
        },
    ]

    n = 1

    id_streaming = data_side[n]["id_streaming"]
    side = data_side[n]["side"]

    ts = ktk.TimeSeries()
    ts.time = data[id_streaming].time

    ts.data[f"Meta2{side}"] = ktk.geometry.matmul(
        data[id_streaming].data[id_streaming], data_side[n]["local_meta2"]
    )

    t_min = max(ts.time[0], data["102"].time[0])
    t_max = min(ts.time[-1], data["102"].time[-1])

    ts_data = data["102"].get_ts_between_times(t_min, t_max)
    ts = ts.get_ts_between_times(t_min, t_max)

    ts = ts.resample(ts_data.time)

    ts.data[f"Meta2{side}"] = ktk.geometry.get_local_coordinates(
        global_coordinates=ts.data[f"Meta2{side}"],
        reference_frames=ts_data.data["102"],
    )
    ts.data[f"Meta2{side}"] = ts.data[f"Meta2{side}"][:, 0]

    # # Set sample rate constant
    dt = np.median(np.diff(ts.time))
    time_uniform = np.arange(ts.time[0], ts.time[-1], dt)
    ts = ts.resample(time_uniform)

    # Filter butterworth order 4 with cut frequency of 6Hz
    ts = ktk.filters.butter(ts, fc=6, order=4)

    # Add velocity and acceleration timeseries
    ts_df = ktk.filters.deriv(ts, n=1)
    ts_dff = ktk.filters.deriv(ts, n=2)

    ts = ts.get_ts_before_index(len(ts.time) - 1)
    ts.data[f"Meta2{side}_df"] = ts_df.data[f"Meta2{side}"]
    ts = ts.get_ts_before_index(len(ts.time) - 1)
    ts.data[f"Meta2{side}_dff"] = ts_dff.data[f"Meta2{side}"]

    # Cycles detection
    ts_events = ktk.cycles.detect_cycles(
        ts_df,
        f"Meta2{side}",
        thresholds=(0.0, 0.0),
        event_names=["push", "recovery"],
    )

    events = [e for e in ts_events.events if e.name != "_"]

    cycles = []
    
    # Creation des cycles lorsque la direction change --> v = 0 avec critere temporel : durée cycle supérieur à 0.4 s
    for i in range(len(events) - 2):
        if (events[i].name == "push" and events[i+1].name == "recovery" and events[i+2].name == "push"):
    
            index_t = ts.get_index_at_time(events[i].time)
            index_t1 = ts.get_index_at_time(events[i+1].time)
            index_t2 = ts.get_index_at_time(events[i+2].time)        
            
            delta_t = events[i+2].time - events[i].time
            
            index_t = ts.get_index_at_time(events[i].time)
            index_t1 = ts.get_index_at_time(events[i+1].time)
            index_t2 = ts.get_index_at_time(events[i+2].time)
            
            delta_x = ts.data[f"Meta2{side}"][index_t1] - ts.data[f"Meta2{side}"][index_t]
            delta_x_ = ts.data[f"Meta2{side}"][index_t2] - ts.data[f"Meta2{side}"][index_t1]
            
            if delta_t > 0.4: # seuil delta t
                cycles.append({
                    "in_push": {"time": events[i].time, "value": ts.data[f"Meta2{side}"][index_t]},
                    "recovery": {"time": events[i+1].time, "value": ts.data[f"Meta2{side}"][index_t1]},
                    "end_push": {"time": events[i+2].time, "value": ts.data[f"Meta2{side}"][index_t2]},
                    "range": ts.data[f"Meta2{side}"][index_t1] - ts.data[f"Meta2{side}"][index_t],
                })
    
    
    # Critère cinématique n°1 : amplitude minimale fonction de l'amplitude générale (médiane) des 3 derniers cycles
    filtered = []
    
    for cycle in cycles:
        if len(filtered) < 3:
            filtered.append(cycle)
            continue
    
        prev_ranges = np.array([
                filtered[-1]["range"],
                filtered[-2]["range"],
                filtered[-3]["range"]
                ])
    
        if cycle["range"] >= 0.3 * np.median(prev_ranges):
            filtered.append(cycle)
    
    cycles = filtered
    
    
    # Critère cinématique n°2 : condition de traverser le point milieu entre la position la plus antérieure et la plus postérieure générale des 3 derniers cycles
    filtered = []
    
    signal = ts.data[f"Meta2{side}"]
    
    for r in range(len(cycles)):
        if r < 3:
            filtered.append(cycles[r])
            continue
    
        prev_values = [
            (cycles[r-1]["recovery"]["value"] + cycles[r-1]["in_push"]["value"])/2,
            (cycles[r-2]["recovery"]["value"] + cycles[r-2]["in_push"]["value"])/2,
            (cycles[r-3]["recovery"]["value"] + cycles[r-3]["in_push"]["value"])/2
        ]
    
        median_val = sorted(prev_values)[1]
    
        t0 = ts.get_index_at_time(cycles[r]["in_push"]["time"])
        t2 = ts.get_index_at_time(cycles[r]["end_push"]["time"])
    
        segment = signal[t0:t2+1]
    
        crossed_up = False
        crossed_down = False
    
        for i in range(len(segment) - 1):
            if segment[i] < median_val and segment[i+1] >= median_val:
                crossed_up = True
            if segment[i] > median_val and segment[i+1] <= median_val:
                crossed_down = True
    
            if crossed_up and crossed_down:
                break
    
        if crossed_up and crossed_down:
            filtered.append(cycles[r])
    
    cycles = filtered
    
    
    for cycle in cycles:
        
        ts = ts.add_event(cycle["in_push"]["time"], "in_push")
        # ts = ts.add_event(cycle["recovery"], "recovery")
        ts = ts.add_event(cycle["end_push"]["time"], "end_push")

    # Timeseries for pattern Meta2L
    _ts = ktk.TimeSeries()
    _ts.time = data[id_streaming].time
    _ts.data[f"Meta2{side}"] = ktk.geometry.matmul(
        data[id_streaming].data[id_streaming], data_side[n]["local_meta2"]
    )

    t_min = max(_ts.time[0], data["102"].time[0])
    t_max = min(_ts.time[-1], data["102"].time[-1])

    ts_data = data["102"].get_ts_between_times(t_min, t_max)
    _ts = _ts.get_ts_between_times(t_min, t_max)

    _ts = _ts.resample(ts_data.time)

    _ts.data[f"Meta2{side}"] = ktk.geometry.get_local_coordinates(
        global_coordinates=_ts.data[f"Meta2{side}"],
        reference_frames=ts_data.data["102"],
    )
    _ts.data[f"Meta2{side}"] = _ts.data[f"Meta2{side}"][:, 0:2]

    dt = np.median(np.diff(_ts.time))
    time_uniform = np.arange(_ts.time[0], _ts.time[-1], dt)
    _ts = _ts.resample(time_uniform)

    # # Plot Position and velocity
    plt.figure()
    plt.subplot(5, 1, 1)
    plt.title("Position")
    colors = [(1, 0, 0), (0.5, 0.25, 0.25)]
    color = colors[i % 2]

    for i, cycle in enumerate(cycles):
        start = cycle["in_push"]["time"]
        end = cycle["end_push"]["time"]
        color = colors[i % 2]

        plt.axvspan(start, end, color=color, alpha=0.3)
    ts.plot(f"Meta2{side}")

    plt.subplot(5, 1, 3)
    plt.title("Velocity")
    ts.plot(f"Meta2{side}_df")
    plt.subplot(5, 1, 5)
    plt.title("Acceleration")
    ts.plot(f"Meta2{side}_dff")

    # Plot combined normalised cycles
    plt.figure()
    ts_normalised = ktk.cycles.time_normalize(ts, "in_push", "end_push")
    data_ = ktk.cycles.stack(ts_normalised)
    data_
    n_cycles = data_[f"Meta2{side}"].shape[0]
    for i_cycle in range(n_cycles):
        plt.plot(data_[f"Meta2{side}"][i_cycle], label=f"Cycle {i_cycle}")
    plt.legend()

    # Plot single pattern push
    n_ = 1
    plt.figure()

    for cycle in cycles:
        ax = plt.subplot(7, 7, n_)

        circle = plt.Circle(
            (
                coordinates_right_wheel_center[0][0],
                coordinates_right_wheel_center[0][1],
            ),
            0.54 / 2,
            fill=False,
            linestyle="--",
        )
        ax.add_patch(circle)

        _ts_ = _ts.get_ts_between_times(cycle["in_push"]["time"], cycle["end_push"]["time"])
        ax.plot(
            _ts_.data[f"Meta2{side}"][:, 0], _ts_.data[f"Meta2{side}"][:, 1]
        )

        ax.set_xlim(-0.8, 0.2)
        ax.set_ylim(0, 1.15)

        # ax.set_xlim(-0.8, 0)
        # ax.set_ylim(0, 0.7)
        ax.set_aspect("equal")

        n_ += 1
    plt.show()

    # list push frequency and mean
    push_frequency = []
    for i in range(len(cycles)):
        push_frequency.append(cycles[i]["push_frequency"])
        # print(str(i), " ", str(cycles[i]["push_frequency"]))
    mean_push_frequency = np.mean(push_frequency)

    return mean_push_frequency
