#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# create_load_contg.py:
#
# Takes a given base case, consisting of EITHER two corresponding DynaFlow and Hades
# cases OR two corresponding DynaFlow cases, and, enumerating all LOADs that can be
# matched in the two, generates the files for running all possible single-LOAD
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
# load_LABEL1, load_LABEL2, etc.
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
from frozendict import frozendict
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

    # Extract the list of all (active) LOADS in the Dynawo case
    if dwohds:
        dynawo_loads = extract_dynawo_loads(
            parsed_case.dydTree, parsed_case.iidmTree, verbose
        )
        # And reduce the list to those LOADS that are matched in Hades
        dynawo_loads = matching_in_hades(parsed_case.asthdsTree, dynawo_loads, verbose)
    else:
        dynawo_loads = extract_dynawo_loads(
            parsed_case.A.dydTree, parsed_case.A.iidmTree, verbose
        )
        dynawo_loadsB = extract_dynawo_loads(
            parsed_case.B.dydTree, parsed_case.B.iidmTree, verbose
        )
        # And reduce the list to those LOADS that are matched in the Dynawo B case
        dynawo_loads = matching_in_dwoB(dynawo_loads, dynawo_loadsB)

    # Prepare for random sampling if there's too many
    if not args.allcontg:
        sampling_ratio = MAX_NCASES / len(dynawo_loads)
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
    contg_casedir = dirname + "/load#NOCONTINGENCY"

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
    # It will also keep Hades's (P,Q) of each load
    processed_loadsPQ = dict()

    # Main loop: generate the contingency cases
    for load_name in dynawo_loads:

        # If the script was passed a list of load, filter for them here
        load_name_matches = [r.search(load_name) for r in filter_list]
        if len(filter_list) != 0 and not any(load_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating contingency case for load %s (at bus: %s)"
            % (load_name, dynawo_loads[load_name].bus)
        )

        # We fix any device names with slashes in them (illegal filenames)
        contg_casedir = dirname + "/load#" + load_name.replace("/", "+")

        if dwohds:
            # Copy the basecase (unchanged files and dir structure)
            copy_dwohds_basecase(base_case, dwo_paths, contg_casedir)
            # Modify the Dynawo case (DYD,PAR,CRV)
            config_dynawo_load_contingency(
                contg_casedir,
                parsed_case,
                dwo_paths,
                dwo_tparams,
                dynawo_loads[load_name],
            )
            # Modify the Hades case, and obtain the disconnected generation (P,Q)
            processed_loadsPQ[load_name] = config_hades_load_contingency(
                contg_casedir, parsed_case.asthdsTree, load_name
            )
        else:
            # Copy the basecase (unchanged files and dir structure)
            copy_dwodwo_basecase(base_case, dwo_pathsA, dwo_pathsB, contg_casedir)
            # Modify the Dynawo A & B cases (DYD,PAR,CRV)
            config_dynawo_load_contingency(
                contg_casedir,
                parsed_case.A,
                dwo_pathsA,
                dwo_tparamsA,
                dynawo_loads[load_name],
            )
            config_dynawo_load_contingency(
                contg_casedir,
                parsed_case.B,
                dwo_pathsB,
                dwo_tparamsB,
                dynawo_loads[load_name],
            )
            # Get the disconnected generation (P,Q) for case B
            processed_loadsPQ[load_name] = (
                dynawo_loadsB[load_name].P,
                dynawo_loadsB[load_name].Q,
            )

    # Finally, save the (P,Q) values of disconnected loads in all *processed* cases
    save_total_loadpq(dirname, dwohds, dynawo_loads, processed_loadsPQ)

    return 0


def extract_dynawo_loads(dyd_tree, iidm_tree, verbose=False):
    dyd_root = dyd_tree.getroot()
    dmloads = dict()
    # We first enumerate all loads from the DYD and keep their model type and IDs
    DMload_info = namedtuple("DMload_info", "dydId modelLib")
    ns_dyd = etree.QName(dyd_root).namespace
    for bbm in dyd_root.iter("{%s}blackBoxModel" % ns_dyd):
        if bbm.get("lib") in LOAD_MODELS:
            dmloads[bbm.get("staticId")] = DMload_info(
                dydId=bbm.get("id"), modelLib=bbm.get("lib")
            )
    # We enumerate all loads and extract their properties
    Load_info = namedtuple("Load_info", "P Q dydId modelLib loadType bus busTopology")
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    loads = dict()
    for load in root.iter("{%s}load" % ns):
        load_name = load.get("id")
        if load_name not in dmloads:
            continue
        P_val = float(load.get("p0"))
        Q_val = float(load.get("q0"))
        dydId = dmloads[load_name].dydId
        modelLib = dmloads[load_name].modelLib
        load_type = load.get("loadType")
        # Find the bus (depends on the topology of its voltageLevel)
        topo_val = load.getparent().get("topologyKind")
        if topo_val == "BUS_BREAKER":
            bus_name = load.get("bus")
            if bus_name is None:
                continue
        elif topo_val == "NODE_BREAKER":
            # don't try to resolve the topology, just take the first active busbar
            bus_name = None
            vl = load.getparent()
            topology = vl.find("./nodeBreakerTopology", root.nsmap)
            for node in topology:
                node_type = etree.QName(node).localname
                if node_type == "busbarSection" and node.get("v") is not None:
                    bus_name = node.get("id")
                    break
        else:
            raise ValueError("TopologyKind not found for load: %s" % load_name)

        # Collect all info
        loads[load_name] = Load_info(
            P=P_val,
            Q=Q_val,
            dydId=dydId,
            modelLib=modelLib,
            loadType=load_type,
            bus=bus_name,
            busTopology=topo_val,
        )

    print("\nFound %d ACTIVE loads in the Dynawo IIDM file" % len(loads))
    if verbose:
        print("List of all loads in Dynawo DYD file: (total: %d)" % len(loads))
        load_list = sorted(loads.keys())
        if len(load_list) < 10:
            print(load_list)
        else:
            print(load_list[:5] + ["..."] + load_list[-5:])
        print()

    return loads


def matching_in_hades(hades_tree, dynawo_loads, verbose=False):
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
    new_list = [x for x in dynawo_loads.items() if x[0] in hades_loads]
    print("   (matched %d loads against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def matching_in_dwoB(dynawo_loadsA, dynawo_loadsB):
    # Match:
    new_list = [x for x in dynawo_loadsA.items() if x[0] in dynawo_loadsB]
    print("   (matched %d loads against Dynawo A case)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_load_contingency(
    casedir, case_trees, dwo_paths, dwo_tparams, load_info
):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + "/" + dwo_paths.dydFile_contg
    print("   Configuring file %s" % dyd_file)
    dyd_tree = case_trees.dydTree_contg
    root = dyd_tree.getroot()
    ns = etree.QName(root).namespace

    disconn_eventmodel = "EventSetPointBoolean"
    cnx_id2 = load_info.dydId
    cnx_var2 = LOAD_MODELS[load_info.modelLib]
    param_eventname = "event_stateEvent1"

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
    event_id = "Disconnect my load"
    event.set("id", event_id)
    event.set("lib", disconn_eventmodel)
    event.set("parFile", dwo_paths.parFile_contg)
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iterfind(f"./{{{ns}}}connect"):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the load
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
    new_parset.append(
        etree.Element("{%s}par" % ns, type="BOOL", name=param_eventname, value="true")
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
    # load).  We will keep these, and add new ones.
    #
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we would use the IIDM file, where the load has an
    # attribute that directly provides the bus it is connected to. We
    # already stored this value in the Load_info tuple before.

    bus_label = load_info.bus

    # Add the corresponding curve to the CRV file
    crv_file = casedir + "/" + dwo_paths.curves_inputFile
    print("   Configuring file %s" % crv_file)
    crv_tree = case_trees.crvTree
    root = crv_tree.getroot()
    ns = etree.QName(root).namespace
    new_crv1 = etree.Element(
        "{%s}curve" % ns, model="NETWORK", variable=bus_label + "_Upu_value"
    )
    root.append(new_crv1)
    # Write out the CRV file, preserving the XML format
    crv_tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )
    # And erase the curve we've just added, because we'll be reusing the parsed tree
    root.remove(new_crv1)

    return


def config_hades_load_contingency(casedir, hades_tree, load_name):
    hades_file = casedir + HADES_PATH
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


def save_total_loadpq(dirname, dwohds, dynawo_loads, processed_loads):
    file_name = dirname + "/total_PQ_per_load.csv"
    # Using a dataframe for sorting
    if dwohds:
        column_list = [
            "LOAD",
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
            "LOAD",
            "P_dwoA",
            "P_dwoB",
            "Pdiff_pct",
            "Q_dwoA",
            "Q_dwoB",
            "Qdiff_pct",
            "sumPQdiff_pct",
        ]
    # The processed_loads dict (which contains B case data) contains only the cases
    # that have actually been processed (we may have skipped some in the main loop)
    data_list = []
    for load_name in processed_loads:
        P_dwo = dynawo_loads[load_name].P
        P_proc = processed_loads[load_name][0]
        Pdiff_pct = 100 * (P_dwo - P_proc) / max(abs(P_proc), 0.001)
        Q_dwo = dynawo_loads[load_name].Q
        Q_proc = processed_loads[load_name][1]
        Qdiff_pct = 100 * (Q_dwo - Q_proc) / max(abs(Q_proc), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [
                load_name,
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
