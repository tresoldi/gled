# A Global Lexical Dataset (GLED) with cognate annotation and phonological alignment

Data and code for the Global Lexical Database (GLED), derived from ASJP

## Installation


Install all packages and supplementary data (preferably within a virtual environment). Note that this requires downloading a substantial amount of data, particularly for the catalogues of the CLDF ecosystem. This step is not necessary if you decide to use the precompiled data (distributed in `data/`).

```bash
$ pip install --upgrade pip setuptools wheel 
$ pip install -r requirements.txt
$ cldfbench catconfig -q
```

## Running

Two steps are necessary for a new release: the data preparation from the raw sources, includign cognate detection and analysis, and the data release that build the files to be distributed. The two steps can be carried from the command line:

```bash
$ pipeline/prepare_data.py
$ pipeline/prepare_release.py
```

In order to include the Bayesian phylogenetics, which take a very long time to
run, one first needs to prepare the phylogenetic data:

```bash
$ pipeline/prepare_bayesian.py
```