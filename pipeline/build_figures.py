#!/usr/bin/env python3

"""
Prepare figures for release.
"""

# Import Python standard libraries
import logging
from pathlib import Path
import glob


def main():
    """
    Script entry point.
    """

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    releases = sorted(glob.glob(str(Path(__file__).parent.parent / "releases" / "*")))
    RELEASE_PATH = Path(releases[-1])

    print(RELEASE_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
