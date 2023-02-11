# __init__.py

# Set the metadata for the package
__author__ = "Tiago Tresoldi"
__email__ = "tiago.tresoldi@lingfil.uu.se"
__version__ = "0.1.4"

# Local imports
from .common import read_matrix, read_default_matrix
from .sampling import language_sample

# Expose the functions
all = ["read_matrix", "read_default_matrix", "language_sample"]