#!/usr/bin/env python
"""Check code quality before creating a code request."""

import subprocess
import webbrowser
import os


def run_style_formatter() -> None:  # pragma: no cover
    """Run style formatter (black)."""
    print("========================================")
    print("Reformatting to black and numpydoc")
    print("Running black...")
    subprocess.call(["black", "."])
    print("Running docformatter...")
    subprocess.call(
        [
            "docformatter",
            "--style=numpy",
            "--in-place",
            "--recursive",
            "--pre-summary-newline",
            "--blank",
            ".",
        ]
    )


def run_static_type_checker() -> None:  # pragma: no cover
    """Run static typing checker (mypy)."""
    print("========================================")
    print("Checking Static Types (mypy)")
    subprocess.call(["mypy", "."])


def run_pylint() -> None:  # pragma: no cover
    """Run code quality review (pylint)."""
    print("========================================")
    print("Code Quality Review (pylint)")
    subprocess.call(["pylint", "."])


def run_unit_tests() -> None:  # pragma: no cover
    """Run all unit tests."""
    print("========================================")
    print("Running Unit Tests (coverage/pytest)")
    subprocess.call(
        [
            "coverage",
            "run",
            "--source",
            ".",
            "-m",
            "pytest",
        ]
    )
    subprocess.call(["coverage", "html"])
    webbrowser.open_new_tab("file://" + os.path.abspath("htmlcov/index.html"))


if __name__ == "__main__":  # pragma: no cover
    run_style_formatter()
    run_static_type_checker()
    run_pylint()
    run_unit_tests()
    print("Completed.")
    print(
        "Do not forget to merge main into your branch and run these checks again."
    )
