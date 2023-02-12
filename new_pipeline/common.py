# Import from the standard library
from typing import *
import itertools
import re
import string
from pathlib import Path
import csv


def slug_label(label: str) -> str:
    """
    Return a slugged version of a label.
    Parameters
    ----------
    label : str
        The label to be slugged.
    Returns
    -------
    str
        A slugged version of the label.
    """

    # Delete contents inside parentheses and parantheses themselves, if any
    label = label.split("(")[0].strip()
    label = label.split("[")[0].strip()

    # Replace spaces with underscores
    label = re.sub(r"\s+", " ", label)
    label = label.replace(" ", "_")

    # Lower the characters in the label and keep only letters, numbers, and underscores
    label = "".join([c for c in label.lower() if c.isalnum() or c == "_"])

    return label


def unique_ids(labels: List[str]) -> List[str]:
    """
    Map a sequence of identifiers to a slugged version with unique identifiers.
    This function will add a suffix to the slugged version of the labels
    if there are more than one occurrence of the same label in the list.
    The suffix will be a letter, starting from "a" and going up to "zzz...".
    Parameters
    ----------
    labels : List[str]
        A list of labels to be slugged and made unique.
    Returns
    -------
    List[str]
        A list of slugged and unique labels.
    """

    def _label_iter():
        """
        Custom internal label iterator.
        -> "a", "b", ..., "aa", "ab", ..., "zz", "aaa", "aab", ...
        """
        for length in itertools.count(1):
            for chars in itertools.product(string.ascii_lowercase, repeat=length):
                yield "-" + "".join(chars)

    # Slugify all labels
    slugged = [slug_label(label) for label in labels]

    # Build a corresponding list with the count of previous occurrences of the same value
    loc_counts = [slugged[:idx].count(value) for idx, value in enumerate(slugged)]

    # Build a dictionary of suffixes using the maximum count
    # NOTE: This might look as an overkill, but will allow to easily
    #       adapt other models in the future
    label_iter = _label_iter()
    suffix = {count: next(label_iter) for count in range(max(loc_counts) + 1)}

    # Build the new list, adding the suffix if there is more than one
    # occurrence overall, and return
    unique_slug_labels = [
        f"{label}{suffix[loc_count]}" if slugged.count(label) > 1 else label
        for label, loc_count in zip(slugged, loc_counts)
    ]

    return unique_slug_labels


def load_glottolog():
    """
    Load a serialized version of the Glottolog database as a dictionary.
    """

    # Obtain the newest version of the Glottolog database
    etc_path = Path(__file__).parent / "etc"
    filename = sorted(etc_path.glob("glottolog.*.tsv"))[-1]

    # Load the contents of the TSV file as a dictionary, using column
    # `glottocode` as key
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter="\t")
        glottolog = {row["glottocode"]: row for row in reader}

    return glottolog
