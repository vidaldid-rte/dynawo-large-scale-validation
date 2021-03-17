#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# shunt_contingencies.py:
#
# Takes a base case consisting of two corresponding Dynawo and Astre
# files and, enumerating all SHUNTS that can be matched in the two,
# generates the files for running a single-shunt contingency for each
# device.
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
# On output, the script generates new dirs sibling to basecase:
# shunt_LABEL1, shunt_LABEL2, etc.
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
        print("\nUsage: %s base_case [element1 element2 element3 ...]\n" % sys.argv[0])
        print(
            "\nThe optional list may include regular expressions. "
            "If the list is empty, all possible contingencies will be generated "
            "(if below MAX_NCASES=%d; otherwise a random sample is generated).\n"
            % MAX_NCASES
        )
        return 2
    base_case = sys.argv[1]
    filter_list = [re.compile(x) for x in sys.argv[2:]]

    # Get Dynawo paths from the JOB file
    dwo_paths = get_dwo_jobpaths(base_case)

    # Get the simulation time parameters (from Dynawo's case)
    dwo_tparams = get_dwo_tparams(base_case)

    # Check that all needed files are in place
    base_case, basename, dirname = check_inputfiles(base_case, dwo_paths, verbose)

    # Parse all XML files in the basecase
    parsed_case = parse_basecase(base_case, dwo_paths, ASTRE_PATH)

    # Extract the list of all (active) SHUNTS in the Dynawo case
    dynawo_shunts = extract_dynawo_shunts(parsed_case.iidmTree, verbose)

    # Reduce the list to those SHUNTS that are matched in Astre
    dynawo_shunts = matching_in_astre(parsed_case.astreTree, dynawo_shunts, verbose)

    # Prepare for random sampling if there's too many
    sampling_ratio = MAX_NCASES / len(dynawo_shunts)
    random.seed(RNG_SEED)
    if len(filter_list) == 0 and sampling_ratio < 1:
        print(
            "LIMITING to a sample of about %d cases (%.2f%% of all cases)"
            % (MAX_NCASES, 100 * sampling_ratio)
        )

    # Initialize another dict to keep Astre's Q of each shunt
    astre_shunts = dict()

    # For each matching SHUNT, generate the contingency case
    for shunt_name in dynawo_shunts:

        # If the script was passed a list of shunts, filter for them here
        shunt_name_matches = [r.search(shunt_name) for r in filter_list]
        if len(filter_list) != 0 and not any(shunt_name_matches):
            continue

        # Limit the number of cases to approximately MAX_NCASES
        if len(filter_list) == 0 and random.random() > sampling_ratio:
            continue

        print(
            "Generating contingency case for shunt %s (at bus: %s)"
            % (shunt_name, dynawo_shunts[shunt_name].bus)
        )

        # Copy the basecase (unchanged files and dir structure)
        # Note we fix any device names with slashes in them (illegal filenames)
        contg_casedir = dirname + "/shunt_" + shunt_name.replace("/", "+")
        copy_basecase(base_case, dwo_paths, contg_casedir)

        # Modify the Dynawo case (DYD,PAR,CRV)
        config_dynawo_shunt_contingency(
            contg_casedir,
            parsed_case,
            dwo_paths,
            dwo_tparams,
            shunt_name,
            dynawo_shunts[shunt_name],
        )

        # Modify the Astre case, and obtain the disconnected shunt's injection (Q)
        astre_shunts[shunt_name] = config_astre_shunt_contingency(
            contg_casedir, parsed_case.astreTree, shunt_name, dynawo_shunts[shunt_name]
        )

    # Finally, save the values of disconnected shunts in all processed cases
    save_total_shuntq(dirname, dynawo_shunts, astre_shunts)

    return 0


def extract_dynawo_shunts(iidm_tree, verbose=False):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace
    shunts = dict()
    Shunt_info = namedtuple("Shunt_info", "Q bus busTopology")

    # We enumerate all shunts and keep only the active ones:
    for shunt in root.iter("{%s}shunt" % ns):
        if shunt.get("bus") is not None:
            shunt_name = shunt.get("id")
            shunts[shunt_name] = Shunt_info(
                Q=float(shunt.get("q")),
                bus=shunt.get("bus"),
                busTopology=shunt.getparent().get("topologyKind"),
            )

    print("\nFound %d ACTIVE shunts in the Dynawo IIDM file" % len(shunts))
    if verbose:
        print(
            "List of all ACTIVE shunts in the Dynawo DYD file: (total: %d)"
            % len(shunts)
        )
        shunt_list = sorted(shunts.keys())
        if len(shunt_list) < 10:
            print(shunt_list)
        else:
            print(shunt_list[:5] + ["..."] + shunt_list[-5:])
        print()

    return shunts


def matching_in_astre(astre_tree, dynawo_shunts, verbose=False):
    root = astre_tree.getroot()

    # Retrieve the list of Astre shunts
    astre_shunts = set()  # for faster matching below
    reseau = root.find("./reseau", root.nsmap)
    donneesShunts = reseau.find("./donneesShunts", root.nsmap)
    for shunt in donneesShunts.iterfind("./shunt", root.nsmap):
        # Discard disconnected shunts
        if shunt.get("noeud") != "-1":
            astre_shunts.add(shunt.get("nom"))

    print("\nFound %d shunts in Astre file" % len(astre_shunts))
    if verbose:
        print(
            "Sample list of all SHUNTS in Astre file: (total: %d)" % len(astre_shunts)
        )
        shunt_list = sorted(astre_shunts)
        if len(shunt_list) < 10:
            print(shunt_list)
        else:
            print(shunt_list[:5] + ["..."] + shunt_list[-5:])
        print()

    # Match:
    new_list = [x for x in dynawo_shunts.items() if x[0] in astre_shunts]
    print("   (matched %d shunts against Dynawo file)\n" % len(new_list))

    return dict(new_list)


def config_dynawo_shunt_contingency(
    casedir, case_trees, dwo_paths, dwo_tparams, shunt_name, shunt_info
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
    event_id = "Disconnect my shunt"
    event.set("id", event_id)
    event.set("lib", "EventConnectedStatus")
    event.set("parFile", dwo_paths.parFile)
    event.set("parId", "99991234")

    # Erase all connections of the previous Events we removed above
    for cnx in root.iterfind("./connect", root.nsmap):
        if cnx.get("id1") in old_eventIds or cnx.get("id2") in old_eventIds:
            cnx.getparent().remove(cnx)

    # Declare a new Connect between the Event model and the shunt
    cnx = etree.SubElement(root, "{%s}connect" % ns)
    cnx.set("id1", event_id)
    cnx.set("var1", "event_state1_value")
    cnx.set("id2", "NETWORK")
    cnx.set("var2", shunt_name + "_state_value")

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
    new_parset.append(
        etree.Element("{%s}par" % ns, type="BOOL", name="event_open", value="true")
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
    # For now we'll just add the voltage at the contingency bus. To do
    # this, we would use the IIDM file, where the shunt has an
    # attribute that directly provides the bus it is connected to. We
    # already stored this value in the Shunt_info tuple before.

    bus_label = shunt_info.bus

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

    return 0


def config_astre_shunt_contingency(casedir, astre_tree, shunt_name, shunt_info):
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

    # Find the shunt in Astre
    astre_shunt = None
    reseau = root.find("./reseau", root.nsmap)
    donneesShunts = reseau.find("./donneesShunts", root.nsmap)
    for s in donneesShunts.iterfind("./shunt", root.nsmap):
        if s.get("nom") == shunt_name:
            astre_shunt = s
            break
    shunt_id = astre_shunt.get("num")
    bus_id = astre_shunt.get("noeud")
    bus_name = shunt_info.bus  # we can use Dynawo's name for the curve var
    shunt_Q = -10000 * float(astre_shunt.get("valnom"))  # TODO: ask RTE if this is OK

    # We now insert our own events. We link to the shunt id using the
    # `ouvrage` attribute.  The event type for shunts is "4", and
    # typeevt for disconnections is "1").
    ns = etree.QName(root).namespace
    event = etree.SubElement(scenario, "{%s}evtouvrtopo" % ns)
    event.set("instant", event_time)
    event.set("ouvrage", shunt_id)
    event.set("type", "4")
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
    # this, we get the id of the bus that the shunt is attached to and
    # add an element as in the example:
    #
    #     ```
    #       <courbe nom="BUSNAME_Upu_value" typecourbe="63" ouvrage="BUSID" type="7"/>
    #     ```
    #
    # Since the name of the curve variable is free, we'll use names
    # that match Dynawo.
    new_crv1 = etree.Element(
        "{%s}courbe" % ns,
        nom="NETWORK_" + bus_name + "_Upu_value",
        typecourbe="63",
        ouvrage=bus_id,
        type="7",
    )
    entreesAstre.append(new_crv1)

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

    return shunt_Q


def save_total_shuntq(dirname, dynawo_shunts, astre_shunts):
    file_name = dirname + "/total_shuntQ_per_bus.csv"
    # Using a dataframe for sorting
    column_list = ["SHUNT", "Q_dwo", "Q_ast", "Qdiff_pct"]
    data_list = []
    # We enumerate the astre_shunts dict because it contains the cases
    # that have actually been processed (because we may have skipped
    # some in the main loop).
    for shunt_name in astre_shunts:
        Q_dwo = dynawo_shunts[shunt_name].Q
        Q_ast = astre_shunts[shunt_name]
        Qdiff_pct = 100 * (Q_dwo - Q_ast) / max(abs(Q_dwo), 0.001)
        data_list.append([shunt_name, Q_dwo, Q_ast, Qdiff_pct])

    df = pd.DataFrame(data_list, columns=column_list)
    df.sort_values(by=["Qdiff_pct"], inplace=True, ascending=False, na_position="first")
    df.to_csv(file_name, index=False, sep=";", float_format="%.2f", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
