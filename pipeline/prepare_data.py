# Import Python standard libraries
import csv
from pathlib import Path

# Setup paths
BASE_PATH = Path(__file__).parent
ROOT_PATH = BASE_PATH.parent

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
    with open(BASE_PATH / "raw" / "languages.csv", encoding="utf-8") as handler:
        langmap = {row["ID"]: row for row in csv.DictReader(handler)}

    # Read and cache the custom orthographic profile
    with open(BASE_PATH / "etc" / "orthography.tsv", encoding="utf-8") as handler:
        profile = {
            row["GRAPHEME"]: row["IPA"]
            for row in csv.DictReader(handler, delimiter="\t")
        }

    # Read the source data
    data = []
    with open(BASE_PATH / "raw" / "asjp19Clustered.csv", encoding="utf-8") as handler:
        for row in csv.DictReader(handler):
            # Get language id and classification
            tokens = row["language"].split(".")
            classification = ".".join(tokens[:-1])
            lang_id = tokens[-1]

            # Get language information
            glottocode = langmap[lang_id]["Glottocode"]
            glottoname = langmap[lang_id]["Glottolog_Name"]
            glottoclass = langmap[lang_id]["classification_glottolog"]
            iso_code = langmap[lang_id]["ISO639P3code"]

            # Extend the data with the current entry
            # TODO: redo IDs so they are indeed unique
            # TODO: use glottolog classification for the cogid
            # TODO: pick the "best" doculect for each glottocode
            # TODO: map to concepticon-like
            data.append(
                {
                    "ID": f"{lang_id}_{row['concept']}",
                    "LANG_ID": lang_id,
                    "LANGUAGE_NAME": glottoname,
                    "GLOTTOCODE": glottocode,
                    "ISOCODE": iso_code,
                    "CONCEPT": row["concept"],
                    "ASJP_FORM": row["word"],
                    "TOKENS": get_orthography(row["word"], profile),
                    "COGID": f"{classification}_{row['cc']}",
                }
            )

    return data


def write_data(data):
    """
    Write final aggregated single table to disk.
    """

    with open(BASE_PATH / "output" / "full_data.csv", "w", encoding="utf-8") as handler:
        writer = csv.DictWriter(
            handler,
            fieldnames=[
                "ID",
                "LANG_ID",
                "LANGUAGE_NAME",
                "GLOTTOCODE",
                "ISOCODE",
                "CONCEPT",
                "ASJP_FORM",
                "TOKENS",
                "COGID",
            ],
        )
        writer.writeheader()
        writer.writerows(data)


def main():
    # Read data from Jäger, extending language information and adding
    # transcriptions
    jaeger = read_jaeger()

    # TODO: do some sorting

    # Write aggregated table to disk
    write_data(jaeger)


if __name__ == "__main__":
    main()
