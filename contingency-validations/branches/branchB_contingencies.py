#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# branch_contingencies.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all BRANCHES (i.e. lines & transformers) that
# can be matched in the two, generates the files for running a
# single-branch contingency for each device.
#
# On input, the files are expected to have this structure:
#
# basedir/
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
# On output, the script generates new dirs parallel to basedir, with
# prefixes that depend on the type of branch disconnection:
#
#   * Both ends: branchB_LABEL1, branchB_LABEL2, etc.
#
#   * FROM end: branchF_LABEL1, branchF_LABEL2, etc.
#
#   * TO end: branchT_LABEL1, branchT_LABEL2, etc.
#
# The type of disconnection is selected by means of the name with
# which this script is invoked ("branchF_contingencies.py", etc.).
#


import sys
import os
import subprocess
from lxml import etree
from collections import namedtuple
import pandas as pd


ASTRE_FILE = "/Astre/donneesModelesEntree.xml"
JOB_FILE = "/fic_JOB.xml"
DYD_FILE = "/tFin/fic_DYD.xml"
PAR_FILE = "/tFin/fic_PAR.xml"
CRV_FILE = "/tFin/fic_CRV.xml"
IIDM_FILE = "/tFin/fic_IIDM.xml"


def main():

    if len(sys.argv) < 2:
        print("\nUsage: %s BASECASE [element1 element2 element3 ...]\n" % sys.argv[0])
        return 2
    base_case = sys.argv[1]
    filter_list = sys.argv[2:]
    # DEBUG:(Lyon) filter_list = ["CHARPL31CIVRI", "CHARPY631",
    # ".CHAML61.CHTD", RULHAY711, "VALS L31ZP.VE"]

    verbose = True

    # Select disconnection mode from how the script is named:
    disconn_mode = "BOTH_ENDS"
    called_as = os.path.basename(sys.argv[0])
    if called_as[:7] == "branchF":
        disconn_mode = "FROM"
    elif called_as[:7] == "branchT":
        disconn_mode = "TO"

    # Check all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, verbose)
    edited_case = dirname + "/TMP_CONTINGENCYCASE"

    # Extract the list of all (active) BRANCHES in the Dynawo case
    dynawo_branches = extract_dynawo_branches(base_case + IIDM_FILE, verbose)

    # Reduce the list to those BRANCHES that are matched in Astre
    dynawo_branches = matching_in_astre(
        base_case + ASTRE_FILE, dynawo_branches, verbose
    )

    # Initialize another dict to keep Astre's (P,Q)-flows of the disconnected branch
    astre_branches = dict()

    # For each matching BRANCH, generate the contingency case
    for branch_name in dynawo_branches:

        # If the script was passed a list of branches, filter for them here
        if len(filter_list) != 0 and branch_name not in filter_list:
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

        # Copy the whole input tree to a new path:
        clone_base_case(base_case, edited_case)

        # Modify the Dynawo case (DYD,PAR,CRV)
        config_dynawo_branch_contingency(
            edited_case, branch_name, dynawo_branches[branch_name], disconn_mode
        )

        # Modify the Astre case, and obtain its disrupted power flows (P,Q)
        astre_branches[branch_name] = config_astre_branch_contingency(
            edited_case, branch_name, dynawo_branches[branch_name], disconn_mode
        )

        # Save the wole case using "deduplication"
        deduped_case = dirname + "/branch" + disconn_mode[0] + "_" + branch_name
        dedup_save(basename, edited_case, deduped_case)

    # Finally, save the (P,Q) values of disconnected branches in all processed cases
    save_total_branchPQ(dirname, dynawo_branches, astre_branches)

    return 0


def check_inputfiles(input_case, verbose=False):
    if not os.path.isdir(input_case):
        raise ValueError("source directory %s not found" % input_case)

    # remove trailing slash so that basename/dirname below behave consistently:
    if input_case[-1] == "/":
        input_case = input_case[:-1]
    basename = os.path.basename(input_case)
    dirname = os.path.dirname(input_case)
    # corner case: if called from the parent dir, dirname is empty
    if dirname == "":
        dirname = "."

    print("\nUsing input_case: %s" % input_case)
    print("New cases will be generated under: %s" % dirname)
    if verbose:
        print("input_case: %s" % input_case)
        print("basename: %s" % basename)
        print("dirname:  %s" % dirname)

    if not (
        os.path.isfile(input_case + "/Astre/donneesModelesEntree.xml")
        and os.path.isfile(input_case + "/fic_JOB.xml")
        and os.path.isfile(input_case + "/tFin/fic_DYD.xml")
        and os.path.isfile(input_case + "/tFin/fic_PAR.xml")
        and os.path.isfile(input_case + "/tFin/fic_CRV.xml")
    ):
        raise ValueError("some expected files are missing in %s\n" % input_case)

    return input_case, basename, dirname


def clone_base_case(input_case, dest_case):
    # If the destination exists, remove it (it's temporary anyway)
    if os.path.exists(dest_case):
        remove_case(dest_case)

    try:
        retcode = subprocess.call(
            "cp -a '%s' '%s'" % (input_case, dest_case), shell=True
        )
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def remove_case(dest_case):
    try:
        retcode = subprocess.call("rm -rf '%s'" % dest_case, shell=True)
        if retcode < 0:
            raise ValueError("rm of bad case was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("rm of bad case returned error code: %d" % retcode)
    except OSError as e:
        print("call to rm failed: ", e, file=sys.stderr)
        raise


def dedup_save(basename, edited_case, deduped_case):
    # If the destination exists, warn and rename it to OLD
    if os.path.exists(deduped_case):
        print(
            "   WARNING: destination %s exists! -- renaming it to *__OLD__"
            % deduped_case
        )
        os.rename(deduped_case, deduped_case + "__OLD__")

    # Save it using "deduplication" (actually, hard links)
    dedup_cmd = "rsync -a --delete --link-dest=../%s '%s/' '%s'" % (
        basename,
        edited_case,
        deduped_case,
    )
    try:
        retcode = subprocess.call(dedup_cmd, shell=True)
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def extract_dynawo_branches(iidm_file, verbose=False):
    tree = etree.parse(iidm_file)
    root = tree.getroot()
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


def matching_in_astre(astre_file, dynawo_branches, verbose=False):
    tree = etree.parse(astre_file)
    root = tree.getroot()
    astre_branches = set()  # for faster matching below

    for branch in root.iterfind(".//quadripole", root.nsmap):
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


def config_dynawo_branch_contingency(casedir, branch_name, branch_info, disc_mode):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + DYD_FILE
    print("   Editing file %s" % dyd_file)
    tree = etree.parse(dyd_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Erase all existing Event models (keep the IDs to remove their
    # connections later below)
    old_eventIds = []
    old_parIds = []
    for event in root.iter("{%s}blackBoxModel" % ns):
        if event.get("lib")[0:5] == "Event":
            old_eventIds.append(event.get("id"))
            old_parIds.append(event.get("parId"))
            event.getparent().remove(event)

    # Declare a new Event
    event_id = "Disconnect my branch"
    event = etree.SubElement(root, "blackBoxModel")
    event.set("id", event_id)
    event.set("lib", "EventQuadripoleDisconnection")
    event.set("parFile", "tFin/fic_PAR.xml")
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iter("{%s}connect" % ns):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the branch
    cnx = etree.SubElement(root, "connect")
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", "NETWORK")
    cnx.set("var2", branch_name + "_state_value")

    # Write out the DYD file, preserving the XML format
    tree.write(
        dyd_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    ###########################################################
    # PAR file: add a section with the disconnecton parameters
    ###########################################################
    par_file = casedir + PAR_FILE
    print("   Editing file %s" % par_file)
    tree = etree.parse(par_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Erase all existing parsets used by the Events removed above
    # But keep the event time (read from the first one)
    event_time = None
    for parset in root.iter("{%s}set" % ns):
        if parset.get("id") == old_parIds[0]:
            for param in parset:
                if param.get("name") == "event_tEvent":
                    event_time = param.get("value")
                    break
        if parset.get("id") in old_parIds:
            parset.getparent().remove(parset)

    if not event_time:
        print("Error found while processing the PAR file!!!")
        raise ValueError("No event_tEvent found to use for the Event")

    # Insert the new parset with the params we need
    new_parset = etree.Element("set", id="99991234")
    new_parset.append(
        etree.Element("par", type="DOUBLE", name="event_tEvent", value=event_time)
    )
    open_F = "true"
    open_T = "true"
    if disc_mode == "FROM":
        open_T = "false"
    if disc_mode == "TO":
        open_F = "false"
    new_parset.append(
        etree.Element("par", type="BOOL", name="event_disconnectOrigin", value=open_F)
    )
    new_parset.append(
        etree.Element(
            "par", type="BOOL", name="event_disconnectExtremity", value=open_T
        )
    )
    root.append(new_parset)

    # Write out the PAR file, preserving the XML format
    tree.write(
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
    crv_file = casedir + CRV_FILE
    print("   Editing file %s" % crv_file)
    tree = etree.parse(crv_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    root.append(
        etree.Element("curve", model="NETWORK", variable=bus_from + "_Upu_value")
    )
    root.append(etree.Element("curve", model="NETWORK", variable=bus_to + "_Upu_value"))
    # Write out the CRV file, preserving the XML format
    tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    return 0


def config_astre_branch_contingency(casedir, branch_name, branch_info, disc_mode):
    astre_file = casedir + ASTRE_FILE
    print("   Editing file %s" % astre_file)
    tree = etree.parse(astre_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Configure the event by means of the `evtouvrtopo` element.  We
    # first remove all existing events (keeping the event time from
    # the first one).
    event_time = None
    scenario = None
    nevents = 0
    for astre_event in root.iter("{%s}evtouvrtopo" % ns):
        if nevents == 0:
            event_time = astre_event.get("instant")
            scenario = astre_event.getparent()
            astre_event.getparent().remove(astre_event)
            nevents = 1
        else:
            astre_event.getparent().remove(astre_event)
    if nevents != 1:
        raise ValueError("Astre file %s does not contain any events!" % astre_file)

    # Find the branch in Astre
    for astre_branch in root.iter("{%s}quadripole" % ns):
        if astre_branch.get("nom") == branch_name:
            break
    branch_id = astre_branch.get("num")
    busID_from = astre_branch.get("nor")
    busID_to = astre_branch.get("nex")
    if busID_from == "-1" or busID_to == "-1":
        raise ValueError("this branch is disconnected in Astre!!!")
    bus_from = branch_info.busFrom  # we will use Dynawo's name for the curve var
    bus_to = branch_info.busTo  # we will use Dynawo's name for the curve var
    branch_vars = astre_branch.find("{%s}variables" % ns)
    branch_P = float(branch_vars.get("por"))
    branch_Q = float(branch_vars.get("qor"))

    # We now insert our own events. We link to the branch id using the
    # `ouvrage` attribute.  The type for branches is "9", and the
    # typeevt for disconnections is "1".  The side is given by the
    # `cote` attribute (0 = both ends; 1 = "From" end; 2 = "To" end.
    event = etree.SubElement(scenario, "evtouvrtopo")
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
    first_astre_curve = root.find(".//{%s}courbe" % ns)
    astre_entrees = first_astre_curve.getparent()
    astre_entrees.append(
        etree.Element(
            "courbe",
            nom="NETWORK_" + bus_from + "_Upu_value",
            typecourbe="63",
            ouvrage=busID_from,
            type="7",
        )
    )
    astre_entrees.append(
        etree.Element(
            "courbe",
            nom="NETWORK_" + bus_to + "_Upu_value",
            typecourbe="63",
            ouvrage=busID_to,
            type="7",
        )
    )

    # Write out the Astre file, preserving the XML format
    tree.write(
        astre_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="ISO-8859-1",
        standalone=False,
    )

    return (branch_P, branch_Q)


def save_total_branchPQ(dirname, dynawo_branches, astre_branches):
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
