#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# load_contingencies_identByBus.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all BUSES that can be matched in the two,
# generates the files for running a multiple contingency of all loads
# attached to the bus. So it is essentially the same as
# "load_contingencies.py", but this one is designed to work better
# with the newer Dynawo RTE cases, in which many loads have been
# merged (and therefore have very few individual loads left that match
# between Dynawo and Astre).
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
# busloads_LABEL1, busloads_LABEL2, etc.
#


import sys
import os
import subprocess
from lxml import etree
from collections import namedtuple


ASTRE_FILE = "/Astre/donneesModelesEntree.xml"
JOB_FILE = "/fic_JOB.xml"
DYD_FILE = "/tFin/fic_DYD.xml"
PAR_FILE = "/tFin/fic_PAR.xml"
CRV_FILE = "/tFin/fic_CRV.xml"
IIDM_FILE = "/tFin/fic_IIDM.xml"


def main():

    if len(sys.argv) != 2:
        print("\nUsage: %s base_case\n" % sys.argv[0])
        return 2
    base_case = sys.argv[1]
    verbose = False

    # Check all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, verbose)
    edited_case = dirname + "/TMP_CONTINGENCYCASE"

    # Extract the list of all BUSES having LOADS in the Dynawo case (of either topology)
    dynawo_buses = extract_dynawo_buses(base_case + IIDM_FILE, verbose)

    # Reduce the list to those BUSES that are matched in Astre
    dynawo_buses = matching_in_astre(base_case + ASTRE_FILE, dynawo_buses, verbose)

    # Initialize another dict to keed Astre total P,Q of loads
    astre_buses = dict()

    # For each matching load, generate the contingency cases
    for bus_name in dynawo_buses:

        # Uncomment this for generating just a few cases:
        # if bus_name not in ["CRENEP61", "CERGYP71", "BIPOLP71"]: continue

        print(
            "Generating contingency case for loads at bus: %s (type %s)"
            % (bus_name, dynawo_buses[bus_name].topology)
        )

        # Copy the whole input tree to a new path:
        clone_base_case(base_case, edited_case)

        # Modify the Dynawo case (DYD,PAR,CRV)
        result = config_dynawo_loads_contingency(
            edited_case, bus_name, dynawo_buses[bus_name]
        )
        if result == -1:
            remove_case(edited_case)
            continue

        # Modify the Astre case, and obtain total disconnected load (P,Q)
        astre_buses[bus_name] = config_astre_loads_contingency(edited_case, bus_name)

        # Save the wole case using "deduplication"
        deduped_case = dirname + "/busloads_" + bus_name
        dedup_save(basename, edited_case, deduped_case)

    # Finally, save the values of disconnected load in all processed cases
    save_total_load(dirname, dynawo_buses, astre_buses)

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
    Bus_info = namedtuple(
        "Bus_info", "voltageLevel topology busbarSection loads totalP totalQ"
    )

    # Remember that Dynawo's IIDM files contain buses expressed in
    # both topologies (bus-breaker and node-breaker). By inspection,
    # the buses in Astre RTE files seem to correspond the most with
    # those that are of the bus-breaker type in the Dynawo
    # files. Therefore our strategy will be to match bus-breaker buses
    # directly one-to-one, while for node-breaker ones we _assume_
    # that Dynawo's busbarSections will coalesce into one single bus
    # in Astre. (This way, for example, in the Lille case we're able
    # to match 759 buses out of a total of 763 buses in the Dynawo
    # file -- and all 499 buses having loads).
    #
    # We'll do this by enumerating all voltageLevels in the IIDM to
    # build a dictionary {key=<BUSNAME_ASTRE>, value=<Bus_info>}, where
    # BUSNAME_ASTRE is the name it is _expected_ to have in Astre,
    # which is constructed as follows:
    #    * If topology is BUS_BREAKER: use the name(s) of the Dynawo bus(es)
    #    * If topology is NODE_BREAKER: use the name of the voltageLevel + "1"
    buses_with_bad_topo = False
    for vl in root.iterfind(".//voltageLevel", root.nsmap):
        vl_label = vl.get("id")
        if vl.get("topologyKind") == "BUS_BREAKER":
            # The VL may contain more than one bus
            for bus in vl.iter("{%s}bus" % ns):
                bus_label = bus.get("id")
                load_list = []
                totalP = 0
                totalQ = 0
                for load in vl.iter("{%s}load" % ns):
                    if load.get("bus") == bus_label:
                        # Ignore fictitious loads that:
                        #   (a) have no DYD model (id=fict_*)
                        #   (b) have q0="9999" (disconnected in Astre)
                        if load.get("loadType") != "FICTITIOUS" or (
                            load.get("id")[:5] != "fict_" and load.get("q0") != "9999"
                        ):
                            load_list.append(load.get("id"))
                            totalP += float(load.get("p"))
                            totalQ += float(load.get("q"))
                # Only buses having valid loads
                if len(load_list) != 0:
                    buses[bus_label] = Bus_info(
                        voltageLevel=vl_label,
                        topology="BUS_BREAKER",
                        busbarSection=None,
                        loads=load_list,
                        totalP=totalP,
                        totalQ=totalQ,
                    )
        elif vl.get("topologyKind") == "NODE_BREAKER":
            # We will ASSUME connectivity such that there's only one bus in the VL
            load_list = []
            totalP = 0
            totalQ = 0
            for load in vl.iter("{%s}load" % ns):
                # Ignore fictitious loads that:
                #   (a) have no DYD model (id=fict_*)
                #   (b) have q0="9999" (disconnected in Astre)
                if load.get("loadType") != "FICTITIOUS" or (
                    load.get("id")[:5] != "fict_" and load.get("q0") != "9999"
                ):
                    load_list.append(load.get("id"))
                    totalP += float(load.get("p"))
                    totalQ += float(load.get("q"))
            # Only buses having valid loads
            if len(load_list) != 0:
                bus_label = vl_label + "1"
                # don't try to resolve the topology, just take the first active busbar
                busbar_name = None
                topology = vl.find("{%s}nodeBreakerTopology" % ns)
                for node in topology:
                    node_type = etree.QName(node).localname
                    if node_type == "busbarSection" and node.get("v") is not None:
                        busbar_name = node.get("id")
                        break
                buses[bus_label] = Bus_info(
                    voltageLevel=vl_label,
                    topology="NODE_BREAKER",
                    busbarSection=busbar_name,
                    loads=load_list,
                    totalP=totalP,
                    totalQ=totalQ,
                )
        else:
            buses_with_bad_topo = True

    if buses_with_bad_topo:
        print("WARNING: found voltageLevels with bad topology")

    print("\nFound %d buses (having loads) in Dynawo IIDM file" % len(buses))
    if verbose:
        print("Sample list of all buses in Dynawo IIDM file: (total: %d)" % len(buses))
        bus_list = list(buses.items())
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
        print("Sample list of all buses in Astre file: (total: %d)" % len(astre_buses))
        bus_list = sorted(astre_buses)
        if len(bus_list) < 10:
            print(bus_list)
        else:
            print(bus_list[:5] + ["..."] + bus_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_buses.items() if x[0] in astre_buses]
    print("   (matched %d buses against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_loads_contingency(casedir, bus_name, bus_info):
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
    event_id = "Disconnect all loads at bus"
    event = etree.SubElement(root, "blackBoxModel")
    event.set("id", event_id)
    event.set("lib", "EventSetPointBoolean")
    event.set("parFile", "tFin/fic_PAR.xml")
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iter("{%s}connect" % ns):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and each load model
    found_any_load = False
    for load_staticId in bus_info.loads:
        found = False
        for dyn_load in root.iter("{%s}blackBoxModel" % ns):
            if (
                dyn_load.get("lib")[0:4] == "Load"
                and dyn_load.get("staticId") == load_staticId
            ):
                found = True
                load_id = dyn_load.get("id")
                break
        if not found:
            print(
                "      WARNING: load %s on bus %s not found in DYD file"
                % (load_staticId, bus_name)
            )
            continue
        found_any_load = True
        cnx = etree.SubElement(root, "connect")
        cnx.set("id1", event_id)
        cnx.set("var1", "event_state1_value")
        cnx.set("id2", load_id)
        cnx.set("var2", "load_switchOffSignal2_value")

    # If no load was found in th DYD file for this bus, invalidate the case
    if not found_any_load:
        print("      *** no loads found in DYD file, invalidating the case")
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
        etree.Element("par", type="BOOL", name="event_stateEvent1", value="true")
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

    if bus_info.topology == "BUS_BREAKER":
        bus_label = bus_name
    elif bus_info.topology == "NODE_BREAKER":
        # first busbarSection found with a non-null voltage; see extract_dynawo_buses()
        bus_label = bus_info.busbarSection

    # Add the corresponding curve to the CRV file
    crv_file = casedir + CRV_FILE
    print("   Editing file %s" % crv_file)
    tree = etree.parse(crv_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    root.append(
        etree.Element("curve", model="NETWORK", variable=bus_label + "_Upu_value")
    )
    # Write out the CRV file, preserving the XML format
    tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    return 0


def config_astre_loads_contingency(casedir, bus_name):
    astre_file = casedir + ASTRE_FILE
    print("   Editing file %s" % astre_file)
    tree = etree.parse(astre_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Find all loads that are attached to the given bus_name
    bus_num = None
    for astre_bus in root.iter("{%s}noeud" % ns):
        if astre_bus.get("nom") == bus_name:
            bus_num = astre_bus.get("num")
            break
    load_Ids = []
    totalP = 0.0
    totalQ = 0.0
    for astre_load in root.iter("{%s}conso" % ns):
        if astre_load.get("noeud") == bus_num and astre_load.get("nom")[:5] != "fict_":
            load_Ids.append(astre_load.get("num"))
            load_vars = astre_load.find("{%s}variables" % ns)
            if astre_load.get("fixe") == "true":
                totalP += float(load_vars.get("peFixe"))
                totalQ += float(load_vars.get("qeFixe"))
            else:
                totalP += float(load_vars.get("peAff"))
                totalQ += float(load_vars.get("qeAff"))

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

    # We now insert our own events. We link to the load id using the
    # `ouvrage` attribute.  The event type for loads is "3", and
    # typeevt for disconnections is "1").
    for load_id in load_Ids:
        event = etree.SubElement(scenario, "evtouvrtopo")
        event.set("instant", event_time)
        event.set("ouvrage", load_id)
        event.set("type", "3")
        event.set("typeevt", "1")
        event.set("cote", "0")

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
    first_astre_curve = root.find(".//{%s}courbe" % ns)
    astre_entrees = first_astre_curve.getparent()
    astre_entrees.append(
        etree.Element(
            "courbe",
            nom="NETWORK_" + bus_name + "_Upu_value",
            typecourbe="63",
            ouvrage=bus_num,
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

    return (totalP, totalQ)


def save_total_load(dirname, dynawo_buses, astre_buses):
    f = open(dirname + "/total_load_per_bus.csv", "w")
    f.write("# BUS; P_dwo; P_ast; Pdiff_pct; Q_dwo; Q_ast; Qdiff_pct\n")
    # Iterating astre_buses because some dynawo_buses may have been skipped
    for bus_name in astre_buses:
        P_dwo = dynawo_buses[bus_name].totalP
        P_ast = astre_buses[bus_name][0]
        Pdiff_pct = 100 * (P_dwo - P_ast) / max(abs(P_ast), 0.001)
        Q_dwo = dynawo_buses[bus_name].totalQ
        Q_ast = astre_buses[bus_name][1]
        Qdiff_pct = 100 * (Q_dwo - Q_ast) / max(abs(Q_ast), 0.001)
        f.write(
            "{}; {:.3f}; {:.3f}; {:.2f}; {:.3f}; {:.3f}; {:.2f}\n".format(
                bus_name, P_dwo, P_ast, Pdiff_pct, Q_dwo, Q_ast, Qdiff_pct
            )
        )
    f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
