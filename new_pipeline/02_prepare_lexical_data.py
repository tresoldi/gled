#!/usr/bin/env python3

"""
Read the local ASJP dump and prepare the lexical data for the dataset.

The script will take care of the normal tasks of computational historical
linguistics, such as parsing the raw data, filtering out entries that are
not relevant for the analysis, obtaining phonological transcriptions,
performing cognate detection and alignment, and so on.
"""

# Import standard modules
import csv
from typing import *
from pathlib import Path
import subprocess
import logging

# Import local modules
import common

ROOT_PATH = Path(__file__).parent


def read_cldf_dataset(dataset_path: str) -> Tuple[List[dict], str, str]:
    """
    Read a dataset CLDF dataset as a single list of dictionaries.
    """

    # Build the dataset path
    dataset_path = ROOT_PATH / dataset_path

    # Build a language map from the contents of `languages.csv`
    with open(dataset_path / "cldf" / "languages.csv") as f:
        reader = csv.DictReader(f)
        languages = {
            row["ID"]: {"Name": row["Name"], "Glottocode": row["Glottocode"]}
            for row in reader
        }

    # Build a parameter map from the contents of `parameters.csv`
    with open(dataset_path / "cldf" / "parameters.csv") as f:
        reader = csv.DictReader(f)
        parameters = {
            row["ID"]: {
                "Name": row["Name"],
                "Concepticon_ID": row["Concepticon_ID"],
                "Concepticon_Gloss": row["Concepticon_Gloss"],
            }
            for row in reader
        }

    # Build a cognate set map from the contents of `cognates.csv`, if available
    try:
        with open(dataset_path / "cldf" / "cognates.csv") as f:
            reader = csv.DictReader(f)
            cognates = {
                row["Form_ID"]: {
                    "Cognateset": row["Cognateset_ID"],
                    "Cognate_Detection_Method": row["Cognate_Detection_Method"],
                    "Source": row["Source"],
                }
                for row in reader
            }
    except:
        cognates = {}

    # Build a list of entries from the contents of `forms.csv`
    entries = []
    with open(dataset_path / "cldf" / "forms.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["ID"] in cognates:
                cognate_set = cognates[row["ID"]]["Cognateset"]
                cognate_method = cognates[row["ID"]]["Cognate_Detection_Method"]
                cognate_source = cognates[row["ID"]]["Source"]
            else:
                cognate_set = ""
                cognate_method = ""
                cognate_source = ""

            entry = {
                "Lexibank_ID": row["ID"],
                "Language": languages[row["Language_ID"]]["Name"],
                "Glottocode": languages[row["Language_ID"]]["Glottocode"],
                "Parameter": parameters[row["Parameter_ID"]]["Name"],
                "Concepticon_ID": parameters[row["Parameter_ID"]]["Concepticon_ID"],
                "Concepticon_Gloss": parameters[row["Parameter_ID"]][
                    "Concepticon_Gloss"
                ],
                "Value": row["Value"],
                "Form": row["Form"],
                "Segments": row["Segments"],
                "Cognateset": cognate_set,
                "Cognate_Detection_Method": cognate_method,
                "Cognate_Source": cognate_source,
                "Entry_Source": row["Source"],
            }

            entries.append(entry)

    # Build a slug map for the concepts, making sure they are unique
    slug_map = {}
    for entry in entries:
        if entry["Parameter"] not in slug_map:
            if entry["Concepticon_Gloss"]:
                label = entry["Concepticon_Gloss"]
            else:
                label = entry["Parameter"]

            slug_map[entry["Parameter"]] = label

    sources, targets = list(slug_map.keys()), list(slug_map.values())
    targets = common.unique_ids(targets)
    slug_map = {source: target for source, target in zip(sources, targets)}

    # Collect a set of all cognateset per concept, and build a map of replacements
    # that carry more human information than the cognateset IDs usually do
    cognatesets = {}
    for entry in entries:
        if entry["Cognateset"]:
            cognatesets.setdefault(entry["Parameter"], set()).add(entry["Cognateset"])

    cognate_rename = {}
    for concept, cognatesets in cognatesets.items():
        for i, cognateset in enumerate(cognatesets):
            cognate_rename[
                cognateset
            ] = f"{dataset_path}.{slug_map[concept]}.{i + 1:03d}"

    # Replace the cognateset IDs in the entries with the new names
    for entry in entries:
        if entry["Cognateset"]:
            entry["Cognateset"] = cognate_rename[entry["Cognateset"]]

    # Obtain the commit hash of the dataset, for versioning purposes
    commit = (
        subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=dataset_path, capture_output=True
        )
        .stdout.decode("utf-8")
        .strip()
    )

    # Read the bibliographic information, if available
    if (dataset_path / "sources.bib").exists():
        with open(dataset_path / "sources.bib") as f:
            sources = f.read()
    else:
        sources = ""

    return entries, commit, sources


def apply_corrections(entries):
    """
    Apply custom corrections to the raw data.
    """

    # Load the list of ASJP corrections from disk as a dictionary,
    # using the `Language` column as key
    with open(ROOT_PATH / "etc" / "asjp_corrections.csv") as f:
        reader = csv.DictReader(f)
        asjp_corrections = {row["language"]: row for row in reader}

    # Apply the corrections to all entries: if `asjp_corrections` contains
    # a `glottocode` field, replece the `glottocode` field in the entry;
    # if it contains a `force_include` field, set a new field `force_include`
    # in the entry to True (otherwise, set it to False)
    for entry in entries:
        if entry["Language"] in asjp_corrections:
            if "glottocode" in asjp_corrections[entry["Language"]]:
                entry["Glottocode"] = asjp_corrections[entry["Language"]]["glottocode"]

            if "force_include" in asjp_corrections[entry["Language"]]:
                entry["force_include"] = True
            else:
                entry["force_include"] = False

    return entries


def filter_entries(entries):
    """
    Filter the entries.
    """

    # Obtain a copy of glottolog
    glottolog = common.load_glottolog()

    # To filter entries, first check if the entry has a `force_include` field
    # set to True; if so, keep the entry. Otherwise, check if the family of
    # the glottocode associated with the entry is marked as "Artificial Language",
    # "Bookkeeping", "Speech Register" and similar in the `family` column of
    # `glottolog`; if so, remove the entry. Otherwise, keep the entry.
    filtered_entries = []
    for entry in entries:
        # Continue the loop for entries without a "Glottocode" field,
        # unless the entry has a `force_include` field set to True
        if not entry["Glottocode"]:
            if not entry.get("force_include", False):
                continue
        elif glottolog[entry["Glottocode"]]["family"] in [
            "Artificial Language",
            "Bookkeeping",
            "Speech Register",
        ]:
            continue

        filtered_entries.append(entry)

    return filtered_entries


def main():
    """
    Main function.
    """

    # Read the raw ASJP dataset and apply corrections
    asjp_entries, asjp_commit, asjp_sources = read_cldf_dataset("raw")
    asjp_entries = apply_corrections(asjp_entries)

    # Filter data
    print(len(asjp_entries))
    asjp_entries = filter_entries(asjp_entries)
    print(len(asjp_entries))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
