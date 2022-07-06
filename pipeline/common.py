"""
Utility data and functions for the world trees project.
"""

# Import Python standard libraries
from pathlib import Path
import re
import unidecode

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


def slug(label, drop_parentheses=False):
    """
    Returns a slugged version of a label.
    """

    if drop_parentheses:
        label = re.sub(r"\([^)]*\)", "", label)

    label = label.strip()
    label = re.sub(r"\s+", "_", label)
    label = label.replace("-", "_")
    label = unidecode.unidecode(label)
    label = label.lower()

    for delchar in ".!,?*'":
        label = label.replace(delchar, "")

    return label
