#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# adapted from the dynaflow pipeline
#
#
# extract_powerflow_values.py: Once a case has been run in Hades and OpenLoadFlow.
# this script extracts all relevant values of the resulting steady state, for the
# purpose of comparing both solutions in later analysis. In the output, the device
# types, IDs.
#
# On input, the script takes a directory containing both an Hades and a DynaFlow
# power-flow case, both of which have already been run.
#


import os
import argparse
import math
import re
import sys
import json
import pandas as pd
from lxml import etree
from collections import namedtuple
from itertools import chain

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

OLF_SOLUTION = "olf.xiidm"
OLF_LOG = "OLF.RunStdout.txt"
HDS_INPUT = "entreeHades.xml"
HDS_SOLUTION = "out.xml"
HDS_VERSION = "LAUNCHER_HADES"
OLF_VERSION = "LAUNCHER_OLF"
OLF_PARAMS = "OLFParams.json"
OUTPUT_FILE = "pfsolution_HO.csv"
TAP_SCORE_FILE = "tapScore.csv"
ERRORS_HADES_FILE = "elements_not_in_Hades.csv"
ERRORS_OLF_FILE = "elements_not_in_Olf.csv"
HDS_INACT_BUS = "999999.000000000000000"  # "magic" value used in Hades
HDS_INACT_SHUNT = "999999"
HDS_INACT_SHUNT2 = "0"  # we found a few cases where Hades uses this instead!
ZEROPQ_TOL = 1.0e-5  # inactivity detection: flows below this (in MW) considered zero

# named tuples
Branch_info = namedtuple("Branch_info", ["type", "bus1", "bus2","compute_tap"])
Hds_gridinfo = namedtuple(
    "Hds_gridinfo",
    ["branch_sides", "tap2xfmr", "pstap2xfmr", "shunt2busname", "svc_qfixed"],
)
Hds_branch_side = namedtuple("Hds_branch_side", ["bus1", "bus2"])

parser = argparse.ArgumentParser()
parser.add_argument(
    "-i",
    "--launcherInfo",
    help="extracts solver version and parameters",
    action='store_true'
)

parser.add_argument(
    "-v",
    "--verbose",
    help="verbose",
    action='store_true'
)

parser.add_argument(
    "case_dir",
    help="directory containing the network case"
)

args = parser.parse_args()

verbose = args.verbose


def main():

    case_dir = args.case_dir

    if verbose:
        print(f"Extracting solution values for case: {case_dir}")

    hades_input = os.path.join(case_dir, HDS_INPUT)
    hades_output = os.path.join(case_dir, HDS_SOLUTION)
    hades_version = os.path.join(case_dir, HDS_VERSION)
    olf_version = os.path.join(case_dir, OLF_VERSION)
    olf_params = os.path.join(case_dir, OLF_PARAMS)
    olf_file = os.path.join(case_dir, OLF_SOLUTION)
    olf_log = os.path.join(case_dir, OLF_LOG)
    check_input_files(case_dir, [hades_output, hades_version, olf_version, olf_params, olf_file])

    if args.launcherInfo:
        if verbose:
            print(f"Extracting solver info")
        hades_info = extract_hades_info(hades_version, hades_input)
        olf_info = extract_olf_info(olf_version, olf_params)
        hades_info.to_csv(os.path.join(case_dir, "hadesInfo.csv"),index=False, sep=";", encoding="utf-8")
        olf_info.to_csv(os.path.join(case_dir, "olfInfo.csv"), index=False, sep=";", encoding="utf-8")

    bus_connections = extract_hds_buses_connections(hades_input)

    # Extract the solution values from Dynawo results
    df_olf, vl_nomV, branch_info = extract_iidm_solution(olf_file, bus_connections)
    extract_olf_status(df_olf, olf_log)

    # TODO - faire les psTap aussi  (lorsque indicateurs dispos)
    nb_computed_tap=sum(1 for b in branch_info if branch_info[b].type=="xfmr" and branch_info[b].compute_tap)

    # Extract the solution values from Hades results
    df_hds = extract_hades_solution(
        hades_input, hades_output, vl_nomV, branch_info
    )
    extract_hades_status(df_hds, hades_output)

    # Merge, sort, and save
    save_extracted_values(df_hds, df_olf, case_dir, nb_computed_tap)
    save_nonmatching_elements(
        df_hds, df_olf, os.path.join(case_dir, ERRORS_HADES_FILE), os.path.join(case_dir,ERRORS_OLF_FILE)
    )

    return 0


def check_input_files(case_dir, fileList):
    if not os.path.isdir(case_dir):
        raise ValueError(f"case directory {case_dir} not found")

    # TODO: Verifier ce qu'il se passe si un des fichiers ne converge pas
    for file in fileList:
        if not (
            os.path.isfile(file)
        ):
            raise ValueError(f"Expected file missing in {case_dir} : file {file}\n")


def extract_olf_status(df_olf, olf_log):
    # Assuming only one component
    with open(olf_log) as f:
        found = False
        for line in f.readlines():
            if '|' in line:
                tokens = line.split('|')
                if len(tokens) == 11 and found:
                    status_string = tokens[3].strip()
                    slack = float(tokens[8].replace(",","."))
                    break
                if len(tokens) == 11 and "Slack bus mismatch" in tokens[8]:
                    found = True

    #TODO: Add new statuts as they occur in tests
    if status_string=="CONVERGED":
        status_code = 0
    elif status_string=="MAX_ITERATION_REACHED":
        status_code = 1
    elif status_string == "FAILED":
        status_code = 2
    else:
        raise Exception("Unknown OLF status: " + status_string)
    # Hades:
    #    2 (cause 3) si nonVentilé trop fort

    if status_code > 0 :
        # Remove all values as they make no sense
        df_olf.drop(df_olf.index, axis=0, inplace=True)

    df_olf.loc[len(df_olf)] = ["status#code", "status", None, "status", status_code]
    df_olf.loc[len(df_olf)] = ["status#slack", "status", None, "p", slack]



def extract_hades_status(df_hds, hades_output):
    tree = etree.parse(hades_output)
    root = tree.getroot()

    # Assume only one connected component
    result = root.find("./modele/sorties/sortieHades", root.nsmap)
    slack = float(result.get("ecartNoeudBilan"))
    res_lf = result.find("./resLF", root.nsmap)
    status = res_lf.get("statut")
    slack = 0.000999 if res_lf.get("nonVentile") is None else float(res_lf.get("nonVentile"))

    df_hds.loc[len(df_hds)] = ["status#code", "status", "status", status]
    df_hds.loc[len(df_hds)] = ["status#slack", "status", "p", slack]


def extract_iidm_solution(iidm_output, bus_connections):
    """Read all output and return a dataframe. Create vl_nomv & branches"""
    tree = etree.parse(iidm_output)

    root = tree.getroot()

    vl_nomv = dict()
    branches = dict()

    # We'll be using a dataframe, for sorting
    column_list = ["ID", "ELEMENT_TYPE", "VOLT_LEVEL", "VAR", "VALUE_OLF"]
    data = []
    print("   found in IIDM file: ", end="")
    # Buses: get V & angle
    valid_buses = extract_iidm_buses(root, data, vl_nomv, bus_connections)
    # Lines: p & q flows
    extract_iidm_lines(root, data, vl_nomv, branches, bus_connections)
    # Transformers and phase shifters: p & q flows
    extract_iidm_xfmrs(root, data, vl_nomv, branches, bus_connections)

    # Aggregate bus injections (loads, generators, shunts, VSCs)
    extract_iidm_bus_inj(root, data, vl_nomv, valid_buses, bus_connections)

    return pd.DataFrame(data, columns=column_list), vl_nomv, branches

def identify_line_buses(root, bus_connections):
    for line in chain(root.iterfind(".//iidm:line", root.nsmap), root.iterfind(".//iidm:twoWindingsTransformer", root.nsmap)):
        lid = line.get("id")
        voltageLevelId1 = line.get("voltageLevelId1")
        key = (lid, voltageLevelId1)
        if key in bus_connections:
            node1=line.get("node1")
            if node1 is not None:
                bus_connections[(voltageLevelId1, node1)] = bus_connections[key]
        voltageLevelId2 = line.get("voltageLevelId2")
        key = (lid, voltageLevelId2)
        if key in bus_connections:
            node2 = line.get("node2")
            if node2 is not None:
                bus_connections[(voltageLevelId2, node2)] = bus_connections[key]


def get_bus_name(bus, voltage_level, toplogy, root, bus_connections):
    if toplogy=="BUS_BREAKER":
        return bus.get("id")
    else:
        vlid = voltage_level.get("id")
        nodes = set(bus.get("nodes").split(","))
        for n in nodes:
            if (vlid,n) in bus_connections:
                return bus_connections[(vlid,n)]
        for g in voltage_level.iterfind(".//iidm:generator", root.nsmap):
            if g.get("node") in nodes and g.get("id") in bus_connections:
                return bus_connections[g.get("id")]
        for l in voltage_level.iterfind(".//iidm:load", root.nsmap):
            if l.get("node") in nodes and l.get("id") in bus_connections:
                return bus_connections[l.get("id")]

        # If nothing found in voltage level check transformers and lines
        substation = voltage_level.getparent()
        for t in chain(substation.iterfind(".//iidm:twoWindingsTransformer", root.nsmap), root.iterfind(".//iidm:line", root.nsmap)):
            t_vl1 = t.get("voltageLevelId1")
            if t_vl1 == vlid and t.get("node1") in nodes and (t.get("id"), t_vl1) in bus_connections:
                return bus_connections[(t.get("id"), t_vl1)]
            t_vl2 = t.get("voltageLevelId2")
            if t_vl2 == vlid and t.get("node2") in nodes and (t.get("id"), t_vl2) in bus_connections:
                return bus_connections[(t.get("id"), t_vl2)]

        return None

def extract_iidm_buses(root, data, vl_nomv, bus_connections):
    """Read V & angles, and update data. Also update the vl_nomv dict"""
    ctr = 0
    ign = 0
    validBuses = []

    identify_line_buses(root,bus_connections)

    for voltage_level in root.iterfind(".//iidm:voltageLevel", root.nsmap):
        nominalV = float(voltage_level.get("nominalV"))
        toplogy = voltage_level.get("topologyKind")
        for bus in voltage_level.iterfind(".//iidm:bus", root.nsmap):
            bus_name = get_bus_name(bus, voltage_level, toplogy, root, bus_connections)
            if bus_name is None:
                print("Bus ignored in vl " + voltage_level.get("id"))
                continue
            if bus_name in vl_nomv:
                # in node breaker mode a bus node has already been visited
                continue
            v = bus.get("v")
            angle = bus.get("angle")
            # build the voltlevel dict *before* skipping inactive buses
            vl_nomv[bus_name] = nominalV
            # Assign load buses if needed (some loads have different names in hades/CVG an OLF/Arcade)
            if toplogy == "NODE_BREAKER":
                bus_nodes = bus.get("nodes").split(",")
                for load in voltage_level.iterfind(".//iidm:load", root.nsmap):
                    lid = load.get("id")
                    if lid not in bus_connections and load.get("node") in bus_nodes:
                        bus_connections[lid] = bus_name

            # skip inactive buses
            if (v == "0" or v is None) and (angle == "0" or angle is None) :
                continue
            validBuses.append(bus_name)
            volt_level = vl_nomv[bus_name]
            data.append([bus_name, "bus", volt_level, "v", float(v)])
            data.append([bus_name, "bus", volt_level, "angle", float(angle)])
            ctr += 1

    print(f" {ctr:5d} buses", end="")
    print(f" {ign:5d} ignored buses", end="")
    return validBuses

def floatOrZero(v):
    return 0 if v is None else float(v)

def get_inj_bus(elt, bus_connections):
    bus = elt.get("bus")
    if bus is not None:
        return bus
    else:
        id = elt.get("id") if "vscConverterStation" not in elt.tag else elt.get("name")
        return bus_connections[id] if id in bus_connections else None

def get_line_bus1(line, bus_connections):
    bus1 = line.get("connectableBus1")
    if bus1 is not None:
        return bus1
    else:
        return bus_connections[(line.get("voltageLevelId1"), line.get("node1"))] if (line.get(
            "voltageLevelId1"), line.get("node1")) in bus_connections else None

def get_line_bus2(line, bus_connections):
    bus2 = line.get("connectableBus2")
    if bus2 is not None:
        return bus2
    else:
        return bus_connections[(line.get("voltageLevelId2"), line.get("node2"))] if (line.get(
            "voltageLevelId2"), line.get("node2")) in bus_connections else None

def get_line_vnom_bus1(line, vl_nomv, bus_connections):
    bus1 = get_line_bus1(line, bus_connections)
    if bus1 is not None and bus1 in vl_nomv:
        return vl_nomv[bus1]
    else:
        None

def get_line_vnom_bus2(line, vl_nomv, bus_connections):
    bus2 = get_line_bus2(line, bus_connections)
    if bus2 is not None and bus2 in vl_nomv:
        return vl_nomv[bus2]
    else:
        None


def extract_iidm_lines(root, data, vl_nomv, branches, bus_connections):
    """Read line flows, and update data. Also update branches dict"""
    ctr = 0
    for line in root.iterfind("./iidm:line", root.nsmap):
        line_name = line.get("id")
        p1 = floatOrZero(line.get("p1"))
        q1 = floatOrZero(line.get("q1"))
        p2 = floatOrZero(line.get("p2"))
        q2 = floatOrZero(line.get("q2"))
        # build the branches dict *before* skipping inactive lines
        branches[line_name] = Branch_info(
            type="line",
            bus1=get_line_bus1(line, bus_connections),
            bus2=get_line_bus2(line, bus_connections),
            compute_tap=False,
        )
        # skip inactive lines (beware threshold effect when comparing to the other case)
        if (
            abs(p1) < ZEROPQ_TOL
            and abs(q1) < ZEROPQ_TOL
            and abs(p2) < ZEROPQ_TOL
            and abs(q2) < ZEROPQ_TOL
        ):
            continue
        volt_level = get_line_vnom_bus1(line, vl_nomv, bus_connections)
        if volt_level is not None:
            element_type = branches[line_name].type
            data.append([line_name, element_type, volt_level, "p1", p1])
            data.append([line_name, element_type, volt_level, "q1", q1])
            data.append([line_name, element_type, volt_level, "p2", p2])
            data.append([line_name, element_type, volt_level, "q2", q2])
            ctr += 1
    print(f" {ctr:5d} lines", end="")


def extract_iidm_xfmrs(root, data, vl_nomv, branches, bus_connections):
    """Read xfmr flows & taps, and update data. Also update branches dict, if case_A"""
    ctr, psctr = [0, 0]
    for xfmr in root.iterfind(".//iidm:twoWindingsTransformer", root.nsmap):
        xfmr_name = xfmr.get("id")
        p1 = floatOrZero(xfmr.get("p1"))
        q1 = floatOrZero(xfmr.get("q1"))
        p2 = floatOrZero(xfmr.get("p2"))
        q2 = floatOrZero(xfmr.get("q2"))
        tap = xfmr.find("./iidm:ratioTapChanger", root.nsmap)
        ps_tap = xfmr.find("./iidm:phaseTapChanger", root.nsmap)
        # build branches dict *before* skipping inactive transformers
        if ps_tap is not None:
            branches[xfmr_name] = Branch_info(
                type="psxfmr",
                bus1= get_line_bus1(xfmr, bus_connections),
                bus2=get_line_bus2(xfmr, bus_connections),
                compute_tap=False, # TODO
            )
        else:
            branches[xfmr_name] = Branch_info(
                type="xfmr",
                bus1= get_line_bus1(xfmr, bus_connections),
                bus2= get_line_bus2(xfmr, bus_connections),
                compute_tap=tap.get("regulating") == "true" if tap is not None else False,
            )
        volt_level = get_line_vnom_bus2(xfmr, vl_nomv, bus_connections)  # side 2 assumed always HV
        data.append([xfmr_name, branches[xfmr_name].type, volt_level, "p1", p1])
        data.append([xfmr_name, branches[xfmr_name].type, volt_level, "q1", q1])
        data.append([xfmr_name, branches[xfmr_name].type, volt_level, "p2", p2])
        data.append([xfmr_name, branches[xfmr_name].type, volt_level, "q2", q2])
        # transformer taps
        if tap is not None:
            data.append(
                [
                    xfmr_name,
                    branches[xfmr_name].type,
                    volt_level,
                    "tap",
                    int(tap.get("tapPosition")),
                ]
            )
        # phase-shifter taps
        if ps_tap is not None:
            data.append(
                [
                    xfmr_name,
                    branches[xfmr_name].type,
                    volt_level,
                    "pstap",
                    int(ps_tap.get("tapPosition")) - int(ps_tap.get("lowTapPosition")),
                ]
            )
        # counters
        if branches[xfmr_name].type == "psxfmr":
            psctr += 1
        else:
            ctr += 1
    print(f" {ctr:5d} xfmrs", end="")
    print(f" {psctr:3d} psxfmrs", end="")


def extract_iidm_bus_inj(root, data, vl_nomv, valid_buses, bus_connections):
    """Aggregate injections (loads, gens, shunts, VSCs) by bus, and update data."""
    # Since a voltage level may contain more than one bus, it is easier to keep the
    # aggregate injections in dicts indexed by bus, and then output at the end.
    p_inj = dict()
    q_inj = dict()
    injection_types = (
        "load",
        "generator",
        "battery",
        "shunt",
        "vscConverterStation",
        "staticVarCompensator",
    )
    for vl in root.iterfind(".//iidm:voltageLevel", root.nsmap):
        injection_elements = [
            e for e in vl if etree.QName(e.tag).localname in injection_types
        ]
        for element in injection_elements:
            bus_name = get_inj_bus(element, bus_connections)
            if bus_name is not None:
                if element.get("p") is not None:
                    p_inj[bus_name] = p_inj.get(bus_name, 0.0) + float(element.get("p"))
                if element.get("q") is not None:
                    q_inj[bus_name] = q_inj.get(bus_name, 0.0) + float(element.get("q"))

    # Set 0 to buses without injection
    for b in valid_buses:
        if not b in p_inj:
            p_inj[b]=0
        if not b in q_inj:
            q_inj[b]=0
    # update data
    for bus_name in p_inj:
        if bus_name is not None and bus_name in vl_nomv:
            data.append([bus_name, "bus", vl_nomv[bus_name], "p", p_inj[bus_name]])
    for bus_name in q_inj:
        if bus_name is not None and bus_name in vl_nomv:
            data.append([bus_name, "bus", vl_nomv[bus_name], "q", q_inj[bus_name]])
    print("                         ", end="")  # Hades has extra output here
    print(f" {len(p_inj):5d} P-injections", end="")
    print(f" {len(q_inj):5d} Q-injections")

def extract_hds_injection_bus(root, reseau, category, tag, bus_connections, bus_names):
    donnees = reseau.find(category, root.nsmap)
    for inj in donnees.iterfind(tag, root.nsmap):
        bus = inj.get("noeud") if "cspr" not in tag else inj.get("conbus")
        if bus in bus_names:
            bus_connections[inj.get("nom")] = bus_names[bus]
def extract_hds_buses_connections(hades_input):
    tree = etree.parse(hades_input)
    root = tree.getroot()
    """Read V & angles, and update data."""
    reseau = root.find("./reseau", root.nsmap)
    donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    bus_names={bus.get("num"):bus.get("nom") for bus in donneesNoeuds.iterfind("./noeud", root.nsmap)}

    postes = reseau.find("./postes", root.nsmap)
    poste_names={poste.get("num"):poste.get("nom") for poste in postes.iterfind("./poste", root.nsmap)}

    bus_connections={}

    reseau = root.find("./reseau", root.nsmap)

    extract_hds_injection_bus(root, reseau, "./donneesShunts", "./shunt", bus_connections, bus_names)
    extract_hds_injection_bus(root, reseau, "./donneesGroupes", "./groupe", bus_connections, bus_names)
    extract_hds_injection_bus(root, reseau, "./donneesConsos", "./conso", bus_connections, bus_names)
    extract_hds_injection_bus(root, reseau, "./donneesHvdcs/stationsVsc", "./stationVsc", bus_connections, bus_names)
    extract_hds_injection_bus(root, reseau, "./donneesCsprs", "./cspr", bus_connections, bus_names)

    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for quadripole in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        if quadripole.get("postor") in poste_names and quadripole.get("nor") in bus_names:
            bus_connections[(quadripole.get("nom"),poste_names[quadripole.get("postor")])] = bus_names[quadripole.get("nor")]
        if quadripole.get("postex") in poste_names and quadripole.get("nex") in bus_names:
            bus_connections[(quadripole.get("nom"),poste_names[quadripole.get("postex")])] = bus_names[quadripole.get("nex")]

    return bus_connections

    # The fixed part of SVCs will need to be calculated inside the loop below
    # svc_qfixed = gridinfo.svc_qfixed
    # # Finally, we collect all the injection data, making the appropriate corrections
    # pctr, qctr = [0, 0]
    # donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    # for bus in donneesNoeuds.iterfind("./noeud", root.nsmap):
    #     bus_name = bus.get("nom")
    #     bus_vars = bus.find("./variables", root.nsmap)
    #     if bus_vars.get("v") == HDS_INACT_BUS and bus_vars.get("ph") == HDS_INACT_BUS:
    #         continue  # skip inactive buses
    #     # update data (note the opposite sign convention w.r.t. Dynawo)
    #     p = -float(bus_vars.get("injact"))
    #     data.append([bus_name, "bus", "p", p])
    #     pctr += 1
    #     # SVC's fixed shunt Q values are calculated here because we need the bus V
    #     q = (
    #         -float(bus_vars.get("injrea"))
    #         + shunt_qcorr.get(bus_name, 0)
    #         - (svc_qfixed.get(bus_name, 0) * float(bus_vars.get("v")) ** 2)
    #     )
    #     data.append([bus_name, "bus", "q", q])
    #     qctr += 1
    # print(f" {pctr:5d} P-injections", end="")
    # print(f" {qctr:5d} Q-injections")

def extract_hades_solution(
    hades_input, hades_output, vl_nomv, dwo_branches
):
    """Read all output and return a dataframe."""
    # We'll be using a dataframe, for sorting
    column_list = ["ID", "ELEMENT_TYPE", "VAR", "VALUE_HADES"]
    data = []
    # Some structural info is not in the output; we need to get it from the Hades input
    gridinfo = extract_hds_gridinfo(hades_input)
    # And the rest will be obtained from the output file
    tree = etree.parse(hades_output)
    root = tree.getroot()

    print("   found in Hades file:", end="")
    # Buses: get V & angle
    extract_hds_buses(vl_nomv, root, data)
    # Branches (line/xfmr/psxfmr): p & q flows and xfmr taps
    extract_hds_branches(dwo_branches, gridinfo, root, data)
    # Aggregate bus injections (loads, generators, shunts, VSCs)
    extract_hds_bus_inj(gridinfo, root, data)
    return pd.DataFrame(data, columns=column_list)


def extract_hds_gridinfo(hades_input):
    """Read info that's only available in the input file (branch buses; xfmr taps)."""

    tree = etree.parse(hades_input)
    root = tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    # an auxiliary dict that maps "num" to "nom"
    buses = dict()
    donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    for bus in donneesNoeuds.iterfind("./noeud", root.nsmap):
        buses[bus.get("num")] = bus.get("nom")
    buses["-1"] = "DISCONNECTED"
    # Build a dict that maps branch names to their bus1 and bus2 names
    branch_sides = dict()
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        branch_sides[branch.get("nom")] = Hds_branch_side(
            bus1=buses[branch.get("nor")] if branch.get("nor") is not None else None,
            bus2=buses[branch.get("nex")] if branch.get("nex") is not None else None
        )
    # Build a dict that maps "regleur" IDs to their transformer's name AND a dict
    # that maps "dephaseur" IDs to their transformer's name
    tap2xfmr = dict()
    pstap2xfmr = dict()
    for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        tap_ID = branch.get("ptrregleur")
        if tap_ID != "0" and tap_ID is not None:
            tap2xfmr[tap_ID] = branch.get("nom")
        pstap_ID = branch.get("ptrdepha")
        if pstap_ID != "0" and pstap_ID is not None:
            pstap2xfmr[pstap_ID] = branch.get("nom")
    # Build a dict that maps shunt IDs to their respective bus names
    shunt2busname = dict()
    donneesShunts = reseau.find("./donneesShunts", root.nsmap)
    for shunt in donneesShunts.iterfind("./shunt", root.nsmap):
        bus_num = shunt.get("noeud")
        if bus_num != "-1" and bus_num is not None:
            shunt2busname[shunt.get("num")] = buses[bus_num]
    # Build a dict that maps bus names to total QFixed originated from SVCs (if any)
    svc_qfixed = dict()
    donneesCsprs = reseau.find("./donneesCsprs", root.nsmap)
    for cspr in donneesCsprs.iterfind("./cspr", root.nsmap):
        bus_num = cspr.get("conbus")
        if bus_num != "-1":
            svc_qfixed[buses[bus_num]] = svc_qfixed.get(buses[bus_num], 0) + float(
                cspr.get("shunt")
            )
    return Hds_gridinfo(
        branch_sides=branch_sides,
        tap2xfmr=tap2xfmr,
        pstap2xfmr=pstap2xfmr,
        shunt2busname=shunt2busname,
        svc_qfixed=svc_qfixed,
    )


def extract_hds_buses(vl_nomv, root, data):
    """Read V & angles, and update data."""
    reseau = root.find("./reseau", root.nsmap)
    donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    ctr = 0
    ign = 0
    for bus in donneesNoeuds.iterfind("./noeud", root.nsmap):
        bus_name = bus.get("nom")
        v = bus[0].get("v")
        angle = bus[0].get("ph")
        if v == HDS_INACT_BUS and angle == HDS_INACT_BUS:
            continue  # skip inactive buses
        if bus_name in vl_nomv:
            data.append([bus_name, "bus", "v", float(v) * vl_nomv[bus_name] / 100])
            data.append([bus_name, "bus", "angle", float(angle) * 180 / math.pi])
            ctr += 1
        else:
            ign += 1
    print(f" {ctr:5d} buses", end="")
    print(f" {ign:5d} ignored buses", end="")


def extract_hds_branches(dwo_branches, gridinfo, root, data):
    """Read branch flows (incl. xfmr taps), and update data."""
    # First we extract tap and phase-shifter tap values (used in the loop below)
    taps, pstaps = extract_hds_taps(root, gridinfo)
    # And now we extract the branch (quadripole) data
    hds_branch_sides = gridinfo.branch_sides  # for checking side convention below
    lctr, xctr, psctr, bad_ctr = [0, 0, 0, 0]
    reseau = root.find("./reseau", root.nsmap)
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    for quadrip in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        quadrip_name = quadrip.get("nom")
        p1 = float(quadrip[0].get("por"))
        q1 = float(quadrip[0].get("qor"))
        p2 = float(quadrip[0].get("pex"))
        q2 = float(quadrip[0].get("qex"))
        # magic number 999999 is used for disconnected branches
        if p1 > 999_990:
            p1 = math.nan
        if q1 > 999_990:
            q1 = math.nan
        if p2 > 999_990:
            p2 = math.nan
        if q2 > 999_990:
            q2 = math.nan

        # find out whether it is a line/xfmr/psxfmr by looking it up in Dynawo case
        dwo_branch_info = dwo_branches.get(quadrip_name)
        if dwo_branch_info is not None:
            element_type = dwo_branch_info.type
            # and if side-labeling convention is reversed, fix it
            if hds_branch_sides[quadrip_name].bus1 == dwo_branch_info.bus2:
                p1, p2 = (p2, p1)
                q1, q2 = (q2, q1)
        else:
            element_type = "QUADRIPOLE_NOT_IN_DWO"
        # collect the data
        data.append([quadrip_name, element_type, "p1", p1])
        data.append([quadrip_name, element_type, "q1", q1])
        data.append([quadrip_name, element_type, "p2", p2])
        data.append([quadrip_name, element_type, "q2", q2])
        tap_value = taps.get(quadrip_name)
        if tap_value is not None:
            data.append([quadrip_name, element_type, "tap", tap_value])
        pstap_value = pstaps.get(quadrip_name)
        if pstap_value is not None:
            data.append([quadrip_name, element_type, "pstap", pstap_value])
        # counters
        if element_type == "line":
            lctr += 1
        elif element_type == "xfmr":
            xctr += 1
        elif element_type == "psxfmr":
            psctr += 1
        else:
            bad_ctr += 1
    print(
        f" {lctr:5d} lines {xctr:5d} xfmrs {psctr:3d} psxfmrs"
        f" ({bad_ctr} quadrip. not in XIIDM) ",
        end=""
    )


def extract_hds_taps(root, gridinfo):
    """Read tap values and return them in two dicts indexed by name (taps, pstaps)."""
    # First transformer taps
    tap2xfmr = gridinfo.tap2xfmr
    taps = dict()
    reseau = root.find("./reseau", root.nsmap)
    donneesRegleurs = reseau.find("./donneesRegleurs", root.nsmap)
    for regleur in donneesRegleurs.iterfind("./regleur", root.nsmap):
        quadrip_name = tap2xfmr.get(regleur.get("num"))
        if quadrip_name is None:
            raise ValueError(
                f"in Hades output file: regleur {regleur.get('num')}"
                "  has no associated transformer!"
            )
        taps[quadrip_name] = int(regleur.find("./variables", root.nsmap).get("plot"))
    # Now phase-shifter taps
    pstap2xfmr = gridinfo.pstap2xfmr
    pstaps = dict()
    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        quadrip_name = pstap2xfmr.get(dephaseur.get("num"))
        if quadrip_name is None:
            raise ValueError(
                f"in Hades output file: dephaseur {dephaseur.get('num')}"
                "  has no associated transformer!"
            )
        pstaps[quadrip_name] = int(
            dephaseur.find("./variables", root.nsmap).get("plot")
        )
    return taps, pstaps


def extract_hds_bus_inj(gridinfo, root, data):
    """Aggregate injections (loads, gens, shunts, VSCs) by bus, and update data."""
    # Conveniently, Hades already provides the bus injections in the bus output
    # section Alas, Hades has two bugs:
    #   1) these injections don't include shunts!
    #   2) these injections don't include the fixed part of Static Var Compensators
    # So we'll correct for these two things here.
    # First collect shunt's Q injections
    shunt2busname = gridinfo.shunt2busname
    shunt_qcorr = dict()
    reseau = root.find("./reseau", root.nsmap)
    donneesShunts = reseau.find("./donneesShunts", root.nsmap)
    for shunt in donneesShunts.iterfind("./shunt", root.nsmap):
        shunt_vars = shunt.find("./variables", root.nsmap)
        q = shunt_vars.get("q")
        if q in (HDS_INACT_SHUNT, HDS_INACT_SHUNT2):
            continue  # skip inactive shunts
        bus_name = shunt2busname[shunt.get("num")]
        shunt_qcorr[bus_name] = shunt_qcorr.get(bus_name, 0.0) - float(q)
    # The fixed part of SVCs will need to be calculated inside the loop below
    svc_qfixed = gridinfo.svc_qfixed
    # Finally, we collect all the injection data, making the appropriate corrections
    pctr, qctr = [0, 0]
    donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    for bus in donneesNoeuds.iterfind("./noeud", root.nsmap):
        bus_name = bus.get("nom")
        bus_vars = bus.find("./variables", root.nsmap)
        if bus_vars.get("v") == HDS_INACT_BUS and bus_vars.get("ph") == HDS_INACT_BUS:
            continue  # skip inactive buses
        # update data (note the opposite sign convention w.r.t. Dynawo)
        p = -float(bus_vars.get("injact"))
        data.append([bus_name, "bus", "p", p])
        pctr += 1
        # SVC's fixed shunt Q values are calculated here because we need the bus V
        q = (
            -float(bus_vars.get("injrea"))
            + shunt_qcorr.get(bus_name, 0)
            - (svc_qfixed.get(bus_name, 0) * float(bus_vars.get("v")) ** 2)
        )
        data.append([bus_name, "bus", "q", q])
        qctr += 1
    print(f" {pctr:5d} P-injections", end="")
    print(f" {qctr:5d} Q-injections")

def save_tap_score(df, nb_computed_tap, case_dir):
    Tap_score = namedtuple("tap_score",
                           ["computed_tap",
                            "max_tap_diff",
                            "nb_tap_diff",
                            "max_q1_diff",
                            "q1_2_count",
                            "max_p1_diff"])
    if df[df.ID=="status#code"].VALUE_HADES.min() == 0 or df[df.ID=="status#code"].VALUE_OLF.min() == 0:
        df_xfmr = df[df.ELEMENT_TYPE=="xfmr"].copy()
        df_xfmr["DIFF"]=abs(df_xfmr.VALUE_HADES - df_xfmr.VALUE_OLF)
        df_q1 = df[df.VAR=="q1"].copy()
        df_q1["DIFF"]=abs(df_q1.VALUE_HADES - df_q1.VALUE_OLF)
        df_p1 = df[df.VAR == "p1"].copy()
        df_p1["DIFF"] = abs(df_p1.VALUE_HADES - df_p1.VALUE_OLF)
        score = Tap_score(
            computed_tap=nb_computed_tap,
            max_tap_diff=int(df_xfmr[df_xfmr.VAR=="tap"].DIFF.max()),
            nb_tap_diff=len(df_xfmr[(df_xfmr.VAR=="tap") & (df_xfmr.DIFF>0)]),
            max_q1_diff= df_q1.DIFF.max(),
            q1_2_count=len(df_q1[df_q1.DIFF > 2]),
            max_p1_diff=df_p1.DIFF.max(),
        )
    else:
        score = Tap_score(
            computed_tap=None,
            max_tap_diff=None,
            nb_tap_diff=None,
            max_q1_diff= None,
            q1_2_count=None,
            max_p1_diff=None,
        )

    score_df = pd.DataFrame(columns=Tap_score._fields, data=[score])
    output_file=os.path.join(case_dir,TAP_SCORE_FILE)
    score_df.to_csv(output_file, index=False, sep=";", encoding="utf-8")

def save_extracted_values(df_hds, df_olf, case_dir, nb_computed_tap):
    """Save the values for all elements that are matched in both outputs."""
    # Merge (inner join) the two dataframes, checking for duplicates (just in case)
    key_fields = ["ELEMENT_TYPE", "ID", "VAR"]

    df = pd.merge(
        df_hds,
        df_olf,
        how="inner",
        on=key_fields,
        validate="one_to_one",
    )
    # Print some summaries
    print("   common to both files:", end="")
    bus_angles = (df["ELEMENT_TYPE"] == "bus") & (df["VAR"] == "angle")
    print(f" {len(df.loc[bus_angles]):5d} buses", end="")
    lines_p1 = (df["ELEMENT_TYPE"] == "line") & (df["VAR"] == "p1")
    print(f" {len(df.loc[lines_p1]):5d} lines", end="")
    xfmr_p1 = (df["ELEMENT_TYPE"] == "xfmr") & (df["VAR"] == "p1")
    print(f" {len(df.loc[xfmr_p1]):5d} xfmrs", end="")
    psxfmr_p1 = (df["ELEMENT_TYPE"] == "psxfmr") & (df["VAR"] == "p1")
    print(f" {len(df.loc[psxfmr_p1]):3d} psxfmrs")
    # Adjust the bus angles to those of solution A
    if len(df.loc[bus_angles]) > 0:
        swing_idx = df.loc[bus_angles, "VALUE_OLF"].abs().idxmin()
        angle_offset = df.at[swing_idx, "VALUE_HADES"] - df.at[swing_idx, "VALUE_OLF"]
        df.loc[bus_angles, "VALUE_HADES"] -= angle_offset
        print(f'   (angle offset adjusted; zero angle at bus: {df.at[swing_idx, "ID"]})')
    # Sort and save to file
    sort_order = [True, True, True]
    tempcol = df.pop("VOLT_LEVEL")
    df.insert(2, "VOLT_LEVEL", tempcol)
    df.sort_values(
        by=key_fields, ascending=sort_order, inplace=True, na_position="first"
    )
    output_file=os.path.join(case_dir,OUTPUT_FILE)
    df.to_csv(output_file, index=False, sep=";", encoding="utf-8")
    print(f"Saved output to file: {output_file}... ")
    save_tap_score(df, nb_computed_tap, case_dir)


def save_nonmatching_elements(df_hds, df_olf, errors_hds_file, errors_olf_file):
    """Save the elements that did not match. Some may be due to threshold flows."""
    key_fields = ["ELEMENT_TYPE", "ID", "VAR"]
    # Output the diffs. Newer versions of Pandas support df.compare(), but here we do
    # it in a more backwards-compatible way.
    set_hds = frozenset(df_hds["ID"].add(df_hds["ELEMENT_TYPE"]))
    set_olf = frozenset(df_olf["ID"].add(df_olf["ELEMENT_TYPE"]))
    elements_not_in_hds = list(set_olf - set_hds)
    elements_not_in_olf = list(set_hds - set_olf)
    if len(elements_not_in_hds) != 0:
        df_not_in_hds = df_olf.loc[
            (df_olf["ID"] + df_olf["ELEMENT_TYPE"]).isin(elements_not_in_hds)
        ]
        df_not_in_hds.sort_values(by=key_fields, ascending=[True, True, True]).to_csv(
            errors_hds_file, index=False, sep=";", encoding="utf-8"
        )
        print(
            f"{len(elements_not_in_hds)} elements from case OLF not in case Hades "
            f"saved in file: {errors_hds_file}"
        )
    if len(elements_not_in_olf) != 0:
        df_not_in_olf = df_hds.loc[
            (df_hds["ID"] + df_hds["ELEMENT_TYPE"]).isin(elements_not_in_olf)
        ]
        df_not_in_olf.sort_values(by=key_fields, ascending=[True, True, True]).to_csv(
            errors_olf_file, index=False, sep=";", encoding="utf-8"
        )
        print(
            f"{len(elements_not_in_olf)} elements from Hades not in case OLF "
            f"saved in file: {errors_olf_file}"
        )


def extract_hades_info(hades_version, hades_input):
    column_list = ["PARAM", "VALUE"]

    lines = open(hades_version, 'r').readlines()
    regexp = re.compile(r'Hades.*- V.*')

    data=[]
    version = None
    for l in lines:
        if re.match(regexp, l) :
            version=l.strip()
    data.append(["Version", version])

    # Get the parameters
    tree = etree.parse(hades_input)
    root = tree.getroot()
    #paramHades
    modele = root.find("./modele", root.nsmap)
    params = modele.find("./parametres", root.nsmap)
    paramHades = params.find("./paramHades", root.nsmap)
    for name, value in paramHades.items():
        data.append([name, value])

    return pd.DataFrame(data, columns=column_list)

def extract_olf_info(olf_version, olf_params):
    column_list = ["PARAM", "VALUE"]

    data=[]
    lines = open(olf_version, 'r').readlines()
    for l in lines:
        if "powsybl-open-loadflow" in l:
            tokens = l.split('|')
            print(len(tokens))
            if len(tokens) == 7:
                data.append(["Version", tokens[1].strip() + " - V" + tokens[2].strip()])
    jsonparams = json.load(open(olf_params, 'r'))
    for p in jsonparams:
        if p not in ["version", "extensions"]:
            data.append([p, jsonparams[p]])
        elif p == "extensions":
            if "open-load-flow-parameters" in jsonparams[p] is not None:
                olfp = jsonparams[p]["open-load-flow-parameters"]
                for p2 in olfp:
                    data.append(["olf."+p2, olfp[p2]])

    return pd.DataFrame(data, columns=column_list)

if __name__ == "__main__":
    sys.exit(main())
