#!/usr/bin/env python3

"""
Script for preparing data for release.
"""

# Import Python standard libraries
from collections import defaultdict
from pathlib import Path
import copy
import csv
import datetime
import itertools
import logging
import re

# Import 3rd party modules
from Bio.Phylo.TreeConstruction import DistanceMatrix
from Bio.Phylo.TreeConstruction import DistanceTreeConstructor
from ete3 import Tree

# Import other modules
import common

BASE_PATH = Path(__file__).parent
TODAY = datetime.date.today().strftime("%Y%m%d")
RELEASE_PATH = BASE_PATH.parent / "releases" / TODAY


def output_nexus(charstates, matrix, assumptions, family):
    """
    Output the NEXUS file for an given family.
    """

    # Confirm that all vectors have the same length
    lengths = set([len(vector) for _, vector in matrix.items()])
    if len(lengths) != 1:
        raise ValueError("Different vector lengths in `%s`", family)

    # Set buffer for output
    buffer = []

    buffer.append("#NEXUS")
    buffer.append("")
    buffer.append("BEGIN DATA;")
    buffer.append(f"    DIMENSIONS NTAX={len(matrix)} NCHAR={len(charstates)};")
    buffer.append('    FORMAT DATATYPE=STANDARD MISSING=? GAP=- SYMBOLS="01";')
    buffer.append("    CHARSTATELABELS")
    charstate_buf = [
        f"        {idx + 1} {charstate}" for idx, charstate in enumerate(charstates)
    ]
    buffer.append(",\n".join(charstate_buf))
    buffer.append(";")
    buffer.append("")

    buffer.append("MATRIX")
    taxon_length = max([len(doculect) for doculect in matrix])
    for taxon, vector in sorted(matrix.items()):
        buffer.append(f"{taxon.lower().ljust(taxon_length)} {vector}")
    buffer.append(";")
    buffer.append("END;")
    buffer.append("")

    buffer.append("BEGIN ASSUMPTIONS;")
    for concept, idx_a, idx_b in assumptions:
        buffer.append(f"    charset {concept} = {idx_a}-{idx_b};")
    buffer.append("END;")

    # Open file and write
    NEXUS_PATH = RELEASE_PATH / "nexus"
    nexus_file = NEXUS_PATH / f"{common.slug(family, level='full')}.nex"
    with open(nexus_file, "w", encoding="utf-8") as handler:
        handler.write("\n".join(buffer))
        handler.write("\n")


def build_nexus(data):
    """
    Build a NEXUS file for each family in the current release.
    """

    NEXUS_PATH = RELEASE_PATH / "nexus"
    NEXUS_PATH.mkdir()

    # Make sure the cognates are good for IDs and for NEXUS -- this is not the
    # most efficient implementation, but works fine for this purpose
    data = copy.copy(data)
    for entry in data:
        entry["CONCEPT"] = common.slug(entry["CONCEPT"], level="full")

    # Collect cogset and language info for building NEXUS files as sorted lists
    logging.info("Collecting data for NEXUS files...")
    concepts = sorted(set([entry["CONCEPT"] for entry in data]))
    cogsets = defaultdict(set)
    lang_cogsets = defaultdict(set)
    lang_concepts = defaultdict(set)
    families = defaultdict(set)
    for entry in data:
        cogsets[entry["FAMILY"], entry["CONCEPT"]].add(entry["COGSET"])
        lang_cogsets[entry["DOCULECT"]].add(entry["COGSET"])
        lang_concepts[entry["DOCULECT"]].add(entry["CONCEPT"])
        families[entry["FAMILY"]].add(entry["DOCULECT"])

    cogsets = {key: sorted(value) for key, value in cogsets.items()}

    # Process and output each family
    for family in list(families):
        logging.info("Processing NEXUS for `%s`...", family)

        matrix = defaultdict(str)
        charstates = []
        assumptions = []
        last_idx = 0

        for concept in concepts:
            cs = cogsets.get((family, concept), None)
            if cs:
                # Add all character states, including ascertainment, to both
                # charstates and assumptions
                charstates.append(f"{concept}_0ascertainment".lower())
                for cog in cs:
                    charstates.append(f"{concept}_{cog.split('_')[-1]}".lower())

                assumptions.append(
                    [
                        concept,
                        last_idx + 1,
                        last_idx + 1 + len(cogsets[family, concept]),
                    ]
                )
                last_idx += 1 + len(cogsets[family, concept])

                # Extend the matrix
                for doculect in sorted(families[family]):
                    if concept in lang_concepts[doculect]:
                        vector = [
                            cog in lang_cogsets[doculect]
                            for cog in cogsets[family, concept]
                        ]
                        b_vector = "0" + "".join([["0", "1"][v] for v in vector])
                    else:
                        b_vector = "0" + "?" * len(cogsets[family, concept])

                    matrix[doculect] += b_vector

        # Output NEXUS file
        output_nexus(charstates, matrix, assumptions, family)


def build_released_data(languoids):
    """
    Build the release tabular file from the processed one.
    """

    # Load data
    logging.info("Reading data...")
    fulldata_file = BASE_PATH / "output" / "full_data.csv"
    with open(fulldata_file, encoding="utf-8") as handler:
        data = list(csv.DictReader(handler))

    # Collect all COGIDs to provide a purely numerical index
    cogid_map = {
        cogid: idx + 1
        for idx, cogid in enumerate(sorted(set([row["COGID"] for row in data])))
    }

    # Collect fields as defined in the main released file and sort them
    logging.info("Processing and sorting data...")
    release_data = []
    for entry in data:
        # Get Glottolog name, if any
        if entry["GLOTTOCODE"] in languoids:
            glottolog_name = languoids[entry["GLOTTOCODE"]].name
        else:
            glottolog_name = ""

        # Append data
        release_data.append(
            {
                "ID": entry["ID"],
                "DOCULECT": entry["LANG_ID"],
                "LANGUAGE_NAME": entry["LANGUAGE_NAME"],
                "GLOTTOCODE": entry["GLOTTOCODE"],
                "GLOTTOLOG_NAME": glottolog_name,
                "FAMILY": entry["GLOTTOFAMILY"],
                "CONCEPT": entry["CONCEPT"],
                "CONCEPTICON_ID": entry["CONCEPTICON_ID"],
                "ASJP_FORM": entry["ASJP_FORM"],
                "FORM": entry["TOKENS"].replace(" ", ""),
                "IPA": entry["TOKENS"],
                "ALIGNMENT": entry["ALIGNMENT"],
                "COGSET": entry["COGID"],
                "COGSET_INT": cogid_map[entry["COGID"]],
            }
        )

    release_data = sorted(
        release_data, key=lambda e: (e["FAMILY"], e["COGSET"], e["ID"])
    )

    return release_data


def write_release_data(release_data):
    """
    Write release data to disk.
    """

    # Write output file
    output_file = RELEASE_PATH / f"gled.tsv"
    logging.info("Writing datafile to `%s`...", output_file)
    with open(output_file, "w", encoding="utf-8") as handler:
        writer = csv.DictWriter(
            handler,
            delimiter="\t",
            fieldnames=[
                "ID",
                "DOCULECT",
                "LANGUAGE_NAME",
                "GLOTTOCODE",
                "GLOTTOLOG_NAME",
                "FAMILY",
                "CONCEPT",
                "CONCEPTICON_ID",
                "ASJP_FORM",
                "FORM",
                "IPA",
                "ALIGNMENT",
                "COGSET",
                "COGSET_INT",
            ],
        )
        writer.writeheader()
        writer.writerows(release_data)


def build_readme(release_data):
    """
    Build the root README.md file for the current release.
    """

    # Collect and show statistics
    entries = len(release_data)
    doculects = len(set([e["DOCULECT"] for e in release_data]))
    families = len(set([e["FAMILY"] for e in release_data]))
    cogsets = len(set([e["COGSET"] for e in release_data]))
    tokens = sum([len(e["IPA"]) for e in release_data])

    # Load template and do replacements
    with open(BASE_PATH / "etc" / "README.template.md", encoding="utf-8") as handler:
        readme = handler.read()

    badges_str = f"""
[![Release](https://img.shields.io/badge/Release-{TODAY}-informational)](https://img.shields.io/badge/Release-{TODAY}-informational)
[![Lemmas](https://img.shields.io/badge/Lemmas-{entries}-success)](https://img.shields.io/badge/Lemmas-{entries}-success)
[![Languages](https://img.shields.io/badge/Languages-{doculects}-success)](https://img.shields.io/badge/Languages-{doculects}-success)
[![Families](https://img.shields.io/badge/Families-{families}-success)](https://img.shields.io/badge/Families-{families}-success)
[![Cognatesets](https://img.shields.io/badge/Cognatesets-{cogsets}-success)](https://img.shields.io/badge/Cognatesets-{cogsets}-success)
[![Tokens](https://img.shields.io/badge/Tokens-{tokens}-success)](https://img.shields.io/badge/Tokens-{tokens}-success)
    """
    readme = readme.replace("{{BADGES}}", badges_str)

    stats_str = f"""
The {TODAY} release comprises:

  - Entries: {entries}
  - Doculects: {doculects}
  - Families: {families} (including isolates)
  - Cognate sets: {cogsets}
  - Tokens: {tokens}

"""
    readme = readme.replace("{{STATISTICS}}", stats_str)

    # Replace README.md in the root
    with open(BASE_PATH.parent / "README.md", "w", encoding="utf-8") as handler:
        handler.write(readme)


def build_metadata():
    """
    Build the frictionless metadata for the current release.
    """

    with open(BASE_PATH / "etc" / "gled.template.resource.yaml") as handler:
        source = handler.read()

    source = source.replace("{{RELEASE}}", TODAY)

    with open(
        RELEASE_PATH / f"gled.resource.yaml",
        "w",
        encoding="utf-8",
    ) as handler:
        handler.write(source)


def build_distance_matrices_and_trees(data):
    """
    Build a distance matrix and an NJ tree for each family in the released data.
    """

    PHYLO_PATH = RELEASE_PATH / "phylo"
    PHYLO_PATH.mkdir()

    # Collect per-family information (as well as information on isolates,
    # on the same pass, so that we can skip them)
    cogsets = defaultdict(lambda: defaultdict(set))
    logging.info("Collecting matrix distance data...")
    for entry in data:
        cogsets[entry["FAMILY"]][entry["DOCULECT"]].add(entry["COGSET"])

    newicks = []
    isolates = []
    for family, entries in cogsets.items():
        logging.info(f"Generating matrix distance (if possible) for family `{family}`.")
        # Collect list of languages and skip over isolates
        langs = sorted(entries.keys())
        if len(langs) == 1:
            isolates.append(langs[0])
            continue

        # Get all pairwise distances; to account for distances of zero,
        # we perform a small correction by using the lowest value
        dists = {}
        for lang1, lang2 in itertools.combinations(langs, 2):
            union_len = len(entries[lang1].union(entries[lang2]))
            intersect = entries[lang1].intersection(entries[lang2])
            dists[lang1, lang2] = len(intersect) / union_len

        min_dist = min([dist for dist in dists.values() if dist > 0])
        dists = {
            (lang1, lang2): (dist + min_dist) / (1.0 + min_dist)
            for (lang1, lang2), dist in dists.items()
        }

        # Output the distance matrix
        dst_file = PHYLO_PATH / f"{common.slug(family, level='full')}.dst"
        with open(dst_file, "w", encoding="utf-8") as handler:
            # Write header with the number of languages
            handler.write(" %i\n" % len(langs))

            # Get the length of the language name for padding
            langlen = max([len(lang) for lang in langs]) + 2

            # Write one language per row
            for lang1 in langs:
                str_vector = []
                for lang2 in langs:
                    if (lang1, lang2) in dists:
                        dist = 1.0 - dists[lang1, lang2]
                    elif (lang2, lang1) in dists:
                        dist = 1.0 - dists[lang2, lang1]
                    else:
                        dist = 0.0

                    str_vector.append("%.04f" % dist)

                handler.write(lang1.ljust(langlen))
                handler.write(" ".join(str_vector))
                handler.write("\n")

        # Build the tree
        logging.info(f"Generating NJ tree for family `{family}`.")
        triang_matrix = []
        for lang1 in langs:
            row = []
            for lang2 in langs:
                if (lang2, lang1) in dists:
                    row.append(1.0 - dists[lang2, lang1])
                elif lang1 == lang2:
                    row.append(0.0)
            triang_matrix.append(row)

        # Obtain the tree from BioPython, removing the "inner" labels
        constructor = DistanceTreeConstructor()
        tree = constructor.nj(DistanceMatrix(langs, triang_matrix))
        newick = tree.format("newick")
        newick = re.sub(r"Inner\d+", "", newick)
        newick = newick.replace("Inner", "")

        # Output the tree
        tree_file = PHYLO_PATH / f"{common.slug(family, level='full')}.tree"
        with open(tree_file, "w", encoding="utf-8") as handler:
            handler.write(newick)

        # Append to the general list (for building the world tree)
        newicks.append(newick)

    # Build the world tree
    global_tree = Tree()

    for isolate in isolates:
        isolate_tree = Tree()
        isolate_tree.dist = 1.0
        isolate_tree.name = isolate
        global_tree.add_child(isolate_tree)

    for family_newick in newicks:
        family_tree = Tree(family_newick)
        family_tree.dist += 1.0
        global_tree.add_child(family_tree)

    # Output the world tree; we fix the "1:" introduced by ete3
    tree_file = PHYLO_PATH / "WORLD.tree"
    with open(tree_file, "w", encoding="utf-8") as handler:
        world_newick = global_tree.write()
        world_newick = world_newick.replace(")1:", "):")
        handler.write(world_newick)


def main():
    """
    Script entry point.
    """

    # Create release path if it does not exist, leaving if it is there
    if RELEASE_PATH.is_dir():
        raise ValueError(f"Release output directory already exists (`{RELEASE_PATH}`).")
    else:
        logging.info(f"Creating output directory (`{RELEASE_PATH}`).")
        RELEASE_PATH.mkdir(parents=True)

    # Instantiate `glottolog` object and cache languoids
    logging.info("Caching Glottolog languoids...")
    glottolog = common.get_glottolog()
    languoids = {}
    for lang in glottolog.languoids():
        languoids[lang.glottocode] = lang
    logging.info(f"Cached {len(languoids)} languoids.")

    # Actually build the data and files'
    build_metadata()

    release_data = build_released_data(languoids)
    write_release_data(release_data)
    build_readme(release_data)
    build_distance_matrices_and_trees(release_data)

    # Build nexus files
    logging.info("Building NEXUS files...")
    build_nexus(release_data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
