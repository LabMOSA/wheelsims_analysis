# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 12:24:34 2026

@author: School
"""

import os
import time
import shutil
import unittest
import pandas as pd
import data_logging
from datetime import date, datetime
from nextwheel.software.python.nextwheel import NextWheel


class TestLogging(unittest.TestCase):
    def setUp(self) -> None:
        self.arg = {
            "folder": os.getcwd(),
            "participant": "unittest",
            "time": "0000000000.000",
            "scene": "scene",
            "player_trajectory": False,
            "instrumented_wheels": True,
            "motion_capture": False,
            "position": "(0,0,0)",
            "rotation": "(0,0,0)",
        }

        self.wheels = {
            "right": NextWheel(),
            # "left": NextWheel(),
        }

        self.IP = {
            "right": "192.168.0.86",
            # "left": ,
        }

        self.wheel_keys = ["Analog", "IMU", "Encoder", "Power"]

        pass

    def get_folders(self):
        folder = os.path.join(self.arg["folder"], self.arg["participant"])

        self.assertTrue(
            os.path.isdir(folder),
            msg=f"Folder missing: {folder}",
        )

        session = data_logging._get_number(folder)

        session_folder = data_logging._make_folder(
            self.arg["folder"],
            self.arg["participant"],
            session=str(date.today()),
        )

        self.assertTrue(
            os.path.isdir(session_folder),
            msg=f"Folder missing: {session_folder}",
        )

        session = data_logging._get_number(session_folder)

        return folder, session, session_folder

    def get_trials(self, folder, session, session_folder):
        trial = data_logging._get_number(session_folder)

        self.assertGreaterEqual(
            trial,
            0,
            msg=f"Trial value {trial} is not greater than 0",
        )
        trial = str(trial)

        trial_folder = os.path.join(
            self.arg["folder"],
            self.arg["participant"],
            str(date.today()),
            "T" + trial,
        )

        self.assertTrue(
            os.path.isdir(trial_folder),
            msg=f"Folder missing: {trial_folder}",
        )
        return trial, trial_folder

    def get_file(self, session, trial, data_type):
        filename = (
            "S"
            + str(session)
            + "_"
            + str(date.today())
            + "_T"
            + trial
            + "_"
            + self.arg["scene"]
            + "_"
            + data_type
            + ".csv"
        )
        return filename

    def test_00_start_log(self):
        print("-----TESTING FUNCTION data_logging.start_log-----")
        data_logging.start_log(self.arg, wheels=self.wheels)

        folder, session, session_folder = self.get_folders()

        if self.arg["instrumented_wheels"]:
            for key in self.wheels.keys():
                self.assertEqual(
                    self.wheels[key].IP,
                    self.IP[key],
                    msg=f"An incorrect IP was assigned to wheel: {key}",
                )

    def test_01_create_trial(self):
        print("-----TESTING FUNCTION data_logging.create_trial-----")
        data_logging.start_log(self.arg, wheels=self.wheels)
        data_logging.create_trial(self.arg, wheels=self.wheels)

        folder, session, session_folder = self.get_folders()
        trial, trial_folder = self.get_trials(folder, session, session_folder)

        if self.arg["player_trajectory"]:
            filename = self.get_file(session, trial, "trajectory")

            self.assertTrue(
                os.path.isfile(os.path.join(trial_folder, filename)),
                msg=f"Trajectory file does not exist: {os.path.join(trial_folder, filename)}",
            )

            trajectory = pd.read_csv(os.path.join(trial_folder, filename))
            trajectory_data = ["position", "rotation"]
            self.assertEqual(
                list(trajectory.columns),
                ["time"]
                + [
                    trajectory_data[i] + "[:," + str(j) + "]"
                    for i in range(len(trajectory_data))
                    for j in range(4)
                ],
                msg=f"File {filename} has the wrong header",
            )

        if self.arg["instrumented_wheels"]:
            for key in self.wheels.keys():
                self.assertTrue(
                    self.wheels[key]._thread_is_running,
                    msg=f"Wheel {key} is not streaming when it should be.",
                )

                for subkey in self.wheel_keys:
                    wheel_file = self.get_file(
                        session, trial, key + "_" + subkey
                    )

                    self.assertTrue(
                        os.path.isfile(os.path.join(trial_folder, wheel_file)),
                        msg=f"File missing: {wheel_file}",
                    )

    def test_02_save_data(self):
        print("-----TESTING FUNCTION data_logging.save_data-----")
        data_logging.start_log(self.arg, wheels=self.wheels)
        data_logging.create_trial(self.arg, wheels=self.wheels)

        for i in range(3):
            time.sleep(4)  # make sure to catch some events
            data_logging.save_data(self.arg, wheels=self.wheels)

        folder, session, session_folder = self.get_folders()
        trial, trial_folder = self.get_trials(folder, session, session_folder)

        if self.arg["player_trajectory"]:
            filename = self.get_file(session, trial, "trajectory")

            self.assertTrue(
                os.path.isfile(os.path.join(trial_folder, filename)),
                msg=f"File {filename} does not exist",
            )

            trajectory = pd.read_csv(os.path.join(trial_folder, filename))

            for col in trajectory.columns:
                if col == "position[:,3]":
                    self.assertEqual(
                        trajectory.loc[0][col],
                        1.0,
                        msg="Column {col} does not contain the value 1.0.",
                    )
                elif col == "rotation[:,3]":
                    self.assertEqual(
                        trajectory.loc[0][col],
                        0.0,
                        msg="Column {col} does not contain the value 0.0.",
                    )
                else:
                    self.assertIsInstance(
                        trajectory.loc[0][col],
                        float,
                        msg="Column {col} does not contain a float.",
                    )

        if self.arg["instrumented_wheels"]:
            for key in self.wheels.keys():
                self.assertTrue(
                    self.wheels[key]._thread_is_running,
                    msg=f"Wheel {key} is not streaming when it should be.",
                )

                for subkey in self.wheel_keys:
                    wheel_file = self.get_file(
                        session, trial, key + "_" + subkey
                    )

                    self.assertTrue(
                        os.path.isfile(os.path.join(trial_folder, wheel_file)),
                        msg=f"File missing: {wheel_file}",
                    )

                    wheel_data = pd.read_csv(
                        os.path.join(trial_folder, wheel_file)
                    )

                    self.assertTrue(
                        len(wheel_data) > 0,
                        msg=f"Wheel data {subkey} was not properly recorded.",
                    )

                    self.assertEqual(
                        datetime.fromtimestamp(wheel_data["time"][0]).date(),
                        date.today(),
                        msg="Wheel data {subkey} logged did not happen today",
                    )

    def test_03_end_log(self):
        print("-----TESTING FUNCTION data_logging.end_log-----")
        data_logging.start_log(self.arg, wheels=self.wheels)
        data_logging.create_trial(self.arg, wheels=self.wheels)

        time.sleep(5)
        data_logging.end_log(self.arg, wheels=self.wheels)

        folder, session, session_folder = self.get_folders()
        trial, trial_folder = self.get_trials(folder, session, session_folder)

        if self.arg["instrumented_wheels"]:
            for key in self.wheels.keys():
                self.assertFalse(
                    self.wheels[key]._thread_is_running,
                    msg=f"Wheel {key} is still streaming when it not should be.",
                )

    def tearDown(self) -> None:
        if os.path.exists(
            os.path.join(self.arg["folder"], self.arg["participant"])
        ):
            shutil.rmtree(
                os.path.join(self.arg["folder"], self.arg["participant"])
            )
        if self.arg["instrumented_wheels"]:
            for key in self.wheels.keys():
                if self.wheels[key]._thread_is_running:
                    self.wheels[key].stop_streaming()


if __name__ == "__main__":
    unittest.main(buffer=True)
