"""
Interface with Glottolog to obtain a starting tree.
"""

# TODO: deal with bookkeeping

# Import Python standard libraries
from collections import defaultdict
from pathlib import Path
import csv
import difflib
import logging
import re

# Import 3rd party libraries
from ete3 import Tree

# Import other modules
import common


BASE_PATH = Path(__file__).parent


def get_mapping(languoids):
    """
    Obtain a mapping for all the glottocodes in our data.
    """

    logging.info("Obtaining the glottocode to doculect mapping...")

    # Obtain a map of glottocodes to doculects in our released data;
    # note there are both cases of doculects without a Glottolog
    # mapping and cases of a glottocode corresponding to two or more
    # doculects.
    prev_glottomap = defaultdict(set)
    with open(BASE_PATH / "output" / "full_data.csv", encoding="utf-8") as handler:
        for row in csv.DictReader(handler):
            if row["GLOTTOCODE"]:
                prev_glottomap[row["GLOTTOCODE"]].add(row["LANG_ID"])

    # Trim down the list of languages: in cases of two or more doculects mapped
    # to the same glottocode, we first pick the one without underscores (based
    # on the fact that these are usually varieties in ASJP), then the one with
    # the shortest edit distance to the
    # Glottolog name.
    glottomap = {}
    for glottocode, doculects in prev_glottomap.items():
        # Get a sorted list
        doculects = sorted(doculects)

        # First round of strategy
        if len(doculects) == 1:
            # Pick the first one, if there is only one
            glottomap[glottocode] = doculects[0]
        elif any(["_" not in doculect for doculect in doculects]):
            # Keep only the doculects without underscores, provided that
            # at least one of them has no underscores
            doculects = [doculect for doculect in doculects if "_" not in doculect]

            if len(doculects) == 1:
                glottomap[glottocode] = doculects[0]
                continue

        # Final strategy by name similarity
        matches = difflib.get_close_matches(
            languoids[glottocode].name.upper(), doculects, cutoff=0.0
        )
        glottomap[glottocode] = matches[0]

    return glottomap


def get_roots(glottomap, languoids):
    # Get a mapping for family root and languoids found in our data
    roots = defaultdict(list)
    for glottocode in glottomap:
        ancestors = languoids[glottocode].ancestors
        if len(ancestors) == 0:
            root = glottocode
        else:
            root = languoids[glottocode].ancestors[0].glottocode

        roots[root].append(glottocode)

    return roots


def get_trees(roots, glottolog):
    # Get the Glottolog tree for the root
    trees = {}
    for root, glottocodes in roots.items():
        # Get the Glottolog tree as an ETE3 via newick
        tree = Tree(glottolog.newick_tree(root), format=1)
        logging.info(f"Collecting Glottolog tree for `{tree.name}`")

        # Traverse the tree collecting the node names to preserve,
        # which are the root and those with the glottocodes, and prune
        # the tree
        to_prune = []
        for node in tree.traverse("preorder"):
            if node == tree:
                to_prune.append(node.name)
            if any([glottocode in node.name for glottocode in glottocodes]):
                to_prune.append(node.name)
        tree.prune(to_prune)

        # Rename all existing nodes only to the glottocode
        # TODO: investigate why the regex r"\[(....\d+)\]" is failing
        for node in tree.traverse("preorder"):
            idx_a = node.name.find("[") + 1
            idx_b = node.name.find("]", idx_a)
            node.name = node.name[idx_a:idx_b]

        # Store the tree
        trees[root] = tree.write()

    return trees


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

    # Get the glottocode mapping, roots, and trees
    glottomap = get_mapping(languoids)
    roots = get_roots(glottomap, languoids)
    trees = get_trees(roots, glottolog)

    print(trees)


if __name__ == "__main__":
    main()
