"""
Run the commands related to data logging called from the python bridge.

Data logged includes the player's virtual position in the simulator, as
well as information collected through the instrumented wheels.

"""

import glob
import os
from datetime import date
from pathlib import Path
from typing import Any, TypedDict, cast

import kineticstoolkit as ktk
import numpy as np
import pandas as pd
from nextwheel import NextWheel

import optitrack as ot

# %% Session dictionaries

wheels = {
    "wheels": {
        "right": NextWheel(),
        # "left": NextWheel(),
    },
    "ip_addresses": {
        "right": "192.168.0.86",
        "left": "192.168.0.13",
    },
}


# %% Classes to hold data and arguments


class FileLogger:
    """FileLogger class holds an open file of filename."""

    def __init__(self, filename):
        """Initialize FileLogger object."""
        self.filename = filename
        self.file = None

    def open_log(self) -> None:
        """Open file and create writer object."""
        self.file = open(
            self.filename, "w", encoding="utf-8", buffering=1024 * 1024
        )

    def log_row(self, data_lines: np.ndarray) -> None:
        """
        Log data to self.file.

        Parameters
        ----------
        data_lines :
            Data to append to the file.

        Raises
        ------
        ValueError
            Error is raised when trying to write to a closed file.
        """
        if self.file and not self.file.closed:
            for row in data_lines:
                self.file.write("\t".join(map(str, row)) + "\n")

        else:
            raise ValueError(f"File {self.filename} is closed.")

    def close_log(self) -> None:
        """Close an opened file."""
        if self.file:
            self.file.close()

    def convert_csv(self) -> None:
        """Convert the written file from .txt to .csv."""
        try:
            txt_data = pd.read_csv(self.filename, sep="\t")
            if len(txt_data) > 0:
                txt_data.to_csv(
                    self.filename.split(".txt")[0] + ".csv", index=False
                )
        except:
            print(f"Could not convert {self.filename} to .csv")


session_writers: dict[str, FileLogger] = {}


class FileDetails(TypedDict, total=False):
    """
    Structure of the dictionary containing details about current session/trial.

    participant_folder:
        The current participant folder where data is saved for all sessions.
    session:
        The current session number.
    session_date:
        The current session date.
    session_folder:
        The current participant folder where data is saved for this session.
    trial:
        The current trial number.
    trial_folder:
        The current participant folder where data is saved for this trial.
    """

    participant_folder: str
    session: int
    session_date: str
    session_folder: str
    trial: int
    trial_folder: str


session_details = FileDetails()


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


def _make_filename(
    scene: str,
    data_type: str,
    session_details: FileDetails = session_details,
) -> str:
    """
    Create a filename appropriate for the trajectory data to be saved.

    Parameters
    ----------
    scene :
        Current playable scene selected (out of 6 options).
    data_type :
        The type of data to be saved from Simulator or instrumented wheels.
        Options are:
            Simulator (through Godot): trajectory.
            Optitrack: RigidBody + ID.
            NextWheel: Analog, IMU, Encoder, Power.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    Returns
    -------
    str
        Name of file to be created.

    """
    file = (
        "S"
        + str(session_details["session"])
        + "_"
        + str(session_details["session_date"])
        + "_"
        + "T"
        + str(session_details["trial"])
        + "_"
        + scene
        + "_"
        + data_type
        + ".txt"
    )

    return file


def _make_file(
    filename: str,
    header: list[list[str]],
    filetype: str,
    session_writers: dict[str, FileLogger] = session_writers,
) -> None:
    """
    Create a file of a particular header within specified folder.

    Parameters
    ----------
    filename :
        Name of file to be created.
    header :
        Header of file to be created.
    filetype :
        Type of file to be created, used as key in session_writers.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.

    """
    session_writers[filetype] = FileLogger(filename)
    session_writers[filetype].open_log()
    session_writers[filetype].log_row(np.array(header))


# %% Logging simulator


def _make_header(
    data_headers: list[str],
    data_columns: list[int],
) -> list[list[str]]:
    """
    Create a header appropriate for the type of data to be saved.

    Parameters
    ----------
    data_headers
        The specific column titles to be saved in the file.
        For player_trajectory, the input should be ['position', 'rotation'].
    data_columns
        The number of columns per column title.
        For player_trajectory, the input should be [4, 4].

    Returns
    -------
    list[str]
        Header to be used when creating the CSV file.

    """
    header = [
        ["time"]
        + [
            data_headers[i] + "[:," + str(j) + "]"
            for i in range(len(data_headers))
            for j in range(data_columns[i])
        ]
    ]
    return header


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


def _save_trajectory(
    data_values: dict[str, str],
    session_writers: dict[str, FileLogger] = session_writers,
) -> None:
    """
    Append data to an existing CSV file containing trajectory.

    Parameters
    ----------
    data_values :
        Current data values to save.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.

    """
    data_line = [
        [data_values["time"]]
        + list(data_values["position"].strip("()").split(","))
        + ["1"]
        + list(data_values["rotation"].strip("()").split(","))
        + ["0"]
    ]

    session_writers["player_trajectory"].log_row(np.array(data_line))


# %% Logging TimeSeries


def _save_ts(
    ts: ktk.TimeSeries,
    filetype: str,
    scene: str,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Open and append data to CSV file containing time series data.

    Parameters
    ----------
    ts :
        Newly-fetched data from NextWheel or Optitrack.
    filetype :
        Type of file to be created, used as key in session_writers.
    scene :
        Current scene.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    if len(ts.time) > 0:
        if filetype not in session_writers:
            header = [["time"] + list(ts.to_dataframe().columns)]
            filename = _make_filename(scene, filetype, session_details)
            _make_file(
                os.path.join(str(session_details["trial_folder"]), filename),
                header,
                filetype,
                session_writers,
            )

        data_lines = np.column_stack(
            [
                ts.data[list(ts.data.keys())[i]]
                for i in range(len(list(ts.data.keys())))
            ]
        )

        session_writers[filetype].log_row(
            np.column_stack(
                (
                    ts.time,
                    data_lines,
                )
            )
        )


# %% Stopping devices external to Simulator


def _stop_wheels(
    scene: str,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Stop instrumented wheels streaming and catch final events.

    Parameters
    ----------
    scene :
        Current scene.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    for key, wheel in wheels["wheels"].items():
        wheel.stop_streaming()
        print("Successfully stopped stream from wheel: " + wheel.ip)
        nw = wheel.fetch(clear=True)
        for subkey, ts in nw.items():
            _save_ts(
                ts,
                key + "_" + subkey,
                "instrumented_wheels",
                session_writers,
                session_details,
            )


def _stop_ot(
    scene: str,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
):
    """
    Stop Optitrack streaming and catch final events.

    Parameters
    ----------
    scene:
        Current scene.
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    motion = ot.fetch(clear_buffer=True, transform_data=False)
    ot.stop()
    print("Streaming ended for optitrack.")
    for ID, ts in motion.items():
        if len(ID) == 3:
            _save_ts(
                ts, "rigidbody_" + ID, scene, session_writers, session_details
            )


# %% Public functions


def start_log(
    arg: ArgStructure,
    session_details: FileDetails = session_details,
) -> None:
    """
    Create folders for current (new) session, in which trials will be saved.

    Parameters
    ----------
    arg
        Dictionary containing arguments received from Godot.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    session_details["session_date"] = str(date.today())
    session_details["participant_folder"] = _make_folder(
        arg["folder"], arg["participant"]
    )
    session_details["session_folder"] = _make_folder(
        arg["folder"],
        arg["participant"],
        session=session_details["session_date"],
    )
    session_details["session"] = _get_number(
        session_details["participant_folder"]
    )

    if arg["instrumented_wheels"]:
        for key, wheel in wheels["wheels"].items():
            try:
                wheel.ip = wheels["ip_addresses"][key]
                print(
                    "Successfully established connection to wheel: " + wheel.ip
                )
            except TimeoutError:
                print(
                    "Connection could not be established to wheel: " + wheel.ip
                )


def create_trial(
    arg: ArgStructure,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Create empty files where data will be saved during this current trial.

    Parameters
    ----------
    arg :
        Dictionary containing arguments received from Godot.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    if session_details["session_date"] == None:
        start_log(arg, session_details)

    if arg["instrumented_wheels"]:
        for key, wheel in wheels["wheels"].items():
            wheel.start_streaming()
            print("Streaming started for wheel: ", key, " of IP ", wheel.ip)

    if arg["motion_capture"]:
        ot.start()
        print("Streaming started for Optitrack.")

    session_details["trial"] = (
        _get_number(session_details["session_folder"]) + 1
    )

    session_details["trial_folder"] = _make_folder(
        arg["folder"],
        arg["participant"],
        session=session_details["session_date"],
        trial="T" + str(session_details["trial"]),
    )

    if arg["player_trajectory"]:
        filename = _make_filename(
            arg["scene"],
            "trajectory",
            session_details,
        )

        header = _make_header(["position", "rotation"], [4, 4])
        _make_file(
            os.path.join(session_details["trial_folder"], filename),
            header,
            "player_trajectory",
            session_writers,
        )
        print("Created the file " + filename)


def save_data(
    arg: ArgStructure,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Open and append new data line to trajectory and instrumented wheels files.

    Parameters
    ----------
    arg :
        Dictionary containing arguments received from Godot.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    if session_details["session_date"] == None:
        start_log(arg, session_details)
    if len(session_writers.keys()) == 0:
        create_trial(arg, session_writers, session_details)

    if arg["player_trajectory"]:
        trajectory_data = _get_subset(arg, ["time", "position", "rotation"])

        if (trajectory_data["position"] is not None) or (
            trajectory_data["rotation"] is not None
        ):
            _save_trajectory(
                trajectory_data,
                session_writers,
            )

    if arg["instrumented_wheels"]:
        for key, wheel in wheels["wheels"].items():
            nw = wheel.fetch(clear=True)
            for subkey, ts in nw.items():
                _save_ts(
                    ts,
                    key + "_" + subkey,
                    arg["scene"],
                    session_writers,
                    session_details,
                )

    if arg["motion_capture"]:
        motion = ot.fetch(clear_buffer=True, transform_data=False)
        for ID, ts in motion.items():
            if len(ID) == 3:
                _save_ts(
                    ts,
                    "rigidbody_" + ID,
                    arg["scene"],
                    session_writers,
                    session_details,
                )


def end_trial(
    arg: ArgStructure,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Confirm the end of recording and terminate instrumented wheels streaming.

    Parameters
    ----------
    arg :
        Dictionary containing arguments received from Godot.
    session_writers :
        Dictionary holding all the FileLogger objects for this session.
        The default is session_writers.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    if arg["instrumented_wheels"]:
        _stop_wheels(
            arg["scene"],
            session_writers,
            session_details,
        )

    if arg["motion_capture"]:
        _stop_ot(arg["scene"], session_writers, session_details)

    for _key, writer in session_writers.items():
        writer.close_log()

    session_writers.clear()

    print(
        "Logging is done for current trial: ",
        session_details["trial_folder"],
    )


def end_log(
    arg: ArgStructure,
    session_writers: dict[str, FileLogger] = session_writers,
    session_details: FileDetails = session_details,
) -> None:
    """
    Convert all recorded files from txt to csv.

    Parameters
    ----------
    arg :
        Dictionary containing arguments received from Godot.
    session_details :
        Dictionary holding folder details for current session/trial.
        The default is session_details.

    """
    if len(session_writers) > 0:
        end_trial(arg, session_writers, session_details)

    for i in range(1, session_details["trial"] + 1):
        trial_folder = os.path.join(
            session_details["session_folder"], "T" + str(i)
        )
        files = list(Path(trial_folder).glob("*.txt"))
        for file in files:
            FileLogger(str(file)).convert_csv()
