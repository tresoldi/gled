"""
Setup script for `arcaverborum` package.
"""

# Import Python standard libraries
from setuptools import setup, find_packages
import glob
import pathlib

# The directory containing this file
LOCAL_PATH = pathlib.Path(__file__).parent

# The text of the README file
README_FILE = (LOCAL_PATH / "arcaverborum.md").read_text(encoding="utf-8")

# Load requirements, so they are listed in a single place
with open("requirements.txt", encoding="utf-8") as fp:
    install_requires = [dep.strip() for dep in fp.readlines() if dep.strip()]

# This call to setup() does all the work
setup(
    author="Tiago Tresoldi",
    author_email="tiago.tresoldi@lingfil.uu.se",
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Text Processing :: Linguistic",
    ],
    description="Library for interfacing with data from the GLED project",
    extras_require={
        "dev": ["black", "flake8", "twine", "wheel"],
        "test": ["pytest"],
    },
    include_package_data=True,
    install_requires=install_requires,
    keywords=[
        "linguistics",
        "typology",
        "sampling",
    ],
    license="MIT",
    long_description=README_FILE,
    long_description_content_type="text/markdown",
    name="arcaverborum",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    test_suite="tests",
    tests_require=[],
    url="https://github.com/tresoldi/arcaverborum",
    version="0.1.4",  # remember to sync with __init__.py
    zip_safe=False,
)
