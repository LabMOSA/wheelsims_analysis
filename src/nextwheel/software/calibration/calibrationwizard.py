"""Fonctions to organise the instrumented wheelchair wheel calibration."""

import os
import time

import kineticstoolkit as ktk
import limitedinteraction as li
import numpy as np
import wheelcalibration as wc

import nextwheel


def interface(dialog: str, title: str):
    """
    Use a cute little interface that describe the actions to do.

    Exemple :
        >> dialog = "Make sure the wheel is not moving and click Ok"
        >> title = "Calibration part 1"
        >> interface(dialog, title)

    Parameters
    ----------
    dialog
        The description of the desired action to accomplish.
    title
        The title of the interface.

    Returns
    -------
    None.

    """
    li.button_dialog(
        dialog,
        choices=["OK"],
        title=title,
        icon="light",
    )


def measure(nw: nextwheel.NextWheel, waiting_time: int = 5) -> dict:
    """
    Make a measurement with the NextWheel module.

    Parameters
    ----------
    nw :
        NextWheel object of nextwheel module.
    waiting_time : optional
        The waiting time of a measure in second. The default is 5 sec.

    Returns
    -------
    dict
        The dictionary fetched from the NextWheel.

    """
    li.message(
        "Please wait a few moments.", title="Measuring...", icon="clock"
    )
    nw.start_streaming()
    nw.fetch()
    time.sleep(5)
    nw.stop_streaming()
    li.message("")
    return nw.fetch()


def save_file(data: dict, file_name: str, path: str):
    """
    Save file with Kinetics Toolskit.

    The function doesn't overwrite any file.

    Parameters
    ----------
    data :
        The fectched data from the measure function.
    file_name :
        The file name of the new created file.
    path :
        The path where the file is saved.

    Returns
    -------
    None.

    """
    n_trial = 0
    while os.path.isfile(f"{path}{file_name}{n_trial}"):  # not overwriting
        n_trial += 1
    ktk.save(f"{path}{file_name}{n_trial}", data)


def calibrate_part1(nw: nextwheel.NextWheel, path: str):
    """
    Save two measures to find z-axis on the wheel frame.

    First, the bias is measured with a static measure of the wheel. Since the
    wheel is not moving, the measurement is the bias.

    Second, the wheel is spinning around it's rotation axis (the z-axis in the
    wheel referential). Since the gyroscope measurement is the rotation axis
    with the norm being the angular speed, the normalized gyroscope measure is
    the z-axis in the wheel frame.

    Parameters
    ----------
    nw :
        NextWheel object of nextwheel module.
    path :
        The path where the files are saved.

    Returns
    -------
    None.

    """
    # Measure 1 - Gyro bias measurement
    interface(
        "Make sure the wheel is not moving and click Ok",
        "z-axis calibration - Static trial",
    )
    gyro_bias_measured = measure(nw)
    save_file(gyro_bias_measured, "GyroForBias", path)

    # Measure 2 - Z-axis
    interface(
        "Spin the wheel anticlockwise around the desired z-axis and click OK",
        "z-axis calibration - Dynamic trial",
    )

    z_axis_measured = measure(nw)
    save_file(z_axis_measured, "GyroForZAxis", path)


def calibrate_part2(nw: nextwheel.NextWheel, path: str):
    """
    Save two measures to find the xz-plane in the wheel frame.

    Both measures are the gravity measured by the accelerometer in the desired
    xz-plane in the wheel frame.

    Parameters
    ----------
    nw :
        NextWheel object of nextwheel module.
    path :
        The path where the files are saved.

    Returns
    -------
    None.

    """
    # Measure 1
    interface(
        "Make sure the wheel is not moving and that the x-axis point to the lower part",
        "xz-axis calibration - Static trial 1",
    )
    xz_acc_vector_measured1 = measure(nw)
    save_file(xz_acc_vector_measured1, "AccForXZPlane", path)

    # Measure 2
    interface(
        "Same indication that before, but with an other orientation around y-axis",
        "xz-axis calibration - Static trial 2",
    )

    xz_acc_vector_measured2 = measure(nw)
    save_file(xz_acc_vector_measured2, "AccForXZPlane", path)


def calibrate_part3(nw: nextwheel.NextWheel, path: str):
    """
    Save measure with a known hanging mass on the pushrim.

    The mass and the position of the mass on the push rim (in degree) are
    needed. The degree value is determined with the cylindrical coordinate on
    the wheel frame.

    Parameters
    ----------
    nw :
        NextWheel object of nextwheel module.
    path :
        The path where the files are saved.

    Returns
    -------
    None.

    """
    # Measure 1
    interface("Measure the offset force of the channels", "Offset")
    nw.start_streaming()
    nw.fetch()

    offset_measured = measure(nw)
    offset = np.mean(offset_measured["Analog"]["Force"], axis=0)

    # Measure 2
    mass = float(
        li.input_dialog("What is the mass you add on rim?", icon="question")
    )
    degree = float(
        li.input_dialog("At witch degree on the rim?", icon="question")
    )
    interface(
        "Measure the gravity and forces on rim",
        "Calibration - Force Measurements",
    )
    forces_on_rim_measured = measure(nw)
    forces_on_rim_measured["Mass"] = mass
    forces_on_rim_measured["Degree"] = degree
    forces_on_rim_measured["ForceOffset"] = offset_measured

    forces_on_rim_measured["Analog"]["Force"] -= np.tile(
        offset, (np.shape(forces_on_rim_measured["Analog"]["Force"])[0], 1)
    )

    save_file(
        forces_on_rim_measured,
        "ForcesForCalibrationMatrix",
        path,
    )


def estimate_calibration_matrix(path: str) -> np.array:
    """
    Calculate the calibration matrix with wheelcalibration.py module.

    Estimate the gyroscope bias -> estimate the z-axis -> estimate the frame
    changing matrix (base) -> estimate the accelerometer bias -> estimate the
    calibration matrix with a least square.

    Note : The count variables (count1, count2, count3) are only assuring that
    the newest measure is being used over older measures. It counts the number
    of file with similar name and takes the higher numbers (most recent
    measures). WARNING IF YOU DELETE OR RENAME FILES!

    Parameters
    ----------
    path :
        The path where the files are saved.

    Returns
    -------
    A :
        Calibration matrix.

    """
    Trials = {}
    grav_measured = np.ndarray((1, 3))
    count1 = 0
    count2 = 0
    count3 = 0

    for file_name in os.listdir(path):
        if file_name.startswith("Forces"):
            Trials[file_name] = ktk.load(f"{path}{file_name}")
            grav = -np.mean(Trials[file_name]["IMU"]["Acc"], axis=0)

            grav_measured = np.vstack(
                (
                    grav_measured,
                    grav,
                )
            )

        elif file_name.startswith("GyroForBias"):
            Trials[file_name] = ktk.load(f"{path}{file_name}")
            count1 += 1

        elif file_name.startswith("GyroForZAxis"):
            Trials[file_name] = ktk.load(f"{path}{file_name}")
            count2 += 1

        elif file_name.startswith("AccForXZPlane"):
            Trials[file_name] = ktk.load(f"{path}{file_name}")
            count3 += 1

    # Estimate the gyroscope bias
    Trials["GyroBias"] = wc.estimate_gyro_bias(
        Trials[f"GyroForBias{count1 - 1}"]["IMU"]["Gyro"]
    )

    # Estimate the z-axis

    Trials["Z-Axis"] = wc.get_z_axis(
        Trials["GyroBias"], Trials[f"GyroForZAxis{count2 - 1}"]["IMU"]["Gyro"]
    )

    # Estimate the frame changing matrix
    Trials["Base"] = wc.get_wheel_reference(
        -Trials[f"AccForXZPlane{count3 - 2}"]["IMU"]["Acc"],
        -Trials[f"AccForXZPlane{count3 - 1}"]["IMU"]["Acc"],
        Trials["Z-Axis"],
    )  # estimate the base change matrix

    Trials["AccBias"] = wc.estimate_acc_bias(
        grav_measured[1:, :]
    )  # estimate accelerometer bias

    forces_channels = np.ndarray((1, 6))
    FMs = np.ndarray((1, 6))
    for trial in Trials:
        if trial.startswith("Forces"):
            FM = wc.make_an_estimation_of_forces_moments(
                Trials[trial],
                Trials["AccBias"],
                Trials["Base"],
            )

            # forces = np.mean(Trials[trial]["Analog"]["Force"], axis=0)
            forces = np.median(Trials[trial]["Analog"]["Force"], axis=0)
            forces_channels = np.vstack(
                (
                    forces_channels,
                    forces,
                )
            )

            FMs = np.vstack((FMs, FM))

    A = wc.calculate_calibration_matrix(
        FMs[1:, :], forces_channels[1:, :]
    )  # estimate the calibration matrix in A*forces_channels.T = FMs.T

    return A, Trials


if __name__ == "__main__":
    # nw = nextwheel.NextWheel("192.168.1.155")
    nw = nextwheel.NextWheel("192.168.1.228")

    path = "C:/Users/Nicolas/Documents/NextWheel/calibration/"
    trials_dir = "Trials_Wheel2/"

# %% Part 1 - Z-axis calculated from gyroscope

calibrate_part1(nw, path + trials_dir)

# %% Part 2 - XZ-Plane determined from acc + base change matrix completion

calibrate_part2(nw, path + trials_dir)

# %% Part 3 - More static Force mesures for calibration matrix

calibrate_part3(nw, path + trials_dir)
while not li.button_dialog(
    "Do you want to do another measure ?",
    choices=["Oui", "Non"],
    title="Force Measures for Calibration Matrix",
    icon="gear",
):
    calibrate_part3(nw, path + trials_dir)

# %% Part 4 - Calibration matrix calculation
A, Trials = estimate_calibration_matrix(path + trials_dir)
