#!/usr/bin/env python3

# Import Python standard libraries
from collections import defaultdict
from pathlib import Path
from typing import *
import csv
import logging
import random
import re
import string

# Import 3rd-party labels
import lingpy
from unidecode import unidecode

# Setup paths
BASE_PATH = Path(__file__).parent
ROOT_PATH = BASE_PATH.parent

# Set a flag for development, leading to faster execution
DEVEL = False


def slug(label: str, level: str) -> str:
    """
    Return a slugged version of a label.
    @param label: The text to be slugged. Note that, as this operates on
        a single string, there is no guarantee of non-collision.
    @param level: Define the level of slugging to be applied. Currently,
        accepted levels are "none", "simple", and "full".
    @return: The slugged version of the label.
    """

    if level not in ["none", "simple", "full"]:
        raise ValueError(f"Unknown level of slugging `{level}`.")

    logging.debug("Slugging label `%s` with level `%s`.", label, level)

    # This implementation of the different levels of slugging seems a
    # bit cumbersome at first, but makes it easy for us to explore alternatives
    if level in ["simple", "full"]:
        label = unidecode(label)
    if level in ["full"]:
        label = label.lower()
    if level in ["simple"]:
        label = "".join(
            [
                char
                for char in label
                if char in string.ascii_letters + string.digits + "-_"
            ]
        )
    if level in ["full"]:
        label = "".join([char for char in label if char in string.ascii_letters])
    if level in ["simple", "full"]:
        label = re.sub(r"\s+", "_", label.strip())

    logging.debug("Label slugged to `%s`.", label)

    return label


# NOTE: This implements a custom implementation of orthographic profiles,
# so that we don't need the full CLDF/CLLD dependency system
def get_orthography(asjp_form: str, profile: dict) -> str:
    """
    Get the IPA tokens from an ASJP form using an orthographic profile approach.
    """

    form = f"^{asjp_form}$"

    tokens = []
    start_idx = 0
    while True:
        for end_idx in range(len(form) - 1, -1, -1):
            candidate = form[start_idx : end_idx + 1]
            token = profile.get(candidate, None)

            if token is not None:
                if token != "NULL":
                    tokens.append(token)
                start_idx += len(candidate)
                break
            elif len(candidate) == 1:
                print(f"Token missing [{candidate}] in {form}.")
                break

        if start_idx == len(form):
            break

    return " ".join([token for token in tokens if token])


def read_jaeger():
    """
    Read and process the clustered data from Jäger (2021).
    """

    # Read the language mapping provided by Jäger
    logging.info("Reading language mapping data.")
    with open(BASE_PATH / "raw" / "languages.csv", encoding="utf-8") as handler:
        langmap = {row["ID"]: row for row in csv.DictReader(handler)}

    # Read the concept mapping provided by us
    logging.info("Reading concept mapping data.")
    with open(BASE_PATH / "etc" / "concepts.csv", encoding="utf-8") as handler:
        concmap = {
            row["GLOSS"]: {
                "CONCEPT": row["CONCEPT"],
                "CONCEPTICON_ID": row["CONCEPTICON_ID"],
            }
            for row in csv.DictReader(handler)
        }

    # Read and cache the custom orthographic profile
    logging.info("Reading orthographic profile.")
    with open(BASE_PATH / "etc" / "orthography.tsv", encoding="utf-8") as handler:
        profile = {
            row["GRAPHEME"]: row["IPA"]
            for row in csv.DictReader(handler, delimiter="\t")
        }

    # Read the source data
    logging.info("Reading Jaeger 2021 clustered data.")
    data = []
    with open(BASE_PATH / "raw" / "asjp19Clustered.csv", encoding="utf-8") as handler:
        for row in csv.DictReader(handler):
            # Get language id and classification
            tokens = row["language"].split(".")
            classification = ".".join(tokens[:-1])  # TODO: use it in the output
            lang_id = tokens[-1]

            # Get language information
            glottocode = langmap[lang_id]["Glottocode"]
            glottoname = langmap[lang_id]["Glottolog_Name"]
            glottoclass = langmap[lang_id]["classification_glottolog"]

            # Build additional information as needed
            concept = concmap[row["concept"]]["CONCEPT"]
            concepticon_id = concmap[row["concept"]]["CONCEPTICON_ID"]

            glottolog_family = slug(glottoclass.split(",")[0], level="simple")
            cogid_num = row["cc"].split("_")[-1]
            cogid = f"{slug(glottolog_family, level='full')}.{concept}.{cogid_num}"

            # Extend the data with the current entry; we keep track of the IDs
            # TODO: pick the "best" doculect for each glottocode
            data.append(
                {
                    "ID": f"{lang_id}.{concept}",
                    "LANG_ID": lang_id,
                    "LANGUAGE_NAME": glottoname,
                    "GLOTTOFAMILY": glottolog_family.replace("_", " "),
                    "GLOTTOCODE": glottocode,
                    "CONCEPT": concept,
                    "CONCEPTICON_ID": concepticon_id,
                    "ASJP_FORM": row["word"],
                    "TOKENS": get_orthography(row["word"], profile),
                    "COGID": cogid,
                }
            )
    logging.info(f"Read {len(data)} entries from Jaeger 2021.")

    # If the global development flag was set, grab a random selection of the
    # data for quick experimenting
    if DEVEL:
        sample_size = int(len(data) * 0.1)
        logging.info(f"Getting a random sample of {sample_size} entries.")
        random.seed("gled")
        data = random.sample(data, sample_size)

    # Sort the data and add the row number to the existing ID, so that we make sure
    # they are unique
    logging.info("Sorting data and guaranteeing unique IDs.")
    data = sorted(
        data, key=lambda r: (r["CONCEPT"], r["GLOTTOFAMILY"], r["LANG_ID"], r["COGID"])
    )
    for idx, row in enumerate(data):
        row["ID"] = f"{row['ID']}-{idx+1}"

    return data


def write_data(data):
    """
    Write final aggregated single table to disk.
    """

    logging.info(f"Writing full data ({len(data)} entries) to disk.")

    with open(BASE_PATH / "output" / "full_data.csv", "w", encoding="utf-8") as handler:
        writer = csv.DictWriter(
            handler,
            fieldnames=[
                "ID",
                "LANG_ID",
                "LANGUAGE_NAME",
                "GLOTTOFAMILY",
                "GLOTTOCODE",
                "CONCEPT",
                "CONCEPTICON_ID",
                "ASJP_FORM",
                "TOKENS",
                "COGID",
                "ALIGNMENT",
            ],
        )
        writer.writeheader()
        writer.writerows(data)


def add_alignments(data):
    """
    Add alignments based on the existing COGID mappings.
    """

    # Collect all forms in all cognate sets
    cogsets = defaultdict(set)
    for entry in data:
        cogsets[entry["COGID"]].add(entry["TOKENS"])

    # Collect aligned forms
    alm_map = {}
    cogset_size = len(cogsets)
    for idx, (cogset, forms) in enumerate(cogsets.items()):
        if idx % 1000 == 0:
            logging.info(
                "Collecting alignments for `%s` (%i/%i)", cogset, idx + 1, cogset_size
            )

        alm_forms = sorted(forms)
        msa = lingpy.Multiple(alm_forms)
        msa.prog_align()

        for form, alm in zip(alm_forms, msa.alm_matrix):
            alm_map[cogset, form] = " ".join(alm)

    # Add alignments and return
    for entry in data:
        entry["ALIGNMENT"] = alm_map.get((entry["COGID"], entry["TOKENS"]))

    return data


def main():
    # Read data from Jäger, extending language information and adding
    # transcriptions
    data = read_jaeger()

    # Add alignments
    data = add_alignments(data)

    # Write aggregated table to disk
    write_data(data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
