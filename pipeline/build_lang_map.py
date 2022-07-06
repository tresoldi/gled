#!/usr/bin/env python3

"""
Build the language mapping in a reproducible way.
"""

# TODO: rewrite code, make it beautiful, etc.

from asyncore import write
import csv
from pathlib import Path
from collections import Counter, defaultdict
import common
import difflib

BASE_PATH = Path(__file__).parent

# Define custom mappings as code/proxy pairs
CUSTOM_MAPPING = {
    "ARAMAIC_ANCIENT": ["olda1246", ""],
    "BANKALA": ["bank1257", ""],
    "COLAN": ["cola1238", ""],
    "DJADJALA": ["*DJADJALA", "werg1234"],  # proxy
    "DJAPU": ["djap1238", ""],
    "GANDANGARA": ["*GANDANGARA", "gund1248"],  # proxy
    "GUARANI_ANTIGO": ["oldp1258", ""],
    "HELSINKI_STADIN_SLANGI": ["", ""],  # delete
    "HOAN": ["dzuo1238", ""],
    "JIRINGAYN": ["*JIRINGAYN", "sout2771"],  # proxy
    "KAWA": ["", ""],  # delete
    "KERAMIN": ["kera1256", ""],
    "KITANEMUK": ["kita1252", ""],
    "LATE_EGYPTIAN": ["late1256", ""],
    "MIDDLE_EGYPTIAN": ["midd1369", ""],
    "MOMI_YADIM": ["momi1241", ""],
    "OAS": ["oass1237", ""],
    "OGADEN_ARABIC": ["", ""],  # delete
    "OMEO": ["*OMEO", "sout2770"],  # proxy
    "SOUTH_EASTERN_GONDI": ["sout3234", ""],
}


def main():
    table = []

    # Instantiate `glottolog` object and cache languoids
    print("Caching Glottolog languoids...")
    glottolog = common.get_glottolog()
    languoids = {}
    for lang in glottolog.languoids():
        languoids[lang.glottocode] = lang

    # Load all languages in the raw CLDF data
    with open(
        BASE_PATH / "raw" / "asjp" / "languages.csv", encoding="utf-8"
    ) as handler:
        data = list(csv.DictReader(handler))

    # Collect all glottocodes with a single doculect mapping and add to the table;
    # note that we exclude reconstructions
    occur = Counter([entry["Glottocode"] for entry in data if entry["Glottocode"]])
    singletons = [key for key, value in occur.most_common() if value == 1]
    for entry in data:
        if entry["Glottocode"] in singletons:
            if entry["Name"].startswith("PROTO_"):
                continue

            table.append(
                {
                    "ID": entry["ID"],
                    "NAME": entry["Name"],
                    "GLOTTOCODE": entry["Glottocode"],
                    "PROXY": "",
                }
            )

    # For all glottocodes with more than one occurrence, use the one
    # with the shortest name (if there is a single one if that length)
    gc2name = defaultdict(list)
    for entry in data:
        if occur[entry["Glottocode"]] > 1:
            gc2name[entry["Glottocode"]].append(entry)

    for gc, entries in gc2name.items():
        min_len = min([len(entry["Name"]) for entry in entries])
        filter = [entry for entry in entries if len(entry["Name"]) == min_len]
        if len(filter) == 1:
            table.append(
                {
                    "ID": filter[0]["ID"],
                    "NAME": filter[0]["Name"],
                    "GLOTTOCODE": filter[0]["Glottocode"],
                    "PROXY": "",
                }
            )
        else:
            # Get the closest match to the glottolog name for the language
            lid = languoids[gc]
            glottolog_name = lid.name.lower()
            name_map = {e["Name"].lower(): e for e in filter}
            closest = difflib.get_close_matches(
                glottolog_name, list(name_map), cutoff=0.0
            )
            table.append(
                {
                    "ID": name_map[closest[0]]["ID"],
                    "NAME": name_map[closest[0]]["Name"],
                    "GLOTTOCODE": name_map[closest[0]]["Glottocode"],
                    "PROXY": "",
                }
            )

    # Add custom mappings
    excludes = []
    for name, (gc, proxy) in CUSTOM_MAPPING.items():
        if gc:
            excludes.append(name)
            table.append(
                {
                    "ID": name,
                    "NAME": name,
                    "GLOTTOCODE": gc,
                    "PROXY": proxy,
                }
            )

    # Treat entries without glottocode
    missing = [entry for entry in data if not entry["Glottocode"]]
    missing = [entry for entry in missing if entry["Name"] not in excludes]
    missing = [entry for entry in missing if not entry["Name"].startswith("PROTO_")]
    missing = [
        entry for entry in missing if "ARTIFICIAL" not in entry["classification_wals"]
    ]
    missing = [entry for entry in missing if not "NAHUATL" in entry["Name"]]
    for m in missing:
        print(m)
    print(".......... MISSING", len(missing))

    # Make sure there is a glottocode for all doculects, and only one doculect per glottocode
    glottocodes = [e["GLOTTOCODE"] for e in table if e["GLOTTOCODE"]]
    assert len(glottocodes) == len(table)
    assert len(set(glottocodes)) == len(table)

    # Output the complete table
    table = sorted(table, key=lambda l: l["NAME"])
    with open(
        BASE_PATH / "etc" / "custom_mapping.csv", "w", encoding="utf-8"
    ) as handler:
        writer = csv.DictWriter(
            handler, fieldnames=["ID", "NAME", "GLOTTOCODE", "PROXY"]
        )
        writer.writeheader()
        writer.writerows(table)


if __name__ == "__main__":
    main()
