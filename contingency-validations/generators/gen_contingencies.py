#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# gen_contingencies.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all GENERATORS that can be matched in the
# two, generates the files for running a single-gen contingency for
# each device.
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
# gen_LABEL1, gen_LABEL2, etc.
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
        print("\nUsage: %s base_case [element1 element2 element3 ...]\n" % sys.argv[0])
        return 2
    base_case = sys.argv[1]
    filter_list = sys.argv[2:]

    verbose = False

    # Check all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, verbose)
    edited_case = dirname + "/TMP_CONTINGENCYCASE"

    # Extract the list of all (active) GENS in the Dynawo case
    dynawo_gens = extract_dynawo_gens(base_case + IIDM_FILE, verbose)

    # Reduce the list to those GENS that are matched in Astre
    dynawo_gens = matching_in_astre(base_case + ASTRE_FILE, dynawo_gens, verbose)

    # Initialize another dict to keep Astre's (P,Q) of each gen
    astre_gens = dict()

    # For each matching GEN, generate the contingency case
    for gen_name in dynawo_gens:

        # If the script was passed a list of generators, filter for them here
        # DEBUG: filter_list = ["CXSSEIN1", "BARNA7ANNEAU1PALU", "PENL57ANNEAU1PENL"]
        if len(filter_list) != 0 and gen_name not in filter_list:
            continue

        print(
            "Generating contingency case for gen %s (at bus: %s)"
            % (gen_name, dynawo_gens[gen_name].bus)
        )

        # Copy the whole input tree to a new path:
        clone_base_case(base_case, edited_case)

        # Modify the Dynawo case (DYD,PAR,CRV)
        config_dynawo_gen_contingency(edited_case, gen_name, dynawo_gens[gen_name])

        # Modify the Astre case, and obtain total disconnected generation (P,Q)
        astre_gens[gen_name] = config_astre_gen_contingency(
            edited_case, gen_name, dynawo_gens[gen_name]
        )

        # Save the wole case using "deduplication"
        deduped_case = dirname + "/gen_" + gen_name
        dedup_save(basename, edited_case, deduped_case)

    # Finally, save the (P,Q) values of disconnected gens in all processed cases
    save_total_genPQ(dirname, dynawo_gens, astre_gens)

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


def extract_dynawo_gens(iidm_file, verbose=False):
    tree = etree.parse(iidm_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace
    gens = dict()
    Gen_info = namedtuple("Gen_info", "P Q genType bus busTopology")

    # We enumerate all gens and extract their properties
    for gen in root.iter("{%s}generator" % ns):
        # Keep only the active ones
        if gen.get("p") == "-0" and gen.get("q") == "-0":
            continue
        gen_name = gen.get("id")
        P_val = -float(gen.get("targetP"))  # float(gen.get("p"))
        Q_val = float(gen.get("q"))
        gen_type = gen.get("energySource")
        topo_val = gen.getparent().get("topologyKind")
        if topo_val == "BUS_BREAKER":
            bus_name = gen.get("bus")
        elif topo_val == "NODE_BREAKER":
            # don't try to resolve the topology, just take the first active busbar
            bus_name = None
            vl = gen.getparent()
            topology = vl.find("{%s}nodeBreakerTopology" % ns)
            for node in topology:
                node_type = etree.QName(node).localname
                if node_type == "busbarSection" and node.get("v") is not None:
                    bus_name = node.get("id")
                    break
        else:
            raise ValueError("TopologyKind not found for generator: %s" % gen_name)
        gens[gen_name] = Gen_info(
            P=P_val, Q=Q_val, genType=gen_type, bus=bus_name, busTopology=topo_val
        )

    print("\nFound %d ACTIVE gens in the Dynawo IIDM file" % len(gens))
    if verbose:
        print("List of all ACTIVE gens in the Dynawo DYD file: (total: %d)" % len(gens))
        gen_list = sorted(gens.keys())
        if len(gen_list) < 10:
            print(gen_list)
        else:
            print(gen_list[:5] + ["..."] + gen_list[-5:])
        print()

    return gens


def matching_in_astre(astre_file, dynawo_gens, verbose=False):
    tree = etree.parse(astre_file)
    root = tree.getroot()
    astre_gens = set()  # for faster matching below

    for gen in root.iterfind(".//groupe", root.nsmap):
        # Discard gens having noeud="-1"
        if gen.get("noeud") != "-1":
            astre_gens.add(gen.get("nom"))

    print("\nFound %d gens in Astre file" % len(astre_gens))
    if verbose:
        print("Sample list of all GENS in Astre file: (total: %d)" % len(astre_gens))
        gen_list = sorted(astre_gens)
        if len(gen_list) < 10:
            print(gen_list)
        else:
            print(gen_list[:5] + ["..."] + gen_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_gens.items() if x[0] in astre_gens]
    print("   (matched %d gens against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_gen_contingency(casedir, gen_name, gen_info):
    ###########################################################
    # DYD file: configure an event model for the disconnection
    ###########################################################
    dyd_file = casedir + DYD_FILE
    print("   Editing file %s" % dyd_file)
    tree = etree.parse(dyd_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Generators with vs. without a dynamic model in the DYD file:
    # they need to be disconnected differently.
    disconn_eventmodel = "EventConnectedStatus"
    cnx_id2 = "NETWORK"
    cnx_var2 = gen_name + "_state_value"
    param_eventname = "event_open"
    for dyn_gen in root.iter("{%s}blackBoxModel" % ns):
        if (
            dyn_gen.get("lib")[0:9] == "Generator"
            and dyn_gen.get("staticId") == gen_name
        ):
            disconn_eventmodel = "EventSetPointBoolean"
            cnx_id2 = dyn_gen.get("id")
            cnx_var2 = "generator_switchOffSignal2_value"
            param_eventname = "event_stateEvent1"
            break

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
    event_id = "Disconnect my gen"
    event = etree.SubElement(root, "blackBoxModel")
    event.set("id", event_id)
    event.set("lib", disconn_eventmodel)
    event.set("parFile", "tFin/fic_PAR.xml")
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iter("{%s}connect" % ns):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the gen
    cnx = etree.SubElement(root, "connect")
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", cnx_id2)
    cnx.set("var2", cnx_var2)

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
        etree.Element("par", type="BOOL", name=param_eventname, value="true")
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
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we would use the IIDM file, where the gen has an
    # attribute that directly provides the bus it is connected to. We
    # already stored this value in the Gen_info tuple before.

    bus_label = gen_info.bus

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


def config_astre_gen_contingency(casedir, gen_name, gen_info):
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

    # Find the gen in Astre
    for astre_gen in root.iter("{%s}groupe" % ns):
        if astre_gen.get("nom") == gen_name:
            break
    gen_id = astre_gen.get("num")
    bus_id = astre_gen.get("noeud")
    bus_name = gen_info.bus  # we can use Dynawo's name for the curve var
    gen_vars = astre_gen.find("{%s}variables" % ns)
    gen_P = -float(gen_vars.get("pc"))
    gen_Q = -float(gen_vars.get("q"))

    # We now insert our own events. We link to the gen id using the
    # `ouvrage` attribute.  The event type for gens is "2", and
    # typeevt for disconnections is "1").
    event = etree.SubElement(scenario, "evtouvrtopo")
    event.set("instant", event_time)
    event.set("ouvrage", gen_id)
    event.set("type", "2")
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
    # this, we get the id of the bus that the gen is attached to and
    # add an element as in the example:
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

    return (gen_P, gen_Q)


def save_total_genPQ(dirname, dynawo_gens, astre_gens):
    file_name = dirname + "/total_PQ_per_generator.csv"
    # Using a dataframe for sorting
    column_list = [
        "GEN",
        "P_dwo",
        "P_ast",
        "Pdiff_pct",
        "Q_dwo",
        "Q_ast",
        "Qdiff_pct",
        "sumPQdiff_pct",
    ]
    data_list = []
    # We enumerate the astre_gens dict because it contains the cases
    # that have actually been processed (because we may have skipped
    # some in the main loop).
    for gen_name in astre_gens:
        P_dwo = dynawo_gens[gen_name].P
        P_ast = astre_gens[gen_name][0]
        Pdiff_pct = 100 * (P_dwo - P_ast) / max(abs(P_ast), 0.001)
        Q_dwo = dynawo_gens[gen_name].Q
        Q_ast = astre_gens[gen_name][1]
        Qdiff_pct = 100 * (Q_dwo - Q_ast) / max(abs(Q_ast), 0.001)
        sumPQdiff_pct = abs(Pdiff_pct) + abs(Qdiff_pct)
        data_list.append(
            [gen_name, P_dwo, P_ast, Pdiff_pct, Q_dwo, Q_ast, Qdiff_pct, sumPQdiff_pct]
        )

    df = pd.DataFrame(data_list, columns=column_list)
    df.sort_values(
        by=["sumPQdiff_pct"], inplace=True, ascending=False, na_position="first"
    )
    df.to_csv(file_name, index=False, sep=";", float_format="%.3f", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
