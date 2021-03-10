#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# calc_automata_diffmetrics.py:
#
# Given a directory containing processed Astre and Dynawo cases, all
# of them derived from a common base case, this script calculates
# several metrics that try to assess the differences in automata
# events (such as tap changers and shunt engagement / disengagement
# actions). It works on the output files produced by the script
# "extract_automata_changes.py".
#
#   * On input: you have to provide the "aut" directory that contains the
#     files that have the extracted automata events
#     (e.g. "*-AstreAutomata.csv.xz", etc.), plus a filename prefix
#     for them (e.g. "shunt_"). Additionally, you have to provide the
#     original BASECASE from which all those cases were derived (this
#     is needed for querying the network model, and also for getting the
#     time parameters of the simulation).
#
#   * On output, the script generates a file "aut_diffmetrics.csv"
#     with the calculated metrics for each case. The file is left in
#     a "metrics" subdirectory, sibling to the "aut" dir.
#
#
# NOTES: The metrics we calculate here are as follows. STRICT means the
# differences are calculated by matching individual devices. RELAXED
# means it is calculated at the level of the whole bus, using some
# grouping heuristic (this is the case of Load-Transformers, because
# the presence of merged loads in Dynawo precludes a comparison
# at the device level).
#
#    * For Shunt events "ShuntConnected/ShuntDisconnected": (STRICT)
#       - shunt_netchanges: diffs in the amount of net change a. t. (binary)
#       - shunt_numchanges: diffs in the total number of changes
#
#   * For Transmission Transformer events "TapUp/TapDown": (STRICT)
#       - tap_netchanges: diffs in the amount of net change after transient
#       - tap_p2pchanges: diffs in the amount of peak-to-peak change
#       - tap_numchanges: diffs in the total number of changes
#
#    * For Load-Transformer events "TapUp/TapDown": (RELAXED)
#       - ldtap_netchanges: diffs in the amount of net change after transient
#       - ldtap_p2pchanges: diffs in the amount of peak-to-peak change
#       - ldtap_numchanges: diffs in the total number of changes
#
# In this last case, Load-Transformers, the heuristic for grouping things at the bus
# level is to keep the "worst case" among all load-transformers of the bus, and use
# that for comparing.
#
# In all cases, the final figure is the L1 norm of diffs.
#

import glob
import os
import sys
from collections import namedtuple
from pathlib import Path
import numpy as np
import pandas as pd
from lxml import etree

# Relative imports only work for proper Python packages, but we do not want to
# structure all these as a package; we'd like to keep them as a collection of loose
# Python scripts, at least for now (because this is not really a Python library). So
# the following hack is ugly, but needed:
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Alternatively, you could set PYTHONPATH to PYTHONPATH="/<dir>/dynawo-validation-AIA"
from xml_utils.dwo_jobinfo import get_dwo_tparams  # noqa: E402
from xml_utils.dwo_jobinfo import get_dwo_jobpaths  # noqa: E402


N_TWPOINTS = 41  # 41 TW data points results in 30s timesteps when Tsim is 1200s
AST_SUFFIX = "-AstreAutomata.csv.xz"
DWO_SUFFIX = "-DynawoAutomata.csv.xz"
verbose = True
pd.set_option("display.max_rows", 50)


def main():

    if len(sys.argv) != 4:
        print("\nUsage: %s AUT_DIR PREFIX BASECASE\n" % sys.argv[0])
        return 2
    aut_dir = sys.argv[1]
    prefix = sys.argv[2]
    base_case = sys.argv[3]

    # Get the simulation time parameters (from Dynawo's case)
    dwo_tparams = get_dwo_tparams(base_case)
    startTime = dwo_tparams.startTime
    stopTime = dwo_tparams.stopTime
    tEvent = dwo_tparams.event_tEvent

    # Get some Dynawo paths from the JOB file
    dwo_paths = get_dwo_jobpaths(base_case)

    # Check all needed dirs are in place, and get the list of files to process
    file_list = check_inputfiles(aut_dir, prefix, base_case, dwo_paths)

    # Build a dict: load-->bus (needed for Load_Transformers)
    ld_bus = load2bus_dict(base_case, dwo_paths)

    # Get the normalization factors for each class of metric (shunt, xfmr, etc.)
    norm_factor = get_norm_factor(base_case, dwo_paths)

    # We'll need this later on, for correcting Dynawo's shunt events count
    is_shunt_contg = "shunt" == prefix[:5]

    ############################################################################
    # PART I : compute the metrics for all cases (at the end of the simulation)
    ############################################################################
    print("Calculating diffmetrics for automata changes in: %s" % aut_dir)
    metrics_rowdata = []
    for case_label in file_list:
        if verbose:
            print("   processing: " + prefix + case_label)
        ast_df = pd.read_csv(file_list[case_label].ast, sep=";")
        dwo_df = pd.read_csv(file_list[case_label].dwo, sep=";")
        metrics = calc_metrics(ast_df, dwo_df, ld_bus, norm_factor)
        metrics_rowdata.append({"Contg_case": case_label, **metrics})

    # Save the metrics to file
    col_names = list(metrics_rowdata[0].keys())
    df = pd.DataFrame(metrics_rowdata, columns=col_names)
    metrics_dir = aut_dir + "/../metrics"
    Path(metrics_dir).mkdir(parents=False, exist_ok=True)
    df.to_csv(
        metrics_dir + "/aut_diffmetrics.csv", sep=";", index=False, float_format="%.4f"
    )
    print("Saved diffmetrics for automata changes in: %s" % metrics_dir)

    ###############################################################################
    # PART II: compute how these same metrics evolve in time (only non-zero cases)
    ###############################################################################
    print("Calculating TIME WINDOWED diffmetrics for automata changes in: %s" % aut_dir)
    metrics_rowdata = []
    nz = df["any_shunt_evt"] | df["any_xfmr_tap"] | df["any_ldxfmr_tap"]
    for case_label in df.loc[nz, "Contg_case"]:
        if verbose:
            print("   TW processing: " + prefix + case_label)
        ast_df = pd.read_csv(file_list[case_label].ast, sep=";")
        dwo_df = pd.read_csv(file_list[case_label].dwo, sep=";")
        dwo_df["TIME"] -= startTime  # undo the time offset in Dynawo
        for tw in np.linspace(0, stopTime - startTime, N_TWPOINTS):
            ast_tw = ast_df[ast_df["TIME"] <= tw]
            dwo_tw = dwo_df[dwo_df["TIME"] <= tw]
            if is_shunt_contg and tw >= (tEvent - startTime):
                shunt_corr = True
            else:
                shunt_corr = False
            metrics = calc_metrics(ast_tw, dwo_tw, ld_bus, norm_factor, shunt_corr)
            metrics_rowdata.append({"Contg_case": case_label, "time": tw, **metrics})

    # Save the metrics to file
    if 0 == len(metrics_rowdata):
        print("(no events found -- TIME-WINDOWED diffmetrics will be empty)")
    col_names.insert(1, "time")
    tw_df = pd.DataFrame(metrics_rowdata, columns=col_names)
    tw_df = tw_df.drop(columns=["any_shunt_evt", "any_xfmr_tap", "any_ldxfmr_tap"])
    tw_df.to_csv(
        metrics_dir + "/aut_tw_diffmetrics.csv",
        sep=";",
        index=False,
        float_format="%.4f",
    )
    print("Saved TIME-WINDOWED diffmetrics for automata changes in: %s" % metrics_dir)

    return 0


def check_inputfiles(aut_dir, prefix, base_case, dwo_paths):
    if not os.path.isdir(aut_dir):
        raise ValueError("Automata data input directory %s not found" % aut_dir)

    if not (
        os.path.isfile(base_case + "/Astre/donneesModelesEntree.xml")
        and os.path.isfile(base_case + "/" + dwo_paths.iidmFile)
        and os.path.isfile(base_case + "/" + dwo_paths.dydFile)
        and os.path.isfile(base_case + "/" + dwo_paths.parFile)
        and os.path.isfile(base_case + "/" + dwo_paths.curves_inputFile)
    ):
        raise ValueError(
            "some expected files are missing in BASECASE dir %s\n" % base_case
        )

    # We first find out all Astre files
    ast_filepattern = aut_dir + "/" + prefix + "*" + AST_SUFFIX
    ast_files = glob.glob(ast_filepattern)
    if len(ast_files) == 0:
        raise ValueError("no input files found with prefix %s\n" % prefix)

    # Then we find their corresponding Dynawo counterparts
    Aut_Pair = namedtuple("Aut_Pair", ["ast", "dwo"])
    file_list = dict()
    for ast_file in ast_files:
        case_label = ast_file.split(AST_SUFFIX)[0].split(prefix)[-1]
        dwo_file = ast_file.split(AST_SUFFIX)[0] + DWO_SUFFIX
        if not (os.path.isfile(dwo_file)):
            raise ValueError("Dynawo data file not found for %s\n" % ast_file)
        file_list[case_label] = Aut_Pair(ast=ast_file, dwo=dwo_file)

    if verbose:
        print("aut_dir: %s" % aut_dir)
        print("prefix: %s" % prefix)
        print("base_case: %s" % base_case)
        print("List of cases to process: (total: %d)" % len(file_list))
        case_list = sorted(file_list.keys())
        if len(case_list) < 10:
            print(case_list)
        else:
            print(case_list[:5] + ["..."] + case_list[-5:])

    return file_list


def calc_metrics(ast_df, dwo_df, ld_bus, norm_factor, shunt_correction=False):
    # SHUNTS:
    shunt_metrics = calc_shunt_metrics(ast_df, dwo_df)
    if shunt_correction:  # because Dynawo shows the contingency itself as an event
        shunt_metrics["shunt_netchanges"] += -1
        shunt_metrics["shunt_numchanges"] += -1
    shunt_metrics["shunt_netchanges"] /= norm_factor.shunt
    shunt_metrics["shunt_numchanges"] /= norm_factor.shunt

    # TRANSFORMERS:
    xfmr_metrics = calc_xfmr_metrics(ast_df, dwo_df)
    xfmr_metrics["tap_netchanges"] /= norm_factor.xfmr
    xfmr_metrics["tap_p2pchanges"] /= norm_factor.xfmr
    xfmr_metrics["tap_numchanges"] /= norm_factor.xfmr

    # LOAD TRANSFORMERS:
    ldxfmr_metrics = calc_ldxfmr_metrics(ast_df, dwo_df, ld_bus)
    ldxfmr_metrics["ldtap_netchanges"] /= norm_factor.ldxfmr
    ldxfmr_metrics["ldtap_p2pchanges"] /= norm_factor.ldxfmr
    ldxfmr_metrics["ldtap_numchanges"] /= norm_factor.ldxfmr

    return {**shunt_metrics, **xfmr_metrics, **ldxfmr_metrics}


def event_counts(df, event):
    row_filter = df["EVENT"] == event
    filtered_df = df.loc[row_filter, ["DEVICE", "EVENT"]]
    counts_df = filtered_df.groupby(by="DEVICE", as_index=True).count()
    # Only one column left, so we return a Series since it's lighter
    return counts_df["EVENT"]


#################################################
# SHUNTS
#################################################
def calc_shunt_metrics(ast_df, dwo_df):
    ast_df = ast_df.loc[ast_df["DEVICE_TYPE"] == "Shunt"]
    dwo_df = dwo_df.loc[dwo_df["DEVICE_TYPE"] == "Shunt"]
    # Shortcut: a vast majority of cases have no relevant events
    if ast_df.empty and dwo_df.empty:
        return {"shunt_netchanges": 0, "shunt_numchanges": 0, "any_shunt_evt": False}

    # Auxiliary counts of Shunt connection/disconnection events
    ast_shunts_on = event_counts(ast_df, "ShuntConnected")
    ast_shunts_off = event_counts(ast_df, "ShuntDisconnected")
    dwo_shunts_on = event_counts(dwo_df, "ShuntConnected")
    dwo_shunts_off = event_counts(dwo_df, "ShuntDisconnected")

    # Shunt metric: "diff in net change" (STRICT)
    ast_netchanges = ast_shunts_on.sub(ast_shunts_off, fill_value=0)
    dwo_netchanges = dwo_shunts_on.sub(dwo_shunts_off, fill_value=0)
    netchange_diffs = ast_netchanges.sub(dwo_netchanges, fill_value=0)
    shunt_netchanges_metric = netchange_diffs.abs().sum()  # L1 norm

    # Shunt metric: "diff in the total number of changes" (STRICT)
    ast_numchanges = ast_shunts_on.add(ast_shunts_off, fill_value=0)
    dwo_numchanges = dwo_shunts_on.add(dwo_shunts_off, fill_value=0)
    numchange_diffs = ast_numchanges.sub(dwo_numchanges, fill_value=0)
    shunt_numchanges_metric = numchange_diffs.abs().sum()  # L1 norm

    metrics = {
        "shunt_netchanges": shunt_netchanges_metric,
        "shunt_numchanges": shunt_numchanges_metric,
        "any_shunt_evt": True,
    }

    return metrics


#################################################
# TRANSFORMERS (only transmission transformers)
#################################################
def calc_xfmr_metrics(ast_df, dwo_df):
    ast_df = ast_df.loc[ast_df["DEVICE_TYPE"] == "Transformer"]
    dwo_df = dwo_df.loc[dwo_df["DEVICE_TYPE"] == "Transformer"]
    # Shortcut: a vast majority of cases have no relevant events
    if ast_df.empty and dwo_df.empty:
        return {
            "tap_netchanges": 0,
            "tap_p2pchanges": 0,
            "tap_numchanges": 0,
            "any_xfmr_tap": False,
        }

    # Auxiliary counts of Tap changer events
    ast_taps_up = event_counts(ast_df, "TapUp")
    ast_taps_down = event_counts(ast_df, "TapDown")
    dwo_taps_up = event_counts(dwo_df, "TapUp")
    dwo_taps_down = event_counts(dwo_df, "TapDown")

    # Tap changer metric: "diff in net change" (STRICT)
    ast_netchange = ast_taps_up.sub(ast_taps_down, fill_value=0)
    dwo_netchange = dwo_taps_up.sub(dwo_taps_down, fill_value=0)
    netchange_diffs = ast_netchange.sub(dwo_netchange, fill_value=0)
    tap_netchanges_metric = netchange_diffs.abs().sum()  # L1 norm

    # Tap changer metric: "diff in the total number of changes" (STRICT)
    ast_numchanges = ast_taps_up.add(ast_taps_down, fill_value=0)
    dwo_numchanges = dwo_taps_up.add(dwo_taps_down, fill_value=0)
    numchange_diffs = ast_numchanges.sub(dwo_numchanges, fill_value=0)
    tap_numchanges_metric = numchange_diffs.abs().sum()  # L1 norm

    # Auxiliary calculation of Tap peak-to-peak changes
    ast_p2pchange = peak2peak(ast_df, ["Transformer"], ["TapUp", "TapDown"])
    dwo_p2pchange = peak2peak(dwo_df, ["Transformer"], ["TapUp", "TapDown"])

    # Tap changer metric: "diff in peak-to-peak change" (STRICT)
    p2pchange_diffs = ast_p2pchange.sub(dwo_p2pchange, fill_value=0)
    tap_p2pchanges_metric = p2pchange_diffs.abs().sum()  # L1 norm

    metrics = {
        "tap_netchanges": tap_netchanges_metric,
        "tap_p2pchanges": tap_p2pchanges_metric,
        "tap_numchanges": tap_numchanges_metric,
        "any_xfmr_tap": True,
    }

    return metrics


#################################################
# LOAD TRANSFORMERS
#################################################
def calc_ldxfmr_metrics(ast_df, dwo_df, ld_bus):
    ast_df = ast_df.loc[ast_df["DEVICE_TYPE"] == "Load_Transformer"]
    dwo_df = dwo_df.loc[dwo_df["DEVICE_TYPE"] == "Load_Transformer"]
    # Shortcut: a vast majority of cases have no relevant events
    if ast_df.empty and dwo_df.empty:
        return {
            "ldtap_netchanges": 0,
            "ldtap_p2pchanges": 0,
            "ldtap_numchanges": 0,
            "any_ldxfmr_tap": False,
        }

    # The process is very similar to xfmrs, except that the comparison is made BY
    # BUS, instead of element. We choose the worst (i.e. highest) metric among all
    # load-transformers found on the same bus. This is in order to cope with Dynawo's
    # merged loads, which prevent matching loads on an individual basis.

    # Auxiliary counts of Tap changer events
    ast_taps_up = event_counts(ast_df, "TapUp")
    ast_taps_down = event_counts(ast_df, "TapDown")
    dwo_taps_up = event_counts(dwo_df, "TapUp")
    dwo_taps_down = event_counts(dwo_df, "TapDown")

    # Tap changer metric: "diff in net change" (RELAXED)
    ast_netchange = ast_taps_up.sub(ast_taps_down, fill_value=0)
    dwo_netchange = dwo_taps_up.sub(dwo_taps_down, fill_value=0)
    ast_netchange_bybus = worst_netchange_bybus(ast_netchange, ld_bus)
    dwo_netchange_bybus = worst_netchange_bybus(dwo_netchange, ld_bus)
    netchange_diffs = ast_netchange_bybus.sub(dwo_netchange_bybus, fill_value=0)
    ldtap_netchanges_metric = netchange_diffs.abs().sum()  # L1 norm

    # Tap changer metric: "diff in the total number of changes" (RELAXED)
    ast_numchange = ast_taps_up.add(ast_taps_down, fill_value=0)
    dwo_numchange = dwo_taps_up.add(dwo_taps_down, fill_value=0)
    ast_numchange_bybus = worst_numchange_bybus(ast_numchange, ld_bus)
    dwo_numchange_bybus = worst_numchange_bybus(dwo_numchange, ld_bus)
    numchange_diffs = ast_numchange_bybus.sub(dwo_numchange_bybus, fill_value=0)
    ldtap_numchanges_metric = numchange_diffs.abs().sum()  # L1 norm

    # Auxiliary calculation of Tap peak-to-peak changes
    ast_p2pchange = peak2peak(ast_df, ["Load_Transformer"], ["TapUp", "TapDown"])
    dwo_p2pchange = peak2peak(dwo_df, ["Load_Transformer"], ["TapUp", "TapDown"])

    # Tap changer metric: "diff in peak-to-peak change" (RELAXED)
    ast_p2pchange_bybus = worst_p2pchange_bybus(ast_p2pchange, ld_bus)
    dwo_p2pchange_bybus = worst_p2pchange_bybus(dwo_p2pchange, ld_bus)
    p2pchange_diffs = ast_p2pchange_bybus.sub(dwo_p2pchange_bybus, fill_value=0)
    ldtap_p2pchanges_metric = p2pchange_diffs.abs().sum()  # L1 norm

    metrics = {
        "ldtap_netchanges": ldtap_netchanges_metric,
        "ldtap_p2pchanges": ldtap_p2pchanges_metric,
        "ldtap_numchanges": ldtap_numchanges_metric,
        "any_ldxfmr_tap": True,
    }

    return metrics


def peak2peak(df, rows, binary_event_names):
    # Only contemplates events of type plus--minus (i.e. taps and shunts)
    plus = binary_event_names[0]
    minus = binary_event_names[1]
    row_filter = df["DEVICE_TYPE"].isin(rows)
    cols = ["DEVICE", "TIME", "EVENT"]
    events_df = df.loc[row_filter, cols]

    # Don't trust that the input is sorted by time; do it here, just in case
    sort_fields = ["DEVICE", "TIME"]
    sort_order = [True, True]
    events_df = events_df.sort_values(
        by=sort_fields, ascending=sort_order, inplace=False, na_position="first"
    )

    # Now follow the sequences to catch the min & max peak. This cannot be done via
    # simple groupby operations.
    p2pchanges = dict()
    devices = events_df["DEVICE"].unique()
    for dev in devices:
        events = events_df.loc[(events_df["DEVICE"] == dev), "EVENT"].values.tolist()
        max_peak = 0
        min_peak = 0
        curve = 0
        for evt in events:
            if evt == plus:
                curve = curve + 1
                max_peak = max(curve, max_peak)
            elif evt == minus:
                curve = curve - 1
                min_peak = min(curve, min_peak)

        p2pchanges[dev] = max_peak - min_peak

    return pd.Series(p2pchanges, name="P2PCHANGE")


def worst_netchange_bybus(nc, ld_bus):
    # Reduce the metrics by bus, keeping the worst one. In this case, "worst" means
    # the netchange that is largest in abs value, but preserving its sign.
    if nc.empty:  # because adding the MAX column below would fail
        return nc
    df = pd.DataFrame(nc).assign(BUS=nc.index)
    df["BUS"] = df["BUS"].map(ld_bus)  # fast replacement of load --> bus
    # Obtain min & max at each bus; then keep the largest of the two in abs value:
    reduced_nc = df.groupby(by="BUS", as_index=True).min()
    reduced_nc["MAX"] = df.groupby(by="BUS", as_index=True).max()
    reduced_nc = reduced_nc.apply(max, axis=1, key=abs)
    return reduced_nc


def worst_numchange_bybus(nc, ld_bus):
    # Reduce the metrics by bus, keeping the worst (i.e. largest) one.
    df = pd.DataFrame(nc).assign(BUS=nc.index)
    df["BUS"] = df["BUS"].map(ld_bus)  # fast replacement of load --> bus
    reduced_nc = df.groupby(by="BUS", as_index=True).max()
    # returned object must be a Series, not a DataFrame:
    return reduced_nc["EVENT"]


def worst_p2pchange_bybus(nc, ld_bus):
    # Reduce the metrics by bus, keeping the worst (i.e. largest) one.
    df = pd.DataFrame(nc).assign(BUS=nc.index)
    df["BUS"] = df["BUS"].map(ld_bus)  # fast replacement of load --> bus
    reduced_nc = df.groupby(by="BUS", as_index=True).max()
    # returned object must be a Series, not a DataFrame
    return reduced_nc["P2PCHANGE"]


def load2bus_dict(base_case, dwo_paths):
    # Build a dictionary load_label-->bus_label, common to both Astre
    # and Dynawo.
    #
    # On buses whose topology is NODE-BREAKER, bus_labels may not match
    # between Astre and Dynawo. So the strategy we follow is:
    #
    #    * Build the dictionary first by using Dynawo's case. If the
    #      load is on a BUS_BREAKER bus, keep the bus name (they
    #      usually match bus names in Astre). But if the load is on a
    #      NODE_BREAKER bus, use the Voltage Level as its bus label (+
    #      a suffix "*" to mark these).
    #
    #    * Then complete it by reading Astre's case. If the load
    #      already exists, just keep the dictionary entry (this avoids
    #      having to match the bus name). If it does not not: check
    #      that its Astre bus exists in Dynawo; if not, then use the
    #      "poste" name (+ a suffix "*" to mark these).
    #
    ld_bus = dict()
    astre_file = base_case + "/Astre/donneesModelesEntree.xml"
    iidm_file = base_case + "/" + dwo_paths.iidmFile

    # Initial build, enumerating loads in Dynawo
    tree = etree.parse(iidm_file)
    root = tree.getroot()
    buses_with_bad_topo = False
    for load in root.iterfind(".//load", root.nsmap):
        vl = load.getparent()
        vl_topo = vl.get("topologyKind")
        if vl_topo == "BUS_BREAKER":
            bus_label = load.get("bus")
            if bus_label is None:
                bus_label = load.get("connectableBus")
            ld_bus[load.get("id")] = bus_label
        elif vl_topo == "NODE_BREAKER":
            ld_bus[load.get("id")] = vl.get("id") + "*"
        else:
            buses_with_bad_topo = True

    if buses_with_bad_topo:
        print("WARNING: found loads at Voltage Levels with bad topology!!!")

    print(
        "Building ld_bus dict from BASECASE: found %d active loads in Dynawo file"
        % len(ld_bus),
        end="",
    )
    dwo_loadbuses = set(list(ld_bus.values()))

    # Now complete the dict with Astre's loads
    tree = etree.parse(astre_file)
    root = tree.getroot()
    # first we'll need two auxiliary dicts to speed up Astre bus & vl lookups
    bus_nom = dict()
    reseau = root.find("./reseau", root.nsmap)
    donneesNoeuds = reseau.find("./donneesNoeuds", root.nsmap)
    for bus in donneesNoeuds.iterfind("./noeud", root.nsmap):
        bus_nom[bus.get("num")] = bus.get("nom")
    vl_nom = dict()
    postes = reseau.find("./postes", root.nsmap)
    for vl in postes.iterfind("./poste", root.nsmap):
        vl_nom[vl.get("num")] = vl.get("nom")
    # now enumerate all loads
    donneesConsos = reseau.find("./donneesConsos", root.nsmap)
    for load in donneesConsos.iterfind("./conso", root.nsmap):
        load_label = load.get("nom")
        noeud_id = load.get("noeud")
        vl_id = load.get("poste")
        if noeud_id == "-1":  # skip disconnected loads
            continue
        # If load name matches in Dynawo, just keep Dynawo's bus name
        if load_label in ld_bus:
            continue
        # If not, add it to the dict. First get its Astre bus name:
        bus_label = bus_nom[noeud_id]
        # If this bus name is not in Dynawo, use the voltage level name
        if bus_label not in dwo_loadbuses:
            bus_label = vl_nom[vl_id] + "*"
        ld_bus[load_label] = bus_label

    print("  (increased to %d after reading Astre file)" % len(ld_bus))

    return ld_bus


def get_norm_factor(base_case, dwo_paths):
    # Calculate the normalization factors to use with each class of metric:
    #
    #    * shunts: the number of shunts
    #    * xfmrs: the number of transformers
    #    * ldxfmrs: the number of load-transformers
    #
    # We get these numbers from Dynawo's DYD (that is, the number of elements that
    # could potentially leave events in the timeline).
    #
    dyd_file = base_case + "/" + dwo_paths.dydFile
    tree = etree.parse(dyd_file)
    root = tree.getroot()
    nshunts = 0
    nldfxmrs = 0
    for mc in root.iterfind("./macroConnect", root.nsmap):
        if mc.get("connector")[-16:] == "ControlledShunts":
            nshunts += 1
    for bbm in root.iterfind("./blackBoxModel", root.nsmap):
        if bbm.get("lib")[:4] == "Load":
            nldfxmrs += 1

    iidm_file = base_case + "/" + dwo_paths.iidmFile
    tree = etree.parse(iidm_file)
    root = tree.getroot()
    nxfmrs = len(tuple(root.iterfind(".//twoWindingsTransformer", root.nsmap)))

    Norm_Factor = namedtuple("Norm_Factor", ["shunt", "xfmr", "ldxfmr"])
    norm_factor = Norm_Factor(shunt=nshunts, xfmr=nxfmrs, ldxfmr=nldfxmrs)

    if verbose:
        print("Normalizing factors: ", norm_factor)

    return norm_factor


if __name__ == "__main__":
    sys.exit(main())
