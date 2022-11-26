#!/usr/bin/env python3

"""
Prepare figures for release.
"""

# Import Python standard libraries
from pathlib import Path
import glob
import logging
import subprocess

# Import 3rd-party libraries
from ete3 import Tree


def build_global_tree_plots(RELEASE_PATH):
    logging.info(
        "Generate the tree with iTol, SVG, font 2px, no leaf sorting, no treescale box"
    )
    logging.info("https://doi.org/10.1093/nar/gkab301")
    logging.info("Converting with Inkscape")

    input = str(RELEASE_PATH / "gled.svg")
    output = str(RELEASE_PATH / "gled.png")
    output_small = str(RELEASE_PATH / "gled_small.png")
    for dpi, outfile in [(1800, output), (300, output_small)]:
        subprocess.run(
            [
                "inkscape",
                "-d",
                str(dpi),
                "-b",
                "white",
                "-o",
                outfile,
                input,
            ]
        )


def main():
    """
    Script entry point.
    """

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    releases = sorted(glob.glob(str(Path(__file__).parent.parent / "releases" / "*")))
    RELEASE_PATH = Path(releases[-1])

    build_global_tree_plots(RELEASE_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
