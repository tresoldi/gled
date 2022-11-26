#!/usr/bin/env python3

"""
Prepare figures for release.
"""

# Import Python standard libraries
from itertools import chain
from pathlib import Path
import glob
import logging
import subprocess

# Import 3rd-party libraries
from ete3 import Tree
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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


def draw_map(m, scale=0.2):
    # draw a shaded-relief image
    m.shadedrelief(scale=scale)

    # lats and longs are returned as a dictionary
    lats = m.drawparallels(np.linspace(-90, 90, 13))
    lons = m.drawmeridians(np.linspace(-180, 180, 13))

    # keys contain the plt.Line2D instances
    lat_lines = chain(*(tup[1][0] for tup in lats.items()))
    lon_lines = chain(*(tup[1][0] for tup in lons.items()))
    all_lines = chain(lat_lines, lon_lines)

    # cycle through these lines and set the desired style
    for line in all_lines:
        line.set(linestyle="-", alpha=0.3, color="w")


def build_map_plot():
    # Read the data directly from the raw ASJP source
    langfile = Path(__file__).parent / "raw" / "languages.csv"
    gled = pd.read_csv(langfile)
    gled = gled[["Glottocode", "Latitude", "Longitude", "Family"]]
    gled = gled.drop_duplicates()

    # Build map
    fig = plt.figure(figsize=(8, 6), edgecolor="w")
    map = Basemap(
        projection="cyl",
        resolution=None,
        llcrnrlat=-90,
        urcrnrlat=90,
        llcrnrlon=-180,
        urcrnrlon=180,
    )
    # draw_map(map)

    pass


def main():
    """
    Script entry point.
    """

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    releases = sorted(glob.glob(str(Path(__file__).parent.parent / "releases" / "*")))
    RELEASE_PATH = Path(releases[-1])

    build_global_tree_plots(RELEASE_PATH)
    # build_map_plot()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
