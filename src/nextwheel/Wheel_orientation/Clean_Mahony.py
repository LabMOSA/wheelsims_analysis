# Imports

import matplotlib.pyplot as plt  # tested with version 3.8.4
import numpy as np  # tested with version 1.26.4
from scipy.spatial.transform import Rotation as R  # tested with 1.13.0

from nextwheel import read_dat


# %%
def q2R(q: np.ndarray, version: int = 1) -> np.ndarray:
    """Convert quaternions to matrix."""
    return np.array(
        [
            [
                1.0 - 2.0 * (q[2] ** 2 + q[3] ** 2),
                2.0 * (q[1] * q[2] - q[0] * q[3]),
                2.0 * (q[1] * q[3] + q[0] * q[2]),
            ],
            [
                2.0 * (q[1] * q[2] + q[0] * q[3]),
                1.0 - 2.0 * (q[1] ** 2 + q[3] ** 2),
                2.0 * (q[2] * q[3] - q[0] * q[1]),
            ],
            [
                2.0 * (q[1] * q[3] - q[0] * q[2]),
                2.0 * (q[0] * q[1] + q[2] * q[3]),
                1.0 - 2.0 * (q[1] ** 2 + q[2] ** 2),
            ],
        ]
    )


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
    # Note : To be coherent, there is some work that is done here to have a
    # unique quaternion (seem to have better result without magnetometer)
    ux = np.cross(ug0, [0, 0, 1])
    ux = ux / np.linalg.norm(ux)
    uy = np.cross(ux, ug0)
    uy = -uy / np.linalg.norm(uy)

    matrix1 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    matrix2 = np.vstack((ux, uy, ug0))

    R0 = np.linalg.solve(matrix1, matrix2)
    R1 = R.from_matrix(R0)
    q0 = R1.as_quat()
    qw = 1 * q0[-1]
    q0[1:] = q0[:-1]
    q0[0] = qw

    acc = -1 * dynamic_trial["IMU"]["Acc"]

    gyro = 1 * dynamic_trial["IMU"]["Gyro"] / 180 * np.pi
    gyro_bias = np.mean(gyro[initial:start, :], axis=0)
    gyro = gyro - gyro_bias

    Q = np.zeros((len(acc[start:]) + 1, 4))
    Q[0] = q0

    return acc, gyro, encoder_datas, ug0, q0, Q


def estimate_linear_acc(
    g, Q0, Q, ang_speed0, ang_speed1, diameter_wheel=0.6096
):
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

    direction0 = direction0 - np.dot(direction0, gw) * gw
    direction0 = direction0 / np.linalg.norm(direction0)

    linear_speed0 = ang_speed0[2] * direction0 * diameter_wheel / 2
    linear_speed1 = ang_speed1[2] * direction1 * diameter_wheel / 2

    estimated_acc = (linear_speed1 - linear_speed0) / dt

    return -1.0 * estimated_acc  # the 1.0 can be reduce to "trim" the lin_acc


def adjust_mahony(
    acc,
    gyro,
    Q,
    k_I=0.3,
    k_P=1.0,
    version=0,
):
    """
    Use Mahony filter to estimate the orientation with an accelerometer and an
    gyroscope (IMU; could also work with a magnetometer with minor changes).

    Parameters
    ----------
    acc : np.array
        Array of the trial's acceleration (From IMU).
    gyro : np.array
        Array of the trial's angular velocity (From IMU).
    Q : np.array
        Array of quaternion orientation history.
    k_I : float, optional
        Integral filter gain. The default from the article is 0.3.
    k_P : float, optional
        Proportional filter gain. The default from the article is 1.0.
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
    gm = [ug0]
    b2 = np.array([0, 0, 0])
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
                Q[i - 1],
                Q[i - 1] + dt * q_Dot,
                gyro[n - 1],
                ang_speed,
            )

            if version == 2:
                accn = acc[n] - linear_acc

            else:
                accn = acc[n] - acc_IMU - linear_acc

        if np.linalg.norm(gyro[n]) > 0:
            a_norm = np.linalg.norm(accn)

            if a_norm > 0:
                accn = accn / a_norm

                R = q2R(Q[i - 1])

                v_a = R.T @ np.array([0, 0, 1])

                v_x_mes = np.cross(accn, [0, 0, 1])
                v_x_mes = v_x_mes / np.linalg.norm(v_x_mes)
                v_x = R.T @ [1, 0, 0]

                v_y_mes = np.cross(v_x_mes, accn)
                v_y_mes = -v_y_mes / np.linalg.norm(v_y_mes)
                v_y = R.T @ [0, 1, 0]

                omega_mes2 = (
                    0.80 * np.cross(accn, v_a)
                    + 0.10 * np.cross(v_x_mes, v_x)
                    + 0.10 * np.cross(v_y_mes, v_y)
                )
                # omega_mes2 = np.cross(accn, v_a)
                bDot2 = -k_I * omega_mes2
                b2 = b2 + dt * bDot2
                omega2 = gyro[n] - b2 + k_P * (omega_mes2)
                p2 = np.append(0, omega2)
                qDot2 = 0.5 * q_mult(Q[i - 1], p2)
                Q[i] = Q[i - 1] + dt * qDot2

                Q[i] = Q[i] / np.linalg.norm(Q[i])

        else:
            Q[i] = Q[i - 1]

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
RMSE_Mahony = {}
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
# %% mahony normal
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_mahony(acc, gyro, QM)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
axs[0].plot(diff, label=f"Normal Mahony (RMSE = {RMSE})")
axs[0].legend()
RMSE_Mahony["Normal mahony"] = RMSE

# %% mahony minus angular acceleration from wheel
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_mahony(acc, gyro, QM, version=1)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
axs[1].plot(diff, label=f"Adjust mahony 1 (RMSE = {RMSE})")
axs[1].legend()
RMSE_Mahony["Adjust mahony 1"] = RMSE

# %% mahony minus linear acceleration (estimation)
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_mahony(acc, gyro, QM, version=2)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
axs[2].plot(diff, label=f"Adjust mahony 2 (RMSE = {RMSE})")
axs[2].legend()
RMSE_Mahony["Adjust mahony 2"] = RMSE

# %% mahony minus acceleration (estimation)
acc, gyro, encoder_datas, ug0, q0, QM = init(
    dynamic_trial, initial=initial, start=start
)

gm, z_angles, QM = adjust_mahony(acc, gyro, QM, version=3)

diff = encoder_datas[start:] - z_angles
RMSE = ((sum(diff**2)) / len(z_angles)) ** 0.5
axs[3].plot(diff, label=f"Adjust mahony 3 (RMSE = {RMSE})")
axs[3].legend()
RMSE_Mahony["Adjust mahony 3"] = RMSE


# %%
# plt.plot(np.zeros((len(diff), 1)))
# plt.plot(5 * np.ones((len(diff), 1)))
# plt.plot(-5 * np.ones((len(diff), 1)))
