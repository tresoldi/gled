#!/usr/bin/env python3

"""
Script for preparing data for release.
"""

# Import Python standard libraries
from pathlib import Path
import datetime
import logging
import csv

BASE_PATH = Path(__file__).parent


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
