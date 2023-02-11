"""
Common functions for the library.
"""

# Import standard libraries
import re
from pathlib import Path
from typing import *

ETC_PATH = Path(__file__).parent / "etc"

def read_matrix(filename:Union[Path, str]) -> Dict[str, Dict[str, float]]:
    """
    Read a distance matrix from a file.

    The distance matrix is returned as a dictionary of dictionaries,
    with each value as a dictionary to all other taxa.

    Parameters
    ----------
    filename
        The file to read.
    
    Returns
    -------
    matrix
        A dictionary of dictionaries, where the first key is the taxon and the
        second key is the taxon to which the distance is computed.
    """

    # Read raw data
    header = True
    taxa = []
    matrix = {}
    with open(Path(filename), encoding="utf-8") as handler:
        for line in handler.readlines():
            if header:
                header = False
            else:
                line = re.sub(r"\s+", " ", line)
                tokens = line.split()
                taxon = tokens[0]
                taxa.append(taxon)
                dists = [float(dist) for dist in tokens[1:]]
                matrix[taxon] = dists

    # Make an actual dictionary matrix
    ret_matrix = {}
    for taxon_a, dists in matrix.items():
        ret_matrix[taxon_a] = {taxon_b: dist for dist, taxon_b in zip(dists, taxa)}

    return ret_matrix

def read_default_matrix() -> Dict[str, Dict[str, float]]:
    """
    Read the default global distance matrix.

    Returns
    -------
    matrix
        A dictionary of dictionaries, where the first key is the taxon and the
        second key is the taxon to which the distance is computed.
    """

    # TODO: read the latest version
    return read_matrix(ETC_PATH / "global.20221127.dst")