import os
from datetime import date
import csv
import glob


def make_folder(data_folder: str, participant: str) -> str:
    """
    Within the folder where all data is saved, creates a sub-folder for current
    participant if it does not exist already.

    Parameters
    ----------
    data_folder : str
        Base folder containing data for all participants.
    participant : str
        Participant identifier number.

    Returns
    -------
    folder : str
        Sub-folder specific to this participant.
    """
    folder = os.path.join(data_folder, participant)
    if not os.path.exists(folder):
        os.makedirs(folder)
    print("Preparing to save onto folder ", folder)
    return folder


def get_session(folder: str) -> str:
    """
    Parses files already in current participant's sub-folder to identify the
    current session number. If no sessions have been recorded for this
    participant, the number is set to 0.

    Parameters
    ----------
    folder : str
        Sub-folder corresponding to current participant.

    Returns
    -------
    session : str
        Current session number.
    """
    # determining which session number to write to (to not over-write data)
    files = glob.glob(os.path.join(folder, "*.csv"))
    if (len(files)) > 0:
        sessions = [
            int(file.split("\\")[-1].split("_")[0].split("S")[1])
            for file in files
        ]
        session = str(max(sessions) + 1)
    else:
        session = "0"
    return session


def make_headers(
    data_to_save: list[bool],
    data_types: list[str] | None = [
        "position",
        "rotation",
        "wheels",
        "motion",
    ],
    data_columns: list[int] | None = [4, 4, 1, 1],
) -> list[list[str]]:
    """
    For the user-selected data types to save from the Godot interface, creates
    a corresponding header for the file.

    Parameters
    ----------
    data_to_save : list of bool
        Selections made through Godot interface for data saving. Each entry
        indicates if the same-index entry in data_types is to be saved or not.
    data_types : list of str, optional
        The different data types that can be selected for saving through the
        Godot interface.
        The default is ["position", "rotation", "wheels", "motion"].
    data_columns : list of int, optional
        For each corresponding entry in data_types, the number of columns to be
        expected for the file to be saved.
        The default is [4, 4, 1, 1].

    Returns
    -------
    headers : List of str
        Headers corresponding to each file in files.
    """
    headers = []
    for i in range(len(data_types)):
        if data_to_save[i] == True:
            headers.append(
                ["time"]
                + [
                    data_types[i] + "[:," + str(j) + "]"
                    for j in range(data_columns[i])
                ]
            )
    return headers


def make_filenames(
    session: str,
    scene: str,
    data_to_save: list[bool],
    data_types: list[str] | None = [
        "position",
        "rotation",
        "wheels",
        "motion",
    ],
) -> list[str]:
    """
    For the user-selected data types to save from the Godot interface, creates
    a corresponding name for the file.

    Parameters
    ----------
    session : str
        Current session number.
    scene : str
        Current playable scene selected (6 options).
    data_to_save : list of bool
        Selections made through Godot interface for data saving. Each entry
        indicates if the same-index entry in data_types is to be saved or not.
    data_types : list of str, optional
        The different data types that can be selected for saving through the
        Godot interface.
        The default is ["position", "rotation", "wheels", "motion"].

    Returns
    -------
    files : List of str
        Names of files to be created.
    """
    files = []
    for i in range(len(data_types)):
        if data_to_save[i] == True:
            files.append(
                "S"
                + session
                + "_"
                + str(date.today())
                + "_"
                + scene
                + "_"
                + data_types[i]
                + ".csv"
            )
    return files


def make_csv(folder: str, filename: str, header: list[str]) -> None:
    """
    Creates a CSV file within a specific folder, with its particular header.

    Parameters
    ----------
    folder : str
        Sub-folder corresponding to current participant.
    filename : str
        Name of file to be created.
    header : str
        Header of file to be created.

    Returns
    -------
    None
    """
    with open(os.path.join(folder, filename), "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)


def create_files(
    arg: dict[str, str, str, bool, bool, bool, bool],
    data_types: list[str] | None = [
        "player_position",
        "player_rotation",
        "instrumented_wheels",
        "motion_capture",
    ],
) -> None:
    """
    Creates empty files where data will be saved during this current session.

    Parameters
    ----------
    arg : dict[str, str, str, bool, bool, bool, bool]
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "scene": str, the current selected playable scene.
            "participant": str, the current participant identifier.
            "player_position": bool, whether to save the player's position.
            "player_rotation": bool, whether to save the player's rotation.
            "instrumented_wheels": bool, whether to save the wheels.
            "motion_capture": bool,  whether to save the motion capture.
    data_types : list of str, optional
        The different data types that can be selected for saving through the
        Godot interface.
        The default is ["player_position", "player_rotation",
                        "instrumented_wheels", "motion_capture"].

    Returns
    -------
    None
    """
    folder = make_folder(arg["folder"], arg["participant"])
    session = get_session(folder)

    data_to_save = [arg[data_types[i]] for i in range(len(data_types))]
    filenames = make_filenames(session, arg["scene"], data_to_save)
    headers = make_headers(data_to_save)

    for i in range(len(filenames)):
        make_csv(folder, filenames[i], headers[i])
        print("Created the file " + filenames[i])


def find_files(
    folder: str, scene: str, participant: str
) -> tuple[list[str], str]:
    """
    SUMMARY.

    Parameters
    ----------
    folder : str
        Folder containing data for all of the participants.
    scene : str
        Selected playable scene for current session.
    participant : str
        Current participant identifier.

    Returns
    -------
    session_files : list of str
        Files pertaining to the current session in-progress.
    session_basename : str
        Common base for all kept files.
    """
    # get latest session only
    if os.path.exists(folder):
        # setting up the data logging folder and participant name
        data_folder = os.path.join(folder, participant)
        files = glob.glob(os.path.join(data_folder, "*.csv"))
        sessions = [
            int(file.split("\\")[-1].split("_")[0].split("S")[1])
            for file in files
        ]
        if len(sessions) > 0:
            session = str(max(sessions))
        else:
            session = "0"
        session_files = glob.glob(
            os.path.join(
                data_folder, "*S" + session + "_" + str(date.today()) + "*.csv"
            )
        )

        session_basename = session_files[0].rsplit("_", 1)[0] + "_"
    else:
        print("The data-saving folder selected does not exist.")
    return session_files, session_basename


def save_file(base: str, timestamp: str, data_type: str, data_values: str) -> None:
    """
    Opens already-created file pertaining to this data type and saves values.

    Parameters
    ----------
    base : str
        Current participant's data sub-folder.
    timestamp : str
        Current timestamp to save.
    data_type : str
        Current data type to save.
    data_values : str
        Current data values to save.

    Returns
    -------
    None
    """
    filename = base + data_type + ".csv"

    data_line = [timestamp] + [x for x in data_values.strip("()").split(",")]

    # add appropriate values for last column
    if data_type == "position":
        data_line.append("1")
    elif data_type == "rotation":
        data_line.append("0")

    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data_line)


def save_data(
    arg: dict[
        str, str, str, str, str or None, str or None, str or None, str or None
    ],
    data_types: list[str] | None = [
        "time",
        "position",
        "rotation",
        "wheels",
        "motion",
    ],
) -> None:
    """
    SUMMARY.

    Parameters
    ----------
    arg : dict[str, str, str, str, str or None, str or None, str or None, str or None]
        Dictionary containing arguments sent through Godot:
            "folder": str, the main folder where all data is saved.
            "scene": str, the current selected playable scene.
            "participant": str, the current participant identifier.
            "time": str, the current Unix timestamp.
            "position": str or None, the position at current timestamp, if saved.
            "rotation": str or None, the rotation at current timestamp, if saved.
            "wheels": str or None, the wheels at current timestamp, if saved.
            "motion": str or None, the motion at current timestamp, if saved.
    data_types : list[str] | None, optional
        Time, and the different data types that can be selected for saving
        through the Godot interface.
        The default is ["time", "position", "rotation", "wheels", "motion"].

    Returns
    -------
    None
    """
    session_files, session_basename = find_files(
        arg["folder"], arg["scene"], arg["participant"]
    )
    data_to_save = {key: arg[key] for key in data_types if key in arg}

    for i in range(len(data_to_save) - 1):
        # only save if data was received
        if (list(data_to_save.values())[i + 1]) is not None:
            save_file(
                session_basename,
                data_to_save["time"],
                list(data_to_save.keys())[i + 1],
                list(data_to_save.values())[i + 1],
            )


if __name__ == "__main__":
    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "scene": "scene",
        "participant": "test",
        "player_position": True,
        "player_rotation": True,
        "instrumented_wheels": False,
        "motion_capture": False,
    }

    create_files(arg)

    arg = {
        "folder": r"D:\Maria_school\Documents\S2026\data",
        "scene": "scene",
        "participant": "test",
        "time": "0000000000.000",
        "position": "(0,0,0)",
        "rotation": "(0,0,0)",
        "wheels": None,
        "motion": None,
    }

    save_data(arg)
