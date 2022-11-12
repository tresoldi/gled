# Functions and data shared among different scripts

# Import Python standard libraries
from pathlib import Path
import logging
import re
import string

# Import 3rd-party libraries
from unidecode import unidecode

# Import MPI-SHH libraries
from pyglottolog import Glottolog


def get_glottolog(glottolog_path=None):
    """
    Instantiates and returns a Glottolog object.
    """

    # If glottolog path was not provided, default to ~/.config/cldf/glottolog
    if not glottolog_path:
        glottolog_path = Path.home() / ".config" / "cldf" / "glottolog"
        glottolog_path = glottolog_path.as_posix()

    glottolog = Glottolog(glottolog_path)

    return glottolog


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
        label = label.replace("'", "__")

    logging.debug("Label slugged to `%s`.", label)

    return label
