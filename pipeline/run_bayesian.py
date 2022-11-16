#!/usr/bin/env python3

"""
Run Bayesian analyses and collect results.
"""

# Import Python standard libraries
from pathlib import Path
from collections import defaultdict
import glob
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

PROBLEMATIC_FAMILIES = ["bookkeeping", "easterntransfly", "mairasic", "walioic"]


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


def collect_global_tree(BAYES_PATH, OUTPUT_PATH):
    """
    Collect all trees into a single, global tree.
    """

    # Collect all trees and the longest distance
    max_dist = defaultdict(int)
    trees = {}
    for tree_file in glob.glob(str(BAYES_PATH / "*.mcc.nex")):
        # Extract tree, write it to disk, and append to collection
        tree = extract_tree(tree_file)
        tree_name = Path(tree_file).stem.split(".")[0]
        if tree_name in PROBLEMATIC_FAMILIES:
            continue

        with open(OUTPUT_PATH / f"{tree_name}.tree", "w") as handler:
            handler.write(tree.write(format=1))
        trees[tree_name] = tree

        # Get the biggest distance
        dist = max([leaf.get_distance(tree) for leaf in tree.iter_leaves()])
        if max_dist[tree_name] < dist:
            max_dist[tree_name] = dist

    # Build global tree
    # TODO: missing isolates
    global_tree = Tree()
    global_max_dist = max(max_dist.values())
    for family, tree in trees.items():
        global_tree.add_child(tree, dist=global_max_dist - max_dist[family])

    return global_tree


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
    TREES_PATH = BAYES_PATH.parent / "trees"
    TREES_PATH.mkdir(exist_ok=True)

    # run_inference(BAYES_PATH, languoids)
    global_tree = collect_global_tree(BAYES_PATH, TREES_PATH)
    with open(TREES_PATH / "global.tree", "w") as handler:
        handler.write(global_tree.write(format=1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
