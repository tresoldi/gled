#!/usr/bin/env python3

"""
This script will make local copies of all the files necessary for building the dataset.

The most important file is a cloned copy of the `asjp` repository, which contains the
ASJP dataset in CLDF format.
"""

# Import standard modules
from pathlib import Path
import logging
import subprocess
from typing import *

ROOT_PATH = Path(__file__).parent


def download_cldf_dataset(url: str, dir_name: str, version: Optional[str] = None):
    """
    Download a CLDF dataset from GitHub by cloning it.
    """

    # Downloading the dataset by externally invoking `git`
    # as long as 1. the dataset is not already present locally, or 2. the
    # commit hash specified in the CSV file is different from the one
    # currently present locally.

    # Get the path to the dataset
    path = ROOT_PATH / dir_name

    # Set a `download` flag to `True` if the dataset is not already
    # present locally, or if the commit hash specified in the CSV
    # file is different from the one currently present locally.
    download = False
    if not path.exists():
        download = True
    elif version:
        # Obtain the local commit hash with `git rev-parse HEAD` and
        # compare it with the one specified in the CSV file
        logging.info(f"Checking {dir_name} local commit hash")
        commit = (
            subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True)
            .stdout.decode("utf-8")
            .strip()
        )
        if commit != version:
            logging.info(f"Updating {dir_name}")
            download = True

    # If the `download` flag is set, download the dataset, deleting
    # the existing one if it is already present locally (which will
    # happen if the `--force` flag is set or if the commit hash
    # specified in the CSV file is different from the one currently
    # present locally).
    if download:
        logging.info(f"Downloading {dir_name}")
        if path.exists():
            subprocess.run(["rm", "-rf", str(path)])
        subprocess.run(
            [
                "git",
                "clone",
                url,
                str(path),
            ]
        )

        # If a commit hash is specified in the CSV file, perform a hard
        # reset to that commit
        if version:
            logging.info(f"Checking out {dir_name} commit {version}")
            subprocess.run(
                ["git", "reset", "--hard", version],
                cwd=path,
            )
    else:
        logging.info(f"Skipping {dir_name} (already present locally)")


def main():
    """
    Main function.
    """

    download_cldf_dataset(
        "https://github.com/lexibank/asjp",
        "raw",
        "f0f1d0d43917eb432f838359e14e313c7ff808e4",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
