# A Global Lexical Dataset (GLED) with cognate annotation and phonological alignment

Data and code for the Global Lexical Database (GLED), derived from ASJP

## Installation


Install all packages and supplementary data (preferably within a virtual environment). Note that this requires downloading a substantial amount of data, particularly for the catalogues of the CLDF ecosystem. This step is not necessary if you decide to use the precompiled data (distributed in `data/`).

```bash
$ pip install --upgrade pip setuptools wheel 
$ pip install -r requirements.txt
$ cldfbench catconfig -q
```

The first script will take the raw data for both the custom version of ASJP
and NorthEuraLex, stored in `raw/`, and store it in `data/`. The data is
separated in files according to the source and the linguistic family specified
in the source. It is not necessary to run this script yourself, as the
preprocessed data is distributed along with this repository.

```bash
$ python 01_prepare_data.py
```

The second and most computationally intensive script (probably taking
several hours to finish) will perform the
cognate detection using the extended LexStat method here presented, taking
the preprocessed data from `data/` and writing the results in the
`cluster/` directory. As mentioned above, this can executed with only
the "tidy requirements".

```bash
$ python 02_cluster.py
```

The results from the long clustering processing can be aggregated into
simple long-table tabular files in `output/`.

```bash
$ python 03_aggregate.py
```

Datafiles for phylogenetic analyses can be generated with the appropriate
script. This script is going to read data from `output/`.

```bash
$ python 04_prepare_phylo.py
```
