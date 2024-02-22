#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# adapter from dynaflow directory

import os
import random
import re
import sys
from collections import namedtuple
from dynawo_validation.openloadflow.pipeline.common_funcs import parse_basecase, copy_basecase

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
    "-a", "--allcontg", help="generate all the contingencies", action="store_true"
)
parser.add_argument(
    "-r",
    "--randomc",
    help="generate a different random sample of contingencies",
    action="store_true",
)
parser.add_argument(
    "-m",
    "--max",
    type=int,
    default=20,
    help="maximum number of contingencies to generate",
)
parser.add_argument(
    "-l",
    "--list",
    help="enter regular expressions or contingencies in "
    "string form separated with pipe(|)",
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
parser.add_argument("base_case", help="enter base case directory")
args = parser.parse_args()

def main():
    RNG_SEED = 42
    max_ncases = args.max
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

    # Select disconnection mode from how the script is named:
    disconn_mode = "BOTH_ENDS"
    called_as = os.path.basename(sys.argv[0])
    if called_as[:7] == "branchF":
        disconn_mode = "FROM"
    elif called_as[:7] == "branchT":
        disconn_mode = "TO"

    # Contingency cases will be created under the same dir as the basecase
    dirname = os.path.dirname(os.path.abspath(base_case))

    print("RNG_SEED used to create contingencies = " + str(RNG_SEED))


    # Parse all XML files in the basecase
    parsed_case = parse_basecase(
        base_case, HADES_FILE, OLF_FILE
    )

    # Extract the list of all (active) BRANCHES in the Dynawo case
    olf_branches = extract_olf_branches(parsed_case.olf_tree, verbose)
    # And reduce the list to those BRANCHES that are matched in Hades
    olf_branches = matching_in_hades(
        parsed_case.hades_tree, olf_branches, verbose
    )

    # finally only keep those with active power greater than minP
    olf_branches = {branch:olf_branches[branch] for branch in olf_branches if abs(olf_branches[branch].P) >= args.minP}
    print("   (kept {0} branches with P > {1})\n".format(len(olf_branches), args.minP))

    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = max_ncases / len(olf_branches)
        random.seed(RNG_SEED)
        if len(filter_list) == 0 and sampling_ratio < 1:
            print(
                "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
                % (max_ncases, 100 * sampling_ratio)
            )
    else:
        sampling_ratio = 1

    # This dict will keep track of which contingencies are actually processed
    # It will also keep Hades's (P,Q) of each branch
    processed_branchesPQ = dict()

    # Main loop: generate the contingency cases
    for branch_name in olf_branches:

        # If the script was passed a list of generators, filter for them here
        branch_name_matches = [r.search(branch_name) for r in filter_list]
        if len(filter_list) != 0 and not any(branch_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating conting. case for branch %s (busFrom: %s, busTo: %s), mode: %s"
            % (
                branch_name,
                olf_branches[branch_name].busFrom,
                olf_branches[branch_name].busTo,
                disconn_mode,
            )
        )


        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = os.path.join(dirname, "branch" + disconn_mode[0] + "#"
                                     + branch_name.replace("/", "+").replace(" ", "_"))


        # Copy the basecase (unchanged files and dir structure)
        copy_basecase(base_case, OLF_FILE, HADES_FILE, PARAM_FILE, contg_casedir)
        # Modify the Dynawo case (DYD,PAR,CRV)
        config_olf_branch_contingency(
            contg_casedir,
            parsed_case.olf_tree,
            branch_name,
            olf_branches[branch_name],
            disconn_mode,
        )

        # Modify the Hades case, and obtain the disconnected generation (P,Q)
        processed_branchesPQ[branch_name] = config_hades_branch_contingency(
            contg_casedir, parsed_case.hades_tree, branch_name, disconn_mode
        )


    # Finally, save the (P,Q) values of disconnected branches in all *processed* cases
    save_total_branchpq(dirname, olf_branches, processed_branchesPQ)

    return 0


def extract_olf_branches(iidm_tree, verbose=False):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    branches = dict()
    Branch_info = namedtuple("Branch_info", "P Q branchType busFrom busTo")

    # We enumerate all branches and extract their properties
    nlines = 0
    ntransf = 0
    npshifters = 0
    for branch in root.iter("{%s}line" % ns, "{%s}twoWindingsTransformer" % ns):
        if branch.get("p1") is None or branch.get("p2") is None:
            continue
        if (float(branch.get("p1")) == 0.0 and float(branch.get("q1")) == 0.0) or (
            float(branch.get("p2")) == 0.0 and float(branch.get("q2")) == 0.0
        ):
            continue
        branch_name = branch.get("id")
        P_flow = float(branch.get("p1"))
        Q_flow = float(branch.get("q1"))
        # Find its type (line, xfmer, phase-shifter)
        xml_tag = etree.QName(branch).localname
        if xml_tag == "line":
            branch_type = "Line"
            nlines += 1
        elif xml_tag == "twoWindingsTransformer":
            if branch.find("{%s}phaseTapChanger" % ns) is None:
                branch_type = "Transformer"
                ntransf += 1
            else:
                branch_type = "PhaseShitfer"
                npshifters += 1
        else:
            print("   WARNING: unknown branch type %s (skipping)" % branch_name)
            continue
        # Find its FROM and TO buses
        bus_from = get_endbus(root, branch, branch_type, side="1")
        bus_to = get_endbus(root, branch, branch_type, side="2")
        if bus_from is None or bus_to is None:  # skip branch
            print(
                "   WARNING: couldn't find bus FROM/TO for %s %s (skipping)"
                % (branch_type, branch_name)
            )
            continue

        branches[branch_name] = Branch_info(
            P=P_flow, Q=Q_flow, branchType=branch_type, busFrom=bus_from, busTo=bus_to
        )

    print("\nFound %d ACTIVE branches" % len(branches), end=",")
    print(
        " (%d lines, %d transformers, %d phase shifters) in the IIDM file"
        % (nlines, ntransf, npshifters)
    )

    if verbose:
        print(
            "List of all ACTIVE branches in the Dynawo IIDM file: (total: %d)"
            % len(branches)
        )
        branch_list = sorted(branches.keys())
        if len(branch_list) < 10:
            print(branch_list)
        else:
            print(branch_list[:5] + ["..."] + branch_list[-5:])
        print()

    return branches


def get_endbus(root, branch, branch_type, side):
    ns = etree.QName(root).namespace
    end_bus = branch.get("bus" + side)
    if end_bus is None:
        end_bus = branch.get("connectableBus" + side)
    if end_bus is None:
        # bummer, the bus is NODE_BREAKER
        topo = []
        #  for xfmers, we only need to search the VLs within the substation
        if branch_type == "Line":
            pnode = root
        else:
            pnode = branch.getparent()
        for vl in pnode.iter("{%s}voltageLevel" % ns):
            if vl.get("id") == branch.get("voltageLevelId" + side):
                topo = vl.find("{%s}nodeBreakerTopology" % ns)
                break
        # we won't resolve the actual topo connectivity; just take the first busbar
        for node in topo:
            node_type = etree.QName(node).localname
            if node_type == "busbarSection" and node.get("v") is not None:
                end_bus = node.get("id")
                break
    return end_bus


def matching_in_hades(hades_tree, dynawo_branches, verbose=False):
    # Retrieve the list of Hades branches
    hades_branches = set()  # for faster matching below
    root = hades_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        hades_branches.add(branch.get("nom"))

    print("\nFound %d branches in Hades file" % len(hades_branches))
    if verbose:
        print(
            "Sample list of all BRANCHES in Hades file: (total: %d)"
            % len(hades_branches)
        )
        branch_list = sorted(hades_branches)
        if len(branch_list) < 10:
            print(branch_list)
        else:
            print(branch_list[:5] + ["..."] + branch_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_branches.items() if x[0] in hades_branches]
    print("   (matched %d branches against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_olf_branch_contingency(
    casedir, iidm_tree, branch_name, branch_info, disc_mode
):
    iidm_file = os.path.join(casedir, OLF_FILE)
    print("   Configuring file %s" % iidm_file)
    root = iidm_tree.getroot()

    iidm_branch = None

    ns = etree.QName(root).namespace
    for branch in root.iter("{%s}line" % ns, "{%s}twoWindingsTransformer" % ns):
        if branch.get("id") == branch_name:
            iidm_branch = branch
            break

    bus1 = iidm_branch.get("bus1")
    bus2 = iidm_branch.get("bus2")
    # the branch should always be found, because they have been previously matched

    if disc_mode == "FROM":
        del iidm_branch.attrib["bus1"]  #
    elif disc_mode == "TO":
        del iidm_branch.attrib["bus2"]  #
    else:
        del iidm_branch.attrib["bus1"]
        del iidm_branch.attrib["bus2"]  #

    # Write out the Hades file, preserving the XML format
    # Remove symbolic link if exists
    if os.path.exists(iidm_file):
        os.remove(iidm_file)
    iidm_tree.write(
        iidm_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding=""UTF-8"?>',
        encoding="UTF-8",
        standalone=False,
    )
    # IMPORTANT: undo the changes we made, as we'll be reusing this parsed tree!
    iidm_branch.set("bus1", bus1)
    iidm_branch.set("bus2", bus2)

    return 0


def config_hades_branch_contingency(casedir, hades_tree, branch_name, disc_mode):
    hades_file = os.path.join(casedir, HADES_FILE)
    print("   Configuring file %s" % hades_file)
    root = hades_tree.getroot()
    # Since Hades is a powerflow program, there is no "event" to configure. We simply
    # disconnect the branch by setting its noeud to "-1".
    # First find the branch in Hades and keep its P, Q values (for comnparing vs Dynawo)

    hades_branch = None
    reseau = root.find("./reseau", root.nsmap)
    donneesGroupes = reseau.find("./donneesQuadripoles", root.nsmap)
    for g in donneesGroupes.iterfind("./quadripole", root.nsmap):
        if g.get("nom") == branch_name:
            hades_branch = g
            break

    busID_from = hades_branch.get("nor")
    busID_to = hades_branch.get("nex")
    if busID_from == "-1" or busID_to == "-1":
        raise ValueError("this branch is disconnected in Astre!!!")
    # the branch should always be found, because they have been previously matched

    branch_vars = hades_branch.find("./variables", root.nsmap)
    branch_P = float(branch_vars.get("por"))
    branch_Q = float(branch_vars.get("qor"))

    # Now disconnect it
    bus_id1 = hades_branch.get("nor")
    bus_id2 = hades_branch.get("nex")
    if disc_mode == "FROM":
        hades_branch.set("nor", "-1")
    elif disc_mode == "TO":
        hades_branch.set("nex", "-1")
    else:
        hades_branch.set("nex", "-1")
        hades_branch.set("nor", "-1")

    # Write out the Hades file, preserving the XML format
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
    hades_branch.set("nor", bus_id1)
    hades_branch.set("nex", bus_id2)
    return branch_P, branch_Q


def save_total_branchpq(dirname, olf_branches, processed_branches):
    file_name = os.path.join(dirname, "total_PQ_per_branch.csv")
    # Using a dataframe for sorting

    column_list = [
        "BRANCH",
        "P_olf",
        "P_hds",
        "Pdiff_pct",
        "Q_olf",
        "Q_hds",
        "Qdiff_pct",
        "sumPQdiff_pct",
    ]

    # The processed_branches dict (which contains B case data) contains only the cases
    # that have actually been processed (we may have skipped some in the main loop)
    data_list = []
    for branch_name in processed_branches:
        P_olf = olf_branches[branch_name].P
        P_proc = processed_branches[branch_name][0]
        Pdiff_pct = 100 * (P_olf - P_proc) / max(abs(P_proc), 0.001)
        Q_olf = olf_branches[branch_name].Q
        Q_proc = processed_branches[branch_name][1]
        Qdiff_pct = 100 * (Q_olf - Q_proc) / max(abs(Q_proc), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [
                branch_name,
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
