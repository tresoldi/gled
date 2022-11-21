#!/usr/bin/env python3

"""
Run Bayesian analyses and collect results.
"""

# Import Python standard libraries
from pathlib import Path
from collections import defaultdict
import itertools
import glob
import csv
import logging
import re
import subprocess

# Import 3rd party
from ete3 import Tree

# Import other modules
import common

BASE_PATH = Path(__file__).parent

# Define path to executables
BEAST2_PATH = Path("/home/tiagot/software/BEAST.v2.6.7.Linux/beast/bin")

PROBLEMATIC_FAMILIES = ["bookkeeping"]


def run_inference(BAYES_PATH, languoids):

    # Collect all models
    models_pattern = BAYES_PATH / "*.xml"
    for model in glob.glob(str(models_pattern)):
        model_filename = Path(model)
        basename = model_filename.stem
        logging.info(f"Running BEAST2 for {basename}...")

        # Run BEAST2
        subprocess.run(
            [
                str(BEAST2_PATH / "beast"),
                model_filename.name,  # quote names with spaces
            ],
            cwd=BAYES_PATH,
        )

        # Run Treeannotator
        # TODO: move to phyltr?
        beast2_trees = BAYES_PATH / f"{basename}.nex"
        subprocess.run(
            [
                str(BEAST2_PATH / "treeannotator"),
                "-burnin",
                "50",
                "-noSA",
                str(beast2_trees),
                f"{basename}.mcc.nex",
            ],
            cwd=BAYES_PATH,
        )

        # Remove files that are big and not necessary for release
        beast2_trees.unlink()


def extract_tree(nexus):
    """
    Extract a tree from an MCC nexus file.
    """

    in_translate = False
    translate = {}
    basename = Path(nexus).stem
    basename = basename[: basename.find(".")]
    with open(nexus) as handler:
        for line in handler.readlines():
            if "Translate" in line:
                in_translate = True
            elif in_translate:
                if ";" in line:
                    in_translate = False
                else:
                    source, target = line.strip().replace(",", "").split()
                    translate[source] = f"{target}"
            elif "tree TREE1 =" in line:
                tree_line = line.strip()[line.index("(") :]
                tree_line = re.sub(r"\[[^]]+\]", "", tree_line)
                tree = Tree(tree_line)

    # Translate names
    for node in tree.traverse():
        if node.name in translate:
            node.name = translate[node.name]

    return tree


def collect_global_tree(family_distances, BAYES_PATH, OUTPUT_PATH):
    """
    Collect all trees into a single, global tree.
    """

    # Collect all trees and the longest distance
    max_dist = defaultdict(int)
    trees = {}
    for tree_file in glob.glob(str(BAYES_PATH / "*.mcc.nex")):
        # Extract tree, write it to disk, and append to collection
        tree = extract_tree(tree_file)
        tree_name = common.slug(Path(tree_file).stem.split(".")[0], level="full")
        if tree_name in PROBLEMATIC_FAMILIES:
            continue

        with open(OUTPUT_PATH / f"{tree_name}.tree", "w") as handler:
            handler.write(tree.write(format=1))
        trees[tree_name] = tree

        # Get the biggest distance
        dist = max([leaf.get_distance(tree) for leaf in tree.iter_leaves()])
        if max_dist[tree_name] < dist:
            max_dist[tree_name] = dist

    # Rescale the trees in `trees` so that their biggest distance
    # matches the one in `family_distances` (in order to later have
    # all at the same distances from the dummy root)
    for family, tree in trees.items():
        bayes_dist = max_dist[family]
        nj_dist = family_distances[family]
        print(family, bayes_dist, nj_dist)

    # Build global tree
    # TODO: missing isolates
    global_tree = Tree()
    global_max_dist = max(max_dist.values())
    for family, tree in trees.items():
        global_tree.add_child(tree, dist=global_max_dist - max_dist[family])

    return global_tree, trees


def get_distances(family_trees):
    logging.info("Collecting distances from Bayesian trees")

    distances = {}
    for family, tree in family_trees.items():

        # Collect pairwise distances between leaves and deepest leaf instance
        leaves = tree.get_leaves()
        for lang1, lang2 in itertools.combinations_with_replacement(leaves, 2):
            distances[lang1.name, lang2.name] = lang1.get_distance(lang2)

        deepest = 0.0
        for leaf in leaves:
            dist = tree.get_distance(leaf)
            if dist > deepest:
                deepest = dist

        print(family, deepest)

    # for k, v in distances.items():
    #    print(k, v)


def dst2dict(filename):
    """
    Return the contents of a distance matrix files as a dictionary.
    """

    header = True
    taxa = []
    matrix = []
    with open(filename, encoding="utf-8") as handler:
        for line in handler.readlines():
            line = re.sub(r"\s+", " ", line.strip())
            if header:
                header = False
            else:
                tokens = line.split()
                taxa.append(tokens[0])
                matrix.append([float(v) for v in tokens[1:]])

    dst = {}
    for taxon1, row in zip(taxa, matrix):
        for taxon2, value in zip(taxa, row):
            dst[taxon1, taxon2] = value

    return dst


def collect_distances(BAYES_PATH, PHYLO_PATH):
    # Read the glottocode/doculect mapping
    with open(BAYES_PATH / "glottomap.tsv", encoding="utf-8") as handler:
        glottomap = list(csv.DictReader(handler, delimiter="\t"))
        doculects = sorted([entry["Doculect"] for entry in glottomap])

    # Iterate over all distance files -- while we could collect this
    # information while computing it, for code separation it is better
    # to just consider it external
    file_pattern = str(PHYLO_PATH / "*.dst")
    dst = {}
    for dst_file in glob.glob(file_pattern):
        family_name = Path(dst_file).stem
        logging.info(f"Collecting precomputed distance for `{family_name}`")
        family_dst = dst2dict(dst_file)
        family_dst = {
            (lang1, lang2): value
            for (lang1, lang2), value in family_dst.items()
            if lang1 in doculects and lang2 in doculects
        }

        # Get the family maximum distance if enough values were collected
        values = list(family_dst.values())
        if len(values) >= 2:
            dst[family_name] = max(values)

    return dst


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
    releases = sorted(glob.glob(str(BASE_PATH.parent / "releases" / "*")))
    BAYES_PATH = Path(releases[-1]) / "bayesian"
    PHYLO_PATH = BAYES_PATH.parent / "phylo"
    TREES_PATH = BAYES_PATH.parent / "trees"
    TREES_PATH.mkdir(exist_ok=True)

    # Collect the pre-computed distances for all the doculects
    # that are part of the Bayesian tree
    distances = collect_distances(BAYES_PATH, PHYLO_PATH)

    # Run the inference for all trees
    run_inference(BAYES_PATH, languoids)

    # Build the global tree
    global_tree, family_trees = collect_global_tree(distances, BAYES_PATH, TREES_PATH)
    with open(TREES_PATH / "global.tree", "w") as handler:
        handler.write(global_tree.write(format=1))

    #get_distances(family_trees)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
