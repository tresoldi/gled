#!/usr/bin/env python3

"""
Script for preparing data for release.
"""

# Import Python standard libraries
from pathlib import Path
from collections import defaultdict
import datetime
import logging
import csv
import copy

# Import other modules
import common

BASE_PATH = Path(__file__).parent


def output_nexus(charstates, matrix, assumptions, family):
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
    nexus_file = BASE_PATH.parent / "nexus" / f"{common.slug(family)}.nex"
    with open(nexus_file, "w", encoding="utf-8") as handler:
        handler.write("\n".join(buffer))
        handler.write("\n")


def build_nexus(data):
    # Make sure the cognates are good for IDs and for NEXUS -- this is not the
    # most efficient implementation, but works fine for this purpose
    data = copy.copy(data)
    for entry in data:
        entry["CONCEPT"] = common.slug(entry["CONCEPT"], drop_parentheses=True)

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
        # print(family)
        # print(charstates)
        # lens = set([len(v) for _, v in matrix.items()])
        # print(lens)
        # if len(lens) != 1:
        #    for k, v in matrix.items():
        #        print("!!!!!!!", k, len(v), v)


def main():
    """
    Script entry point.
    """

    # Load data
    logging.info("Reading data...")
    asjp_datafile = BASE_PATH / "output" / "asjp.tsv"
    with open(asjp_datafile, encoding="utf-8") as handler:
        data = list(csv.DictReader(handler, delimiter="\t"))

    # Collect fields as defined in the main released file and sort them
    logging.info("Processing and sorting data...")
    release_data = [
        {
            "ID": entry["ID"],
            "DOCULECT": entry["DOCULECT"],
            "DOCULECT_DATE": entry["DOCULECT_DATE"],
            "GLOTTOCODE": entry["GLOTTOCODE"],
            "GLOTTOLOG_NAME": entry["GLOTTOLOG_NAME"],
            "FAMILY": entry["FAMILY"],
            "CONCEPT": entry["CONCEPTICON_GLOSS"],
            "IPA": entry["TOKENS"],
            "ALIGNMENT": entry["ALIGNMENT"],
            "COGSET": entry["COGSET"],
        }
        for entry in data
    ]
    release_data = sorted(
        release_data, key=lambda e: (e["FAMILY"], e["COGSET"], e["ID"])
    )

    # Write output file
    today = datetime.date.today()
    output_file = BASE_PATH.parent / "data" / f"gled.{today.strftime('%Y%m%d')}.tsv"
    logging.info("Writing datafile to `%s`...", output_file)
    with open(output_file, "w", encoding="utf-8") as handler:
        writer = csv.DictWriter(
            handler,
            delimiter="\t",
            fieldnames=[
                "ID",
                "DOCULECT",
                "DOCULECT_DATE",
                "GLOTTOCODE",
                "GLOTTOLOG_NAME",
                "FAMILY",
                "CONCEPT",
                "IPA",
                "ALIGNMENT",
                "COGSET",
            ],
        )
        writer.writeheader()
        writer.writerows(release_data)

    # Collect and show statistics
    entries = len(release_data)
    doculects = len(set([e["DOCULECT"] for e in release_data]))
    cogsets = len(set([e["COGSET"] for e in release_data]))
    tokens = sum([len(e["IPA"]) for e in release_data])

    # Build nexus files
    logging.info("Building NEXUS files...")
    build_nexus(release_data)

    # Show statistics as a last step
    print("*** REMEMBER TO UPDATE STATISTICS!!! ***\n")
    print("## Statistics\n")
    print(f"The {today.strftime('%Y%m%d')} release comprises:\n")
    print("  - Entries: %i" % entries)
    print("  - Doculects: %i" % doculects)
    print("  - Cognate sets: %i" % cogsets)
    print("  - Tokens: %i" % tokens)
    print("  - Mean cognate set size: %.2f" % (entries / cogsets))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()