#!/usr/bin/env python3

"""
Script for preparing wordlists from ASJP and NorthEuralex.
"""

# TODO: implement custom language filter (remove some duplicates, remove
#       reconstructions, deal with conglangs, etc.)
# TODO: should we just cache glottolog here, the slowest part? it would
#       potentially solve the TODOs above this one (and could include
#       even more info, such as WALS genus)

# Import Python standard libraries
from collections import defaultdict
from pathlib import Path
import argparse
import csv
import logging
import re

# Import other modules
import common

ASJP_PATH = Path(__file__).parent / "raw" / "asjp"
NELX_PATH = Path(__file__).parent / "raw" / "northeuralex"

# Specify output fields
OUTPUT_FIELDS = [
    "ASJP_ID",
    "DOCULECT",
    "LANGUAGE_NAME",
    "GLOTTOCODE",
    "GLOTTOLOG_NAME",
    "LANGUAGE_LINEAGE_0",
    "LANGUAGE_LINEAGE_1",
    "LANGUAGE_LINEAGE_2",
    "LANGUAGE_ISOLATE",
    "PARAMETER_ID",
    "CONCEPT",
    "CONCEPTICON_ID",
    "CONCEPTICON_GLOSS",
    "VALUE",
    "FORM",
    "TOKENS",
    "LOAN",
]


def _read_language_data(args, languoids):
    """
    Read and return CLDF language data.
    """

    # Read custom mapping
    custom = {}
    proxy = {}
    with open("etc/custom_mapping.csv") as csvfile:
        for row in csv.DictReader(csvfile):
            # If there is a glottocode, just extend the mapping
            if row["PROXY"]:
                proxy[row["NAME"]] = (row["PROXY"], row["GLOTTOCODE"])
            else:
                custom[row["NAME"]] = row["GLOTTOCODE"]

    # Read the language data
    filename = ASJP_PATH / "languages.csv"
    language = {}
    unmapped = []
    with open(filename.as_posix()) as handler:
        reader = csv.DictReader(handler)
        for row_idx, row in enumerate(reader):
            logging.info(
                "Processing language `%s` (`%s`)...",
                row["Name"],
                row["Glottocode"],
            )

            lineage_0, lineage_1, lineage_2 = "", "", ""
            isolate = ""
            glottolog_name = ""
            glottocode = ""

            if row["Name"] in custom:
                glottocode = custom[row["Name"]]
                languoid = languoids.get(glottocode)
            elif row["Name"] in proxy:
                glottocode = "*" + row["Name"].lower()
                languoid = languoids.get(proxy[row["Name"]][0])
            else:
                glottocode = row["Glottocode"]
                languoid = languoids.get(row["Glottocode"])

            if not languoid:
                logging.info("Skipping unmapped language `%s`...", row["Name"])
                unmapped.append(row["Name"])
            else:
                isolate = languoid.isolate
                glottolog_name = languoid.name

                if len(languoid.lineage) >= 1:
                    lineage_0 = languoid.lineage[0][0]
                if len(languoid.lineage) >= 2:
                    lineage_1 = languoid.lineage[1][0]
                if len(languoid.lineage) >= 3:
                    lineage_2 = languoid.lineage[2][0]

                language[row["ID"]] = {
                    "Name": row["Name"],
                    "Glottocode": glottocode,
                    "Glottolog_Name": glottolog_name,
                    "Isolate": str(isolate),
                    "Lineage_0": lineage_0,
                    "Lineage_1": lineage_1,
                    "Lineage_2": lineage_2,
                }

    return language


def _read_concept_data(args):
    """
    Read and return CLDF concept data.
    """

    filename = ASJP_PATH / "parameters.csv"
    concept = {}
    with open(filename.as_posix()) as handler:
        reader = csv.DictReader(handler)
        for row in reader:
            logging.info("Processing parameter `%s`...", row["Name"])
            concept[row["ID"]] = {
                "Name": row["Name"],
                "Concepticon_ID": row["Concepticon_ID"],
                "Concepticon_Gloss": row["Concepticon_Gloss"],
            }

    return concept


def read_cldf_data(args, languoids):
    """
    Read CLDF data as a single list of dictionaries.
    """

    # Read language and concept data
    language = _read_language_data(args, languoids)
    concept = _read_concept_data(args)

    # Read form data and join language and concepts
    filename = ASJP_PATH / "forms.csv"
    entries = []
    with open(filename.as_posix()) as handler:
        reader = csv.DictReader(handler)
        for idx, row in enumerate(reader):
            if idx % 10000 == 0:
                logging.info("Processing form #%i...", idx + 1)

            # Skip over loans if requested
            if args.keep_loans and row["Loan"] == "true":
                continue

            # Collect language and parameter ID, skipping over if
            # missing (such as during debug, where we only collect part of it)
            # TODO: always dropping morphological boundaries, should we keep them?
            l_id = row["Language_ID"]
            c_id = row["Parameter_ID"]
            if l_id in language and c_id in concept:
                segments = " ".join(
                    [seg for seg in row["Segments"].split() if seg != "+"]
                )
                entries.append(
                    {
                        "TOKENS": segments,
                        "DOCULECT": l_id,
                        "LANGUAGE_NAME": language[l_id]["Name"],
                        "GLOTTOCODE": language[l_id]["Glottocode"],
                        "GLOTTOLOG_NAME": language[l_id]["Glottolog_Name"],
                        "LANGUAGE_ISOLATE": language[l_id]["Isolate"],
                        "LANGUAGE_LINEAGE_0": language[l_id]["Lineage_0"],
                        "LANGUAGE_LINEAGE_1": language[l_id]["Lineage_1"],
                        "LANGUAGE_LINEAGE_2": language[l_id]["Lineage_2"],
                        "ASJP_ID": row["ID"],
                        "PARAMETER_ID": c_id,
                        "CONCEPT": concept[c_id]["Name"],
                        "CONCEPTICON_ID": concept[c_id]["Concepticon_ID"],
                        "CONCEPTICON_GLOSS": concept[c_id]["Concepticon_Gloss"],
                        "VALUE": row["Value"],
                        "FORM": str(row["Form"]),
                        "LOAN": row["Loan"],
                    }
                )

    return entries


def _write_full_data(data, args):
    """
    Writes full data and collects per-lineage data.
    """

    logging.info("Writing full data collecting per-lineage data...")

    # Holders for the sub-, per-lineage datasets
    lineage_0 = defaultdict(list)
    lineage_1 = defaultdict(list)
    lineage_2 = defaultdict(list)

    # Write the full data file and collect lineage specific subsets
    # NOTE: this is not extremely efficient computationally, but it is
    #       clear in what it does and does not really affect computation,
    #       as it will run a single time
    output_file = Path(args.output_path) / "ASJP_FULL_DATA.tsv"
    with open(output_file.as_posix(), "w") as handler:
        # Write headers
        headers = ["ID"] + OUTPUT_FIELDS
        handler.write("\t".join(headers))
        handler.write("\n")

        # Write entries
        for idx, entry in enumerate(data):
            # Build buffer for full data and write
            buf = [str(idx + 1)] + [entry[field] for field in OUTPUT_FIELDS]
            handler.write("\t".join(buf))
            handler.write("\n")

            # Collect sub-lineage data, skipping over non-existant
            # categories (such as missing lineage2). Note that data at this
            # point is already sorted.
            if entry["LANGUAGE_LINEAGE_0"]:
                lin0_label = common.slug(entry["LANGUAGE_LINEAGE_0"])
                lineage_0[lin0_label].append(entry)

            if entry["LANGUAGE_LINEAGE_1"]:
                lin1_label = "%s-%s" % (
                    lin0_label,
                    common.slug(entry["LANGUAGE_LINEAGE_1"]),
                )
                lineage_1[lin1_label].append(entry)

            if entry["LANGUAGE_LINEAGE_2"]:
                lin2_label = "%s-%s" % (
                    lin1_label,
                    common.slug(entry["LANGUAGE_LINEAGE_2"]),
                )
                lineage_2[lin2_label].append(entry)

    return lineage_0, lineage_1, lineage_2


def _write_lineage_data(data, lineage_label, dataset, args):
    """
    Writes data for a given lineage.
    """

    logging.info("Writing `%s` per-lineage data...", lineage_label)

    output_file = f"{dataset}_{lineage_label}.tsv"
    output_file = Path(args.output_path) / output_file
    with open(output_file.as_posix(), "w") as handler:
        # Write headers
        headers = ["ID"] + OUTPUT_FIELDS
        handler.write("\t".join(headers))
        handler.write("\n")

        # Write entries
        for idx, entry in enumerate(data):
            # Build buffer for full data and write
            buf = [str(idx + 1)] + [entry[field] for field in OUTPUT_FIELDS]
            handler.write("\t".join(buf))
            handler.write("\n")


def write_data(data, args, per_lineage=False):
    """
    Write full and (if requested) per-lineage data.
    """

    # Sort data -- even if computationally expensive, it improves
    # reproducibility, easies debug, and makes diffs more interpretable
    sorted_data = sorted(
        data,
        key=lambda e: (
            e["LANGUAGE_LINEAGE_0"],
            e["LANGUAGE_LINEAGE_1"],
            e["LANGUAGE_LINEAGE_2"],
            e["CONCEPT"],
            e["DOCULECT"],
            e["ASJP_ID"],
        ),
    )

    # Write full data and collect per lineage data
    lineage_0, lineage_1, lineage_2 = _write_full_data(sorted_data, args)

    # Write sublineage datasets
    for label, entries in lineage_0.items():
        _write_lineage_data(entries, label, "asjp", args)
    if per_lineage:
        for label, entries in lineage_1.items():
            _write_lineage_data(entries, label, "asjp", args)
        for label, entries in lineage_2.items():
            _write_lineage_data(entries, label, "asjp", args)


def read_northeuralex_data(args, languoids):
    # Hold data by family
    data = defaultdict(list)

    # Read language data for family filtering
    langfile = NELX_PATH / "northeuralex-0.9-language-data.tsv"
    with open(langfile, encoding="utf-8") as handler:
        langmap = {
            entry["glotto_code"]: (entry["family"], entry["name"])
            for entry in csv.DictReader(handler, delimiter="\t")
        }

    # Read concept data for expansion
    conceptfile = NELX_PATH / "northeuralex-0.9-concept-data.tsv"
    with open(conceptfile, encoding="utf-8") as handler:
        conceptmap = {
            entry["id_nelex"]: entry["gloss_en"]
            for entry in csv.DictReader(handler, delimiter="\t")
        }

    # Read form data filtering by family
    formfile = NELX_PATH / "northeuralex-0.9-forms.tsv"
    next_id = 1
    with open(formfile, encoding="utf-8") as handler:
        for row in csv.DictReader(handler, delimiter="\t"):
            # Filter the contents we want, also adding new ones when necessary;
            # this also skips over empty forms
            row["IPA"] = re.sub("\s+", " ", row["IPA"].strip())
            if row["IPA"]:
                entry = {
                    "ID": str(next_id),
                    "DOCULECT": langmap[row["Glottocode"]][1],
                    "GLOTTOCODE": row["Glottocode"],
                    "GLOTTOLOG_NAME": languoids[row["Glottocode"]],
                    "CONCEPT": conceptmap[row["Concept_ID"]],
                    "CONCEPT_ID": row["Concept_ID"],
                    "VALUE": row["Word_Form"],
                    "TOKENS": row["IPA"],
                }
                next_id += 1

                data[langmap[row["Glottocode"]][0]].append(entry)

    # Output by family
    for family, entries in data.items():
        filename = Path(args.output_path) / f"nelx_{common.slug(family)}.tsv"
        with open(filename, "w", encoding="utf-8") as handler:
            logging.info("Writing NELX %s data...", family)

            writer = csv.DictWriter(
                handler,
                delimiter="\t",
                fieldnames=[
                    "ID",
                    "DOCULECT",
                    "GLOTTOCODE",
                    "GLOTTOLOG_NAME",
                    "CONCEPT",
                    "CONCEPT_ID",
                    "VALUE",
                    "TOKENS",
                ],
            )
            writer.writeheader()
            writer.writerows(entries)


def main(args):
    """
    Entry point for the script.
    """

    # Instantiate `glottolog` object and cache languoids
    logging.info("Caching Glottolog languoids...")
    glottolog = common.get_glottolog(args.glottolog)
    languoids = {}
    for lang in glottolog.languoids():
        languoids[lang.glottocode] = lang

    # Read and process ASJP data
    logging.info("Reading ASJP CLDF data...")
    data = read_cldf_data(args, languoids)
    logging.info("Read %i ASJP entries.", len(data))
    write_data(data, args)

    # Read and process NorthEuraLex data
    logging.info("Reading NorthEuraLex data...")
    read_northeuralex_data(args, languoids)


if __name__ == "__main__":
    # Define the command-line parser arguments
    parser = argparse.ArgumentParser(description="Prepare wordlists.")
    parser.add_argument(
        "-o",
        "--output_path",
        type=str,
        help="Directory for the output files (default: `data`)",
        default="data",
    )
    parser.add_argument(
        "--glottolog",
        type=str,
        help="Path to the Glottolog data (default: `~/.config/cldf/glottolog`)",
    )
    parser.add_argument(
        "--keep_loans",
        action="store_true",
        help="Keep loans in data (default: remove loans)",
    )
    ARGS = parser.parse_args()

    # Set logging level and begin
    logging.basicConfig(level=logging.INFO)
    main(ARGS)
