# A Global Lexical Dataset (GLED) with cognate annotation and phonological alignment

Data and code for the Global Lexical Database (GLED), derived from ASJP

## Installation


Install all packages and supplementary data (preferably within a virtual environment). Note that this requires downloading a substantial amount of data, particularly for the catalogues of the CLDF ecosystem. This step is not necessary if you decide to use the precompiled data (distributed in `data/`).

```bash
$ pip install --upgrade pip setuptools wheel 
$ pip install -r requirements.txt
$ cldfbench catconfig -q
```
