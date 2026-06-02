import os
from datetime import date
import csv
import glob

from nextwheel import NextWheel
from kineticstoolkit import TimeSeries
import numpy as np

wheels = {
    "right": NextWheel(),
    # "left": NextWheel(),
}


def make_folder(
    data_folder: str,
    participant: str,
    session: str | None = "",
    trial: str | None = "",
) -> str:
    """
    Within the folder where all data is saved, creates a sub-folder for current
    participant (and session and trial, if specified) if it does not exist
    already.

    Parameters
    ----------
    data_folder : str
        Base folder containing data for all participants.
    participant : str
        Participant identifier number.
    session : str
        Current session number, if specified
    trial: str
        Current trial number, if specified

    Returns
    -------
    folder : str
        Sub-folder specific to this participant (and session and trial, if
                                                 specified).
    """
    folder = os.path.join(data_folder, participant, session, trial)
    if not os.path.exists(folder):
        os.makedirs(folder)
        print("Created folder ", folder)
    return folder


def get_session(folder: str) -> str:
    """
    Parses folders already in current participant's sub-folder to identify the
    current session number and not over-write data. If no sessions have been
    recorded for this participant, the number is set to 0.

    Parameters
    ----------
    folder : str
        Sub-folder corresponding to current participant.

    Returns
    -------
    session : str
        Current session number.
    """
    folders = [
        f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)
    ]
    if (len(folders)) > 0:
        session = str(len(folders) - 1)
    else:
        session = "0"
    return session


def get_trial(folder: str) -> str:
    """
    Parses folders already in current participant's session sub-folder to
    identify the current trial number. If no trial have been recorded for this
    participant, the number is set to 0.

    Parameters
    ----------
    folder : str
        Sub-folder corresponding to current participant and session.

    Returns
    -------
    trial : str
        Current trial number.
    """
    folders = [
        f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)
    ]
    if (len(folders)) > 0:
        trials = [int(folder.split("\\T")[-1]) for folder in folders]
        trial = str(max(trials))
    else:
        trial = "0"
    return trial


def make_header(
    data_type: str,
    data_column: int | None = 4,
) -> list[list[str]]:
    """
    For the user-selected data types to save from the Godot interface, creates
    a corresponding header for the file.

    Parameters
    ----------
    data_type : str
        The data type to be saved through the Godot interface.
        The options are ["position", "rotation"].
    data_columns : int, optional
        The number of columns to be expected for the file to be saved.
        The default is 4.

    Returns
    -------
    header : str
        Header corresponding to the file to be created.
    """
    header = ["time"] + [
        data_type + "[:," + str(j) + "]" for j in range(data_column)
    ]
    return header


def make_filename(
    session: str,
    trial: str,
    scene: str,
    data_type: str,
) -> list[str]:
    """
    For the user-selected data types to save from the Godot interface, creates
    a corresponding name for the file.

    Parameters
    ----------
    session : str
        Current session number.
    trial : str
        Current trial number.
    scene : str
        Current playable scene selected (out of 6 options).
    data_type : str
        The data type to be saved through the Godot interface.
        The options are ["position", "rotation"].

    Returns
    -------
    file : str
        Name of file to be created.
    """
    file = (
        "S"
        + session
        + "_"
        + str(date.today())
        + "_"
        + "T"
        + trial
        + "_"
        + scene
        + "_"
        + data_type
        + ".csv"
    )

    return file


def make_csv(folder: str, filename: str, header: list[str]) -> None:
    """
    Creates a CSV file within a specific folder, with its particular header.

    Parameters
    ----------
    folder : str
        Sub-folder corresponding to current participant.
    filename : str
        Name of file to be created.
    header : str
        Header of file to be created.

    Returns
    -------
    None
    """
    with open(os.path.join(folder, filename), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)


def wheel_dicts(
    filename: str,
    wheel_data: dict[dict, dict, dict, dict] | None = {
        "Analog": {"Time": [], "Channels": [], "Force": [], "Moment": []},
        "IMU": {"Time": [], "Acc": [], "Gyro": [], "Mag": []},
        "Encoder": {"Time": [], "Angle": []},
        "Power": {"Time": [], "Voltage": [], "Current": [], "Power": []},
    },
    wheel_events: dict | None = {},
) -> None:
    """
    Creates and saves two dictionaries that will contain the information
    pertaining to the instrumented wheels: the collected data and the events
    (logging initiation, new trial initiation, logging termination).

    Parameters
    ----------
    filename : str
        The base filename for the two dictionaries, of the form: SX_YYYY-MM-DD-
        where X is the session number.
    wheel_data : dict | None, optional
        A dictionary of the structure required to collect data from the wheels.
        The default is {"Analog": {"Time": [], "Channels": [], "Force": [], "Moment": []},
                        "IMU": {"Time": [], "Acc": [], "Gyro": [], "Mag": []},
                        "Encoder": {"Time": [], "Angle": []},
                        "Power": {"Time": [], "Voltage": [], "Current": [], "Power": []}}.
    wheel_events : dict | None, optional
        An empty dictionary where events will be collected as
        wheel_events['event_name'] = timestamp.
        The default is {}.

    Returns
    -------
    None
    """

    wheel_info = [wheel_data, wheel_events]
    wheel_names = ["data", "events"]

    for i in range(len(wheel_info)):
        np.save(
            filename + "_" + wheel_names[i] + ".npy",
            wheel_info[i],
            allow_pickle=True,
        )


def start_logging(
    arg: dict[str, str, bool, bool, bool, bool],
    data_types: list[str] | None = [
        "instrumented_wheels",
        "motion_capture",
    ],
    wheels: dict[NextWheel, NextWheel] | None = wheels,
    IP: dict[str, str] | None = {"right": "192.168.0.86", "left": "0.0.0.0"},
) -> None:
    """
    Creates folders for this new session, in which trials will be saved.

    Parameters
    ----------
    arg : dict[str, str, bool, bool, bool, bool]
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "player_position": bool, whether to save the player's position.
            "player_rotation": bool, whether to save the player's rotation.
            "instrumented_wheels": bool, whether to save the wheels.
            "motion_capture": bool,  whether to save the motion capture.
    data_types : list[str], optional
        The different data types selected for saving through the Godot interface
        that are recorded in a single file for a session.
        The default is ["instrumented_wheels", "motion_capture"].
    wheels : dict[NextWheel, NextWheel], optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    IP : dict[str, str], optional
        The two IP addresses corresponding to the right and the left wheels.
        The default is {"right": "192.168.0.86", "left": "0.0.0.0"}


    Returns
    -------
    None
    """
    folder = make_folder(arg["folder"], arg["participant"])
    _ = get_session(folder)
    _ = make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )

    if arg["instrumented_wheels"] == True:
        for key in wheels.keys():
            try:
                wheels[key].IP = IP[key]
                print("Successfully established connection to wheel: " + key)
            except:
                print("Connection could not be established to wheel: " + key)


def wheels_load(trial_folder: str, filebase: str, wheel_type: str):
    """
    Loads an 'events' or a 'data' file pertaining to the recording of the
    instrumented wheels during this current session.

    Parameters
    ----------
    session_folder : str
        The folder where data relating to the current session is saved.
    filebase : str
        The base filename for the events file to load, of the form:
        SX_YYYY-MM-DD- where X is the session number.
    wheel_type : str
        The type of file to be loaded: either 'events' or 'data'.

    Returns
    -------
    TYPE
        DESCRIPTION.
    """
    wheel_dict = np.load(
        os.path.join(trial_folder, filebase + "_" + wheel_type + ".npy"),
        allow_pickle=True,
    ).item()

    return wheel_dict


def wheels_event(trial_folder: str, wheel_file: str, event_name: str) -> None:
    """
    Opens the events file corresponding to this session, appends an event, and
    saves and closes the file.

    Parameters
    ----------
    session_folder : str
        The folder where data relating to the current session is saved.
    wheel_file : str
        The base filename for the events file to load, of the form:
        SX_YYYY-MM-DD- where X is the session number.
    event_name : str
        Name of the event to be logged. Conventions:
            'start_logging' for logging initiation,
            'TX_scene' for initiation of trial number X of scene name 'scene',
            'stop_logging' for logging termination.

    Returns
    -------
    None
    """
    wheel_events = wheels_load(trial_folder, wheel_file, "events")

    wheel_events[event_name] = arg["time"]
    print("Sent new scene event to NextWheel: " + event_name)
    np.save(
        os.path.join(trial_folder, wheel_file + "_events.npy"),
        wheel_events,
        allow_pickle=True,
    )


def create_trial(
    arg: dict[str, str, str, str, bool, bool, bool, bool],
    player_data: list[str, str] | None = [
        "player_position",
        "player_rotation",
    ],
) -> None:
    """
    Creates empty files where data will be saved during this current trial.

    Parameters
    ----------
    arg : dict[str, str, str, bool, bool, bool, bool]
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "scene": str, the current selected playable scene.
            "time": str, the current timestamp.
            "player_position": bool, whether to save the player's position.
            "player_rotation": bool, whether to save the player's rotation.
            "instrumented_wheels": bool, whether to save the wheels.
            "motion_capture": bool,  whether to save the motion capture.
    player_data : list[str, str], optional
        The different data types pertaining to the player that selected through
        the Godot interface (saved per trial).
        The default is ["player_position", "player_rotation"].

    Returns
    -------
    None
    """
    folder = make_folder(arg["folder"], arg["participant"])
    session = get_session(folder)

    session_folder = make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = str(int(get_trial(session_folder)) + 1)

    trial_folder = make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + trial,
    )

    for i in range(len(player_data)):
        if arg[player_data[i]] == True:
            filename = make_filename(
                session, trial, arg["scene"], player_data[i]
            )
            header = make_header(player_data[i])
            make_csv(trial_folder, filename, header)
            print("Created the file " + filename)

    if arg["instrumented_wheels"] == True:
        for key in wheels.keys():
            wheels[key].start_streaming()
        wheel_file = (
            "S"
            + str(session)
            + "_"
            + str(date.today())
            + "_"
            + "T"
            + trial
            + "_"
            + arg["scene"]
        )
        wheel_dicts(os.path.join(trial_folder, wheel_file))
        wheels_event(trial_folder, wheel_file, "stream_start")


def find_files(
    folder: str, scene: str, participant: str, trial: str
) -> tuple[list[str], str]:
    """
    Find files pertaining to the current trial in-progress within the sub-folder
    containing data for this participant's current recording session.

    Parameters
    ----------
    folder : str
        Folder containing data for all of the participants.
    scene : str
        Selected playable scene for current session.
    participant : str
        Current participant identifier.
    trial : str
        Current trial number.

    Returns
    -------
    trial_files : list[str]
        Files pertaining to the current trial in-progress.
    trial_basename : str
        Common base for all files pertaining to this trial.
    """
    # get latest session only
    if os.path.exists(folder):
        # setting up the data logging folder and participant name
        data_folder = os.path.join(
            folder, participant, str(date.today()), "T" + trial
        )

        trial_files = glob.glob(
            os.path.join(
                data_folder, "*" + str(date.today()) + "_T" + trial + "*.csv"
            )
        )

        trial_basename = trial_files[0].rsplit("_", 1)[0] + "_"
    else:
        print("The data-saving folder selected does not exist.")
    return trial_files, trial_basename


def save_file(
    base: str, timestamp: str, data_type: str, data_values: str
) -> None:
    """
    Opens already-created file pertaining to this data type and saves values.

    Parameters
    ----------
    base : str
        Current participant's data sub-folder.
    timestamp : str
        Current timestamp to save.
    data_type : str
        Current data type to save.
    data_values : str
        Current data values to save.

    Returns
    -------
    None
    """
    filename = base + data_type + ".csv"

    data_line = [timestamp] + [x for x in data_values.strip("()").split(",")]

    # add appropriate values for last column
    if data_type == "position":
        data_line.append("1")
    elif data_type == "rotation":
        data_line.append("0")

    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data_line)


def wheels_save(
    session: str,
    trial_folder: str,
    scene: str,
    trial: str,
    wheels=wheels,
    side: str | None = "right",
) -> None:
    """
    Opens the data file corresponding to this session, appends data to it, and
    saves and closes the file.

    Parameters
    ----------
    session : str
        Current session number.
    trial_folder : str
        Current trial folder.
    scene : str
        The current scene.
    trial : str
        The current trial number.
    wheels : dict[NextWheel, NextWheel], optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    side: str, optional
        The specific wheel for which recording must be stopped.
        The default is "right".

    Returns
    -------
    None
    """
    wheel_file = (
        "S"
        + str(session)
        + "_"
        + str(date.today())
        + "_T"
        + trial
        + "_"
        + scene
    )
    wheel_data = wheels_load(trial_folder, wheel_file, "data")

    nw = wheels[side].fetch(clear=True)
    for key in nw.keys():
        if len(wheel_data[key]["Time"]) == 0:
            wheel_data[key]["Time"] = nw[key].time.reshape(-1, 1)
        else:
            wheel_data[key]["Time"] = np.vstack(
                (wheel_data[key]["Time"], nw[key].time.reshape(-1, 1))
            )

        for subkey in nw[key].data.keys():
            data = nw[key].data[subkey]
            if len(nw[key].data[subkey].shape) == 1:
                data = data.reshape(-1, 1)
            if (len(wheel_data[key][subkey])) == 0:
                wheel_data[key][subkey] = data
            else:
                wheel_data[key][subkey] = np.vstack(
                    (wheel_data[key][subkey], data)
                )

    np.save(
        os.path.join(trial_folder, wheel_file + "_data.npy"),
        wheel_data,
        allow_pickle=True,
    )


def save_data(
    arg: dict[str, str, str, bool, str, str, str],
    data_types: list[str] | None = [
        "time",
        "position",
        "rotation",
        "wheels",
        "motion",
    ],
) -> None:
    """
    One by one, opens files pertaining to current participant, session, and
    trial, and save a new line of data.

    Parameters
    ----------
    arg : dict[str, str, str, str, str, str]
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "scene": str, the current selected playable scene.
            "instrumented_wheels": bool, whether to save the wheels.
            "time": str, the current Unix timestamp.
            "position": str, the position at current timestamp, if saved.
            "rotation": str, the rotation at current timestamp, if saved.
    data_types : list[str] | None, optional
        Time, and the different data types that can be selected for saving
        through the Godot interface.
        The default is ["time", "position", "rotation", "wheels", "motion"].

    Returns
    -------
    None
    """
    trial = get_trial(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )
    trial_files, trial_basename = find_files(
        arg["folder"], arg["scene"], arg["participant"], trial
    )
    data_to_save = {key: arg[key] for key in data_types if key in arg}

    for i in range(len(data_to_save) - 1):
        # only save if data was received
        if (list(data_to_save.values())[i + 1]) is not None:
            save_file(
                trial_basename,
                data_to_save["time"],
                list(data_to_save.keys())[i + 1],
                list(data_to_save.values())[i + 1],
            )

    if arg["instrumented_wheels"] == True:
        session = get_session(os.path.join(arg["folder"], arg["participant"]))
        trial_folder = make_folder(
            arg["folder"],
            arg["participant"],
            session=str(date.today()),
            trial="T" + trial,
        )
        wheels_save(session, trial_folder, arg["scene"], trial, side="right")


def wheels_stop(
    session: str,
    trial_folder: str,
    trial: str,
    scene: str,
    wheels: NextWheel | None = wheels,
    side: str | None = "right",
) -> None:
    """
    Stop the streaming of data from the instrumented wheels, catches final
    events, and converts the numpy arrays saved inside of the data file to
    TimeSeries instances before saving the final file to be used for analysis.

    Parameters
    ----------
    session : str
        Current session number.
    trial_folder : str
        Current trial folder.
    trial : str
        The current trial number.
    scene : str
        The current scene.
    wheels : dict[NextWheel, NextWheel], optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    side: str, optional
        The specific wheel for which recording must be stopped.
        The default is "right".


    Returns
    -------
    None
    """
    wheels[side].stop_streaming()

    wheel_file = (
        "S"
        + str(session)
        + "_"
        + str(date.today())
        + "_T"
        + trial
        + "_"
        + scene
    )

    wheels_event(trial_folder, wheel_file, "stream_stop")

    wheels_save(session, trial_folder, scene, trial, side="right")

    wheel_events = wheels_load(trial_folder, wheel_file, "events")
    wheel_data = wheels_load(trial_folder, wheel_file, "data")

    for key in wheel_data.keys():
        wheel_time = wheel_data[key]["Time"][:, 0]

        wheel_data[key] = TimeSeries(time=wheel_time, data=wheel_data[key])

        for subkey in wheel_events:
            wheel_data[key].add_event(
                time=float(wheel_events[subkey]), name=subkey, in_place=True
            )

    np.save(
        os.path.join(trial_folder, wheel_file + ".npy"),
        wheel_data,
        allow_pickle=True,
    )


def end_logging(
    arg: dict[str, str, str, str, bool, bool],
    wheels: dict[NextWheel, NextWheel] | None = wheels,
) -> None:
    """
    Confirms the end of recording and, if the data is recorded through the
    instrumented wheels, terminated the corresponding streaming.

    Parameters
    ----------
    arg : dict[str, str, str, str, str or None, str or None, str or None, str or None]
        Dictionary containing arguments sent through Godot:
                "folder": str, the main folder where all data is saved.
                "participant": str, the current participant identifier.
                "scene": str, the current selected playable scene.
                "time": str, the current Unix timestamp.
                "instrumented_wheels": bool, whether to save the wheels.
                "motion_capture": bool,  whether to save the motion capture.
    wheels : dict[NextWheel, NextWheel], optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.

    Returns
    -------
    None
    """

    folder = make_folder(arg["folder"], arg["participant"])
    session = get_session(folder)
    session_folder = make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = get_trial(session_folder)
    trial_folder = make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + trial,
    )

    if arg["instrumented_wheels"] == True:
        wheels_stop(
            session,
            trial_folder,
            trial,
            arg["scene"],
            side="right",
            wheels=wheels,
        )

    print("Logging is done for current session: ", trial_folder)


if __name__ == "__main__":
    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "time": "0000000000.000",
        "instrumented_wheels": True,
        "motion_capture": False,
    }
    start_logging(arg, wheels=wheels)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "time": "0000000000.000",
        "player_position": True,
        "player_rotation": True,
        "instrumented_wheels": True,
        "motion_capture": False,
    }
    create_trial(arg)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "instrumented_wheels": True,
        "time": "0000000000.000",
        "position": "(0,0,0)",
        "rotation": "(0,0,0)",
    }

    save_data(arg)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "time": "0000000000.000",
        "instrumented_wheels": True,
        "motion_capture": False,
    }
    end_logging(arg, wheels=wheels)
