# Imports

import matplotlib.pyplot as plt  # tested with version 3.8.4
import numpy as np  # tested with version 1.26.4
from ahrs.filters import Madgwick  # tested with version 0.3.1

from nextwheel import read_dat


# %%
def adjust_angle(acc_x, acc_y):
    """
    Adjust the angle of the IMU orientation result to compare it with the
    encoder. The compared angle is obtain with the arctan of the ratio of
    acceleration of the estimated gravity y and x.

    Parameters
    ----------
    acc_x : np.float
        x component of the gravity estimated with the estimator (IMU).
    acc_y : np.float
        y component of the gravity estimated with the estimator (IMU).

    Returns
    -------
    theta : np.float
        Orientation around the z-axis of the wheel. The value is not bound
        to make it comparable with the encoder.

    """
    theta = np.arctan2(acc_y, acc_x)

    for i in range(1, len(theta)):
        if theta[i] - theta[i - 1] > 3:
            theta[i:] -= 2 * np.pi

        elif theta[i] - theta[i - 1] < -3:
            theta[i:] += 2 * np.pi

    return theta


def q_mult(q1, q2):
    """
    Quaternion multiplication.

    Convention is [w, x, y, z]. WARNING : Order is important.

    Parameters
    ----------
    q1 : np.array
        Quaternion to be multiplied.
    q2 : np.array
        Quaternion to be multiplied.

    Returns
    -------
    np.array
        The result quaternion.

    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 + y1 * w2 + z1 * x2 - x1 * z2
    z = w1 * z2 + z1 * w2 + x1 * y2 - y1 * x2
    return np.array([w, x, y, z])


def q_rot(x, q):
    """
    Apply rotation with quaternion q to vector x.

    Parameters
    ----------
    x : np.array
        Normal vector with three components.
    q : np.array
        Rotation quaternion.

    Returns
    -------
    x : np.array
        New quaternion (WARNING : four components).

    """
    qc = 1 * q
    qc[1:] = -qc[1:]

    x = q_mult(q, np.append(0, x))
    x = q_mult(x, qc)
    return x


def init(
    dynamic_trial,
    encoder_variation=0.087890625,
    initial=0,
    start=50,
):
    """
    Initialize variables for estimation.

    Parameters
    ----------
    dynamic_trial : dict
        Dictionary from the dat file.
    encoder_variation : float, optional
        The equivalent of one click in degree of the encoder. The default
        is 0.087890625.
    initial : int, optional
        Must correspond to the intial index of a static sampling for the first
        orientation measure. The default is 0.
    start : int, optional
        Must correspond to the start index of the estimation. It is also the
        last index of the static sampling. The default is 50.

    Returns
    -------
    acc : np.array
        Array of the trial's acceleration (From IMU).
    gyro : np.array
        Array of the trial's angular velocity (From IMU).
    encoder_datas : np.array
        Array of the trial's orientation (From encoder).
    ug0 : np.array
        Unit vector of the initial gravity (found in the [initial, start]
                                            interval).
    q0 : np.array
        Initial quaternion for orientation.
    Q : np.array
        Array of quaternion orientation history.

    """
    encoder_datas = dynamic_trial["Encoder"]["Angle"] * encoder_variation
    encoder_datas = encoder_datas - encoder_datas[start]
    encoder_datas = np.interp(
        time, dynamic_trial["Encoder"]["Time"], encoder_datas
    )

    acc = -1 * dynamic_trial["IMU"]["Acc"]

    g0 = np.mean(acc[initial:start, :], axis=0)
    ug0 = g0 / np.linalg.norm(g0)
    q0 = np.cross(ug0, [0, 0, 1])
    q0 = np.append(1 + (np.dot(ug0, [0, 0, 1])), q0)
    q0 = q0 / np.linalg.norm(q0)

    q = np.zeros((len(acc[start:]) + 1, 4))
    q[0] = q0

    acc = -1 * dynamic_trial["IMU"]["Acc"]

    gyro = 1 * dynamic_trial["IMU"]["Gyro"] / 180 * np.pi
    gyro_bias = np.mean(gyro[initial:start, :], axis=0)
    gyro = gyro - gyro_bias

    Q = np.zeros((len(acc[start:]) + 1, 4))
    Q[0] = q0

    return acc, gyro, encoder_datas, ug0, q0, Q


def estimate_linear_acc(g, Q, ang_speed0, ang_speed1, diameter_wheel=0.6096):
    """
    Estimate the linear speed of the wheelchair with the last estimate of the
    gravity, the last angular speed and the present angular speed.

    Parameters
    ----------
    g : np.array
        The last estimate of the gravity.
    Q : np.array
        Next quaternion estimated using only angular speed.
    ang_speed0 : np.array
        The previous angular speed (index n-1).
    ang_speed1 : np.array
        The present angular speed (index n).
    diameter_wheel : float, optional
        Diameter of the wheel. The default is 0.6096.

    Returns
    -------
    np.array
        Linear speed estimation.

    """
    direction0 = np.cross(g, [0, 0, 1])
    direction0 = direction0 / np.linalg.norm(direction0)

    ang_norm = np.linalg.norm(ang_speed1)

    dq = np.append(
        np.cos(ang_norm * dt / 2),
        -ang_speed1 * np.sin(ang_norm * dt / 2) / ang_norm,
    )
    direction0 = q_rot(direction0, dq)[1:]

    QC = 1 * Q
    QC[1:] = -QC[1:]
    gw = q_rot([0, 0, 1], QC)[1:]
    gw = gw / np.linalg.norm(gw)
    direction1 = np.cross(gw, [0, 0, 1])
    direction1 = direction1 / np.linalg.norm(direction1)

    direction0 = direction0 / np.linalg.norm(direction0)

    linear_speed0 = ang_speed0[2] * direction0 * diameter_wheel / 2
    linear_speed1 = ang_speed1[2] * direction1 * diameter_wheel / 2

    estimated_acc = (linear_speed1 - linear_speed0) / dt

    return -1.0 * estimated_acc  # the 1.0 can be reduce to "trim" the lin_acc


def adjust_madgwick(acc, gyro, Q, gain=0.033, version=0):
    """
    Use Madgwick filter to estimate the orientation with an accelerometer and
    an gyroscope (IMU; could also work with a magnetometer with minor changes).

    Parameters
    ----------
    acc : np.array
        Array of the trial's acceleration (From IMU).
    gyro : np.array
        Array of the trial's angular velocity (From IMU).
    Q : np.array
        Array of quaternion orientation history.
    gain : float, optional
        Weight between angular speed and acceleration. The default from the
        article is 0.033.
    version : int, optional
        Change the version to transform the acceleration:
            0 - Acceleration is taken as measure
            1 - Angular acceleration of the speed is substract
            2 - Linear acceleration is substract (New)
            3 - Both angular and linear acceleration are substract (New)
        The default is 0.

    Returns
    -------
    gm : np.array
        Array of all the gravity estimated.
    z_angles : np.array
        Angles to be compared directly compared with the encoder data.
    Q : np.array
        Rotation quaternion that represent the orientation.

    """
    madgwick = Madgwick(Dt=dt, gain=gain)
    gm = [ug0]

    for n in range(start, len(acc)):
        i = n - start + 1
        ang_speed = gyro[n]
        acc_IMU = -r_IMU * sum(ang_speed**2)

        if version == 0:
            accn = acc[n]

        elif version == 1:
            accn = acc[n] - acc_IMU

        elif version == 2 or version == 3:
            q_Dot = 0.5 * q_mult(Q[i - 1], np.append(0, ang_speed))
            linear_acc = estimate_linear_acc(
                gm[i - 1],
                Q[i - 1] + dt * q_Dot,
                gyro[n - 1],
                ang_speed,
            )

            if version == 2:
                accn = acc[n] - linear_acc

            else:
                accn = acc[n] - acc_IMU - linear_acc

        Q[i] = madgwick.updateIMU(
            Q[i - 1],
            gyr=ang_speed,
            acc=accn,
        )
        QC = 1 * Q[i]
        QC[1:] = -QC[1:]

        gm.append(q_rot([0, 0, 1], QC)[1:])

    gm = np.array(gm[1:])
    z_angles = adjust_angle(gm[:, 0], gm[:, 1]) * 180 / np.pi
    z_angles = z_angles - z_angles[0]

    return gm, z_angles, Q


# %% Constants
r_IMU = np.array([-0.0220, 0.0464, -0.000])  # Wheel center position

# -----------------------------.dat file to read here -----------------------
dynamic_trial = read_dat("exemples/LPATH2.dat")


time = dynamic_trial["IMU"]["Time"]

dt = (time[-1] - time[0]) / len(time)
dt = 1 / 60

initial = 650
start = 780
RMSE_Madgwick = {}
fig, axs = plt.subplots(4)
plt.xlabel("Iteration (fz = 60 Hz)")

for ax in axs.flat:
    ax.set(xlabel="Iteration (fs = 60 Hz)", ylabel="Error (degree)")

axs[0].plot(np.zeros((len(time[start:]), 1)))
axs[1].plot(np.zeros((len(time[start:]), 1)))
axs[2].plot(np.zeros((len(time[start:]), 1)))
axs[3].plot(np.zeros((len(time[start:]), 1)))

axs[0].plot(4 * np.ones((len(time[start:]), 1)), "--k")
axs[1].plot(4 * np.ones((len(time[start:]), 1)), "--k")
axs[2].plot(4 * np.ones((len(time[start:]), 1)), "--k")
axs[3].plot(4 * np.ones((len(time[start:]), 1)), "--k")

axs[0].plot(-4 * np.ones((len(time[start:]), 1)), "--k")
axs[1].plot(-4 * np.ones((len(time[start:]), 1)), "--k")
axs[2].plot(-4 * np.ones((len(time[start:]), 1)), "--k")
axs[3].plot(-4 * np.ones((len(time[start:]), 1)), "--k")

# %% Madgwick normal
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_madgwick(acc, gyro, QM)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
RMSE_Madgwick["Normal Madgwick"] = RMSE
axs[0].plot(diff, label=f"Normal Madgwick (RMSE = {RMSE})")
axs[0].legend()


# %% Madgwick minus angular acceleration from wheel
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_madgwick(acc, gyro, QM, version=1)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
RMSE_Madgwick["Adjust Madgwick 1"] = RMSE
axs[1].plot(diff, label=f"Adjust Madgwick 1 (RMSE = {RMSE})")
axs[1].legend()

# %% Madgwick minus linear acceleration (estimation)
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_madgwick(acc, gyro, QM, version=2)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
RMSE_Madgwick["Adjust Madgwick 2"] = RMSE
axs[2].plot(diff, label=f"Adjust Madgwick 2 (RMSE = {RMSE})")
axs[2].legend()

# %% Madgwick minus acceleration (estimation)
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_madgwick(acc, gyro, QM, version=3)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
RMSE_Madgwick["Adjust Madgwick 3"] = RMSE
axs[3].plot(diff, label=f"Adjust Madgwick 3 (RMSE = {RMSE})")
axs[3].legend()

# %% Searching the optimal gain each time
# acc, gyro, encoder_datas, ug0, q0, QM = init(
#     dynamic_trial, initial=initial, start=start
# )

# gm, z_angles, QM = adjust_madgwick(
#     acc, gyro, QM, version=4, encoder_datas=encoder_datas
# )

# diff = encoder_datas[start:] - z_angles
# plt.plot(diff)
# RMSE_Madgwick["Adjust Madgwick 4"] = ((sum(diff**2)) / len(z_angles)) ** 0.5
# %%
# plt.plot(np.zeros((len(diff), 1)))
# plt.plot(5 * np.ones((len(diff), 1)))
# plt.plot(-5 * np.ones((len(diff), 1)))
