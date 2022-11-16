#!/usr/bin/env python3

"""
Interface with Glottolog to obtain a starting tree.
"""

# TODO: deal with bookkeeping

# Import Python standard libraries
from collections import defaultdict
from pathlib import Path
import csv
import difflib
import glob
import logging

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


def get_trees(roots, languoids, glottolog):
    # Get the Glottolog tree for the root
    trees = {}
    for root, glottocodes in roots.items():
        logging.info(f"Collecting Glottolog tree for family `{root}`")

        # Get the Glottolog tree as an ETE3 via newick
        tree = Tree(glottolog.newick_tree(root), format=1)

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

        # Pruning the tree might lead us to cases where an intermediate
        # node has only one descendant (especially when we have only what
        # Glottolog considers a language and a dialect), which is not
        # acceptable as a monophyletic restriction in BEAST2 (as we are
        # not using sample ancestors). To solve this, in all cases we
        # make the entries sisters
        while True:
            changed = False
            for node in tree.traverse("levelorder"):
                if not node.is_leaf() and node.name in to_prune:
                    node.add_child(name=node.name)
                    node.name = ""
                    changed = True
                    break

            if not changed:
                break

        # Rename all existing nodes only to the glottocode
        # TODO: investigate why the regex r"\[(....\d+)\]" is failing
        for node in tree.traverse("preorder"):
            idx_a = node.name.find("[") + 1
            idx_b = node.name.find("]", idx_a)
            label = node.name[idx_a:idx_b]
            if not label:
                node.name = ""
            else:
                node.name = common.slug(
                    f"{languoids[label].name}_{label}", level="simple"
                )

        # "sort" the tree and sort it Store the tree
        tree.sort_descendants()
        tree.ladderize()
        trees[root] = tree.write()

    return trees


def output_lexical_data(roots, languoids, BAYES_PATH):
    # Get the lexical data for beastling; this means reloading the
    # data that was loaded in get_mapping(), but makes the flow
    # easier to understand
    inv_root_map = {}
    for root, doculects in roots.items():
        for doculect in doculects:
            inv_root_map[doculect] = root

    bayes_data = defaultdict(list)
    with open(BASE_PATH / "output" / "full_data.csv", encoding="utf-8") as handler:
        for row in csv.DictReader(handler):
            root = inv_root_map.get(row["GLOTTOCODE"])
            if root:
                lang_name = f"{languoids[row['GLOTTOCODE']].name}_{row['GLOTTOCODE']}"
                lang_name = common.slug(lang_name, level="simple")
                bayes_data[root].append(
                    {
                        "Language_ID": lang_name,
                        "Feature_ID": row["CONCEPT"],
                        "Value": row["COGID"],
                    }
                )

    for root, entries in bayes_data.items():
        logging.info(f"Outputting lexical data for family `{root}`")

        # Make sure missing entries are explicitly marked as such; we
        # also make sure not to run phylogenetic inference for isolates
        languages = sorted(set([row["Language_ID"] for row in entries]))
        if len(languages) == 1:
            continue
        concepts = sorted(set([row["Feature_ID"] for row in entries]))
        lang_feat_pairs = sorted(
            set([(row["Language_ID"], row["Feature_ID"]) for row in entries])
        )
        for lang in languages:
            for concept in concepts:
                if (lang, concept) not in lang_feat_pairs:
                    entries.append(
                        {"Language_ID": lang, "Feature_ID": concept, "Value": "?"}
                    )

        # Output the data
        name = languoids[root].name
        entries = sorted(
            entries, key=lambda e: (e["Feature_ID"], e["Language_ID"], e["Value"])
        )
        with open(BAYES_PATH / f"{name}.csv", "w", encoding="utf-8") as handler:
            writer = csv.DictWriter(
                handler, fieldnames=["Language_ID", "Feature_ID", "Value"]
            )
            writer.writeheader()
            writer.writerows(entries)


def prepare_beastling_conf(BAYES_PATH):
    # Get the list of families
    families = sorted(
        [Path(filename).stem for filename in glob.glob(str(BAYES_PATH / "*.csv"))]
    )

    # Read template and generate a configuration for each family
    with open(BASE_PATH / "etc" / "beastling.template.conf") as handler:
        conf = handler.read()

    for family in families:
        logging.info(f"Generating BEASTling configuration for `{family}`...")
        family_conf = conf

        replaces = {"family": family, "model_name": common.slug(family, level="full")}
        for source, target in replaces.items():
            family_conf = family_conf.replace("{{" + source + "}}", target)

        with open(BAYES_PATH / f"{family}.conf", "w", encoding="utf-8") as handler:
            handler.write(family_conf)


def main():
    """
    Script entry point.
    """

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    logging.info(f"Creating Bayesian output directory...")
    releases = sorted(glob.glob(str(BASE_PATH.parent / "releases" / "*")))
    BAYES_PATH = Path(releases[-1]) / "bayesian"
    BAYES_PATH.mkdir(exist_ok=False)

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
    trees = get_trees(roots, languoids, glottolog)
    for root, newick in trees.items():
        name = languoids[root].name
        logging.info(f"Outputting pruned tree for family `{name}`")
        with open(BAYES_PATH / f"{name}.tree", "w", encoding="utf-8") as handler:
            handler.write(newick)

    # Output lexical data for Bayesian analysis
    output_lexical_data(roots, languoids, BAYES_PATH)

    # Prepare the beastling configurations
    prepare_beastling_conf(BAYES_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
