#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# load_contingencies.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all loads that can be matched in the two,
# creates the files needed to run all single-load contingency
# simulations.
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
# On output, the script generates new dirs parallel to basedir:
# load_LABEL1, load_LABEL2, etc.
#


import sys
import os
import subprocess
from lxml import etree
import random


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
        print("\nUsage: %s base_case [element1 element2 element3 ...]\n" % sys.argv[0])
        return 2
    base_case = sys.argv[1]
    filter_list = sys.argv[2:]
    # DEBUG: filter_list = [".ANDU7TR751", "AULNO1LMA1"]

    verbose = False

    # Check all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, verbose)

    # Extract the list of all loads present in the Dynawo case (by staticID)
    dynawo_loads = extract_dynawo_loads(base_case + DYD_FILE, verbose)

    # Reduce the list to those loads that are matched in Astre
    dynawo_loads = matching_in_astre(base_case + ASTRE_FILE, dynawo_loads, verbose)

    # Prepare for random sampling if there's too many
    sampling_ratio = MAX_NCASES / len(dynawo_loads)
    random.seed(RNG_SEED)
    if len(filter_list) == 0 and sampling_ratio < 1:
        print(
            "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
            % (MAX_NCASES, 100 * sampling_ratio)
        )

    # For each matching load, generate the contingency cases
    for load_name in dynawo_loads:

        # If the script was passed a list of loads, filter for them here
        if len(filter_list) != 0 and load_name not in filter_list:
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print("Generating contingency case for load: %s" % load_name)
        # Copy the whole input tree to a new path:
        # Here we also fix any device names with slashes in them (illegal filenames)
        dest_case = dirname + "/load_" + load_name.replace("/", "+")
        clone_base_case(base_case, dest_case)
        # Modify Dynawo case
        config_dynawo_load_contingency(dest_case, load_name)
        # Modify Astre case
        config_astre_load_contingency(dest_case, load_name)

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


def clone_base_case(base_case, dest_case):
    # If the destination exists, warn and rename it to OLD
    if os.path.exists(dest_case):
        print(
            "   WARNING: destination %s exists! -- renaming it to *__OLD__" % dest_case
        )
        os.rename(dest_case, dest_case + "__OLD__")

    try:
        retcode = subprocess.call(
            "rsync -aq --exclude 't0/' '%s/' '%s'" % (base_case, dest_case), shell=True
        )
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def extract_dynawo_loads(dyd_file, verbose=False):
    tree = etree.parse(dyd_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace
    loads = []

    # To enumerate all loads, we would like to use XPath as in:
    #    for element in root.iterfind('.//blackBoxModel[@lib = "Load*"]', root.nsmap):
    # But alas, it is not that expressive. We use this instead:
    for element in root.iter("{%s}blackBoxModel" % ns):
        if element.get("lib")[0:4] == "Load":
            loads.append(element.get("staticId"))

    print("\nFound %d loads in Dynawo DYD file" % len(loads))
    if verbose:
        print("List of all loads in Dynawo DYD file: (total: %d)" % len(loads))
        if len(loads) < 10:
            print(loads)
        else:
            print(loads[:5] + ["..."] + loads[-5:])
        print()

    return loads


def matching_in_astre(astre_file, dynawo_loads, verbose=False):
    tree = etree.parse(astre_file)
    root = tree.getroot()
    astre_loads = set()  # for faster matching below

    # To enumerate all loads in Astre, we could use iter():
    #    for element in root.iter("{%s}conso" % ns):
    #        loads.append(element.get("nom"))
    # But this time we'll use XPath since it's quite simple:
    for element in root.iterfind(".//conso", root.nsmap):
        # Discard loads having noeud="-1"
        if element.get("noeud") != "-1":
            astre_loads.add(element.get("nom"))

    print("\nFound %d loads in Astre file" % len(astre_loads))
    if verbose:
        print("List of all loads in Astre file: (total: %d)" % len(astre_loads))
        if len(astre_loads) < 10:
            print(astre_loads)
        else:
            loads = sorted(astre_loads)
            print(loads[:5] + ["..."] + loads[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_loads if x in astre_loads]
    print("   (matched %d loads against Dynawo file)\n" % len(new_list))

    return new_list


def config_dynawo_load_contingency(casedir, load_name):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + DYD_FILE
    print("   Editing file %s" % dyd_file)
    tree = etree.parse(dyd_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Declare a model `EventSetPointBoolean` (in place of the existing Event).
    # We assume there is only one event. Warn if there's more.
    nevents = 0
    for element in root.iter("{%s}blackBoxModel" % ns):
        if element.get("lib")[0:5] == "Event":
            if nevents >= 1:
                print("WARNING: multiple Event models found in DYD file!")
                break
            old_eventId = element.get("id")
            old_parId = element.get("parId")
            element.set("id", "Disconnect my load")
            element.set("lib", "EventSetPointBoolean")
            element.set("parId", "99991234")
            nevents += 1

    # Get the load id using its staticId
    for element in root.iter("{%s}blackBoxModel" % ns):
        if element.get("staticId") == load_name:
            load_id = element.get("id")
            break

    # Connect the Event model with the load model (we reuse the existing connection)
    connected_ok = False
    for element in root.iter("{%s}connect" % ns):
        if element.get("id1") == old_eventId:
            element.set("id1", "Disconnect my load")
            element.set("var1", "event_state1_value")
            element.set("id2", load_id)
            element.set("var2", "load_switchOffSignal2_value")
            connected_ok = True
            break
    if not connected_ok:
        print(
            "WARNING: configuring the connection of "
            "the Event model and load model failed!!!"
        )
        return -1

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
    tree = etree.parse(par_file)  # TODO: why doesn't remove_blank_text work here?
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Find old parset by parId, and keep the event time
    # Then erase the parset and create a new one with the params we need
    for parset in root.iter("{%s}set" % ns):
        if parset.get("id") == old_parId:
            for param in parset:
                if param.get("name") == "event_tEvent":
                    event_time = param.get("value")
                    break
            break

    parent = parset.getparent()
    parent.remove(parset)
    new_parset = etree.Element("set", id="99991234")
    new_parset.append(
        etree.Element("par", type="DOUBLE", name="event_tEvent", value=event_time)
    )
    new_parset.append(
        etree.Element("par", type="BOOL", name="event_stateEvent1", value="true")
    )
    # NOTE: if using lxml v4.5 or higher, you may try
    # using etree.indent(new_parset) for better formatting
    parent.append(new_parset)

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
    # variables that makes sense to have in the output. The base case
    # is expected to have the variables that monitor the behavior of
    # the SVC (pilot point voltage, K level, and P,Q of participating
    # generators).  We will keep these, and add new ones.
    #
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we have to use the IIDM file, where the load has an id
    # equal to the `staticID` attribute of the dynamic load model
    # (variable load_name here). But now you have to take into account
    # that the bus topology may be either `BUS_BREAKER` or
    # `NODE_BREAKER`, as you'll do things differently in each case:
    #
    #   - `BUS_BREAKER`: recognizable because the static load has an
    #     attribute "bus", which is the identifyer of the correspondig
    #     `bus` element in the IIDM (Note: there's no need to search
    #     for this bus through the whole XML; you can search it from
    #     the parent element of the load, the `voltageLevel`). Its
    #     voltage variable is formed by concatenating the bus id and
    #     `"_Upu_value"`. The specified model has to be
    #     "NETWORK". Example, for load ".ANDU7TR751":
    #
    #        `<curve model="NETWORK" variable=".ANDU771_Upu_value"/>`
    #
    #   - `NODE_BREAKER`: recognizable because the static load has an
    #     attribute "node" instead of "bus". In the node-breaker
    #     topology there are no `bus` elements; instead, there are
    #     `busbarSection` elements, which connect with each other and
    #     loads, gens, etc. through "nodes". Now, it would be a bit
    #     contrived to resolve the topology in order to find out which
    #     of the busbarSections a load is effectively connected
    #     to. This is not worth it, as we just want a voltage point to
    #     monitor that is "close enough" to the disconnected load.
    #     Instead, we will resort to this **simple heuristic**: just
    #     take the first busbarSection that happens to have a non-null
    #     voltage value (attribute "v"), and we will assume the load
    #     was connected to that one. Its voltage variable is formed by
    #     concatenating the busbarSection id and `"_Upu_value"`. The
    #     specified model has to be "NETWORK". Example, for load
    #     "AULNO1LMA1":
    #
    #        `<curve model="NETWORK" variable="AULNOP1_1C_Upu_value"/>`
    #

    iidm_file = casedir + IIDM_FILE
    tree = etree.parse(iidm_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace
    # Find out if it's BUS_BREAKER or NODE_BREAKER
    for iidm_load in root.iter("{%s}load" % ns):
        if iidm_load.get("id") == load_name:
            break
    topology = iidm_load.getparent().get("topologyKind")
    # Find out the bus name
    bus_name = None
    if topology == "BUS_BREAKER":
        bus_name = iidm_load.get("bus")
    elif topology == "NODE_BREAKER":
        node_breaker_topo = iidm_load.getparent().find("{%s}nodeBreakerTopology" % ns)
        for node in node_breaker_topo:
            node_type = etree.QName(node).localname
            if node_type == "busbarSection" and node.get("v") is not None:
                bus_name = node.get("id")
                break
        if bus_name is None:
            raise ValueError("No busbar found for load %" % load_name)
    else:
        raise ValueError("Load % in a substation with unknown topology!" % load_name)

    # Finally, add the corresponding curve to the CRV file
    crv_file = casedir + CRV_FILE
    print("   Editing file %s" % crv_file)
    tree = etree.parse(crv_file, etree.XMLParser(remove_blank_text=True))
    curves_input = tree.getroot()
    ns = etree.QName(curves_input).namespace
    curves_input.append(
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


def config_astre_load_contingency(casedir, load_name):
    astre_file = casedir + ASTRE_FILE
    print("   Editing file %s" % astre_file)
    tree = etree.parse(astre_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Find the load in Astre (elements with tag "conso"; load name is atttribute "nom")
    # Keep its load id ("num") and its bus id ("noeud")
    for astre_load in root.iter("{%s}conso" % ns):
        if astre_load.get("nom") == load_name:
            break
    load_id = astre_load.get("num")
    bus_id = astre_load.get("noeud")

    # Configure the event by means of the `evtouvrtopo` element.  We
    # just edit the first existing event (keeping its time value), and
    # remove all other events.  We link to the load id using the
    # `ouvrage` attribute.  The event type for loads is "3", and
    # typeevt for disconnections is "1").
    nevents = 0
    for astre_event in root.iter("{%s}evtouvrtopo" % ns):
        if nevents == 0:
            astre_event.set("ouvrage", load_id)
            astre_event.set("type", "3")
            nevents = 1
        else:
            astre_event.getparent().remove(astre_event)
    if nevents != 1:
        raise ValueError("Astre file %s does not contain any events" % astre_file)

    # Add variables to the curves section: "courbe" elements are
    # children of element "entreesAstre" and siblings to "scenario".
    # The base case file is expected to have some courves configured
    # (the variables that monitor the behavior of the SVC: pilot point
    # voltage, K level, and P,Q of participating generators). We will
    # keep these, and add new ones.
    #
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we get the name of the bus that the load is attached to
    # and add an element as in the example:
    #
    #     ```
    #       <courbe nom="BUSNAME_Upu_value" typecourbe="63" ouvrage="BUSID" type="7"/>
    #     ```
    #
    # Here we use variable names that are as close as possible to
    # those used in Dynawo.
    for load_bus in root.iter("{%s}noeud" % ns):
        if load_bus.get("num") == bus_id:
            break
    load_bus_name = load_bus.get("nom")

    first_astre_curve = root.find(".//{%s}courbe" % ns)
    astre_entrees = first_astre_curve.getparent()
    astre_entrees.append(
        etree.Element(
            "courbe",
            nom="NETWORK_" + load_bus_name + "_Upu_value",
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
