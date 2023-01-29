"""
Functions for obtaining language samples.
"""

# Import from standard library
from typing import *
import itertools
import random


def language_sample(
    matrix: Dict[str, Dict[str, float]],
    k: int,
    method: str = "mean",
    tries: int = 100,
    seed: Optional[Union[int, str]] = None,
):
    """
    Obtain a language sample from a distance matrix.

    Parameters
    ----------
    matrix
        A dictionary of dictionaries, where the first key is the taxon and the
        second key is the taxon to which the distance is computed.
    k
        The number of languages to sample.
    method
        The method to use to compute the weight of a sample. Can be either
        "mean" or "sum".
    tries
        The number of attempts to make to obtain a good sample.
    seed
        The seed to use for the random number generator. If None, the seed
        will be set to the current time.

    Returns
    -------
    sample
        A tuple of the sampled languages.
    """

    # Set the seed for the random number generator
    random.seed(seed)

    # Extract doculects
    lects = sorted(matrix.keys())

    # Run different attempts to get a good sample
    candidates = []
    for i in range(tries):
        # Get a sample, compute the total and mean distances, and store
        sampled_lects = tuple(random.sample(lects, k))
        dists = []
        for lang1, lang2 in itertools.combinations(sampled_lects, 2):
            dists.append(matrix[lang1][lang2])

        # Store the current candidate along with its weight
        if method == "mean":
            candidates.append((sampled_lects, sum(dists) / k))
        elif method == "sum":
            candidates.append((sampled_lects, sum(dists)))

    # Sort and return
    # TODO: implement weight as well
    ret = sorted(candidates, reverse=True, key=lambda e: e[1])

    return ret[0][0]
