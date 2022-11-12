#!/usr/bin/env python3

"""
Run Bayesian analyses and collect results.
"""

# Import Python standard libraries
from pathlib import Path
import glob
import logging
import re
import subprocess

# Import other modules
import common

BASE_PATH = Path(__file__).parent

# Define path to executables
BEAST2_PATH = Path("/home/tiagot/software/BEAST.v2.6.7.Linux/beast/bin")


def run_inference(BAYES_PATH, languoids):

    # Collect all models
    models_pattern = BAYES_PATH / "*.xml"
    for model in glob.glob(str(models_pattern)):
        model_filename = Path(model)
        basename = model_filename.stem
        logging.info(f"Running BEAST2 for {basename}...")

        # Run BEAST2
        subprocess.run(
            [
                str(BEAST2_PATH / "beast"),
                model_filename.name,  # quote names with spaces
            ],
            cwd=BAYES_PATH,
        )

        # Run Treeannotator
        # TODO: move to phyltr?
        temp_tree = BAYES_PATH / f"{basename}.temp.tree"
        subprocess.run(
            [
                str(BEAST2_PATH / "treeannotator"),
                "-burnin",
                "50",
                "-noSA",
                f"{basename}.nex",
                str(temp_tree),
            ],
            cwd=BAYES_PATH,
        )

        # Load list of languages and replace their names in the final tree
        with open(temp_tree) as handler:
            nexus = handler.read()

        base_nex = BAYES_PATH / f"{basename}.nex"
        with open(base_nex) as handler:
            taxa_list = False
            for line in handler.readlines():
                if "Taxlabels" in line:
                    taxa_list = True
                elif taxa_list:
                    if ";" in line:
                        break
                    else:
                        glottocode = line.strip()
                        nexus = nexus.replace(
                            glottocode,
                            common.slug(languoids[glottocode].name, level="simple"),
                        )

        output_tree = f"{model_filename.stem}.mcc.tree"
        with open(BAYES_PATH / output_tree, "w") as handler:
            handler.write(nexus)

        # Delete large and unnecessary files
        # TODO: study a way to keep all .nex files
        base_nex.unlink()
        temp_tree.unlink()

def collect_trees():
    """
    Collect all trees into a single, global tree.
    """

    pass

def main():
    """
    Script entry point.
    """

    # Instantiate `glottolog` object and cache languoids
    logging.info("Caching Glottolog languoids...")
    glottolog = common.get_glottolog()
    languoids = {}
    for lang in glottolog.languoids():
        languoids[lang.glottocode] = lang
    logging.info(f"Cached {len(languoids)} languoids.")

    # Grab the path to the latest release, and create the Bayesian
    # directory if possible
    releases = sorted(glob.glob(str(BASE_PATH.parent / "releases" / "*")))
    BAYES_PATH = Path(releases[-1]) / "bayesian"

    run_inference(BAYES_PATH, languoids)
    collect_trees()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
