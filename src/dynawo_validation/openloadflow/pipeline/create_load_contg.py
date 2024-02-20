#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Adapted from the dynaflow directory
#
#

import os
import random
import re
import sys
from collections import namedtuple
from common_funcs import parse_basecase, copy_basecase
from lxml import etree
import pandas as pd
from frozendict import frozendict
import argparse

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

# This dictionary refers to the possible load models. Depending on each of them, the
# variable for the disconnection event can be one or another.
LOAD_MODELS = frozendict(
    {
        "DYNModelLoadAlphaBeta": "switchOffSignal2",
        "DYNModelLoadRestorativeWithLimits": "switchOff2_value",
        "LoadAlphaBeta": "load_switchOffSignal2_value",
        "LoadAlphaBetaRestorative": "load_switchOffSignal2_value",
        "LoadAlphaBetaRestorativeLimitsRecalc": "load_switchOffSignal2_value",
        "LoadPQCompensation": "load_switchOffSignal2_value",
        "LoadPQ": "load_switchOffSignal2_value",
        "LoadZIP": "load_switchOffSignal2_value",
    }
)

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

    # Extract the list of all (active) LOADS in the OLF case
    olf_loads = extract_olf_loads(
        parsed_case.olf_tree, verbose
    )

    # And reduce the list to those LOADS that are matched in Hades
    olf_loads = matching_in_hades(parsed_case.hades_tree, olf_loads, verbose)


    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = MAX_NCASES / len(olf_loads)
        random.seed(RNG_SEED)
        if len(filter_list) == 0 and sampling_ratio < 1:
            print(
                "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
                % (MAX_NCASES, 100 * sampling_ratio)
            )
    else:
        sampling_ratio = 1


    # This dict will keep track of which contingencies are actually processed
    # It will also keep Hades's (P,Q) of each load
    processed_loadsPQ = dict()

    # Main loop: generate the contingency cases
    for load_name in olf_loads:

        # If the script was passed a list of load, filter for them here
        load_name_matches = [r.search(load_name) for r in filter_list]
        if len(filter_list) != 0 and not any(load_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating contingency case for load %s (at bus: %s)"
            % (load_name, olf_loads[load_name].bus)
        )

        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = os.path.join(dirname , "load#" + load_name.replace("/", "+").replace(" ","_"))

        # Copy the basecase (unchanged files and dir structure)
        copy_basecase(base_case, OLF_FILE, HADES_FILE, PARAM_FILE, contg_casedir)

        # Modify the OLF case
        config_iidm_load_contingency(
            contg_casedir,
            parsed_case.olf_tree,
            load_name,
        )

        # Modify the Hades case, and obtain the disconnected generation (P,Q)
        processed_loadsPQ[load_name] = config_hades_load_contingency(
            contg_casedir, parsed_case.hades_tree, load_name
        )

    # Finally, save the (P,Q) values of disconnected loads in all *processed* cases
    save_total_loadpq(dirname, olf_loads, processed_loadsPQ)

    return 0


def extract_olf_loads(iidm_tree, verbose=False):
    # We enumerate all loads and extract their properties
    Load_info = namedtuple("Load_info", "P Q loadType bus busTopology")
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    loads = dict()
    for load in root.iter("{%s}load" % ns):
        load_name = load.get("id")
        P_val = float(load.get("p0"))
        Q_val = float(load.get("q0"))
        load_type = load.get("loadType")
        # Find the bus (depends on the topology of its voltageLevel)
        topo_val = load.getparent().get("topologyKind")
        if topo_val == "BUS_BREAKER":
            bus_name = load.get("bus")
            if bus_name is None:
                continue
        elif topo_val == "NODE_BREAKER":
            bus_name = None
            load_node = load.get("node")
            vl = load.getparent()
            topology = vl.find("./iidm:nodeBreakerTopology", root.nsmap)
            for node in topology:
                node_type = etree.QName(node).localname
                if node_type == "busbarSection" and node.get("node") == load_node:
                    bus_name = node.get("id")
                    break
                # bus connected to mutiple nodes are ignored because not matched with hades..
                if node_type == "bus" and node.get("nodes") is not None:
                    if load_node in node.get("nodes").split(","):
                        bus_name=node.get("nodes")
                        break

        else:
            raise ValueError("TopologyKind not found for load: %s" % load_name)

        # Collect all info
        loads[load_name] = Load_info(
            P=P_val,
            Q=Q_val,
            loadType=load_type,
            bus=bus_name,
            busTopology=topo_val,
        )

    print("\nFound %d ACTIVE loads in the IIDM file" % len(loads))
    if verbose:
        print("List of all loads in Dynawo DYD file: (total: %d)" % len(loads))
        load_list = sorted(loads.keys())
        if len(load_list) < 10:
            print(load_list)
        else:
            print(load_list[:5] + ["..."] + load_list[-5:])
        print()

    return loads


def matching_in_hades(hades_tree, olf_loads, verbose=False):
    # Retrieve the list of Hades loads
    root = hades_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesConsos = reseau.find("./donneesConsos", root.nsmap)
    hades_loads = set()  # for faster matching below
    for load in donneesConsos.iterfind("./conso", root.nsmap):
        # Discard loads having noeud="-1"
        if load.get("noeud") != "-1":
            hades_loads.add(load.get("nom"))

    print("\nFound %d loads in Hades file" % len(hades_loads))
    if verbose:
        print("List of all loads in Hades file: (total: %d)" % len(hades_loads))
        load_list = sorted(hades_loads)
        if len(load_list) < 10:
            print(load_list)
        else:
            print(load_list[:5] + ["..."] + load_list[-5:])
        print()

    # Match:
    new_list = [x for x in olf_loads.items() if x[0] in hades_loads]
    print("   (matched %d loads against OLF file)\n" % len(new_list))

    return dict(new_list)


def matching_in_dwoB(dynawo_loadsA, dynawo_loadsB):
    # Match:
    new_list = [x for x in dynawo_loadsA.items() if x[0] in dynawo_loadsB]
    print("   (matched %d loads against Dynawo A case)\n" % len(new_list))

    return dict(new_list)


def config_iidm_load_contingency(casedir, olf_tree, load_name):
    iidm_file = os.path.join(casedir, OLF_FILE)
    print("   Configuring file %s" % iidm_file)
    root = olf_tree.getroot()

    olf_load = None
    for load in root.iterfind(".//iidm:load", root.nsmap):
        if load.get("id") == load_name:
            olf_load = load
            break
    # the shunt should always be found, because they have been previously matched
    load_bus = olf_load.get("bus")
    if load_bus is not None:
        del olf_load.attrib["bus"]  # bus breaker case
    load_node = olf_load.get("node")
    if load_node is not None:
        del olf_load.attrib["node"] # node breaker case


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
    if load_bus is not None:
        olf_load.set("bus", load_bus)
    if load_node is not None:
        olf_load.set("node", load_node)

    return


def config_hades_load_contingency(casedir, hades_tree, load_name):
    hades_file = os.path.join(casedir, HADES_FILE)
    print("   Configuring file %s" % hades_file)
    root = hades_tree.getroot()

    # Since Hades is a powerflow program, there is no "event" to configure. We simply
    # disconnect the generator by setting its noeud to "-1".
    # Find the load in Hades
    hades_load = None
    reseau = root.find("./reseau", root.nsmap)
    donneesConsos = reseau.find("./donneesConsos", root.nsmap)
    for g in donneesConsos.iterfind("./conso", root.nsmap):
        if g.get("nom") == load_name:
            hades_load = g
            break
    load_vars = hades_load.find("./variables", root.nsmap)
    if hades_load.get("fixe") == "true":
        load_P = float(load_vars.get("peFixe"))
        load_Q = float(load_vars.get("qeFixe"))
    else:
        load_P = float(load_vars.get("peAff"))
        load_Q = float(load_vars.get("qeAff"))

    # Now disconnect it
    bus_id = hades_load.get("noeud")
    hades_load.set("noeud", "-1")

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
    hades_load.set("noeud", bus_id)

    return load_P, load_Q


def save_total_loadpq(dirname, olf_loads, hades_loads):
    file_name = dirname + "/total_PQ_per_load.csv"
    # Using a dataframe for sorting
    column_list = [
        "LOAD",
        "P_olf",
        "P_hds",
        "Pdiff_pct",
        "Q_olf",
        "Q_hds",
        "Qdiff_pct",
        "sumPQdiff_pct",
    ]

    # The processed_loads dict (which contains B case data) contains only the cases
    # that have actually been processed (we may have skipped some in the main loop)
    data_list = []
    for load_name in hades_loads:
        P_olf = olf_loads[load_name].P
        P_proc = hades_loads[load_name][0]
        Pdiff_pct = 100 * (P_olf - P_proc) / max(abs(P_proc), 0.001)
        Q_olf = olf_loads[load_name].Q
        Q_proc = hades_loads[load_name][1]
        Qdiff_pct = 100 * (Q_olf - Q_proc) / max(abs(Q_proc), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [
                load_name,
                P_olf,
                P_proc,
                Pdiff_pct,
                Q_olf,
                Q_proc,
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
