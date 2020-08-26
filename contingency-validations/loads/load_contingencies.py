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
# creates the files needed to run the simulations.
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


ASTRE_FILE = "/Astre/donneesModelesEntree.xml"
JOB_FILE = "/fic_JOB.xml"
DYD_FILE = "/tFin/fic_DYD.xml"
PAR_FILE = "/tFin/fic_PAR.xml"
CRV_FILE = "/tFin/fic_CRV.xml"
IIDM_FILE = "/tFin/fic_IIDM.xml"


def main():

    if len(sys.argv) != 2:
        print("\nUsage: %s input_case\n" % sys.argv[0])
        return 2
    input_case = sys.argv[1]
    verbose = False

    # Check all needed files are in place
    input_case, basename, dirname = check_inputfiles(input_case, verbose)

    # Extract the list of all loads present in the Dynawo case (by staticID)
    dynawo_loads = extract_dynawo_loads(input_case + DYD_FILE, verbose)

    # Reduce the list to those loads that are matched in Astre
    dynawo_loads = matching_in_astre(input_case + ASTRE_FILE, dynawo_loads, verbose)

    # For each matching load, generate the contingency cases
    for load_name in dynawo_loads:

        # Uncomment this for generating just a few cases:
        # if load_name not in [".ANDU7TR751", "BIPOL7INJ1", "TUNNE6CONSO1"]: continue

        print("Generating contingency case for load: %s" % load_name)
        # Copy the whole input tree to a new path:
        dest_case = dirname + "/load_" + load_name
        clone_input_case(input_case, dest_case)
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


def clone_input_case(input_case, dest_case):
    # If the destination exists, warn and rename it to OLD
    if os.path.exists(dest_case):
        print(
            "   WARNING: destination %s exists! -- renaming it to *__OLD__" % dest_case
        )
        os.rename(dest_case, dest_case + "__OLD__")

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

    # PAR file: add a section with the disconnecton parameters
    par_file = casedir + PAR_FILE
    print("   Editing file %s" % par_file)
    tree = etree.parse(par_file)
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

    return 0


def config_astre_load_contingency(casedir, load_name):
    astre_file = casedir + ASTRE_FILE
    print("   Editing file %s" % astre_file)
    tree = etree.parse(astre_file)
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Find the load in Astre (elements with tag "conso"; load name is atttribute "nom")
    # Keep its "num" attribute, which is the load id.
    for element in root.iter("{%s}conso" % ns):
        if element.get("nom") == load_name:
            break
    load_id = element.get("num")

    # Edit the event by means of the `evtouvrtopo` element
    # (TODO: WE'RE ASSUMING THERE'S ONLY ONE; CONTEMPLATE OTHER CASES)
    # Refer to the load id using the `ouvrage` attribute
    # The event type for loads is "3"  (and typeevt is always 1 for disconnection)
    nevents = 0
    for element in root.iter("{%s}evtouvrtopo" % ns):
        if nevents >= 1:
            print("WARNING: multiple evtouvrtopo events found in Astre file!")
            break
        element.set("ouvrage", load_id)
        element.set("type", "3")
        nevents += 1

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
