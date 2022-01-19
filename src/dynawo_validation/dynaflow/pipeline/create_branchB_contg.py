#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# create_branch_contg.py:
#
# Takes a given base case, consisting of EITHER two corresponding DynaFlow and Hades
# cases OR two corresponding DynaFlow cases, and, enumerating all BRANCHes that can be
# matched in the two, generates the files for running all possible single-BRANCH
# contingency cases (or a provided list of them).
#
# On *input*, the files are expected to have a structure that typically looks as
# either one of these (but this is not strict; see below):
#
#    For DynaFlow-vs-Hades:                For DynaFlow_A vs. DynaFlow_B:
#    ======================                ==============================
#    BASECASE/                             BASECASE/
#    ├── Hades/                            ├── JOB_A.xml
#    │   └── donneesEntreeHADES2.xml       ├── JOB_B.xml
#    ├── JOB.xml                           ├── A/
#    ├── Network.par                       │   ├── Network.par
#    ├── solver.par                        │   ├── solver.par
#    ├── <dwo_casename>.{iidm,dyd,par}    │   ├── <dwo_casename>.{iidm,dyd,par}
#    └── <dwo_casename>_Diagram/           │   └── <dwo_casename>_Diagram/
#                                          └── B/
#                                              ├── Network.par
#                                              ├── solver.par
#                                              ├── <dwo_casename>.{iidm,dyd,par}
#                                              └── <dwo_casename>_Diagram/
#
#
# For Hades, the structure should be strictly as in the above example. On the other
# hand, for Dynawo we only require that there exists a JOB file with patterns
# "*JOB*.xml" (or "*JOB_A*.xml", "*JOB_B*.xml"); and from the job file we read the
# actual paths to the IIDM, DYD, etc. (see module dwo_jobinfo).
#
# On *output*, the script generates new dirs sibling to basecase:
# branch_LABEL1, branch_LABEL2, etc.
#

import os
import random
import re
import sys
from collections import namedtuple
from dynawo_validation.dynaflow.pipeline.common_funcs import (
    copy_dwohds_basecase,
    copy_dwodwo_basecase,
    parse_basecase,
)
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
from dynawo_validation.dynaflow.pipeline.dwo_jobinfo import (
    is_dwohds,
    is_dwodwo,
    get_dwo_jobpaths,
    get_dwo_tparams,
    get_dwodwo_jobpaths,
    get_dwodwo_tparams,
)  # noqa: E402


MAX_NCASES = 5  # limits the no. of contingency cases (via random sampling)
HADES_PATH = "/Hades/donneesEntreeHADES2.xml"

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
parser.add_argument("base_case", help="enter base case directory")
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

    # Check whether it's a Dynawo-vs-Hades or a Dynawo-vs-Dynawo case
    # And get the Dynawo paths from the JOB file, and the simulation time params
    dwo_paths, dwohds = (None, None)
    dwo_pathsA, dwo_pathsB = (None, None)
    if is_dwohds(base_case):
        print(f"Creating contingencies from DYNAWO-vs-HADES case: {base_case}")
        dwo_paths = get_dwo_jobpaths(base_case)
        dwo_tparams = get_dwo_tparams(base_case)
        dwohds = True
    elif is_dwodwo(base_case):
        print(f"Creating contingencies from DYNAWO-vs-DYNAWO case: {base_case}")
        dwo_pathsA, dwo_pathsB = get_dwodwo_jobpaths(base_case)
        dwo_tparamsA, dwo_tparamsB = get_dwodwo_tparams(base_case)
        dwohds = False
    else:
        raise ValueError(f"Case {base_case} is neither an dwo-hds nor a dwo-dwo case")

    # Parse all XML files in the basecase
    parsed_case = parse_basecase(
        base_case, dwo_paths, HADES_PATH, dwo_pathsA, dwo_pathsB
    )

    # Extract the list of all (active) BRANCHES in the Dynawo case
    if dwohds:
        dynawo_branches = extract_dynawo_branches(parsed_case.iidmTree, verbose)
        # And reduce the list to those BRANCHES that are matched in Hades
        dynawo_branches = matching_in_hades(
            parsed_case.asthdsTree, dynawo_branches, verbose
        )
    else:
        dynawo_branches = extract_dynawo_branches(parsed_case.A.iidmTree, verbose)
        dynawo_branchesB = extract_dynawo_branches(parsed_case.B.iidmTree, verbose)
        # And reduce the list to those BRANCHES that are matched in the Dynawo B case
        dynawo_branches = matching_in_dwoB(dynawo_branches, dynawo_branchesB)

    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = MAX_NCASES / len(dynawo_branches)
        random.seed(RNG_SEED)
        if len(filter_list) == 0 and sampling_ratio < 1:
            print(
                "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
                % (MAX_NCASES, 100 * sampling_ratio)
            )
    else:
        sampling_ratio = 1

    # Add NOCONTINGENCY

    # We fix any device names with slashes in them (illegal filenames)
    contg_casedir = dirname + "/branch" + disconn_mode[0] + "#NOCONTINGENCY"

    if dwohds:
        # Copy the basecase (unchanged files and dir structure)
        copy_dwohds_basecase(base_case, dwo_paths, contg_casedir)
        dyd_file = contg_casedir + "/" + dwo_paths.dydFile_contg
        dyd_tree = parsed_case.dydTree_contg
        dyd_tree.write(
            dyd_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        par_file = contg_casedir + "/" + dwo_paths.parFile_contg
        par_tree = parsed_case.parTree_contg
        par_tree.write(
            par_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        crv_file = contg_casedir + "/" + dwo_paths.curves_inputFile
        crv_tree = parsed_case.crvTree
        crv_tree.write(
            crv_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        hades_file = contg_casedir + HADES_PATH
        hades_tree = parsed_case.asthdsTree
        hades_tree.write(
            hades_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )

    else:
        # Copy the basecase (unchanged files and dir structure)
        copy_dwodwo_basecase(base_case, dwo_pathsA, dwo_pathsB, contg_casedir)
        # A
        dyd_file = contg_casedir + "/" + dwo_pathsA.dydFile_contg
        dyd_tree = parsed_case.A.dydTree_contg
        dyd_tree.write(
            dyd_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        par_file = contg_casedir + "/" + dwo_pathsA.parFile_contg
        par_tree = parsed_case.A.parTree_contg
        par_tree.write(
            par_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        crv_file = contg_casedir + "/" + dwo_pathsA.curves_inputFile
        crv_tree = parsed_case.A.crvTree
        crv_tree.write(
            crv_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        # B
        dyd_file = contg_casedir + "/" + dwo_pathsB.dydFile_contg
        dyd_tree = parsed_case.B.dydTree_contg
        dyd_tree.write(
            dyd_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        par_file = contg_casedir + "/" + dwo_pathsB.parFile_contg
        par_tree = parsed_case.B.parTree_contg
        par_tree.write(
            par_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )
        crv_file = contg_casedir + "/" + dwo_pathsB.curves_inputFile
        crv_tree = parsed_case.B.crvTree
        crv_tree.write(
            crv_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8",
        )

    # This dict will keep track of which contingencies are actually processed
    # It will also keep Hades's (P,Q) of each branch
    processed_branchesPQ = dict()

    # Main loop: generate the contingency cases
    for branch_name in dynawo_branches:

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
                dynawo_branches[branch_name].busFrom,
                dynawo_branches[branch_name].busTo,
                disconn_mode,
            )
        )

        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = (
            dirname + "/branch" + disconn_mode[0] + "#" + branch_name.replace("/", "+")
        )

        if dwohds:
            # Copy the basecase (unchanged files and dir structure)
            copy_dwohds_basecase(base_case, dwo_paths, contg_casedir)
            # Modify the Dynawo case (DYD,PAR,CRV)
            config_dynawo_branch_contingency(
                contg_casedir,
                parsed_case,
                dwo_paths,
                dwo_tparams,
                branch_name,
                dynawo_branches[branch_name],
                disconn_mode,
            )
            # Modify the Hades case, and obtain the disconnected generation (P,Q)
            processed_branchesPQ[branch_name] = config_hades_branch_contingency(
                contg_casedir, parsed_case.asthdsTree, branch_name, disconn_mode
            )
        else:
            # Copy the basecase (unchanged files and dir structure)
            copy_dwodwo_basecase(base_case, dwo_pathsA, dwo_pathsB, contg_casedir)
            # Modify the Dynawo A & B cases (DYD,PAR,CRV)
            config_dynawo_branch_contingency(
                contg_casedir,
                parsed_case.A,
                dwo_pathsA,
                dwo_tparamsA,
                branch_name,
                dynawo_branches[branch_name],
                disconn_mode,
            )
            config_dynawo_branch_contingency(
                contg_casedir,
                parsed_case.B,
                dwo_pathsB,
                dwo_tparamsB,
                branch_name,
                dynawo_branches[branch_name],
                disconn_mode,
            )
            # Get the disconnected generation (P,Q) for case B
            processed_branchesPQ[branch_name] = (
                dynawo_branchesB[branch_name].P,
                dynawo_branchesB[branch_name].Q,
            )

    # Finally, save the (P,Q) values of disconnected branches in all *processed* cases
    save_total_branchpq(dirname, dwohds, dynawo_branches, processed_branchesPQ)

    return 0


def extract_dynawo_branches(iidm_tree, verbose=False):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    branches = dict()
    Branch_info = namedtuple("Branch_info", "P Q branchType busFrom busTo")

    # We enumerate all branches and extract their properties
    nlines = 0
    ntransf = 0
    npshifters = 0
    for branch in root.iter("{%s}line" % ns, "{%s}twoWindingsTransformer" % ns):
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
        " (%d lines, %d transformers, %d phase shifters) in the Dynawo IIDM file"
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


def matching_in_dwoB(dynawo_branchesA, dynawo_branchesB):
    # Match:
    new_list = [x for x in dynawo_branchesA.items() if x[0] in dynawo_branchesB]
    print("   (matched %d branches against Dynawo A case)\n" % len(new_list))
    return dict(new_list)


def config_dynawo_branch_contingency(
    casedir, case_trees, dwo_paths, dwo_tparams, branch_name, branch_info, disc_mode
):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + "/" + dwo_paths.dydFile_contg
    print("   Configuring file %s" % dyd_file)
    dyd_tree = case_trees.dydTree_contg
    root = dyd_tree.getroot()
    ns = etree.QName(root).namespace

    # Branches with vs. without a dynamic model in the DYD file:
    # they need to be disconnected differently.
    disconn_eventmodel = "EventQuadripoleDisconnection"
    cnx_id2 = "NETWORK"
    cnx_var2 = branch_name + "_state_value"

    # Erase all existing Event models (keep the IDs to remove their
    # connections later below)
    old_eventIds = []
    old_parIds = []
    for event in root.iterfind(f"./{{{ns}}}blackBoxModel"):
        if event.get("lib")[0:5] == "Event":
            old_eventIds.append(event.get("id"))
            old_parIds.append(event.get("parId"))
            event.getparent().remove(event)

    # Declare a new Event
    event = etree.SubElement(root, f"{{{ns}}}blackBoxModel")
    event_id = "Disconnect my branch"
    event.set("id", event_id)
    event.set("lib", disconn_eventmodel)
    event.set("parFile", dwo_paths.parFile_contg)
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iterfind(f"./{{{ns}}}connect"):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the branch
    cnx = etree.SubElement(root, f"{{{ns}}}connect")
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", cnx_id2)
    cnx.set("var2", cnx_var2)

    # Write out the DYD file, preserving the XML format
    dyd_tree.write(
        dyd_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    ###########################################################
    # PAR file: add a section with the disconnecton parameters
    ###########################################################
    par_file = casedir + "/" + dwo_paths.parFile_contg
    print("   Configuring file %s" % par_file)
    par_tree = case_trees.parTree_contg
    root = par_tree.getroot()

    # Erase all existing parsets used by the Events removed above
    for parset in root.iterfind("./set", root.nsmap):
        if parset.get("id") in old_parIds:
            parset.getparent().remove(parset)

    # The event time was already read from the BASECASE (taken from the first event)
    event_tEvent = str(round(dwo_tparams.event_tEvent))

    # Insert the new parset with the params we need
    ns = etree.QName(root).namespace
    new_parset = etree.Element("{%s}set" % ns, id="99991234")
    new_parset.append(
        etree.Element(
            "{%s}par" % ns, type="DOUBLE", name="event_tEvent", value=event_tEvent
        )
    )
    open_F = "true"
    open_T = "true"
    if disc_mode == "FROM":
        open_T = "false"
    if disc_mode == "TO":
        open_F = "false"
    new_parset.append(
        etree.Element(
            "{%s}par" % ns, type="BOOL", name="event_disconnectOrigin", value=open_F
        )
    )
    new_parset.append(
        etree.Element(
            "{%s}par" % ns, type="BOOL", name="event_disconnectExtremity", value=open_T
        )
    )
    root.append(new_parset)

    # Write out the PAR file, preserving the XML format
    par_tree.write(
        par_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    ############################################################
    # CRV file: configure which variables we want in the output
    ############################################################

    # We expand the `curvesInput` section with any additional
    # variables that make sense to have in the output. The base case
    # is expected to have the variables that monitor the behavior of
    # the SVC (pilot point voltage, K level, and P,Q of participating
    # branches).  We will keep these, and add new ones.
    #
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we would use the IIDM file, where the branch has an
    # attribute that directly provides the bus it is connected to. We
    # already stored this value in the branch_info tuple before.

    bus_from = branch_info.busFrom
    bus_to = branch_info.busTo

    # Add the corresponding curve to the CRV file
    crv_file = casedir + "/" + dwo_paths.curves_inputFile
    print("   Configuring file %s" % crv_file)
    crv_tree = case_trees.crvTree
    root = crv_tree.getroot()
    ns = etree.QName(root).namespace
    new_crv1 = etree.Element(
        "{%s}curve" % ns, model="NETWORK", variable=bus_from + "_Upu_value"
    )
    new_crv2 = etree.Element(
        "{%s}curve" % ns, model="NETWORK", variable=bus_to + "_Upu_value"
    )
    root.append(new_crv1)
    root.append(new_crv2)
    # Write out the CRV file, preserving the XML format
    crv_tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )
    # And erase the 2 curves we've just added, because we'll be reusing the parsed tree
    root.remove(new_crv1)
    root.remove(new_crv2)

    return 0


def config_hades_branch_contingency(casedir, hades_tree, branch_name, disc_mode):
    hades_file = casedir + HADES_PATH
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


def save_total_branchpq(dirname, dwohds, dynawo_branches, processed_branches):
    file_name = dirname + "/total_PQ_per_branch.csv"
    # Using a dataframe for sorting
    if dwohds:
        column_list = [
            "BRANCH",
            "P_dwo",
            "P_hds",
            "Pdiff_pct",
            "Q_dwo",
            "Q_hds",
            "Qdiff_pct",
            "sumPQdiff_pct",
        ]
    else:
        column_list = [
            "BRANCH",
            "P_dwoA",
            "P_dwoB",
            "Pdiff_pct",
            "Q_dwoA",
            "Q_dwoB",
            "Qdiff_pct",
            "sumPQdiff_pct",
        ]
    # The processed_branches dict (which contains B case data) contains only the cases
    # that have actually been processed (we may have skipped some in the main loop)
    data_list = []
    for branch_name in processed_branches:
        P_dwo = dynawo_branches[branch_name].P
        P_proc = processed_branches[branch_name][0]
        Pdiff_pct = 100 * (P_dwo - P_proc) / max(abs(P_proc), 0.001)
        Q_dwo = dynawo_branches[branch_name].Q
        Q_proc = processed_branches[branch_name][1]
        Qdiff_pct = 100 * (Q_dwo - Q_proc) / max(abs(Q_proc), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [
                branch_name,
                P_dwo,
                P_proc,
                Pdiff_pct,
                Q_dwo,
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
