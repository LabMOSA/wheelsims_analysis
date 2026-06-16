"""
Template for pytest.

Copy this file and change modulename for the module to be tested, then
modify test_functionname and maybe add other test functions.

"""

from datetime import date, datetime

import sys
import os
import time
import shutil
import numpy as np
import pandas as pd
import kineticstoolkit as ktk

sys.path.append(r"D:\Maria_school\Documents\S2026\wheelsims_analysis")
import data_logging

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
    "side": "right",
    "headers": {
        "Analog": ["Channels", "Force", "Moment"],
        "IMU": ["Acc", "Gyro", "Mag"],
        "Encoder": ["Angle"],
        "Power": ["Voltage", "Current", "Power"],
    },
    "columns": {
        "Analog": [7, 4, 4],
        "IMU": [3, 3, 3],
        "Encoder": [1],
        "Power": [1, 1, 1],
    },
}


def test_start_log():
    """Test start_log."""
    data_logging.start_log(arg)

    assert os.path.isdir(
        os.path.join(arg["folder"], arg["participant"])
    ), f"TEST start_trial: Participant folder {arg['participant']} was not created."

    assert os.path.isdir(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    ), f"TEST start_trial: Session folder {str(date.today())} was not created"

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_create_trial():
    """Test create_trial."""
    data_logging.create_trial(arg)

    trial = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"], str(date.today()))
    )

    assert isinstance(
        trial, int
    ), f"TEST create_trial: Trial number {trial} must be an integer."

    assert (
        trial > 0
    ), f"TEST create_trial: Trial number {trial} must be positive."

    trial_folder = os.path.join(
        arg["folder"], arg["participant"], str(date.today()), "T" + str(trial)
    )

    assert os.path.isdir(
        trial_folder
    ), f"TEST create_trial: Trial folder {trial} was not created."

    session = data_logging._get_number(
        os.path.join(arg["folder"], arg["participant"])
    )

    filename = data_logging._make_filename(
        str(session), str(trial), arg["scene"], trajectory["file"]
    )

    assert os.path.isfile(
        os.path.join(trial_folder, filename)
    ), f"TEST create_trial: File {trajectory['file']} does not exist."

    data = pd.read_csv(os.path.join(trial_folder, filename))

    data_header, wheel_columns = data_logging._select_header(
        trajectory["file"]
    )
    assert (
        data_header == trajectory["headers"]
    ), f"TEST create_trial: {trajectory['file']} has  has wrong titles of header columns."
    assert (
        wheel_columns == trajectory["columns"]
    ), f"TEST create_trial: {trajectory['file']} has wrong number of header columns."

    assert list(data.columns) == ["time"] + [
        data_header[i] + "[:," + str(j) + "]"
        for i in range(len(data_header))
        for j in range(trajectory["columns"][i])
    ], f"TEST create_trial: Headers for {trajectory['file']} are missing."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_create_wheels():
    """Test _create_wheels."""
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

    data_logging._create_wheels(
        trial_folder, session, trial, arg["scene"], wheels["side"]
    )

    for file_type in wheels["headers"]:
        filename = data_logging._make_filename(
            str(session),
            str(trial),
            arg["scene"],
            wheels["side"] + "_" + file_type,
        )

        assert os.path.isfile(
            os.path.join(trial_folder, filename)
        ), f"TEST _create_wheels: File {filename} is missing."

        data = pd.read_csv(os.path.join(trial_folder, filename))

        data_header, data_column = data_logging._select_header(file_type)

        assert (
            data_header == wheels["headers"][file_type]
        ), f"TEST _create_wheels: {file_type} has wrong titles of header columns."
        assert (
            data_column == wheels["columns"][file_type]
        ), f"TEST _create_wheels: {file_type} has wrong number of header columns."

        assert list(data.columns) == ["time"] + [
            data_header[i] + "[:," + str(j) + "]"
            for i in range(len(data_header))
            for j in range(data_column[i])
        ], f"TEST _create_wheels: Headers for {file_type} are missing."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_save_wheels():
    """Test _save_wheels."""
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

    wheel_data = ktk.load(os.path.join(arg["folder"], "nextwheel_fetch"))

    data_logging._create_wheels(
        trial_folder, str(session), str(trial), arg["scene"], wheels["side"]
    )

    data_logging._save_wheels(
        wheel_data,
        str(session),
        trial_folder,
        arg["scene"],
        str(trial),
        wheels["side"],
    )

    for file_type in wheels["headers"]:
        filename = data_logging._make_filename(
            str(session),
            str(trial),
            arg["scene"],
            wheels["side"] + "_" + file_type,
        )

        assert os.path.isfile(
            os.path.join(trial_folder, filename)
        ), f"TEST _save_wheels: File {filename} is missing."

        data = pd.read_csv(os.path.join(trial_folder, filename))

        assert sum(wheel_data[file_type].time == data["time"]) == len(
            wheel_data[file_type].time
        ), f"TEST _save_wheels: Wheel data {file_type} is missing timestamps."

        wheel_subset = wheel_data[file_type].data
        for subkey in wheel_subset:
            if len(wheel_subset[subkey].shape) == 1:
                wheel_subset[subkey] = wheel_subset[subkey].reshape(-1, 1)
            assert np.allclose(
                wheel_subset[subkey], data.filter(regex=subkey).values
            ), f"TEST _save_wheels: Wheel data {file_type}-{subkey} was not saved properly to csv."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_save_data():
    """Test save_data."""
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

    filename = data_logging._make_filename(
        str(session), str(trial), arg["scene"], trajectory["file"]
    )

    data = pd.read_csv(os.path.join(trial_folder, filename))

    for col in data.columns:
        if col == "position[:,3]":
            assert (
                data.loc[0][col] == 1.0
            ), "TEST save_data: Static position column holds an incorrect value."
        elif col == "rotation[:,3]":
            assert (
                data.loc[0][col] == 0.0
            ), "TEST save_data: Static rotation column holds an incorrect value."
        elif col == "time":
            assert (
                datetime.fromtimestamp(data.loc[0][col]).date() == date.today()
            ), "TEST save_data: Time column holds a value that did not happen today."
        else:
            assert isinstance(
                data.loc[0][col], float
            ), f"TEST save_data: Col {col} holds a value that is not a float."

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


def test_end_log():
    """Test end_log."""
    data_logging.create_trial(arg)
    data_logging.end_log(arg)

    if os.path.exists(os.path.join(arg["folder"], arg["participant"])):
        shutil.rmtree(os.path.join(arg["folder"], arg["participant"]))


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__])
