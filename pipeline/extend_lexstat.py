# Import Python standard libraries
from collections import defaultdict, Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
import csv
import itertools
import random
from importlib_metadata import Pair

# Import 3rd party libraries
from lingpy import LexStat
import igraph

from build_lang_map import BASE_PATH

# Whether to use the extended lexstat method or grab data from other sources
USE_ELEXSTAT = True


def write_wordlist(wordlist):
    """
    Write a wordlist to a temporary file.
    """

    handler = NamedTemporaryFile("w", encoding="utf-8", delete=False)
    writer = csv.DictWriter(
        handler, delimiter="\t", fieldnames=list(wordlist[0].keys())
    )
    writer.writeheader()
    writer.writerows(wordlist)
    handler.close()

    return handler.name


def write_lingpy(data):
    """
    Write a lingpy wordlist to a temporary file.

    We build a "normal" wordlist from the data, and then call `write_wordlist()`.
    """

    fields = data[0]
    new_data = [
        {field: value for field, value in zip(fields, row)}
        for idx, row in data.items()
        if idx != 0
    ]

    return write_wordlist(new_data), new_data


def join_partials(filenames, output_file, method="leiden"):
    # Stores the full data (using IDs as keys), so we don't need to read all
    # files again; note that this will carry the COGID information of the
    # last occurence, which will be replaced later
    full_data = {}

    # Store the new cognates from the partial analysis (note that original cogids
    # without a new set will me missing from here)
    cognate_map = {}

    # Iterate over all files
    edges = defaultdict(list)
    ids_obs = defaultdict(list)
    for filename in filenames:
        with open(filename, encoding="utf-8") as handler:
            # Read contents while removing LingPy comments
            partial = list(csv.DictReader(handler, delimiter="\t"))
            partial = [row for row in partial if not row["ID"].startswith("#")]

        # Extend information on which IDs are found in the same partial analysis
        # (so that we can correct by frequency, as we might get unlucky and
        # have only one or none)
        tiago = defaultdict(set)
        for row in partial:
            tiago[row["CONCEPT"]].add(row["ID"])
        for conc, ids in tiago.items():
            ids_obs[conc] += list(itertools.combinations(sorted(ids), 2))

        # Collect IDs by COGID in this partial; note that the concept would not
        # be needed here (there is no detection of cognates in different concepts
        # in vanilla LexStat), but this helps us carry the information to
        # the next step and later reduce the size of the graphs
        cset = defaultdict(list)
        for row in partial:
            # Update the local `cset`
            cset[row["COGID"], row["CONCEPT"]].append(row["ID"])

            # Store info in the `full_data` for later reuse
            full_data[row["ID"]] = row

        # For each combination in each cogid, extend the `edges` graph
        for (cogid, concept), ids in cset.items():
            combs = list(itertools.combinations(ids, 2))
            edges[concept] += combs

    # Create a count of the observed pairs, for correction
    ids_obs = {conc: Counter(obs) for conc, obs in ids_obs.items()}

    # Use the information in `edges` to build a graph
    for concept, pairs in edges.items():
        print(f"Detecting cognates for concept `{concept}`")

        # Build a weighted tuple for `igraph` and graph
        wtuple = []
        for pair, count in Counter(pairs).most_common():
            obs = ids_obs[concept][tuple(sorted(pair))]
            wtuple.append((pair[0], pair[1], float(count) / obs))
        G = igraph.Graph.TupleList(wtuple, edge_attrs=["weight"])

        # Community detection with infomap
        if method == "infomap":
            comm = G.community_infomap(edge_weights="weight", trials=50)
        elif method == "label_propagation":
            comm = G.community_label_propagation(weights="weight")
        elif method == "leading_eigenvector":
            comm = G.community_leading_eigenvector(weights="weight")
        elif method == "leiden":
            comm = G.community_leiden(
                weights="weight", resolution_parameter=0.9, n_iterations=-1
            )
        else:
            raise ValueError(f"Unknown method `{method}`")

        for i in range(len(comm)):
            for j in comm[i]:
                cognate_map[G.vs[j]["name"]] = (concept, i)

    # Set new cognates, building a wordlist-like structure
    wordlist = []
    cogids = sorted(set(cognate_map.values()))
    next_cognate = len(cogids) + 2
    for row in full_data.values():
        # Get the index for the new cognate in `cogids` and, if not found,
        # use the next free available one
        if row["ID"] in cognate_map:
            n = cogids.index(cognate_map[row["ID"]]) + 1
        else:
            n = next_cognate
            next_cognate += 1

        row["COGID"] = str(n)
        wordlist.append(row)

    # Output
    with open(output_file, "w", encoding="utf-8") as handler:
        writer = csv.DictWriter(
            handler, delimiter="\t", fieldnames=list(wordlist[0].keys())
        )
        writer.writeheader()
        writer.writerows(wordlist)


def elexstat(
    data,
    output,
    cogid="COGID",
    doculect="DOCULECT",
    runs=10000,
    threshold=0.55,
    gop=-2.0,
    cluster="infomap",
    mode="global",
    method="lexstat",
    limit=10000,
    confidence=0.99,
    tau=1.5,
    temp_dir=None,
):
    """
    Wrapper for Lexstat.
    """

    # If `data` is a list, assume it is a "normal" wordlist
    # (i.e., a list of dictionaries such as the ones returned
    # by the `csv` standard library); if `data` is a
    # dictionary, assume it is LingPy wordlist. By default
    # assume `data` is a pointer (such as a string or a
    # Pathlib object) to an in-disk wordlist.
    if isinstance(data, dict):
        # LingPy wordlist, write to disk and store the path
        num_rows = len(data) - 1
        wordlist_file, wordlist = write_lingpy(data)
    elif isinstance(data, list):
        # Wordlist as list of dictionaries, write to disk and
        # store the path
        num_rows = len(data)
        wordlist_file = write_wordlist(data)
        wordlist = data
    else:
        # Path to a wordlist
        wordlist_file = str(data)
        with open(wordlist_file, encoding="utf-8") as handler:
            wordlist = list(csv.DictReader(handler, delimiter="\t"))
            num_rows = len(wordlist)

    # If we are below the threshold of the number of entries,
    # we can just call lexstat in the normal way; otherwise,
    # we need to proceed with sub-detection
    if num_rows > limit:
        if USE_ELEXSTAT:
            # Grab doculects for random selection and compute the
            # mean number of entries per doculect and the subset
            # size
            entries = defaultdict(int)
            for row in wordlist:
                entries[row[doculect]] += 1

            # TODO: deal with correction factor
            doculects = sorted(entries.keys())
            mean = sum(entries.values()) / len(doculects)
            subset_size = int(limit / (mean * tau))

            # Compute the number of subanalyses from an
            # estimation of the probability of each pairwise
            # being observed at least once
            obs = (subset_size / len(doculects)) ** 2
            iters = int(confidence / obs) + 1
            partials = []
            observed = set()
            for filenum in range(iters + 1):
                # First obtain doculects that are missing (we use a random
                # drawing here as well)
                missing = [
                    doculect for doculect in doculects if doculect not in observed
                ]
                if not missing:
                    # Get sample of doculects and filter the data
                    sample = random.sample(doculects, subset_size)
                else:
                    if len(missing) >= subset_size:
                        sample = random.sample(missing, subset_size)
                    else:
                        sample = missing + random.sample(
                            [
                                doculect
                                for doculect in doculects
                                if doculect not in missing
                            ],
                            subset_size - len(missing),
                        )

                observed = observed.union(sample)

                fdata = [row for row in wordlist if row[doculect] in sample]

                # Write temporary file (as unfortunately LexStat does
                # not accept in-memory wordlists as the `Wordlist`
                # class)
                if temp_dir:
                    temp_file = str(Path(temp_dir) / f"elxs.{filenum}")
                else:
                    temp_file = str(Path("/tmp") / f"elxs.{filenum}")

                partials.append(f"{temp_file}.tsv")
                elexstat(
                    fdata,
                    temp_file,
                    cogid,
                    doculect,
                    runs,
                    threshold,
                    gop,
                    cluster,
                    mode,
                    method,
                )

            # Join results
            join_partials(partials, f"{output}.tsv")
            print(
                f"EXTEND_LEXSTAT: Wrote results using partial method to `{output}.tsv`"
            )
        else:
            # large dataset, dont use elexstat
            pass
    else:
        lex = LexStat(wordlist_file)
        lex.get_scorer(runs=runs)
        lex.cluster(
            method=method,
            threshold=threshold,
            ref=cogid,
            mode=mode,
            gop=gop,
            cluster_method=cluster,
        )
        lex.output("tsv", filename=output, prettify=False)
        print(f"EXTEND_LEXSTAT: Wrote results using normal method to `{output}.tsv`")
