# Import Python standard libraries
import csv
from pathlib import Path

# Setup paths
BASE_PATH = Path(__file__).parent
ROOT_PATH = BASE_PATH.parent

def read_jaeger():
    """
    Read and process the clustered data from Jäger (2021).
    """

    # Read the language mapping provided by the source
    with open(BASE_PATH/"raw"/"languages.csv", encoding="utf-8") as handler:
        langmap = {row["ID"]:row for row in csv.DictReader(handler)}

    # Read the source data
    data = []
    with open(BASE_PATH/"raw"/"asjp19Clustered.csv", encoding="utf-8") as handler:
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
            data.append({
                "ID":f"{lang_id}_{row['concept']}",
                "LANG_ID":lang_id,
                "LANGUAGE_NAME":glottoname,
                "GLOTTOCODE":glottocode,
                "ISOCODE":iso_code,
                "CONCEPT":row["concept"],
                "ASJP_FORM":row["word"],
                "COGID":f"{classification}_{row['cc']}",
            })

    return data

def main():
    jaeger = read_jaeger()


    print(jaeger)

if __name__ == "__main__":
    main()