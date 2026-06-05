import sys

sys.path.append(r"D:\Maria_school\Documents\S2026\nextwheel\software\python")

import os
from datetime import date
import csv
import glob
from kineticstoolkit import TimeSeries
import numpy as np

from nextwheel import NextWheel

wheels = {
    "right": NextWheel(),
    # "left": NextWheel(),
}

# %% Folder contents


def _make_folder(
    directory: str,
    participant: str,
    session: str | None = "",
    trial: str | None = "",
) -> str:
    """
    Create a folder for a specific paricipant within directory.

    Sub-folders for sessions and trials can be created through this function
    when those arguments are included.

    Parameters
    ----------
    directory :
        Base folder containing data for all participants.
    participant :
        Participant identifier number.
    session : optional
        Current session number.
    trial: optional
        Current trial number.

    Returns
    -------
    folder :
        Folder specific to this participant (and/or session and trial).
    """
    folder = os.path.join(directory, participant, session, trial)
    if not os.path.exists(folder):
        os.makedirs(folder)
        print("Created folder ", folder)
    return folder


def _get_session(folder: str) -> int:
    """
    Identify session currently being recorded through folder-parsing.

    If none are found, returns 0.

    Parameters
    ----------
    folder :
        Folder corresponding to current participant.

    Returns
    -------
    session :
        Current session number.
    """
    folders = [
        f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)
    ]
    if (len(folders)) > 0:
        session = len(folders) - 1
    else:
        session = 0
    return session


def _get_trial(folder: str) -> int:
    """
    Identify trial currently being recorded through folder-parsing.

    If none are found, returns 0.

    Parameters
    ----------
    folder :
        Sub-folder corresponding to current participant and session.

    Returns
    -------
    trial :
        Current trial number.
    """
    folders = [
        f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)
    ]
    if (len(folders)) > 0:
        trials = [int(folder.split("\\T")[-1]) for folder in folders]
        trial = max(trials)
    else:
        trial = 0
    return trial


def _find_files(
    directory: str, scene: str, participant: str, trial: str
) -> tuple[list[str], str]:
    """
    Find files related to trial in-progress within current recording session.

    Parameters
    ----------
    directory :
        Folder containing data for all of the participants.
    scene :
        Selected playable scene for current session.
    participant :
        Current participant identifier.
    trial :
        Current trial number.

    Returns
    -------
    trial_files :
        Files pertaining to the current trial in-progress.
    trial_basename :
        Common base for all files pertaining to this trial.
    """
    if os.path.exists(directory):
        data_folder = os.path.join(
            directory, participant, str(date.today()), "T" + trial
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


# %% File generation - Simulator


def _make_header(
    trajectory_data: list[str] | None = ["position", "rotation"],
    data_column: int | None = 4,
) -> list[list[str]]:
    """
    Create a header appropriate for the trajectory data to be saved.

    Parameters
    ----------
    trajectory_data : optional
        The two data types to be saved through the Godot interface.
        The default is ["position", "rotation"].
    data_columns : optional
        The number of columns to be expected for each trajectory data to save
        The default is 4.

    Returns
    -------
    header :
        Header corresponding to the file to be created.
    """
    header = ["time"] + [
        trajectory_data[i] + "[:," + str(j) + "]"
        for i in range(len(trajectory_data))
        for j in range(data_column)
    ]
    return header


def _make_filename(session: str, trial: str, scene: str) -> list[str]:
    """
    Create a filename appropriate for the trajectory data to be saved.

    Parameters
    ----------
    session :
        Current session number.
    trial :
        Current trial number.
    scene :
        Current playable scene selected (out of 6 options).

    Returns
    -------
    file :
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
        + "_trajectory.csv"
    )

    return file


def _make_csv(folder: str, filename: str, header: list[str]) -> None:
    """
    Create a CSV file of a particular header within specified folder.

    Parameters
    ----------
    folder :
        Sub-folder corresponding to current participant.
    filename :
        Name of file to be created.
    header :
        Header of file to be created.

    Returns
    -------
    None
    """
    with open(os.path.join(folder, filename), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)


# %% File generation - instrumented wheels


def _create_wheels(
    filename: str,
    wheels: NextWheel | None = wheels,
    wheel_data: dict[str, dict] | None = {
        "Analog": {"Time": [], "Channels": [], "Force": [], "Moment": []},
        "IMU": {"Time": [], "Acc": [], "Gyro": [], "Mag": []},
        "Encoder": {"Time": [], "Angle": []},
        "Power": {"Time": [], "Voltage": [], "Current": [], "Power": []},
    },
    wheel_events: dict | None = {},
) -> None:
    """
    Create and save dictionaries to hold instrumented wheels data and events.

    Typical events include logging initiation and termination, new trials.

    Parameters
    ----------
    filename :
        The base filename for the two dictionaries, of the form: SX_YYYY-MM-DD-
        where X is the session number.
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    wheel_data : optional
        A dictionary of the structure required to collect data from the wheels.
        The default is {"Analog": {"Time": [], "Channels": [], "Force": [], "Moment": []},
                        "IMU": {"Time": [], "Acc": [], "Gyro": [], "Mag": []},
                        "Encoder": {"Time": [], "Angle": []},
                        "Power": {"Time": [], "Voltage": [], "Current": [], "Power": []}}.
    wheel_events : optional
        An empty dictionary where events will be collected as
        wheel_events['event_name'] = timestamp.
        The default is {}.

    Returns
    -------
    None
    """

    np.save(
        filename + "_events.npy",
        wheel_events,
        allow_pickle=True,
    )

    for key in wheels.keys:
        np.save(
            filename + "_data_" + key + ".npy",
            wheel_data,
            allow_pickle=True,
        )


# %% File contents


def _load_wheels(
    trial_folder: str, filebase: str, wheel_type: str, side: str | None = ""
):
    """
    Load a numpy file containing instrumented wheels information (as a dict).

    Parameters
    ----------
    session_folder :
        The folder where data relating to the current session is saved.
    filebase :
        The base filename for the events file to load, of the form:
        SX_YYYY-MM-DD- where X is the session number.
    wheel_type :
        The type of file to be loaded: either 'events' or 'data'.
    side : optional
        The specific wheel for which recording must be stopped, if relevant
        The default is "", for the function to work for event files are well.


    Returns
    -------
    TYPE
        DESCRIPTION.
    """
    wheel_dict = np.load(
        os.path.join(
            trial_folder, filebase + "_" + wheel_type + side + ".npy"
        ),
        allow_pickle=True,
    ).item()

    return wheel_dict


# %% Logging simulator


def _save_trajectory(base: str, data_values: dict[str, str]) -> None:
    """
    Open and append data to an already-created CSV file containing trajectory.

    Parameters
    ----------
    base :
        Current participant's data sub-folder.
    data_values :
        Current data values to save.

    Returns
    -------
    None
    """
    filename = base + "trajectory.csv"

    timestamp = data_values["time"]

    data_line = (
        [timestamp]
        + [x for x in data_values["position"].strip("()").split(",")]
        + ["1"]
        + [x for x in data_values["rotation"].strip("()").split(",")]
        + ["0"]
    )

    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data_line)


# %% Logging instrumented wheels


def _event_wheels(trial_folder: str, wheel_file: str, event_name: str) -> None:
    """
    Open and append event to instrumented wheels event dictionary.

    Parameters
    ----------
    session_folder :
        The folder where data relating to the current session is saved.
    wheel_file :
        The base filename for the events file to load, of the form:
        SX_YYYY-MM-DD- where X is the session number.
    event_name :
        Name of the event to be logged. Conventions:
            'start_logging' for logging initiation,
            'TX_scene' for initiation of trial number X of scene name 'scene',
            'stop_logging' for logging termination.

    Returns
    -------
    None
    """
    wheel_events = _load_wheels(trial_folder, wheel_file, "events")

    wheel_events[event_name] = arg["time"]
    print("Sent new scene event to NextWheel: " + event_name)
    np.save(
        os.path.join(trial_folder, wheel_file + "_events.npy"),
        wheel_events,
        allow_pickle=True,
    )


def _save_wheels(
    session: str,
    trial_folder: str,
    scene: str,
    trial: str,
    wheels: NextWheel | None = wheels,
    side: str | None = "right",
) -> None:
    """
    Open and append data to instrumented wheels data dictionary.

    Parameters
    ----------
    session :
        Current session number.
    trial_folder :
        Current trial folder.
    scene :
        The current scene.
    trial :
        The current trial number.
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    side : optional
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
    wheel_data = _load_wheels(
        trial_folder, wheel_file, "data", side="_" + side
    )

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


def _stop_wheels(
    session: str,
    trial_folder: str,
    trial: str,
    scene: str,
    wheels: NextWheel | None = wheels,
) -> None:
    """
    Stop instrumented wheels streaming and catch final events.


    Parameters
    ----------
    session :
        Current session number.
    trial_folder :
        Current trial folder.
    trial :
        The current trial number.
    scene :
        The current scene.
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.


    Returns
    -------
    wheel_file :
        Basename of files pertaining to instrumented wheels for current trial.
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

    _event_wheels(trial_folder, wheel_file, "stream_stop")

    for key in wheels.keys():
        wheels[key].stop_streaming()
        _save_wheels(session, trial_folder, scene, trial, side=key)
        print("Successfully stopped stream from wheel: " + key)

    return wheel_file


def _convert_wheels(
    wheel_file: str,
    trial_folder: str,
    wheels: NextWheel | None = wheels,
) -> None:
    """
    Convert wheels data to TimeSeries, append events, save final files.

    Parameters
    ----------
    wheel_file :
        Basename of files pertaining to instrumented wheels for current trial.
    trial_folder :
        Current trial folder.
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.

    Returns
    -------
    None
    """
    wheel_events = _load_wheels(trial_folder, wheel_file, "events")

    for side in wheels.keys():
        wheel_data = _load_wheels(
            trial_folder, wheel_file, "data", side="_" + side
        )

        for key in wheel_data.keys():
            wheel_time = wheel_data[key]["Time"][:, 0]

            wheel_data[key] = TimeSeries(time=wheel_time, data=wheel_data[key])

            for subkey in wheel_events:
                wheel_data[key].add_event(
                    time=float(wheel_events[subkey]),
                    name=subkey,
                    in_place=True,
                )

        np.save(
            os.path.join(trial_folder, wheel_file + "_" + side + ".npy"),
            wheel_data,
            allow_pickle=True,
        )


# %% Public functions
def start_log(
    arg: dict[str, str | bool],
    data_types: list[str] | None = [
        "instrumented_wheels",
        "motion_capture",
    ],
    wheels: dict[NextWheel, NextWheel] | None = wheels,
    IP: dict[str, str] | None = {"right": "192.168.0.86", "left": "0.0.0.0"},
) -> None:
    """
    Create folders for current (new) session, in which trials will be saved.

    Parameters
    ----------
    arg :
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "player_trajectory": bool, whether to save the player's trajectory.
            "instrumented_wheels": bool, whether to save the wheels.
            "motion_capture": bool,  whether to save the motion capture.
    data_types : optional
        The different data types selected for saving through the Godot interface
        that are recorded in a single file for a session.
        The default is ["instrumented_wheels", "motion_capture"].
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.
    IP : optional
        The two IP addresses corresponding to the right and the left wheels.
        The default is {"right": "192.168.0.86", "left": "0.0.0.0"}


    Returns
    -------
    None
    """
    folder = _make_folder(arg["folder"], arg["participant"])
    _ = _get_session(folder)
    _ = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )

    if arg["instrumented_wheels"] == True:
        for key in wheels.keys():
            try:
                wheels[key].IP = IP[key]
                print("Successfully established connection to wheel: " + key)
            except:
                print("Connection could not be established to wheel: " + key)


def create_trial(arg: dict[str, str | bool]) -> None:
    """
    Create empty files where data will be saved during this current trial.

    Parameters
    ----------
    arg :
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "scene": str, the current selected playable scene.
            "time": str, the current timestamp.
            "player_trajectory": bool, whether to save the player's position.
            "instrumented_wheels": bool, whether to save the wheels.
            "motion_capture": bool,  whether to save the motion capture.

    Returns
    -------
    None
    """
    folder = _make_folder(arg["folder"], arg["participant"])
    session = _get_session(folder)

    session_folder = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = str(int(_get_trial(session_folder)) + 1)

    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + trial,
    )

    if arg["player_trajectory"] == True:
        filename = _make_filename(str(session), trial, arg["scene"])
        header = _make_header()
        _make_csv(trial_folder, filename, header)
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

        _create_wheels(os.path.join(trial_folder, wheel_file))
        _event_wheels(trial_folder, wheel_file, "stream_start")


def save_data(
    arg: dict[str, str | bool],
    trajectory: list[str] | None = ["time", "position", "rotation"],
) -> None:
    """
    Open and append new data line to trajectory and instrumented wheels files.

    Parameters
    ----------
    arg :
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "participant": str, the current participant identifier.
            "scene": str, the current selected playable scene.
            "instrumented_wheels": bool, whether to save the wheels.
            "time": str, the current Unix timestamp.
            "position": str, the position at current timestamp, if saved.
            "rotation": str, the rotation at current timestamp, if saved.
    trajectory : optional
        The different data types related to the trajectory to be saved.
        The default is ["time", "position", "rotation"].

    Returns
    -------
    None
    """
    trial = _get_trial(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )
    trial_files, trial_basename = _find_files(
        arg["folder"], arg["scene"], arg["participant"], str(trial)
    )
    trajectory_data = {key: arg[key] for key in trajectory if key in arg}

    if (trajectory_data[trajectory[1]] is not None) or (
        trajectory_data[trajectory[2]] is not None
    ):
        _save_trajectory(trial_basename, trajectory_data)

    if arg["instrumented_wheels"] == True:
        session = _get_session(os.path.join(arg["folder"], arg["participant"]))
        trial_folder = _make_folder(
            arg["folder"],
            arg["participant"],
            session=str(date.today()),
            trial="T" + str(trial),
        )

        for key in wheels.keys():
            _save_wheels(
                str(session), trial_folder, arg["scene"], str(trial), side=key
            )


def end_log(
    arg: dict[str, str | bool],
    wheels: dict[NextWheel, NextWheel] | None = wheels,
) -> None:
    """
    Confirm the end of recording and terminate instrumented wheels streaming.

    Parameters
    ----------
    arg :
        Dictionary containing arguments sent through Godot:
                "folder": str, the main folder where all data is saved.
                "participant": str, the current participant identifier.
                "scene": str, the current selected playable scene.
                "time": str, the current Unix timestamp.
                "instrumented_wheels": bool, whether to save the wheels.
                "motion_capture": bool,  whether to save the motion capture.
    wheels : optional
        The two instances of NextWheel created (corresponding to the right and
        the left wheels) when data_logging is imported.
        The default is the global variable wheels.

    Returns
    -------
    None
    """

    folder = _make_folder(arg["folder"], arg["participant"])
    session = _get_session(folder)
    session_folder = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = _get_trial(session_folder)
    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + str(trial),
    )

    if arg["instrumented_wheels"] == True:
        wheel_file = _stop_wheels(
            str(session),
            trial_folder,
            str(trial),
            arg["scene"],
            side="right",
            wheels=wheels,
        )
        _convert_wheels(
            wheel_file,
            str(session),
            trial_folder,
            str(trial),
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
        "instrumented_wheels": False,
        "motion_capture": False,
    }
    start_log(arg, wheels=wheels)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "time": "0000000000.000",
        "player_trajectory": True,
        "instrumented_wheels": False,
        "motion_capture": False,
    }
    create_trial(arg)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "instrumented_wheels": False,
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
        "instrumented_wheels": False,
        "motion_capture": False,
    }
    end_log(arg, wheels=wheels)
