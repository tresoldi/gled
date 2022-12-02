#!/usr/bin/env python3

"""
Collect data for the WOGEL presentation.
"""

# Import Python standard libraries
from pathlib import Path
import logging
import re
import glob
import random
import itertools

# Import other modules
import common

BASE_PATH = Path(__file__).parent.parent


def read_matrix(filename):
    # Read raw data
    header = True
    taxa = []
    matrix = {}
    with open(filename, encoding="utf-8") as handler:
        for line in handler.readlines():
            if header:
                header = False
            else:
                line = re.sub(r"\s+", " ", line)
                tokens = line.split()
                taxon = tokens[0]
                taxa.append(taxon)
                dists = [float(dist) for dist in tokens[1:]]
                matrix[taxon] = dists

    # Make an actual dictionary matrix
    ret_matrix = {}
    for taxon_a, dists in matrix.items():
        ret_matrix[taxon_a] = {taxon_b: dist for dist, taxon_b in zip(dists, taxa)}

    return ret_matrix


def language_sample(matrix, k, method="mean", tries=100):
    # Extract doculects
    lects = sorted(matrix.keys())

    # Run different attempts to get a good sample
    sample_sum = []
    sample_mean = []
    for i in range(tries):
        # Get a sample, compute the total and mean distances, and store
        sampled_lects = tuple(random.sample(lects, k))
        dists = []
        for lang1, lang2 in itertools.combinations(sampled_lects, 2):
            dists.append(matrix[lang1][lang2])

        # Store results
        sample_sum.append((sampled_lects, sum(dists)))
        sample_mean.append((sampled_lects, sum(dists) / k))

    # Sort and return
    if method == "mean":
        ret = sorted(sample_mean, reverse=True, key=lambda e: e[1])
    elif method == "sum":
        ret = sorted(sample_sum, reverse=True, key=lambda e: e[1])

    return ret[0][0]


def main():
    """
    Script entry point.
    """

    # Instantiate `glottolog` object and cache languoids
    logging.info("Caching Glottolog languoids...")
    glottolog = common.get_glottolog()
    languoids = {}
    for lang in glottolog.languoids():
        languoids[lang.glottocode] = lang
    logging.info(f"Cached {len(languoids)} languoids.")

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    releases = sorted(glob.glob(str(BASE_PATH / "releases" / "*")))
    RELEASE_PATH = Path(releases[-1])

    # Collect all NJ matrix distances
    pattern = RELEASE_PATH / "phylo" / "*.dst"
    nj_dist = {}
    for dst_file in glob.glob(str(pattern)):
        logging.info(f"Reading NJ dist file `{dst_file}`...")
        family = Path(dst_file).stem
        nj_dist[family] = read_matrix(dst_file)

    # Collect distances from the Bayesian tree
    logging.info("Reading global Bayes distance")
    bayes_dist = read_matrix(RELEASE_PATH / "global.dst")

    # Get world samples
    for i in range(5):
        world = language_sample(bayes_dist, 5)
        print(world)

    # Filter indo european for experiment
    print(languoids["swed1254"].family)
    ie_langs = [
        glottocode
        for glottocode in bayes_dist
        if languoids[glottocode].family == "Indo-European"
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
