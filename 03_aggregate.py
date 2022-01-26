#!/usr/bin/env python3

"""
Script for aggragating data from clustering, including alignments.
"""

# TODO: add date for latin? and other languages?

import glob
import csv
import logging
from pathlib import Path
from collections import defaultdict
import re
import unidecode
import lingpy

from common import slug

BASE_PATH = Path(__file__).parent

def collect_data(filenames, id_field, parid_field, concept_map=None, lang_date=None):
    """
    Collects data for output as a list of dictionaries.
    """

    data = []
    cogsets = defaultdict(list)

    if not lang_date:
        lang_date = {}

    for filename in filenames:
        logging.info("Processing file `%s`...", filename)

        # Get the family specified in the filename, to use as
        # a fallback
        filename_family = "".join(Path(filename).stem.split("_")[1:])

        with open(filename, encoding="utf-8") as handler:
            for row in csv.DictReader(handler, delimiter="\t"):
                # Skip over lingpy comments
                if row["ID"].startswith("#"):
                    continue

                # If we have no information on the family as a column,
                # extract it from the filename, allowing to compute
                # the `cogset` id
                if "LANGUAGE_LINEAGE_0" in row:
                    family = row["LANGUAGE_LINEAGE_0"]
                    cogset_fields = [
                        row[field]
                        for field in ["LANGUAGE_LINEAGE_0", "CONCEPT", "COGID"]
                    ]
                else:
                    family = filename_family
                    cogset_fields = [family, row["CONCEPT"], row["COGID"]]

                cogset = slug("_".join(cogset_fields))

                # Obtain information on concepticon from a custom mapping or
                # from coluns in the data
                if concept_map:
                    concepticon_gloss, concepticon_id = concept_map[row["CONCEPT"]]
                else:
                    concepticon_gloss = row["CONCEPTICON_GLOSS"]
                    concepticon_id = row["CONCEPTICON_ID"]

                data.append(
                    {
                        "ID": row[id_field],
                        "DOCULECT": row["DOCULECT"],
                        "DOCULECT_DATE": lang_date.get(row["DOCULECT"], ""),
                        "GLOTTOCODE": row["GLOTTOCODE"],
                        "GLOTTOLOG_NAME": row["GLOTTOLOG_NAME"],
                        "FAMILY": family,
                        "PARAMETER_ID": row[parid_field],
                        "CONCEPT": row["CONCEPT"],
                        "CONCEPTICON_ID": concepticon_id,
                        "CONCEPTICON_GLOSS": concepticon_gloss,
                        "FORM": row["VALUE"],
                        "TOKENS": row["TOKENS"],
                        "COGSET": cogset,
                    }
                )

                cogsets[cogset].append(row["TOKENS"])

    # Collect aligned forms
    alm_map = {}
    cogset_size = len(cogsets)
    for idx, (cogset, forms) in enumerate(cogsets.items()):
        if idx % 1000 == 0:
            logging.info(
                "Collecting alignments for `%s` (%i/%i)", cogset, idx + 1, cogset_size
            )

        alm_forms = sorted(set(forms))
        msa = lingpy.Multiple(alm_forms)
        msa.prog_align()

        for form, alm in zip(alm_forms, msa.alm_matrix):
            alm_map[cogset, form] = " ".join(alm)

    # Extend data for output
    for row in data:
        row["ALIGNMENT"] = alm_map[row["COGSET"], row["TOKENS"]]

    # Sort data and return
    data = sorted(
        data,
        key=lambda r: (r["FAMILY"], r["CONCEPT"], r["COGSET"], r["DOCULECT"], r["ID"]),
    )

    return data


def write_results(data, collection):
    """
    Write results to a tabular file.
    """

    output_file = BASE_PATH / "output" / f"{collection}.tsv"
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
                "PARAMETER_ID",
                "CONCEPT",
                "CONCEPTICON_ID",
                "CONCEPTICON_GLOSS",
                "FORM",
                "TOKENS",
                "COGSET",
                "ALIGNMENT",
            ],
        )
        writer.writeheader()
        writer.writerows(data)


def main():
    """
    Script entry point.
    """

    # Prepare ASJP, reading date of extinction of languages
    with open(
        BASE_PATH / "raw" / "asjp" / "languages.csv", encoding="utf-8"
    ) as handler:
        asjp_lang_date = {
            row["Name"]: row["year_of_extinction"]
            for row in csv.DictReader(handler)
            if row["year_of_extinction"]
        }

    asjp_pattern = BASE_PATH / "cluster" / "asjp_*.tsv"
    asjp_files = glob.glob(str(asjp_pattern))
    asjp_data = collect_data(
        asjp_files, "ASJP_ID", "PARAMETER_ID", lang_date=asjp_lang_date
    )
    write_results(asjp_data, "asjp")

    # Prepare NorthEuraLex, where we need to provide the concepticon mapping
    # NOTE: NorthEuralex does not include date of extinction, even though
    #       it carries some historical data (like Latin)
    parameter_file = (
        BASE_PATH / "raw" / "northeuralex" / "northeuralex-0.9-concept-data.tsv"
    )
    with open(parameter_file, encoding="utf-8") as handler:
        nelx_mapping = {}
        for row in csv.DictReader(handler, delimiter="\t"):
            if row["concepticon_id"] == "0":
                nelx_mapping[row["gloss_en"].strip()] = (None, None)
            else:
                nelx_mapping[row["gloss_en"].strip()] = (
                    row["concepticon"].strip(),
                    row["concepticon_id"].strip(),
                )

    nelx_pattern = BASE_PATH / "cluster" / "nelx_*.tsv"
    nelx_files = glob.glob(str(nelx_pattern))
    nelx_data = collect_data(nelx_files, "ID", "CONCEPT_ID", concept_map=nelx_mapping)
    write_results(nelx_data, "nelx")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
