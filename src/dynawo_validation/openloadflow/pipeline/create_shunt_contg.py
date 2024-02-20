#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Adapted from dynaflow/create_shunt_contgy
#

import os
import random
import re
import sys
from collections import namedtuple
from lxml import etree
import pandas as pd
import argparse
from common_funcs import parse_basecase, copy_basecase

# Relative imports only work for proper Python packages, but we do not want (yet) to
# structure all these as a package; we'd like to keep them as a collection of loose
# Python scripts, at least for now (after all, this is not really a Python library). So
# the following hack is ugly, but needed:
sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


MAX_NCASES = 35  # limits the no. of contingency cases (via random sampling)
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
parser.add_argument("base_case", help="base case directory")
parser.add_argument("result_dir", help="result directory")
args = parser.parse_args()


def main():
    RNG_SEED = 42
    filter_list = []
    verbose = False
    if args.verbose:
        verbose = args.verbose
    base_case = args.base_case
    result_dir = args.result_dir
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

    # Contingency cases will be created under the resultDir
    dirname = os.path.abspath(result_dir)
    print("RNG_SEED used to create contingencies = " + str(RNG_SEED))

    # Parse all XML files in the basecase
    parsed_case = parse_basecase(
        base_case, HADES_FILE, OLF_FILE
    )

    # Extract the list of all (active) SHUNTS in the OLF case
    olf_shunts = extract_iidm_shunts(parsed_case.olf_tree, verbose)
    # And reduce the list to those SHUNTS that are matched in Hades
    olf_shunts = matching_in_hades(
        parsed_case.hades_tree, olf_shunts, verbose
    )

    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = MAX_NCASES / len(olf_shunts)
        random.seed(RNG_SEED)
        if len(filter_list) == 0 and sampling_ratio < 1:
            print(
                "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
                % (MAX_NCASES, 100 * sampling_ratio)
            )
    else:
        sampling_ratio = 1

    # Add NOCONTINGENCY


    # This dict will keep track of which contingencies are actually processed
    # It will also keep Hades's (P,Q) of each shunt
    processed_shunts = dict()

    # Main loop: For each matching SHUNT, generate the contingency case
    for shunt_name in olf_shunts:

        # If the script was passed a list of shunt, filter for them here
        shunt_name_matches = [r.search(shunt_name) for r in filter_list]
        if len(filter_list) != 0 and not any(shunt_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating contingency case for shunt %s (at bus: %s)"
            % (shunt_name, olf_shunts[shunt_name].bus)
        )

        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = os.path.join(dirname, "shunt#" + shunt_name.replace("/", "+").replace(" ","_"))

        # Copy the basecase (unchanged files and dir structure)
        copy_basecase(base_case, OLF_FILE, HADES_FILE, PARAM_FILE,  contg_casedir)
        # Modify the IIDM case
        config_iidm_shunt_contingency(
            contg_casedir,
            parsed_case.olf_tree,
            shunt_name,
        )
        # Modify the Hades case, and obtain the disconnected generation (Q)
        processed_shunts[shunt_name] = config_hades_shunt_contingency(
            contg_casedir, parsed_case.hades_tree, shunt_name
        )


    # Finally, save the (P,Q) values of disconnected shunts in all *processed* cases
    save_total_shuntpq(dirname, olf_shunts, processed_shunts)

    return 0


def extract_iidm_shunts(iidm_tree, verbose=False):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    shunts = dict()
    Shunt_info = namedtuple("Shunt_info", "Q bus busTopology")

    # We enumerate all shunts and extract their properties
    for shunt in root.iter("{%s}shunt" % ns):
        if shunt.get("bus") is not None:
            shunt_name = shunt.get("id")
            shunts[shunt_name] = Shunt_info(
                Q=float(shunt.get("q")),
                bus=shunt.get("bus"),
                busTopology=shunt.getparent().get("topologyKind"),
            )

    print("\nFound %d ACTIVE shunts in the IIDM file" % len(shunts))
    if verbose:
        print("List of all ACTIVE shunts in the IIDM file: (total: %d)" % len(shunts))
        shunt_list = sorted(shunts.keys())
        if len(shunt_list) < 10:
            print(shunt_list)
        else:
            print(shunt_list[:5] + ["..."] + shunt_list[-5:])
        print()

    return shunts


def matching_in_hades(hades_tree, dynawo_shunts, verbose=False):
    # Retrieve the list of Hades shunts
    root = hades_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesShunts = reseau.find("./donneesShunts", root.nsmap)
    hades_shunts = set()  # for faster matching below
    for shunt in donneesShunts.iterfind("./shunt", root.nsmap):
        # Discard shunts having noeud="-1"
        if shunt.get("noeud") != "-1":
            hades_shunts.add(shunt.get("nom"))

    print("\nFound %d shunts in Hades file" % len(hades_shunts))
    if verbose:
        print(
            "Sample list of all SHUNTS in Hades file: (total: %d)" % len(hades_shunts)
        )
        shunt_list = sorted(hades_shunts)
        if len(shunt_list) < 10:
            print(shunt_list)
        else:
            print(shunt_list[:5] + ["..."] + shunt_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_shunts.items() if x[0] in hades_shunts]
    print("   (matched %d shunts against IIDM file)\n" % len(new_list))

    return dict(new_list)


def config_iidm_shunt_contingency(casedir, olf_tree, shunt_name):
    iidm_file = os.path.join(casedir, OLF_FILE)
    print("   Configuring file %s" % iidm_file)
    root = olf_tree.getroot()

    olf_shunt = None
    for shunt in root.iterfind(".//iidm:shunt", root.nsmap):
        if shunt.get("id") == shunt_name:
            olf_shunt = shunt
            break
    # the shunt should always be found, because they have been previously matched
    shunt_bus=olf_shunt.get("bus")
    del olf_shunt.attrib["bus"]

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
    olf_shunt.set("bus", shunt_bus)
    return

def config_hades_shunt_contingency(casedir, hades_tree, shunt_name):
    hades_file = os.path.join(casedir, HADES_FILE)
    print("   Configuring file %s" % hades_file)
    root = hades_tree.getroot()

    hades_shunt = None
    reseau = root.find("./reseau", root.nsmap)
    donnees_shunts = reseau.find("./donneesShunts", root.nsmap)
    for g in donnees_shunts.iterfind("./shunt", root.nsmap):
        if g.get("nom") == shunt_name:
            hades_shunt = g
            break
    # the shunt should always be found, because they have been previously matched
    shunt_vars = hades_shunt.find("./variables", root.nsmap)
    shunt_Q = -10000 * float(shunt_vars.get("q"))
    # Now disconnect it
    bus_id = hades_shunt.get("noeud")
    hades_shunt.set("noeud", "-1")
    # Remove previous file if exists (might be aymbolink link) then Write out the Hades file, preserving the XML format
    if os.path.exists(hades_file):
        os.remove(hades_file)
    hades_tree.write(
        hades_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="ISO-8859-1",
        standalone=False,
    )
    # IMPORTANT: undo the changes we made, as we'll be reusing this parsed tree!
    hades_shunt.set("noeud", bus_id)
    return shunt_Q


def save_total_shuntpq(dirname, olf_shunts, processed_shunts):
    file_name = os.path.join(dirname,"total_shuntQ_per_shunts.csv")
    # Using a dataframe for sorting
    column_list = ["SHUNT", "Q_olf", "Q_hades", "Qdiff_pct"]

    data_list = []
    for shunt_name in processed_shunts:
        Q_olf = olf_shunts[shunt_name].Q
        Q_hades = processed_shunts[shunt_name]
        Qdiff_pct = 100 * (Q_olf - Q_hades) / max(abs(Q_hades), 0.001)
        data_list.append([shunt_name, Q_olf, Q_hades, Qdiff_pct])

    df = pd.DataFrame(data_list, columns=column_list)
    df.sort_values(by=["Qdiff_pct"], inplace=True, ascending=False, na_position="first")
    df.to_csv(file_name, index=False, sep=";", float_format="%.3f", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
