import os
from datetime import date
import csv
import glob
import numpy as np

from nextwheel.software.python.nextwheel import NextWheel

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


def _get_number(folder: str) -> int:
    """
    Identify session or trial currently in-progress through folder-parsing.

    If none are found, returns 0.

    Parameters
    ----------
    folder :
        Folder corresponding to current participant and/or session.

    Returns
    -------
    session :
        Current session number.
    """
    folders = [
        f for f in glob.glob(os.path.join(folder, "*")) if os.path.isdir(f)
    ]
    if (len(folders)) > 0:
        number = len(folders)
    else:
        number = 0
    return number


# %% File generation


def _make_header(data_type: str) -> list[list[str]]:
    """
    Create a header appropriate for the type of data to be saved.

    Parameters
    ----------
    data_type :
        The type of data to be saved from Simulator or instrumented wheels.
        Options are:
            Simulator (through Godot): trajectory.
            NextWheel: Analog, IMU, Encoder, Power.

    Returns
    -------
    header :
        Header to be used when creating the CSV file.
    """
    data_to_save, data_columns = _select_header(data_type)
    header = ["time"] + [
        data_to_save[i] + "[:," + str(j) + "]"
        for i in range(len(data_to_save))
        for j in range(data_columns[i])
    ]
    return header


def _select_header(data_type: str) -> tuple[list[str], list[int]]:
    """
    Selects the column titles and number of columns for the CSV file's header.

    Parameters
    ----------
    data_type :
        The type of data to be saved from Simulator or instrumented wheels.
        Options are:
            Simulator (through Godot): trajectory.
            NextWheel: Events, Analog, IMU, Encoder, Power.

    Returns
    -------
    data_to_save :
        The specific column titles to be saved in the CSV file.
    data_columns :
        The number of columns per column title.
    """
    if data_type == "trajectory":
        data_to_save = ["position", "rotation"]
        data_columns = [4, 4]
    elif data_type == "Events":
        data_to_save = ["Event Name"]
        data_columns = ([1],)
    elif data_type == "Analog":
        data_to_save = ["Channels", "Force", "Moment"]
        data_columns = [7, 4, 4]
    elif data_type == "IMU":
        data_to_save = ["Acc", "Gyro", "Mag"]
        data_columns = [3, 3, 3]
    elif data_type == "Encoder":
        data_to_save = ["Angle"]
        data_columns = [1]
    elif data_type == "Power":
        data_to_save = ["Voltage", "Current", "Power"]
        data_columns = [1, 1, 1]
    return data_to_save, data_columns


def _make_filename(
    session: str, trial: str, scene: str, data_type: str
) -> list[str]:
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
    data_type:
        The type of data to be saved from Simulator or instrumented wheels.
        Options are:
            Simulator (through Godot): trajectory.
            NextWheel: Analog, IMU, Encoder, Power.


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
        + "_"
        + data_type
        + ".csv"
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


def _create_wheels(
    trial_folder: str,
    session: int,
    trial: int,
    scene: str,
    wheel_data: list[str] | None = [
        "Analog",
        "IMU",
        "Encoder",
        "Power",
    ],
) -> None:
    """
    Create and save CSV files to hold instrumented wheels data and events.

    Parameters
    ----------
    trial_folder :
        The folder containing data for the current trial in-progress.
    session :
        The current session number.
    trial :
        The current trial number.
    scene :
        The current playable scene selected.
    wheel_data : optional
        The different types of wheel data that can be saved.
        The default is ["Analog", "IMU", "Encoder", "Power"].

    Returns
    -------
    None
    """
    for key in wheel_data:
        header = _make_header(key)
        filename = _make_filename(str(session), str(trial), scene, key)
        _make_csv(trial_folder, filename, header)


# %% Logging simulator


def _save_trajectory(filename: str, data_values: dict[str, str]) -> None:
    """
    Open and append data to an already-created CSV file containing trajectory.

    Parameters
    ----------
    filename :
        Name of the file in which current trial's data is saved.
    data_values :
        Current data values to save.

    Returns
    -------
    None
    """
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


def _save_wheels(
    session: str,
    trial_folder: str,
    scene: str,
    trial: str,
    wheels: NextWheel | None = wheels,
    side: str | None = "right",
    wheel_data: list[str] | None = [
        "Analog",
        "IMU",
        "Encoder",
        "Power",
    ],
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
    wheel_data : optional
        The different types of wheel data that can be saved.
        The default is ["Analog", "IMU", "Encoder", "Power"].

    Returns
    -------
    None
    """
    nw = wheels[side].fetch(clear=True)

    for key in nw.keys():
        filename = _make_filename(session, trial, scene, key)

        data_lines = np.column_stack(
            [nw[key].time]
            + [nw[key].data[subkey] for subkey in nw[key].data.keys()]
        )

        with open(
            os.path.join(trial_folder, filename), "a", newline=""
        ) as file:
            writer = csv.writer(file)
            writer.writerows(data_lines)


def _stop_wheels(
    session: str,
    trial_folder: str,
    trial: str,
    scene: str,
    time: str,
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
    time :
        The current timestamp.
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

    for key in wheels.keys():
        wheels[key].stop_streaming()
        _save_wheels(session, trial_folder, scene, trial, side=key)
        print("Successfully stopped stream from wheel: " + wheels[key].IP)

    return wheel_file


# %% Public functions
def start_log(
    arg: dict[str, str | bool],
    data_types: list[str] | None = [
        "instrumented_wheels",
        "motion_capture",
    ],
    wheels: dict[NextWheel, NextWheel] | None = wheels,
    IP: dict[str, str] | None = {
        "right": "192.168.0.86",
        "left": "192.168.0.13",
    },
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
    _ = _get_number(folder)
    _ = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )

    if arg["instrumented_wheels"] == True:
        for key in wheels.keys():
            try:
                wheels[key].IP = IP[key]
                print(
                    "Successfully established connection to wheel: "
                    + wheels[key].IP
                )
            except:
                print(
                    "Connection could not be established to wheel: "
                    + wheels[key].IP
                )


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
    session = _get_number(folder)

    session_folder = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = str(_get_number(session_folder) + 1)

    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + trial,
    )

    if arg["player_trajectory"] == True:
        filename = _make_filename(
            str(session), trial, arg["scene"], "trajectory"
        )
        header = _make_header("trajectory")
        _make_csv(trial_folder, filename, header)
        print("Created the file " + filename)

    if arg["instrumented_wheels"] == True:
        for key in wheels.keys():
            wheels[key].start_streaming()
            print("Streaming started for wheel: " + wheels[key].IP)

        _create_wheels(trial_folder, session, trial, arg["scene"])


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
    trial = _get_number(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )
    session = _get_number(os.path.join(arg["folder"], arg["participant"]))
    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + str(trial),
    )

    trajectory_file = _make_filename(
        str(session), str(trial), arg["scene"], "trajectory"
    )

    trajectory_data = {key: arg[key] for key in trajectory if key in arg}

    if (trajectory_data[trajectory[1]] is not None) or (
        trajectory_data[trajectory[2]] is not None
    ):
        _save_trajectory(
            os.path.join(trial_folder, trajectory_file), trajectory_data
        )

    if arg["instrumented_wheels"] == True:
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
    session = _get_number(folder)
    session_folder = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = _get_number(session_folder)
    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + str(trial),
    )

    if arg["instrumented_wheels"] == True:
        _stop_wheels(
            str(session),
            trial_folder,
            str(trial),
            arg["scene"],
            arg["time"],
            wheels=wheels,
        )

    print("Logging is done for current session: ", trial_folder)


if __name__ == "__main__":
    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "participant": "test",
        "scene": "scene",
        "time": "0000000000.000",
        "player_trajectory": True,
        "instrumented_wheels": False,
        "motion_capture": False,
        "position": "(0,0,0)",
        "rotation": "(0,0,0)",
    }
    start_log(arg, wheels=wheels)

    create_trial(arg)

    save_data(arg)

    end_log(arg, wheels=wheels)
