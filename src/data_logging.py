"""
Run the commands related to data logging called from the python bridge.

Data logged includes the player's virtual position in the simulator, as
well as information collected through the instrumented wheels.

"""

import csv
import glob
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.getcwd())))

from datetime import date
from typing import Any, TypedDict, cast

import kineticstoolkit as ktk
import wheelsims_analysis.src.optitrack as ot
from wheelsims_analysis.src.nextwheel_repo.software.python.nextwheel import (
    NextWheel,
)

# %% Instrumented Wheels dictionary

wheels = {
    "right": NextWheel(),
    # "left": NextWheel(),
}


class FileIDs(TypedDict):
    """
    Struture of the dictionary containing the names of files to be saved.

    player_trajectory:
        The name of the file containing the player's trajectory.
    instrumented_wheels:
        The name of the file containing the instrumented wheels data.
    motion_capture:
        A list of the names of the files containing the motion capture data.
        Each file contains information about a single Rigid Body

    """

    player_trajectory: "csv.writer"
    instrumented_wheels: "csv.writer"
    motion_capture: list["csv.writer"]


session_writers = {
    "player_trajectory": None,
    "instrumented_wheels": None,
    "motion_capture": None,
}


class ArgStructure(TypedDict):
    """
    Structure of the dictionary containing arguments received from Godot.

    folder:
        The main folder where all data is saved.
    participant:
        The current participant identifier.
    time:
        The current timestamp.
    scene:
        The current selected playable scene.
    player_trajectory:
        Whether to save the player's trajectory.
    instrumented_wheels:
        Whether to save the wheels.
    motion_capture:
        Whether to save the motion capture.
    position:
        The current player position in the simulator.
    rotation:
        The current player rotation in the simulator.

    """

    folder: str
    participant: str
    time: str
    scene: str
    player_trajectory: bool
    instrumented_wheels: bool
    motion_capture: bool
    position: str
    rotation: str


def _get_subset(arg: ArgStructure, keys: list[str]) -> dict[str, Any]:
    """
    Cast the TypedDict ArgStructure into generic dictionary to extract data.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.
    keys
        List of keys to be extracted

    Returns
    -------
    dict
        A generic dictionary containing the extracted data.

    """
    generic_arg = cast(dict[str, Any], arg)
    subset = {k: generic_arg[k] for k in keys if k in generic_arg}
    return subset


# %% Folder contents


def _make_folder(
    directory: str,
    participant: str,
    session: str = "",
    trial: str = "",
) -> str:
    """
    Create a folder for a specific paricipant within directory.

    Sub-folders for sessions and trials can be created through this function
    when those arguments are included.

    Parameters
    ----------
    directory
        Base folder containing data for all participants.
    participant
        Participant identifier number.
    session
        Optional. Current session number.
    trial
        Optional. Current trial number.

    Returns
    -------
    str
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
    folder
        Folder corresponding to current participant and/or session.

    Returns
    -------
    str
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


def _make_header(
    data_headers: list[str] = ["position", "rotation"],
    data_columns: list[int] = [4, 4],
) -> list[str]:
    """
    Create a header appropriate for the type of data to be saved.

    Parameters
    ----------
    data_headers
        The specific column titles to be saved in the CSV file.
        The default is ['position', 'rotation'] for the Simulator position.
    data_columns
        The number of columns per column title.
        The default is [4, 4] for the Simulator position.

    Returns
    -------
    list[str]
        Header to be used when creating the CSV file.

    """
    header = ["time"] + [
        data_headers[i] + "[:," + str(j) + "]"
        for i in range(len(data_headers))
        for j in range(data_columns[i])
    ]
    return header


def _make_filename(
    session: str, trial: str, scene: str, data_type: str
) -> str:
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
            Optitrack: RigidBody + ID.

    Returns
    -------
    str
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


def _make_csv(
    folder: str,
    filename: str,
    header: list[str],
    file_type: str,
    session_writers: FileIDs = session_writers,
) -> None:
    """
    Create a CSV file of a particular header within specified folder.

    Parameters
    ----------
    folder
        Sub-folder corresponding to current participant.
    filename
        Name of file to be created.
    header
        Header of file to be created.

    """
    with open(
        os.path.join(folder, filename), "w", newline="", encoding="utf-8"
    ) as file:
        session_writers[file_type] = csv.writer(file)
        if len(header) > 0:
            session_writers[file_type].writerow(header)
    return session_writers


# %% Logging simulator


def _save_trajectory(
    filename: str,
    data_values: dict[str, str],
    session_writers=session_writers,
) -> None:
    """
    Open and append data to an existing CSV file containing trajectory.

    Parameters
    ----------
    filename
        Name of the file in which current trial's data is saved.
    data_values
        Current data values to save.

    """
    timestamp = data_values["time"]

    data_line = (
        [timestamp]
        + list(data_values["position"].strip("()").split(","))
        + ["1"]
        + list(data_values["rotation"].strip("()").split(","))
        + ["0"]
    )

    session_writers["player_trajectory"].writerow(data_line)


# %% Logging TimeSeries


def _save_ts(
    ts: ktk.TimeSeries,
    filename: str,
    trial_folder: str,
    write_data: bool = True,
    session_writers: FileIDs = session_writers,
) -> None:
    """
    Open and append data to CSV file containing time series data.

    Parameters
    ----------
    ts :
        Newly-fetched data from NextWheel or Optitrack.
    filename :
        Name of file to save to.
    trial_folder :
        Current trial folder.

    """
    data_lines = ts.to_dataframe()
    file_type = filename.rsplit("\\", 4)[0]

    if not data_lines.empty:
        if os.path.isfile(os.path.join(trial_folder, filename)):
            code = "a"
        else:
            code = "w"

        with open(
            os.path.join(trial_folder, filename),
            code,
            newline="",
            encoding="utf-8",
        ) as file:
            session_writers[file_type] = csv.writer(file)

            if code == "w":
                session_writers[file_type].writerow(
                    ["time"] + list(data_lines.columns)
                )

            if write_data:
                session_writers[file_type].writerows(
                    data_lines.reset_index().to_numpy()
                )


def _stop_wheels(
    session: str,
    trial_folder: str,
    trial: str,
    scene: str,
    wheels: NextWheel = wheels,
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
        Current trial number.
    scene :
        Current scene.
    wheels:
        Current instance of NextWheel

    """
    for key, wheel in wheels.items():
        wheel.stop_streaming()
        print("Successfully stopped stream from wheel: " + wheel.IP)
        nw = wheel.fetch(clear=True)
        for subkey, ts in nw.items():
            filename = _make_filename(
                session, trial, scene, key + "_" + subkey
            )
            _save_ts(ts, filename, trial_folder)


def _stop_ot(trial_folder: str, session: str, trial: str, scene: str):
    """
    Stop Optitrack streaming and catch final events.

    Parameters
    ----------
    trial_folder :
        Current trial folder.
    session :
        Current session.
    trial :
        Current trial.
    scene:
        Current scene.

    """
    motion = ot.fetch(clear_buffer=True, transform_data=False)
    ot.stop()
    print("Streaming ended for optitrack.")
    for ID, ts in motion.items():
        if len(ID) == 3:
            filename = _make_filename(
                str(session), str(trial), scene, "rigidbody_" + ID
            )
            _save_ts(ts, filename, trial_folder)


# %% Public functions
def start_log(
    arg: ArgStructure,
    ip_addresses: dict[str, str] = {
        "right": "192.168.0.86",
        "left": "192.168.0.13",
    },
    session_writers: FileIDs = session_writers,
    wheels=wheels,
) -> None:
    """
    Create folders for current (new) session, in which trials will be saved.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.
    ip_addresses
        Optional. The two IP addresses corresponding to the right and the left
        wheels. The default is {"right": "192.168.0.86", "left": "0.0.0.0"}

    """
    folder = _make_folder(arg["folder"], arg["participant"])
    _ = _get_number(folder)
    _ = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )

    if arg["instrumented_wheels"]:
        for key, wheel in wheels.items():
            try:
                wheel.IP = ip_addresses[key]
                print(
                    "Successfully established connection to wheel: " + wheel.IP
                )
            except TimeoutError:
                print(
                    "Connection could not be established to wheel: " + wheel.IP
                )


def create_trial(
    arg: ArgStructure,
    wheels=wheels,
) -> None:
    """
    Create empty files where data will be saved during this current trial.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.

    """
    if arg["instrumented_wheels"]:
        for key, wheel in wheels.items():
            wheel.start_streaming()
            print("Streaming started for wheel: ", key, " of IP ", wheel.IP)

    if arg["motion_capture"]:
        ot.start()
        print("Streaming started for Optitrack.")

    folder = _make_folder(arg["folder"], arg["participant"])
    session = _get_number(folder)

    session_folder = _make_folder(
        arg["folder"], arg["participant"], session=str(date.today())
    )
    trial = _get_number(session_folder) + 1

    trial_folder = _make_folder(
        arg["folder"],
        arg["participant"],
        session=str(date.today()),
        trial="T" + str(trial),
    )

    if arg["player_trajectory"]:
        filename = _make_filename(
            str(session), str(trial), arg["scene"], "trajectory"
        )
        header = _make_header(["position", "rotation"], [4, 4])
        _make_csv(trial_folder, filename, header, "player_trajectory")
        print("Created the file " + filename)


def save_data(
    arg: ArgStructure,
    trajectory: list[str] = ["time", "position", "rotation"],
    wheels=wheels,
    session_writers=session_writers,
) -> None:
    """
    Open and append new data line to trajectory and instrumented wheels files.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.
    trajectory
        The different data types related to the trajectory to be saved.
        The default is ["time", "position", "rotation"].

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

    if arg["player_trajectory"]:
        trajectory_file = _make_filename(
            str(session), str(trial), arg["scene"], "trajectory"
        )

        trajectory_data = _get_subset(arg, trajectory)

        if (trajectory_data[trajectory[1]] is not None) or (
            trajectory_data[trajectory[2]] is not None
        ):
            _save_trajectory(
                os.path.join(trial_folder, trajectory_file),
                trajectory_data,
                session_writers["player_trajectory"],
            )

    if arg["instrumented_wheels"]:
        for key, wheel in wheels.items():
            nw = wheel.fetch(clear=True)
            for subkey, ts in nw.items():
                filename = _make_filename(
                    str(session), str(trial), arg["scene"], key + "_" + subkey
                )
                _save_ts(ts, filename, trial_folder)

    if arg["motion_capture"]:
        motion = ot.fetch(clear_buffer=True, transform_data=False)
        for ID, ts in motion.items():
            if len(ID) == 3:
                filename = _make_filename(
                    str(session),
                    str(trial),
                    arg["scene"],
                    "rigidbody_" + ID,
                )
                _save_ts(ts, filename, trial_folder)


def end_log(
    arg: ArgStructure,
) -> None:
    """
    Confirm the end of recording and terminate instrumented wheels streaming.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.

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

    if arg["instrumented_wheels"]:
        _stop_wheels(
            str(session),
            trial_folder,
            str(trial),
            arg["scene"],
            wheels=wheels,
        )

    if arg["motion_capture"]:
        _stop_ot(trial_folder, str(session), str(trial), arg["scene"])

    print("Logging is done for current session: ", trial_folder)
