#!/usr/bin/env python3

"""
Script for aggragating data from clustering, including alignments.
"""

import csv
import logging
from pathlib import Path
from itertools import chain
from collections import defaultdict
from common import slug

BASE_PATH = Path(__file__).parent


def build_matrix(cogsets, doculects):
    matrix = {}

    # Collect all concepts and their cogsets for this group/family
    group_cs = defaultdict(set)
    doculect_concepts = defaultdict(set)
    for doculect in doculects:
        for concept, concept_cogs in cogsets[doculect]:
            group_cs[concept].add(concept_cogs)
            doculect_concepts[doculect].add(concept)

    # Build the binary and morphological vector for each doculect
    # TODO: allow optional ascertainment?
    for doculect in sorted(doculects):
        bvector = []
        # mvector = []
        for concept, concept_cogs in group_cs.items():
            if concept not in doculect_concepts[doculect]:
                bvector += ["?"] * len(concept_cogs)
                # mvector.append("?")
            else:
                for cog in sorted(concept_cogs):
                    if (concept, cog) in cogsets[doculect]:
                        bvector.append("1")
                    else:
                        bvector.append("0")

        matrix[doculect] = "".join(bvector)

    return matrix

# TODO: collect partitions
def output_phylip(matrix, basename):
    # Get taxa, number of taxa, and longest taxon name
    taxa = sorted(matrix)
    num_taxa = len(taxa)
    num_chars = len(matrix[taxa[0]])
    max_len = max([len(taxon) for taxon in taxa])

    # Build appropriate filename and write
    with open(BASE_PATH / "phylo" / f"{slug(basename)}.phy", "w") as handler:
        handler.write(f"{num_taxa} {num_chars}\n")
        for taxon in taxa:
            handler.write(f"{taxon.ljust(max_len)}  {matrix[taxon]}\n")


def main():
    """
    Script entry point.
    """

    # Read data
    collection = "asjp"
    with open(BASE_PATH / "output" / f"{collection}.tsv", encoding="utf-8") as handler:
        data = list(csv.DictReader(handler, delimiter="\t"))
        logging.info("Read %i entries from collection `%s`.", len(data), collection)

    # Collect all cognates for all taxa, aggragated by family, and all taxa
    # in each family
    families = defaultdict(set)
    cogsets = defaultdict(set)
    for row in data:
        families[row["FAMILY"]].add(row["DOCULECT"])
        cogsets[row["DOCULECT"]].add((row["CONCEPT"], row["COGSET"]))

    for family, doculects in families.items():
        if family not in ["West Bird's Head", "Indo-European"]:
            continue

        # Obtain matrix and write
        matrix = build_matrix(cogsets, doculects)
        output_phylip(matrix, family)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
