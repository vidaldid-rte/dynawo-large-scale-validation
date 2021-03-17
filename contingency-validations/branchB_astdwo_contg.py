#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# branch?_astdwo_contg.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all BRANCHES (i.e. lines & transformers) that
# can be matched in the two, generates the files for running a
# single-branch contingency for each device.
#
# On input, the files are expected to have a structure similar to this
# (not strict, see below):
#
# basecase/
# ├── Astre
# │   └── donneesModelesEntree.xml
# ├── fic_JOB.xml
# ├── t0
# │   ├── fic_CRV.xml
# │   ├── fic_DYD.xml
# │   ├── fic_IIDM.xml
# │   └── fic_PAR.xml
# └── tFin
#    ├── fic_CRV.xml
#    ├── fic_DYD.xml
#    ├── fic_IIDM.xml
#    └── fic_PAR.xml
#
# For Astre, the structure should be strictly as the above example.  However,
# for Dynawo we read the actual paths from the existing JOB file, and we configure the
# contingency in the last job defined inside the JOB file (see module dwo_jobinfo).
#
# On output, the script generates new dirs sibling to basecase, with
# prefixes that depend on the type of branch disconnection:
#   * Both ends: branchB_LABEL1, branchB_LABEL2, etc.
#   * FROM end: branchF_LABEL1, branchF_LABEL2, etc.
#   * TO end: branchT_LABEL1, branchT_LABEL2, etc.
#
# The type of disconnection is selected by means of the name with
# which this script is invoked ("branchF_contingencies.py", etc.).
#

import os
import random
import re
import sys
from collections import namedtuple
from common_funcs import check_inputfiles, copy_basecase, parse_basecase
from lxml import etree
import pandas as pd

# Relative imports only work for proper Python packages, but we do not want to
# structure all these as a package; we'd like to keep them as a collection of loose
# Python scripts, at least for now (because this is not really a Python library). So
# the following hack is ugly, but needed:
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Alternatively, you could set PYTHONPATH to PYTHONPATH="/<dir>/dynawo-validation-AIA"
from xml_utils.dwo_jobinfo import get_dwo_jobpaths  # noqa: E402
from xml_utils.dwo_jobinfo import get_dwo_tparams  # noqa: E402


MAX_NCASES = 5  # limits the no. of contingency cases (via random sampling)
RNG_SEED = 42
ASTRE_PATH = "/Astre/donneesModelesEntree.xml"


def main():
    verbose = False
    if len(sys.argv) < 2:
        print("\nUsage: %s BASECASE [element1 element2 element3 ...]\n" % sys.argv[0])
        print(
            "\nThe optional list may include regular expressions. "
            "If the list is empty, all possible contingencies will be generated "
            "(if below MAX_NCASES=%d; otherwise a random sample is generated).\n"
            % MAX_NCASES
        )
        return 2
    base_case = sys.argv[1]
    filter_list = [re.compile(x) for x in sys.argv[2:]]
    # Select disconnection mode from how the script is named:
    disconn_mode = "BOTH_ENDS"
    called_as = os.path.basename(sys.argv[0])
    if called_as[:7] == "branchF":
        disconn_mode = "FROM"
    elif called_as[:7] == "branchT":
        disconn_mode = "TO"

    # Get Dynawo paths from the JOB file
    dwo_paths = get_dwo_jobpaths(base_case)

    # Get the simulation time parameters (from Dynawo's case)
    dwo_tparams = get_dwo_tparams(base_case)

    # Check that all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, dwo_paths, verbose)

    # Parse all XML files in the basecase
    parsed_case = parse_basecase(base_case, dwo_paths, ASTRE_PATH)

    # Extract the list of all (active) BRANCHES in the Dynawo case
    dynawo_branches = extract_dynawo_branches(parsed_case.iidmTree, verbose)

    # Reduce the list to those BRANCHES that are matched in Astre
    dynawo_branches = matching_in_astre(parsed_case.astreTree, dynawo_branches, verbose)

    # Prepare for random sampling if there's too many
    sampling_ratio = MAX_NCASES / len(dynawo_branches)
    random.seed(RNG_SEED)
    if len(filter_list) == 0 and sampling_ratio < 1:
        print(
            "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
            % (MAX_NCASES, 100 * sampling_ratio)
        )

    # Initialize another dict to keep Astre's (P,Q)-flows of each disconnected branch
    astre_branches = dict()

    # For each matching BRANCH, generate the contingency case
    for branch_name in dynawo_branches:

        # If the script was passed a list of branches, filter for them here
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

        # Copy the basecase (unchanged files and dir structure)
        # Note we fix any device names with slashes in them (illegal filenames)
        contg_casedir = (
            dirname + "/branch" + disconn_mode[0] + "_" + branch_name.replace("/", "+")
        )
        copy_basecase(base_case, dwo_paths, contg_casedir)

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

        # Modify the Astre case, and obtain its disrupted power flows (P,Q)
        astre_branches[branch_name] = config_astre_branch_contingency(
            contg_casedir,
            parsed_case.astreTree,
            branch_name,
            dynawo_branches[branch_name],
            disconn_mode,
        )

    # Finally, save the (P,Q) values of disconnected branches in all processed cases
    save_total_branchpq(dirname, dynawo_branches, astre_branches)

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
        # Keep only the active ones
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


def matching_in_astre(astre_tree, dynawo_branches, verbose=False):
    root = astre_tree.getroot()

    # Retrieve the list of Astre branches
    astre_branches = set()  # for faster matching below
    reseau = root.find("./reseau", root.nsmap)
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        astre_branches.add(branch.get("nom"))

    print("\nFound %d branches in Astre file" % len(astre_branches))
    if verbose:
        print(
            "Sample list of all BRANCHES in Astre file: (total: %d)"
            % len(astre_branches)
        )
        branch_list = sorted(astre_branches)
        if len(branch_list) < 10:
            print(branch_list)
        else:
            print(branch_list[:5] + ["..."] + branch_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_branches.items() if x[0] in astre_branches]
    print("   (matched %d branches against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_branch_contingency(
    casedir, case_trees, dwo_paths, dwo_tparams, branch_name, branch_info, disc_mode
):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + "/" + dwo_paths.dydFile
    print("   Configuring file %s" % dyd_file)
    dyd_tree = case_trees.dydTree
    root = dyd_tree.getroot()

    # Erase all existing Event models (keep the IDs to remove their
    # connections later below)
    old_eventIds = []
    old_parIds = []
    for event in root.iterfind("./blackBoxModel", root.nsmap):
        if event.get("lib")[0:5] == "Event":
            old_eventIds.append(event.get("id"))
            old_parIds.append(event.get("parId"))
            event.getparent().remove(event)

    # Declare a new Event
    ns = etree.QName(root).namespace
    event = etree.SubElement(root, "{%s}blackBoxModel" % ns)
    event_id = "Disconnect my branch"
    event.set("id", event_id)
    event.set("lib", "EventQuadripoleDisconnection")
    event.set("parFile", dwo_paths.parFile)
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iterfind("./connect", root.nsmap):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the branch
    cnx = etree.SubElement(root, "{%s}connect" % ns)
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", "NETWORK")
    cnx.set("var2", branch_name + "_state_value")

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
    par_file = casedir + "/" + dwo_paths.parFile
    print("   Configuring file %s" % par_file)
    par_tree = case_trees.parTree
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
    # generators).  We will keep these, and add new ones.
    #
    # For now we'll just add the voltages of the buses at both ends of
    # the branch. To do this, we would use the IIDM file, where the
    # branch has attribute that directly provides these buses. But we
    # already stored this value in the Branch_info tuple before.

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


def config_astre_branch_contingency(
    casedir, astre_tree, branch_name, branch_info, disc_mode
):
    astre_file = casedir + ASTRE_PATH
    print("   Configuring file %s" % astre_file)
    root = astre_tree.getroot()

    # Configure the event by means of the `evtouvrtopo` element.  We
    # first remove all existing events (keeping the event time from
    # the first one).
    event_time = None
    nevents = 0
    modele = root.find("./modele", root.nsmap)
    entrees = modele.find("./entrees", root.nsmap)
    entreesAstre = entrees.find("./entreesAstre", root.nsmap)
    scenario = entreesAstre.find("./scenario", root.nsmap)
    for astre_event in scenario.iterfind("./evtouvrtopo", root.nsmap):
        if nevents == 0:
            event_time = astre_event.get("instant")
            scenario.remove(astre_event)
            nevents = 1
        else:
            astre_event.getparent().remove(astre_event)
    if nevents != 1:
        raise ValueError("Astre file %s does not contain any events!" % astre_file)

    # Find the branch in Astre
    astre_branch = None
    reseau = root.find("./reseau", root.nsmap)
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for b in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        if b.get("nom") == branch_name:
            astre_branch = b
            break
    branch_id = astre_branch.get("num")
    busID_from = astre_branch.get("nor")
    busID_to = astre_branch.get("nex")
    if busID_from == "-1" or busID_to == "-1":
        raise ValueError("this branch is disconnected in Astre!!!")
    bus_from = branch_info.busFrom  # we will use Dynawo's name for the curve var
    bus_to = branch_info.busTo  # we will use Dynawo's name for the curve var
    branch_vars = astre_branch.find("./variables", root.nsmap)
    branch_P = float(branch_vars.get("por"))
    branch_Q = float(branch_vars.get("qor"))

    # We now insert our own events. We link to the branch id using the
    # `ouvrage` attribute.  The type for branches is "9", and the
    # typeevt for disconnections is "1".  The side is given by the
    # `cote` attribute (0 = both ends; 1 = "From" end; 2 = "To" end.
    ns = etree.QName(root).namespace
    event = etree.SubElement(scenario, "{%s}evtouvrtopo" % ns)
    event.set("instant", event_time)
    event.set("ouvrage", branch_id)
    event.set("type", "9")
    event.set("typeevt", "1")
    if disc_mode == "FROM":
        event.set("cote", "1")
    elif disc_mode == "TO":
        event.set("cote", "2")
    else:
        event.set("cote", "0")

    # Add variables to the curves section: "courbe" elements are
    # children of element "entreesAstre" and siblings to "scenario".
    # The base case file is expected to have some curves configured
    # (the variables that monitor the behavior of the SVC: pilot point
    # voltage, K level, and P,Q of participating generators). We will
    # keep these, and add new ones.
    #
    # For now we'll just add the voltage at the contingency buses. To do
    # this, we get the IDs of the buses at both ends of the branch, and
    # add xml elements as in this example:
    #
    #     ```
    #       <courbe nom="BUSNAME_Upu_value" typecourbe="63" ouvrage="BUSID" type="7"/>
    #     ```
    #
    # Since the name of the curve variable is free, we'll use names
    # that match Dynawo.
    new_crv1 = etree.Element(
        "{%s}courbe" % ns,
        nom="NETWORK_" + bus_from + "_Upu_value",
        typecourbe="63",
        ouvrage=busID_from,
        type="7",
    )
    new_crv2 = etree.Element(
        "{%s}courbe" % ns,
        nom="NETWORK_" + bus_to + "_Upu_value",
        typecourbe="63",
        ouvrage=busID_to,
        type="7",
    )
    entreesAstre.append(new_crv1)
    entreesAstre.append(new_crv2)

    # Write out the Astre file, preserving the XML format
    astre_tree.write(
        astre_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="ISO-8859-1",
        standalone=False,
    )

    # Erase the curve we've just added, because we'll be reusing the parsed tree
    entreesAstre.remove(new_crv1)
    entreesAstre.remove(new_crv2)

    return branch_P, branch_Q


def save_total_branchpq(dirname, dynawo_branches, astre_branches):
    file_name = dirname + "/total_PQ_per_branch.csv"
    # Using a dataframe for sorting
    column_list = [
        "BRANCH",
        "P_dwo",
        "P_ast",
        "Pdiff_pct",
        "Q_dwo",
        "Q_ast",
        "Qdiff_pct",
        "PQdiff_pct",
    ]
    data_list = []
    # We enumerate the astre_branches dict because it contains the cases
    # that have actually been processed (because we may have skipped
    # some in the main loop).
    for branch_name in astre_branches:
        P_dwo = dynawo_branches[branch_name].P
        P_ast = astre_branches[branch_name][0]
        Pdiff_pct = 100 * (P_dwo - P_ast) / max(abs(P_ast), 0.001)
        Q_dwo = dynawo_branches[branch_name].Q
        Q_ast = astre_branches[branch_name][1]
        Qdiff_pct = 100 * (Q_dwo - Q_ast) / max(abs(Q_ast), 0.001)
        PQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [branch_name, P_dwo, P_ast, Pdiff_pct, Q_dwo, Q_ast, Qdiff_pct, PQdiff_pct]
        )

    df = pd.DataFrame(data_list, columns=column_list)
    df.sort_values(
        by=["PQdiff_pct"], inplace=True, ascending=False, na_position="first"
    )
    df.to_csv(file_name, index=False, sep=";", float_format="%.3f", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
