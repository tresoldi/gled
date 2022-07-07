#!/usr/bin/env python3

"""
Script for preparing running cognate detection using the extendend method.
"""

import glob
import logging
from pathlib import Path
from extend_lexstat import elexstat

BASE_PATH = Path(__file__).parent


def main():
    """
    Script entry point.
    """

    # Grab all files and process one by one
    datafiles = glob.glob(str(BASE_PATH / "data" / "*.tsv"))
    datafiles = [filename for filename in datafiles if "FULL_DATA" not in filename]
    datafiles = [filename for filename in datafiles if "gled." not in filename]
    for datafile in sorted(datafiles):
        base_name = datafile.split("/")[-1][:-4]
        logging.info("Clustering file `%s`...", base_name)

        # Build output path and only perform cognate detection if the
        # output file does not exist; note that due to LexStat
        # automatically appending a .tsv extension, we need to
        # build two names here
        check_file = BASE_PATH / "cluster" / f"{base_name}.tsv"
        if Path(check_file).is_file():
            logging.info("Skipping over (results already there).")
        else:
            output = BASE_PATH / "cluster" / base_name
            elexstat(datafile, str(output), limit=15000, confidence=0.9)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
