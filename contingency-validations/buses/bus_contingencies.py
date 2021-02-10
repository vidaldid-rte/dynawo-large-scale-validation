#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# bus_contingencies.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all BUSES that can be matched in the two (but
# only those having a BUS_BREAKER topology in Dynawo), generates the
# files for running a single-bus contingency.
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
# prefix bus_LABEL1, bus_LABEL2, etc.
#
# IMPORTANT NOTES: disconnecting a bus in Dynawo is rather
# straightforward, since it can be declared via a single disconnection
# event. Astre, on the other hand, does not have this feature,
# therefore we resort to enumerating and disconnecting everything
# attached to the bus. In more detail, this is the strategy we follow:
#
#   * Bus candidates: to avoid overly complex processing, we only
#     consider buses having a BUS_BREAKER topology whose neighbor
#     buses are also BUS_BREAKER (this avoids having to do topology
#     processing). Bear in mind that the number of NODE_BREAKER buses
#     in current RTE's Dynawo cases is only around 1% to 2% anyway.
#
#   * Bus disconnection: straightforward in the case of Dynawo. For
#     Astre, we enumerate all connected lines, transformers,
#     generators, loads, and shunts; and disconnect each.
#
#   * Curves: we include not only the neighbor buses but the
#     diconnected bus itself, just to double-check that the
#     disconnection worked.
#


import sys
import os
import subprocess
from lxml import etree
import random
import re


MAX_NCASES = 50000  # limits the no. of contingency cases (via random sampling)
RNG_SEED = 42
ASTRE_FILE = "/Astre/donneesModelesEntree.xml"
JOB_FILE = "/fic_JOB.xml"
DYD_FILE = "/tFin/fic_DYD.xml"
PAR_FILE = "/tFin/fic_PAR.xml"
CRV_FILE = "/tFin/fic_CRV.xml"
IIDM_FILE = "/tFin/fic_IIDM.xml"


def main():

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
    # DEBUG:(Lyon) filter_list = ["BOLL5P61"]

    verbose = True

    # Check all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, verbose)
    edited_case = dirname + "/TMP_CONTINGENCYCASE"

    # Extract the list of all (active) BUSES in the Dynawo case
    dynawo_buses = extract_dynawo_buses(base_case + IIDM_FILE, verbose)

    # Reduce the list to those BUSES that are matched in Astre
    dynawo_buses = matching_in_astre(base_case + ASTRE_FILE, dynawo_buses, verbose)

    # Prepare for random sampling if there's too many
    sampling_ratio = MAX_NCASES / len(dynawo_buses)
    random.seed(RNG_SEED)
    if len(filter_list) == 0 and sampling_ratio < 1:
        print(
            "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
            % (MAX_NCASES, 100 * sampling_ratio)
        )

    # For each matching BUS, generate the contingency case
    for bus_name in dynawo_buses:

        # If the script was passed a list of buses, filter for them here
        bus_name_matches = [r.search(bus_name) for r in filter_list]
        if len(filter_list) != 0 and not any(bus_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print("Generating conting. case for bus %s" % bus_name)

        # Copy the whole input tree to a new path:
        clone_base_case(base_case, edited_case)

        # Modify the Dynawo case (DYD,PAR,CRV)
        config_dynawo_bus_contingency(edited_case, bus_name, dynawo_buses[bus_name])

        # Modify the Astre case
        config_astre_bus_contingency(edited_case, bus_name, dynawo_buses[bus_name])

        # Save the wole case using "deduplication"
        # Here we also fix any device names with slashes in them (illegal filenames)
        deduped_case = dirname + "/bus_" + bus_name.replace("/", "+")
        dedup_save(basename, edited_case, deduped_case)

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
            "rsync -aq --exclude 't0/' '%s/' '%s'" % (input_case, dest_case), shell=True
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
    dedup_cmd = "rsync -a --delete --link-dest='../%s' '%s/' '%s'" % (
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


def extract_dynawo_buses(iidm_file, verbose=False):
    tree = etree.parse(iidm_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace
    buses = dict()

    # We build a dictionary with the buses and their neighbors (to be
    # used when configuring the curves).  We only consider BUS_BREAKER
    # buses, whose neighbors are all BUS_BREAKER as well.  We do this
    # by searching all branches (a good side-effect is that this will
    # also skip non-connected buses).
    for branch in root.iter("{%s}line" % ns, "{%s}twoWindingsTransformer" % ns):
        bus1 = branch.get("bus1")
        bus2 = branch.get("bus2")
        if bus1 is not None:
            if buses.get(bus1) is not None:
                buses[bus1].append(bus2)
            else:
                buses[bus1] = [bus2]
        if bus2 is not None:
            if buses.get(bus2) is not None:
                buses[bus2].append(bus1)
            else:
                buses[bus2] = [bus1]
    keys = list(buses.keys())
    for bus in keys:
        if None in buses[bus]:
            del buses[bus]
        else:
            buses[bus] = set(buses[bus])  # remove duplicates coming from multiple lines

    print(
        "\nFound %d BUS_BREAKER buses (with all BUS_BREAKER neighbors) in the IIDM file"
        % len(buses)
    )

    if verbose:
        print(
            "Abridged list of all BUS_BREAKER buses found in the IIDM file: (total: %d)"
            % len(buses)
        )
        bus_list = sorted(buses.keys())
        if len(bus_list) < 10:
            print(bus_list)
        else:
            print(bus_list[:5] + ["..."] + bus_list[-5:])
        print()

    return buses


def matching_in_astre(astre_file, dynawo_buses, verbose=False):
    tree = etree.parse(astre_file)
    root = tree.getroot()
    astre_buses = set()  # for faster matching below

    for bus in root.iterfind(".//noeud", root.nsmap):
        astre_buses.add(bus.get("nom"))

    print("\nFound %d buses in Astre file" % len(astre_buses))
    if verbose:
        print("Sample list of all BUSES in Astre file: (total: %d)" % len(astre_buses))
        bus_list = sorted(astre_buses)
        if len(bus_list) < 10:
            print(bus_list)
        else:
            print(bus_list[:5] + ["..."] + bus_list[-5:])
        print()

    # Match: not only the buses themselves, but also all of their neighbors
    new_list = [
        x
        for x in dynawo_buses.items()
        if x[0] in astre_buses and x[1].issubset(astre_buses)
    ]
    print("   (matched %d buses against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_bus_contingency(casedir, bus_name, bus_neighbors):
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
    event_id = "Disconnect my bus"
    event = etree.SubElement(root, "blackBoxModel")
    event.set("id", event_id)
    event.set("lib", "EventConnectedStatus")
    event.set("parFile", "tFin/fic_PAR.xml")
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iter("{%s}connect" % ns):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the bus
    cnx = etree.SubElement(root, "connect")
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", "NETWORK")
    cnx.set("var2", bus_name + "_state_value")

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
    new_parset.append(
        etree.Element("par", type="BOOL", name="event_open", value="true")
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
    # We'll just add the voltages of the bus and all its neighbor
    # buses. We already stored these before, in the set bus_neighbors.
    crv_file = casedir + CRV_FILE
    print("   Editing file %s" % crv_file)
    tree = etree.parse(crv_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    for neighbor in bus_neighbors:
        root.append(
            etree.Element("curve", model="NETWORK", variable=neighbor + "_Upu_value")
        )
    root.append(
        etree.Element("curve", model="NETWORK", variable=bus_name + "_Upu_value")
    )

    # Write out the CRV file, preserving the XML format
    tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    return 0


def config_astre_bus_contingency(casedir, bus_name, bus_neighbors):
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

    # To disconnect the bus in Astre, we disconnect all lines,
    # transformers, and switches that connect to it
    bus_id = None
    for noeud in root.iter("{%s}noeud" % ns):
        if noeud.get("nom") == bus_name:
            bus_id = noeud.get("num")
            break
    # Branches:
    for branch in root.iter("{%s}quadripole" % ns):
        busID_from = branch.get("nor")
        busID_to = branch.get("nex")
        if bus_id == busID_from or bus_id == busID_to:
            event = etree.SubElement(scenario, "evtouvrtopo")
            event.set("instant", event_time)
            event.set("ouvrage", branch.get("num"))
            event.set("type", "9")
            event.set("typeevt", "1")
            if bus_id == busID_from:
                event.set("cote", "1")
            else:
                event.set("cote", "2")
    # Breakers/switches:
    for breaker in root.iter("{%s}couplage" % ns):
        busID_from = breaker.get("nor")
        busID_to = breaker.get("nex")
        if bus_id == busID_from or bus_id == busID_to:
            event = etree.SubElement(scenario, "evtouvrtopo")
            event.set("instant", event_time)
            event.set("ouvrage", breaker.get("num"))
            event.set("type", "5")
            event.set("typeevt", "1")
            event.set("cote", "0")

    # Add variables to the curves section: "courbe" elements are
    # children of element "entreesAstre" and siblings to "scenario".
    # The base case file is expected to have some curves configured
    # (the variables that monitor the behavior of the SVC: pilot point
    # voltage, K level, and P,Q of participating generators). We will
    # keep these, and add new ones.
    #
    # We'll just add the voltages of the bus and all its neighbor
    # buses (ee already stored these before, in the set
    # bus_neighbors). We add xml elements as in this example:
    #
    #     ```
    #       <courbe nom="BUSNAME_Upu_value" typecourbe="63" ouvrage="BUSID" type="7"/>
    #     ```
    #
    # Since the name of the curve variable is free, we'll use names
    # that match Dynawo.
    first_astre_curve = root.find(".//{%s}courbe" % ns)
    astre_entrees = first_astre_curve.getparent()
    # First the neighbor buses:
    for neighbor_name in bus_neighbors:
        neighbor_id = None
        for noeud in root.iter("{%s}noeud" % ns):
            if noeud.get("nom") == neighbor_name:
                neighbor_id = noeud.get("num")
                break
        astre_entrees.append(
            etree.Element(
                "courbe",
                nom="NETWORK_" + neighbor_name + "_Upu_value",
                typecourbe="63",
                ouvrage=neighbor_id,
                type="7",
            )
        )
    # Then the bus itself:
    astre_entrees.append(
        etree.Element(
            "courbe",
            nom="NETWORK_" + bus_name + "_Upu_value",
            typecourbe="63",
            ouvrage=bus_id,
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

    return


if __name__ == "__main__":
    sys.exit(main())
