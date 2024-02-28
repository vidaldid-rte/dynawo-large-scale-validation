#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Adapted from dynaflow directory
#
#
import math
import os
import random
import re
import sys
from collections import namedtuple
from common_funcs import parse_basecase, copy_basecase
from lxml import etree
import pandas as pd
import argparse

# Relative imports only work for proper Python packages, but we do not want (yet) to
# structure all these as a package; we'd like to keep them as a collection of loose
# Python scripts, at least for now (after all, this is not really a Python library). So
# the following hack is ugly, but needed:
sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
# Alternatively, you could set PYTHONPATH to PYTHONPATH="/<dir>/dynawo-validation-AIA"


HADES_FILE = "entreeHades.xml"
OLF_FILE = "entreeOLF.xiidm"
PARAM_FILE = "OLFParams.json"

parser = argparse.ArgumentParser()
parser.add_argument(
    "-t",
    "--txt",
    help="enter regular expressions or contingencies in text form, by default, "
    "all possible contingencies will be generated (if below MAX_NCASES; "
    "otherwise a random sample is generated)",
)
parser.add_argument(
    "-v", "--verbose", help="increase output verbosity", action="store_true"
)
parser.add_argument(
    "-l",
    "--list",
    help="enter regular expressions or contingencies in "
    "string form separated with pipe(|)",
)
parser.add_argument(
    "-m",
    "--max",
    type=int,
    default=20,
    help="maximum number of contingencies to generate",
)
parser.add_argument(
    "-a", "--allcontg", help="generate all the contingencies", action="store_true"
)
parser.add_argument(
    "-r",
    "--randomc",
    help="generate a different random sample of contingencies",
    action="store_true",
)
parser.add_argument(
    "-p",
    "--prandom",
    help="generate a different random sample of contingencies with defined seed",
)
parser.add_argument(
    "--minP",
    type=int,
    default=0,
    help="minimum power for contingencies",
)
parser.add_argument(
    "--maxP",
    type=int,
    default=-1,
    help="minimum power for contingencies",
)
parser.add_argument("base_case", help="base case directory")
args = parser.parse_args()


def main():
    RNG_SEED = 42
    max_ncases = args.max
    # args management
    filter_list = []
    verbose = False
    if args.verbose:
        verbose = args.verbose
    base_case = args.base_case
    if args.list:
        temp_list = args.list.split("|")
        filter_list = [re.compile(x) for x in temp_list]
        while re.compile("") in filter_list:
            filter_list.remove(re.compile(""))
    if args.txt:
        with open(args.txt) as f:
            filter_list = [re.compile(x) for x in f.read().split(os.linesep)]
            while re.compile("") in filter_list:
                filter_list.remove(re.compile(""))
    if args.randomc:
        RNG_SEED = random.randint(1, 1000)
    if args.prandom:
        RNG_SEED = int(args.prandom)

    # remove a possible trailing slash
    if base_case[-1] == "/":
        base_case = base_case[:-1]

    # Contingency cases will be created under the same dir as the basecase
    dirname = os.path.dirname(os.path.abspath(base_case))

    print("RNG_SEED used to create contingencies = " + str(RNG_SEED))


    # Parse all XML files in the basecase
    parsed_case = parse_basecase(
        base_case, HADES_FILE, OLF_FILE
    )

    print(f"Creating contingencies from OLF-vs-HADES case: {base_case}")

    # Extract the list of all (active) GENS in the Dynawo case
    olf_gens = extract_olf_gens(parsed_case.olf_tree, verbose)
    # And reduce the list to those GENS that are matched in Hades
    olf_gens = matching_in_hades(parsed_case.hades_tree, olf_gens, verbose)

    # finally only keep those with active power greater than minP
    olf_gens = {gen:olf_gens[gen] for gen in olf_gens if abs(olf_gens[gen].P) >= args.minP}
    if args.maxP > 0:
        olf_gens = {gen: olf_gens[gen] for gen in olf_gens if abs(olf_gens[gen].P) <= args.maxP}
        print("   (kept {0} gens with {1} <= P <= {2})\n".format(len(olf_gens), args.minP, args.maxP))
    else:
        print("   (kept {0} gens with P >= {1})\n".format(len(olf_gens), args.minP))

    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = max_ncases / len(olf_gens)
        random.seed(RNG_SEED)
        if len(filter_list) == 0 and sampling_ratio < 1:
            print(
                "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
                % (max_ncases, 100 * sampling_ratio)
            )
    else:
        sampling_ratio = 1



    # This dict will keep track of which contingencies are actually processed
    # It will also keep Hades's (P,Q) of each gen
    processed_gensPQ = dict()

    # Main loop: generate the contingency cases
    for gen_name in olf_gens:

        # If the script was passed a list of generators, filter for them here
        gen_name_matches = [r.search(gen_name) for r in filter_list]
        if len(filter_list) != 0 and not any(gen_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating contingency case for gen %s (at bus: %s)"
            % (gen_name, olf_gens[gen_name].bus)
        )

        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = os.path.join(dirname,  "gen#" + gen_name.replace("/", "+").replace(" ","_"))

        # Copy the basecase (unchanged files and dir structure)
        copy_basecase(base_case, OLF_FILE, HADES_FILE, PARAM_FILE, contg_casedir)
        # Modify the Dynawo case (DYD,PAR,CRV)
        config_olf_gen_contingency(
            contg_casedir,
            parsed_case.olf_tree,
            gen_name,
        )
        # Modify the Hades case, and obtain the disconnected generation (P,Q)
        processed_gensPQ[gen_name] = config_hades_gen_contingency(
            contg_casedir, parsed_case.hades_tree, gen_name
        )


    # Finally, save the (P,Q) values of disconnected gens in all *processed* cases
    save_total_genpq(dirname, olf_gens, processed_gensPQ)

    return 0


def extract_olf_gens(iidm_tree, verbose=False):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    gens = dict()
    Gen_info = namedtuple("Gen_info", "P Q genType bus busTopology")

    # We enumerate all gens and extract their properties
    for gen in root.iter("{%s}generator" % ns):
        P_val = float(gen.get("p")) if gen.get("p") is not None else float(gen.get("targetP"))
        if gen.get("q") is not None:
            Q_val = float(gen.get("q"))
        else:
            Q_val = float(gen.get("targetQ")) if gen.get("targetQ") is not None else math.nan
        # Skip disconnected (detection via p,q to accommodate BUS_BREAKER/NODE_BREAKER)
        if P_val == 0.0 and Q_val == 0.0:
            continue
        gen_name = gen.get("id")
        gen_type = gen.get("energySource")
        topo_val = gen.getparent().get("topologyKind")
        if topo_val == "BUS_BREAKER":
            bus_name = gen.get("bus")
        elif topo_val == "NODE_BREAKER":
            # To complex to generate contingencies in node breaker (we need to open a switch in all path)
            print(gen_name + " in node breaker technology. Ignoring")
            continue
        else:
            raise ValueError("TopologyKind not found for generator: %s" % gen_name)
        gens[gen_name] = Gen_info(
            P=P_val, Q=Q_val, genType=gen_type, bus=bus_name, busTopology=topo_val
        )

    print("\nFound %d ACTIVE gens in the IIDM file" % len(gens))
    if verbose:
        print("List of all ACTIVE gens in the IIDM file: (total: %d)" % len(gens))
        gen_list = sorted(gens.keys())
        if len(gen_list) < 10:
            print(gen_list)
        else:
            print(gen_list[:5] + ["..."] + gen_list[-5:])
        print()

    return gens


def matching_in_hades(hades_tree, olf_gens, verbose=False):
    # Retrieve the list of Hades gens
    root = hades_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesGroupes = reseau.find("./donneesGroupes", root.nsmap)
    hades_gens = set()  # for faster matching below
    for gen in donneesGroupes.iterfind("./groupe", root.nsmap):
        # Discard gens having noeud="-1"
        if gen.get("noeud") != "-1":
            hades_gens.add(gen.get("nom"))

    print("\nFound %d gens in Hades file" % len(hades_gens))
    if verbose:
        print("Sample list of all GENS in Hades file: (total: %d)" % len(hades_gens))
        gen_list = sorted(hades_gens)
        if len(gen_list) < 10:
            print(gen_list)
        else:
            print(gen_list[:5] + ["..."] + gen_list[-5:])
        print()

    # Match:
    new_list = [x for x in olf_gens.items() if x[0] in hades_gens]
    print("   (matched %d gens against Dynawo file)\n" % len(new_list))

    return dict(new_list)

def config_olf_gen_contingency(casedir, olf_tree, gen_name):
    iidm_file = os.path.join(casedir, OLF_FILE)
    print("   Configuring file %s" % iidm_file)
    root = olf_tree.getroot()

    olf_gen = None
    for generator in root.iterfind(".//iidm:generator", root.nsmap):
        if generator.get("id") == gen_name:
            olf_gen = generator
            break
    # the shunt should always be found, because they have been previously matched
    gen_bus = olf_gen.get("bus")
    if gen_bus is not None:
        del olf_gen.attrib["bus"]  # bus breaker case
    gen_node = olf_gen.get("node")
    if gen_node is not None:
        del olf_gen.attrib["node"] # node breaker case


    # Remove symbolic link if exists
    if os.path.exists(iidm_file):
        os.remove(iidm_file)
    olf_tree.write(
        iidm_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
        standalone=False,
    )
    # IMPORTANT: undo the changes we made, as we'll be reusing this parsed tree!
    if gen_bus is not None:
        olf_gen.set("bus", gen_bus)
    if gen_node is not None:
        olf_gen.set("node", gen_node)

    return


def config_hades_gen_contingency(casedir, hades_tree, gen_name):
    hades_file = os.path.join(casedir, HADES_FILE)
    print("   Configuring file %s" % hades_file)
    root = hades_tree.getroot()
    # Since Hades is a powerflow program, there is no "event" to configure. We simply
    # disconnect the generator by setting its noeud to "-1".
    # First find the gen in Hades and keep its P, Q values (for comnparing vs Dynawo)
    hades_gen = None
    reseau = root.find("./reseau", root.nsmap)
    donneesGroupes = reseau.find("./donneesGroupes", root.nsmap)
    for g in donneesGroupes.iterfind("./groupe", root.nsmap):
        if g.get("nom") == gen_name:
            hades_gen = g
            break
    # the gen should always be found, because they have been previously matched
    gen_vars = hades_gen.find("./variables", root.nsmap)
    gen_P = -float(gen_vars.get("pc"))
    gen_Q = -float(gen_vars.get("q"))
    # Now disconnect it
    bus_id = hades_gen.get("noeud")
    hades_gen.set("noeud", "-1")
    # Write out the Hades file, preserving the XML format
    if os.path.exists(hades_file):  # Remove previous file that can be a symbolic link
        os.remove(hades_file)
    hades_tree.write(
        hades_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="ISO-8859-1",
        standalone=False,
    )
    # IMPORTANT: undo the changes we made, as we'll be reusing this parsed tree!
    hades_gen.set("noeud", bus_id)
    return gen_P, gen_Q


def save_total_genpq(dirname, olf_gens, processed_gensPQ):
    file_name = dirname + "/total_PQ_per_generator.csv"
    # Using a dataframe for sorting

    column_list = [
        "GEN",
        "P_olf",
        "P_hds",
        "Pdiff_pct",
        "Q_olf",
        "Q_hds",
        "Qdiff_pct",
        "sumPQdiff_pct",
    ]

    # The processed_gens dict (which contains B case data) contains only the cases
    # that have actually been processed (we may have skipped some in the main loop)
    data_list = []
    for gen_name in processed_gensPQ:
        p_olf = olf_gens[gen_name].P
        p_hds = processed_gensPQ[gen_name][0]
        Pdiff_pct = 100 * (p_olf - p_hds) / max(abs(p_hds), 0.001)
        q_olf = olf_gens[gen_name].Q
        q_hds = processed_gensPQ[gen_name][1]
        Qdiff_pct = 100 * (q_olf - q_hds) / max(abs(q_hds), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [
                gen_name,
                p_olf,
                p_hds,
                Pdiff_pct,
                q_olf,
                q_hds,
                Qdiff_pct,
                sumPQdiff_pct,
            ]
        )

    df = pd.DataFrame(data_list, columns=column_list)
    df.sort_values(
        by=["sumPQdiff_pct"], inplace=True, ascending=False, na_position="first"
    )
    df.to_csv(file_name, index=False, sep=";", float_format="%.3f", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
