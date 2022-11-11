#!/usr/bin/env python3

# Import Python standard libraries
from collections import defaultdict, Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import *
import csv
import logging
import random
import re

# Import 3rd-party labels
import lingpy
from lingpy.compare.lexstat import LexStat

# Import local modules and functions
from common import slug

# Setup paths
BASE_PATH = Path(__file__).parent
ROOT_PATH = BASE_PATH.parent

# Set a flag for development, leading to faster execution
DEVEL = False

# Maximum number of entries per family in order to try to run LexStat
LINGPY_LIMIT = 18000

# Glottolog family names (after normalization) to be dropped (note
# that some have already been dropped in the source by Jaeger)
DROP_FAMILY = ["MixedLanguage", "Spurious", "Unclassifiable kzw", "Bookkeeping"]

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
        langmap = {row["ID"].upper(): row for row in csv.DictReader(handler)}

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
            lang_id = tokens[-1].upper()

            # Get language information
            glottocode = langmap[lang_id]["Glottocode"]
            glottoname = langmap[lang_id]["Glottolog_Name"]
            glottoclass = langmap[lang_id]["classification_glottolog"]

            # Build additional information as needed
            concept = concmap[row["concept"]]["CONCEPT"]
            concepticon_id = concmap[row["concept"]]["CONCEPTICON_ID"]

            glottolog_family = slug(glottoclass.split(",")[0], level="simple").replace(
                "_", " "
            )
            cogid_num = int(row["cc"].split("_")[-1])
            cogid = f"{slug(glottolog_family, level='full')}.{concept}.{cogid_num:04}"

            # Extend the data with the current entry; we keep track of the IDs
            # TODO: pick the "best" doculect for each glottocode
            if glottolog_family not in DROP_FAMILY:
                # If no glottolog name is provided, repeat the ASJP name
                if not glottoname:
                    lang_name = lang_id
                else:
                    lang_name = glottoname

                data.append(
                    {
                        "ID": f"{lang_id}.{concept}",
                        "LANG_ID": lang_id,
                        "LANGUAGE_NAME": lang_name,
                        "GLOTTOFAMILY": glottolog_family,
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

    # There are many cases in which for the same language variety (=same ASJP name)
    # we have more than one entry, identified by a trailing "_IDX" (which is almost
    # never given for the first entry, i.e., no "_1"). For those
    # cases, we are going to collect all entries and keep the largest lexical
    # catalogs, or the one with the shortest name.
    logging.info("Cleaning duplicate languages")
    lexcatalog = defaultdict(Counter)
    for entry in data:
        match = re.match(
            r"(?P<lang_id0>.+)_(?P<idx>\d+)|(?P<lang_id1>.+)", entry["LANG_ID"]
        )
        if match.group("lang_id1"):
            lexcatalog[match.group("lang_id1")].update(["!"])
        else:
            lexcatalog[match.group("lang_id0")].update([match.group("idx")])

    lang_id_drop = []
    for key, counter in lexcatalog.items():
        if len(counter) > 1:
            to_drop = [lang_id_idx for lang_id_idx, _ in counter.most_common()[1:]]
            lang_id_drop += [f"{key}_{idx}" if idx != "!" else key for idx in to_drop]

    data = [entry for entry in data if entry["LANG_ID"] not in lang_id_drop]
    logging.info(f"Reduced to {len(data)} entries.")

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


def add_lingpy_cogs(data):
    """
    Use lingpy for detecting cognate sets in small families.

    This function replaces the cognates provided in Jäger 2021 by
    those inferred by lingpy's Lexstat method (List and Forkel 2022).
    It cannot be applied to families which are too large (over 10,000
    entries) as the algorithm will eventually fail without enough
    memory. The usage of lingpy, with intermediate files etc., is
    made transparent by this function.
    """

    # Collect the data as necessary
    lingpy_data = defaultdict(list)
    for idx, entry in enumerate(data):
        lingpy_data[entry["GLOTTOFAMILY"]].append(
            {
                "ID": str(idx + 1),
                "DOCULECT": entry["LANG_ID"],
                "CONCEPT": entry["CONCEPT"],
                "FORM": entry["TOKENS"].replace(" ", ""),
                "TOKENS": entry["TOKENS"],
                "SOURCE_ID": entry["ID"],
                "SOURCE_COGID": entry["COGID"],
            }
        )

    # Collect data for each family
    new_cogs = {}
    count = 0  # only used when the DEVEL flag is true
    for family, entries in lingpy_data.items():
        # Break if the list is too big
        if len(entries) > LINGPY_LIMIT:
            continue

        # If running when the DEVEL flag is true, for quick running,
        # make sure to only perform lingpy detection for the first
        # families
        if DEVEL:
            count += 1
            if count == 5:
                break

        # Break if there is a single language
        # TODO: should we keep this? lingpy might give better results here
        if len(set([entry["DOCULECT"] for entry in entries])) == 1:
            continue

        logging.info(f"Running lingpy cognate detection for family {family}...")

        # Write to a temporary file; we need to obtain a temporary name to feed lingpy
        handler = NamedTemporaryFile(mode="w")
        cogid_file = handler.name
        handler.close()
        with open(cogid_file, "w", encoding="utf-8") as handler:
            writer = csv.DictWriter(
                handler,
                delimiter="\t",
                fieldnames=[
                    "ID",
                    "DOCULECT",
                    "CONCEPT",
                    "FORM",
                    "TOKENS",
                    "SOURCE_ID",
                    "SOURCE_COGID",
                ],
            )
            writer.writeheader()
            writer.writerows(entries)

        # Run lexstat, write results to temporary file, and read back
        lex = LexStat(cogid_file)
        lex.get_scorer(runs=10000)
        lex.cluster(
            method="lexstat",
            threshold=0.55,
            ref="COGID",
            mode="global",
            gop=2.0,
            cluster_method="infomap",
        )
        handler = NamedTemporaryFile(mode="w")
        cogid_file = handler.name
        handler.close()
        lex.output("tsv", filename=cogid_file, prettify=False)
        # note that lingpy adds a .tsv...
        with open(f"{cogid_file}.tsv", encoding="utf-8") as handler:
            cogid_data = list(csv.DictReader(handler, delimiter="\t"))
            cogid_data = [row for row in cogid_data if row["ID"][0] != "#"]

        # Expand the list of new cognates
        for entry in cogid_data:
            head = ".".join(entry["SOURCE_COGID"].split(".")[:-1])
            new_cogs[entry["SOURCE_ID"]] = f"{head}.{int(entry['COGID']):04}"

    # Apply new cognates to data
    for entry in data:
        entry["COGID"] = new_cogs.get(entry["ID"], entry["COGID"])

    return data


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

    # Add lingpy cognates for families that are small enough
    data = add_lingpy_cogs(data)

    # Add alignments
    data = add_alignments(data)

    # Write aggregated table to disk
    write_data(data)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
