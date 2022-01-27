# A Global Lexical Dataset (GLED) with cognate annotation and phonological alignment

This repository contains a dataset derived from a subset of ASJP,
carrying X lemmas for Y languages and Z families. All lemmas are
given in a broad IPA transcription, automatically annotated for
cognacy (for a total o W cognate set), and phonologically aligned.

## Contents

The main file released by this project is `gled.tsv` a single textual
tabular file that contains the entirety of the data. This file is
accompanied by a dataset description following the Frictionless
standard in `gled.yaml`, but the latter is not necessary if you
open the main file as a tabular source within a programming
language or a spreadsheet program. A CLDF version of the dataset
will be generated alongside the standalone tabular file
starting from a future release.

The entire software pipeline for downloading, processing, and
releasing new versions of the dataset is available in the `pipeline/`
directory. Please note that, due to processing time necessary for
the core step of automatic cognate detection, the entire process
can take days on a normal desktop or laptop computer.

## Community guidelines

While the author can be contacted directly for support, it is recommended that
third parties use GitHub standard features, such as issues and pull requests, to
contribute, report problems, or seek support.

Contributing guidelines, including a code of conduct, can be found in the
`CONTRIBUTING.md` file.

## Author and citation

The library is developed by Tiago Tresoldi (tiago.tresoldi@lingfil.uu.se). The library is developed in the context of
the [Cultural Evolution of Texts](https://github.com/evotext/) project, with funding from the
[Riksbankens Jubileumsfond](https://www.rj.se/) (grant agreement ID:
[MXM19-1087:1](https://www.rj.se/en/anslag/2019/cultural-evolution-of-texts/)).

If you use `GLED`, please cite it as:

> Tresoldi, T., (2022).

In BibTeX:

```
@article{Tresoldi2022gled,
  year = {2022},
  author = {Tiago Tresoldi},
  title = {A Global Lexical Dataset (GLED) with cognate annotation and phonological alignment},
}
```
