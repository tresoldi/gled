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

Due to incompatibilities in the CLLD framework (such as the dependency of
`beastling` on older version of `clldutils`) a different virtual environment,
as specified by `pipeline/requirements-beastling.txt` is necessary. The
process is currently rather cumbersome, as we need to use both
`beastling` and our patched version of the same, which involves generating
temporary files, etc. An auxiliary script takes care of that: once
this has been created and activated, the running of `beastling` can
be performed with

```bash
$ pipeline/prepare_beastling.py
```

At last, the Bayesian analyses (which take *a long* time) can be
run with the following script (the path to the executables must
be set at the top):

```bash
$ pipeline/run_bayesian.py
```

A stand-alone script can now be used
to generate the plots and images for the paper and for the README:

```bash
$ pipeline/build_figures.py
```
