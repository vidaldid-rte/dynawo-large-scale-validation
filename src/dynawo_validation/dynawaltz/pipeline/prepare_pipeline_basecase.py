#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# prepare_astdwo_basecase.py:
#
# Takes an input case consisting of two corresponding Dynawo and Astre
# cases and prepares a BASECASE for contingency analysis, configuring
# a standard set of CURVES for it.
#
# On input, the case files are expected to be FORMATTED with xmllint (see
# xml_format_dir.sh). As for the directory structure, this is an example
# (not strict, read below):
#
# INPUT_CASE/
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
# for Dynawo we read the actual paths from the existing JOB file, and we prepare the
# curves for the last job defined inside the JOB file (see module dwo_jobpaths).
#
# You also have to provide the name of the SVC Zone (e.g. Lille, Marseille, Nancy,
# Recollement, etc.) that the case belongs to. This allows us to choose which SVC
# variables to have as curves in the output.
#
# On output, the script generates a new dir "INPUT_CASE.BASECASE",
# parallel to the input case.
#


import sys
import os
import subprocess
from lxml import etree
from collections import namedtuple

# Relative imports only work for proper Python packages, but we do not want to
# structure all these as a package; we'd like to keep them as a collection of loose
# Python scripts, at least for now (because this is not really a Python library). So
# the following hack is ugly, but needed:
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Alternatively, you could set PYTHONPATH to PYTHONPATH="/<dir>/dynawo-validation-AIA"
from dynawo_validation.dynawaltz.pipeline.dwo_jobinfo import (
    is_astdwo,
    is_dwodwo,
    get_dwo_jobpaths,
    get_dwodwo_jobpaths,
)  # noqa: E402


ASTRE_FILE = "/Astre/donneesModelesEntree.xml"
verbose = False


def main():

    if len(sys.argv) != 3:
        print(f"\nUsage: {sys.argv[0]} INPUT_CASE CASE_SVC_ZONE\n")
        print(
            "(where CASE_SVC_ZONE is one of: 'Lille', 'Lyon', 'Marseille', "
            "'Nancy', 'Nantes', 'Paris', 'Toulouse', 'Recollement)'\n"
        )
        return 2
    input_case = sys.argv[1]
    case_zone = sys.argv[2]

    # The path for the prepared case
    if input_case[-1] == "/":
        input_case = input_case[:-1]
    if input_case[-10:] == ".FORMATTED":
        edited_case = input_case[:-10] + ".BASECASE"
    else:
        edited_case = input_case + ".BASECASE"

    # Check whether it's an Astre-vs-Dynawo or a Dynawo-vs-Dynawo case
    dwo_paths, astdwo = (None, None)
    dwo_pathsA, dwo_pathsB = (None, None)
    if is_astdwo(input_case):
        print(f"Preparing ASTRE-vs-DYNAWO case: {edited_case}")
        dwo_paths = get_dwo_jobpaths(input_case)
        astdwo = True
    elif is_dwodwo(input_case):
        print(f"Preparing DYNAWO-vs-DYNAWO case: {edited_case}")
        dwo_pathsA, dwo_pathsB = get_dwodwo_jobpaths(input_case)
        astdwo = False
    else:
        raise ValueError(f"Case {input_case} is neither an ast-dwo nor a dwo-dwo case")

    # Copy the whole input tree to the new path
    clone_input_case(input_case, edited_case)

    # And now edit the curve files in place
    if astdwo:
        rst_models, pilot_buses = edit_dwo_curves(
            edited_case, case_zone, dwo_paths, astdwo
        )
        edit_ast_curves(edited_case, case_zone, rst_models, pilot_buses)
    else:
        _, _ = edit_dwo_curves(edited_case, case_zone, dwo_pathsA, astdwo)
        _, _ = edit_dwo_curves(edited_case, case_zone, dwo_pathsB, astdwo)

    # Show some reminders
    msg_astdwo = (
        "\nREMINDER: The BASECASE is almost ready, but not quite. Please do:\n"
        "  * Run the Astre and Dynawo cases to verify they work\n"
        "  * Delete the Astre output files\n"
        "  * Delete the Dynawo tFin output, but keep the t0 files\n"
        "  * Edit the JOB file to comment out the first job (the pre-contingency)\n"
        "  * And tweak the second job (the one containing the contingency):\n"
        "      - set INFO log level, remove the finalState IIDM, etc.\n"
        "      - but MOST IMPORTANTLY, edit the initialState path that the\n"
        "        contingency cases need to see when they're run. For instance:\n"
        '           <initialState file="../20200527_1700.BASECASE/t0/...\n'
    )
    msg_dwodwo = (
        "\nREMINDER: The BASECASE is almost ready, but not quite. Please do:\n"
        "  * Run the A / B Dynawo cases to verify they both work\n"
        "  * Delete their respective tFin outputs, but keep the t0 outputs\n"
        "  * Edit the JOB files to comment out the first job (the pre-contingency)\n"
        "  * And tweak the second job (the one containing the contingency):\n"
        "      - set INFO log level, remove the finalState IIDM, etc.\n"
        "      - but MOST IMPORTANTLY, edit the initialState path that the\n"
        "        contingency cases need to see when they're run. For instance:\n"
        '           <initialState file="../20200527_1700.BASECASE/t0/...\n'
    )
    if astdwo:
        print(msg_astdwo)
    else:
        print(msg_dwodwo)

    return 0


def clone_input_case(input_case, dest_case):
    # If the destination exists, remove it
    if os.path.exists(dest_case):
        remove_case(dest_case)
    try:
        retcode = subprocess.call(f"cp -a {input_case} {dest_case}", shell=True)
        if retcode < 0:
            raise ValueError(
                f"Copy operation ({input_case} -->{dest_case}) was terminated by "
                f"signal: {-retcode}"
            )
        elif retcode > 0:
            raise ValueError(
                f"Copy operation ({input_case} -->{dest_case}) returned error "
                f"code: {retcode}"
            )
    except OSError as e:
        print(
            f"Copy operation ({input_case} -->{dest_case}) failed: ", e, file=sys.stderr
        )
        raise


def remove_case(dest_case):
    try:
        retcode = subprocess.call(f"rm -rf {dest_case}", shell=True)
        if retcode < 0:
            raise ValueError(f"rm of {dest_case} terminated by signal: {-retcode}")
        elif retcode > 0:
            raise ValueError(f"rm of {dest_case} returned error code: {retcode}")
    except OSError as e:
        print("call to rm failed: ", e, file=sys.stderr)
        raise


def get_rst_table():
    # Master dictionary of SVC controls associated to each SVC zone
    rst_zones = {
        "Lille": ["LONNYP7", "MASTAP7", "WARANP7"],
        "Lyon": ["ALBERP7", "CHAFFP7", "GEN_PP6", "LAVEYP6"],
        "Marseille": ["TRI_PP7", "BOLL5P6", "LAVERP6", "PALUNP6", "SISTEP6"],
        "Nancy": ["M_SEIP7", "MUHLBP7", "VIGY_P7", "BAYETP6", "J_VILP6", "VOGELP6"],
        "Nantes": [
            "AVOI5P7",
            "AVOI5P7_",
            "COR_PP7",
            "GAUGLP7",
            "TABARP7",
            "VALDIP7",
            "VERGEP7",
            "BRENNP6",
            "JUSTIP6",
            "MARTYP6",
        ],
        "Paris": [
            "BARNAP7",
            "CERGYP7",
            "MENUEP7",
            "ARRIGP6",
            "CHESNP6",
            "HAVRE5P6",
            "VLEVAP6",
        ],
        "Toulouse": [
            "BAIXAP7",
            "BRAUDP7",
            "DONZAP7",
            "RUEYRP7",
            "BREUIP6",
            "LANNEP6",
            "SSVICP6",
            "TARASP6",
        ],
        "Recollement": [
            "LONNYP7",
            "WARANP7",
            "CHAFFP7",
            "TRI.PP7",
            "M.SEIP7",
            "VIGY P7",
            "COR.PP7",
            "TABARP7",
            "BARNAP7",
            "MENUEP7",
            "BRAUDP7",
            "DONZAP7",
        ],
    }
    # We had initially included ALL 400kV SVCs for the National case
    # (22):
    #
    # "Recollement": ["LONNYP7", "MASTAP7", "WARANP7", "ALBERP7",
    #     "CHAFFP7", "TRI_PP7", "M_SEIP7", "MUHLBP7", "VIGY_P7",
    #     "AVOI5P7", "COR_PP7", "GAUGLP7", "TABARP7", "VALDIP7",
    #     "VERGEP7", "BARNAP7", "CERGYP7", "MENUEP7", "BAIXAP7",
    #     "BRAUDP7", "DONZAP7", "RUEYRP7", ],
    #
    # But now we're using the shortlist of 12 SVCs suggested by RTE.

    return rst_zones


def edit_dwo_curves(edited_case, case_zone, dwo_paths, astdwo):
    # We prepare the `curvesInput` section in Dynawo's CRV input file with the
    # variables that monitor the behavior of the SVC (pilot point voltage, K level,
    # and P,Q of participating generators).  Also the K levels of all other SVC
    # external to the zone.
    rst_table = get_rst_table()
    if case_zone not in rst_table:
        raise ValueError(f"RST Zone {case_zone} is not in the master list")
    all_pilot_buses = set()
    for zone in rst_table:
        all_pilot_buses.update(rst_table[zone])

    # Get the SVC controls that are actually present in the DYD file
    dyd_file = edited_case + "/" + dwo_paths.dydFile
    tree = etree.parse(dyd_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    rst_models = dict()
    for bb in root.iter("{%s}blackBoxModel" % ns):
        if bb.get("lib") == "DYNModelRST":
            rst_id = bb.get("id")
            rst_models[rst_id] = []
            if rst_id[4:] not in all_pilot_buses:
                print(
                    "WARNING: case contains pilot bus %s, not in the master list"
                    % rst_id
                )
    # And their respective participating gens (the ones that are actually connected)
    Gen = namedtuple("Bus", "DM staticId")
    for mc in root.iter("{%s}macroConnect" % ns):
        if mc.get("connector")[:14] == "SVCToGenerator":
            rst_id = mc.get("id1")
            gen_id = mc.get("id2")
            for bb in root.iter("{%s}blackBoxModel" % ns):
                if bb.get("id") == gen_id:
                    rst_models[rst_id].append(
                        Gen(DM=gen_id, staticId=bb.get("staticId"))
                    )
                    break

    # Prepare the curves in the CRV file
    crv_file = edited_case + "/" + dwo_paths.curves_inputFile
    print("   Editing file %s" % crv_file)
    tree = etree.parse(crv_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    # Delete existing curves
    for crv in root:
        root.remove(crv)
    # Add our standard curves
    zone_pilot_buses = rst_table[case_zone]
    for rst_id in rst_models:
        # avoid var mismatches with Astre (SPECIAL CASE)
        if astdwo and rst_id == "RST_AVOI5P7_":
            continue
        # comments to differentiate SVC controls that belong to the Zone
        if rst_id[4:] in zone_pilot_buses:
            root.append(
                etree.Comment(" === Inside %s zone: %s === " % (case_zone, rst_id))
            )
        else:
            root.append(
                etree.Comment(" === Outside %s zone: %s === " % (case_zone, rst_id))
            )
        root.append(etree.Element("curve", model=rst_id, variable="U_IMPIN_value"))
        root.append(etree.Element("curve", model=rst_id, variable="levelK_value"))
        # Participating gens: only for SVC controls that belong to the Zone
        if rst_id[4:] not in zone_pilot_buses:
            continue
        for gen in rst_models[rst_id]:
            root.append(etree.Element("curve", model=gen.DM, variable="generator_PGen"))
            root.append(etree.Element("curve", model=gen.DM, variable="generator_QGen"))

    root.append(etree.Comment(" === below, the contingency-specific curves === "))

    # Write out the CRV file, preserving the XML format
    tree.write(
        crv_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )

    return rst_models, zone_pilot_buses


def edit_ast_curves(edited_case, case_zone, dwo_rst_models, zone_pilot_buses):
    # We here prepare the 'courbe' elements in ASTRE's input xml file, configuring
    # exactly the same curves as in the Dynawo CRV file and using the exact same
    # variable names, so that the column headers match in order and in name.
    ast_file = edited_case + ASTRE_FILE
    print("   Editing file %s" % ast_file)
    tree = etree.parse(ast_file, etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    # Check that the SVC controls (and their gens) coincide with Dynawo's
    # Astre's names have spaces and dots --> convert to underscores
    # Dynawo's names have "RST_" prefixes --> drop them
    donnees_rsts = root.find(".//{%s}donneesRsts" % ns)
    ast_rst_set = {
        x.get("nom").replace(" ", "_").replace(".", "_")
        for x in donnees_rsts.iterfind(".//{%s}zonerst" % ns)
    }
    dwo_rst_set = {x[4:11] for x in dwo_rst_models}  # because of "AVOI5P7_", etc
    if ast_rst_set != dwo_rst_set:
        print(
            "   WARNING: Dynawo and Astre cases have different RST controls!"
            " (these may be Astre's RST whose participating gens are all inactive)"
        )
        print("      Non-matching Astre controls:  ", sorted(ast_rst_set - dwo_rst_set))
        print("      Non-matching Dynawo controls: ", sorted(dwo_rst_set - ast_rst_set))

    # Build an auxiliary dict for Astre generator IDs
    ast_genId = dict()
    for gen in root.iterfind(".//{%s}groupe" % ns):
        ast_genId[gen.get("nom")] = gen.get("num")

    # Delete existing curves
    ast_entrees = root.find(".//{%s}entreesAstre" % ns)
    for crv in ast_entrees.iterfind(".//{%s}courbe" % ns):
        ast_entrees.remove(crv)

    # Add our standard curves, in the same order as Dynawo
    for dwo_zonerst in dwo_rst_models:
        if dwo_zonerst == "RST_AVOI5P7_":  # avoid mismatches (SPECIAL CASE)
            continue
        if dwo_zonerst[4:] in zone_pilot_buses:
            ast_entrees.append(
                etree.Comment(
                    " === Inside %s zone: %s ===  " % (case_zone, dwo_zonerst)
                )
            )
        else:
            ast_entrees.append(
                etree.Comment(
                    " === Outside %s zone: %s === " % (case_zone, dwo_zonerst)
                )
            )
        zonerst_num = None
        pilot_busId = None
        for ast_zonerst in donnees_rsts.iterfind(".//{%s}zonerst" % ns):
            if (
                ast_zonerst.get("nom").replace(" ", "_").replace(".", "_")
                == dwo_zonerst[4:]
            ):
                zonerst_num = ast_zonerst.get("num")
                pilot_busId = ast_zonerst.find(".//{%s}pilotedyn" % ns).get("pilbus")
                break
        ast_entrees.append(
            etree.Element(
                "courbe",
                nom=dwo_zonerst + "_U_IMPIN_value",
                typecourbe="63",
                ouvrage=pilot_busId,
                type="7",
            )
        )
        ast_entrees.append(
            etree.Element(
                "courbe",
                nom=dwo_zonerst + "_levelK_value",
                typecourbe="45",
                ouvrage=zonerst_num,
                type="11",
            )
        )
        # Participating gens: only for SVC controls that belong to the Zone
        if dwo_zonerst[4:] not in zone_pilot_buses:
            continue
        # We assume participating gens match in Dynawo and Astre (they have to)
        for gen in dwo_rst_models[dwo_zonerst]:
            genId = ast_genId[gen.staticId]
            ast_entrees.append(
                etree.Element(
                    "courbe",
                    nom=gen.DM + "_generator_PGen",
                    typecourbe="46",
                    ouvrage=genId,
                    type="2",
                )
            )
            ast_entrees.append(
                etree.Element(
                    "courbe",
                    nom=gen.DM + "_generator_QGen",
                    typecourbe="47",
                    ouvrage=genId,
                    type="2",
                )
            )

    ast_entrees.append(
        etree.Comment(" === below, the contingency-specific curves === ")
    )

    # Write out the CRV file, preserving the XML format
    tree.write(
        ast_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="ISO-8859-1",
        standalone=False,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
