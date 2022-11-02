# Functions and data shared among different scripts

# Import Python standard libraries
import logging
import string
import re

# Import 3rd-party libraries
import unidecode

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

    logging.debug("Label slugged to `%s`.", label)

    return label
