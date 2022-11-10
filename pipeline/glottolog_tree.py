"""
Interface with Glottolog to obtain a starting tree.
"""

# Import Python standard libraries
from pathlib import Path
import csv
from collections import defaultdict
import logging
import difflib

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

    # Get the glottocode mapping
    glottomap = get_mapping(languoids)

    # Get a mapping for family root and languoids found in our data
    roots = defaultdict(list)
    for glottocode in glottomap:
        ancestors = languoids[glottocode].ancestors
        if len(ancestors) == 0:
            root = glottocode
        else:
            root = languoids[glottocode].ancestors[0].glottocode

        roots[root].append(glottocode)

    # Get the Glottolog tree for the root
    for root, glottocodes in roots.items():
        print(root, glottocodes)
        print(glottolog.newick_tree(root))

    # print(glottomap)


if __name__ == "__main__":
    main()
