"""
Template for pytest.

Copy this file and change modulename for the module to be tested, then
modify test_functionname and maybe add other test functions.

"""

import os
import sys

sys.path.append(os.path.dirname(os.getcwd()))

import shutil
import time
from datetime import date, datetime

import kineticstoolkit as ktk
import numpy as np
import pandas as pd

from src import data_logging

arg = {
    "folder": os.getcwd(),
    "participant": "unittest",
    "time": str(time.time()),
    "scene": "scene",
    "player_trajectory": True,
    "instrumented_wheels": False,
    "motion_capture": False,
    "position": "(0,0,0)",
    "rotation": "(0,0,0)",
}

trajectory = {
    "file": "trajectory",
    "headers": ["position", "rotation"],
    "columns": [4, 4],
}

wheels = {
    "file": "right",
    "headers": ["Analog", "IMU", "Encoder", "Power"],
    "sample": "nextwheel_fetch.ktk.zip",
    "data": None,
}

motion = {
    "file": "rigidbody",
    "headers": ["102", "201", "202"],
    "sample": "optitrack_fetch.ktk.zip",
    "data": None,
}


# %% Initiation


def test_start_log():
    """
    Test start_log.

    Asserts folders were created for the test participant and today's session.

    """
    data_logging.start_log(arg)

    assert os.path.isdir(os.path.join(arg["folder"], arg["participant"])), (
        f"TEST start_trial: Folder {arg['participant']} was not created."
    )

    assert os.path.isdir(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    ), f"TEST start_trial: Session folder {str(date.today())} was not created"

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


# %% Ending


def test_end_log():
    """
    Test end_log.

    Does not assert anything, but tests proper functioning (without crashing).
    """
    data_logging.start_log(arg)
    data_logging.create_trial(arg)
    data_logging.end_log(arg)

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


# %% New trial


def test_create_trial():
    """
    Test create_trial.

    Asserts that a new trial was initiated, and that the appropriate CSV file
    was created (to save the player trajectory).
    """
    data_logging.start_log(arg)
    data_logging.create_trial(arg)

    trial = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )

    assert isinstance(trial, int), (
        f"TEST create_trial: Trial number {trial} must be an integer."
    )

    assert trial > 0, (
        f"TEST create_trial: Trial number {trial} must be positive."
    )

    trial_folder = os.path.join(
        arg["folder"], arg["participant"], str(date.today()), "T" + str(trial)
    )

    assert os.path.isdir(trial_folder), (
        f"TEST create_trial: Trial folder {trial} was not created."
    )

    session = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"])
    )

    filename = data_logging._make_filename(
        str(session), str(trial), arg["scene"], trajectory["file"]
    )

    assert os.path.isfile(os.path.join(trial_folder, filename)), (
        f"TEST create_trial: File {trajectory['file']} does not exist."
    )

    data_logging.end_log(arg)
    data = pd.read_csv(os.path.join(trial_folder, filename))

    assert list(data.columns) == ["time"] + [
        trajectory["headers"][i] + "[:," + str(j) + "]"
        for i in range(len(trajectory["headers"]))
        for j in range(trajectory["columns"][i])
    ], f"TEST create_trial: Headers for {trajectory['file']} are incorrect."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


# %% Saving


def test_save_data():
    """
    Test save_data.

    Assert that sample data for the player trajectory is properly saved, with
    the correct date.
    """
    data_logging.start_log(arg)
    data_logging.create_trial(arg)

    trial = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )

    trial_folder = os.path.join(
        arg["folder"], arg["participant"], str(date.today()), "T" + str(trial)
    )

    session = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"])
    )

    data_logging.save_data(arg)
    data_logging.end_log(arg)

    filename = data_logging._make_filename(
        str(session), str(trial), arg["scene"], trajectory["file"]
    )

    data = pd.read_csv(os.path.join(trial_folder, filename))

    for col in data.columns:
        if col == "position[:,3]":
            assert data.loc[0][col] == 1.0, (
                "TEST save_data: Third position column should hold value 1.0."
            )
        elif col == "rotation[:,3]":
            assert data.loc[0][col] == 0.0, (
                "TEST save_data: Third rotation column should hold value 0.0."
            )
        elif col == "time":
            assert (
                datetime.fromtimestamp(data.loc[0][col]).date() == date.today()
            ), "TEST save_data: Time column holds a value that are not today."
        else:
            assert isinstance(data.loc[0][col], float), (
                f"TEST save_data: Col {col} holds a value that is not a float."
            )

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_save_ts():
    """
    Test _save_ts for NextWheels and for Optitrack.

    Asserts that sample data from the instrumented wheels is properly saved,
    with the correct date.
    """
    data_logging.start_log(arg)
    data_logging.create_trial(arg)

    trial = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )

    trial_folder = os.path.join(
        arg["folder"], arg["participant"], str(date.today()), "T" + str(trial)
    )

    session = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"])
    )

    samples = [wheels, motion]
    for sample in samples:
        if arg["folder"].split("\\")[-1] == "tests":
            sample["data"] = ktk.load(
                os.path.join(arg["folder"], "data", sample["sample"])
            )
        else:
            sample["data"] = ktk.load(
                os.path.join(arg["folder"], "tests", "data", sample["sample"])
            )

        for file_type in sample["headers"]:
            filename = data_logging._make_filename(
                str(session),
                str(trial),
                arg["scene"],
                wheels["file"] + "_" + file_type,
            )
            data_logging._save_ts(
                sample["data"][file_type],
                os.path.join(trial_folder, filename),
                file_type,
            )

            assert os.path.isfile(os.path.join(trial_folder, filename)), (
                f"TEST _save_ts: File {filename} is missing."
            )

    data_logging.end_log(arg)

    for sample in samples:
        for file_type in sample["headers"]:
            filename = data_logging._make_filename(
                str(session),
                str(trial),
                arg["scene"],
                wheels["file"] + "_" + file_type,
            )
            data = pd.read_csv(os.path.join(trial_folder, filename))

            data_header = list(
                sample["data"][file_type].to_dataframe().columns
            )

            assert list(data.columns)[1:] == data_header, (
                f"TEST _save_ts: Headers for {file_type} are incorrect."
            )

            assert np.allclose(sample["data"][file_type].time, data["time"]), (
                f"TEST _save_ts: Wheel data {file_type} is missing timestamps."
            )

            assert np.allclose(
                sample["data"][file_type].to_dataframe(),
                data.drop(columns="time"),
            ), f"TEST _save_ts: Data {file_type} not saved properly."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__])
