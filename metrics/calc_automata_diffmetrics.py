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
#   * On input: you have to provide the directory that contains the
#     files that have the extracted automata events
#     (e.g. "*-AstreAutomata.csv.xz", etc.), plus a filename prefix
#     for them (e.g. "shunt_"). Additionally, you have to provide the
#     original BASECASE from which all those cases were derived. This
#     is needed for querying the network model.
#
#   * On output, the script generates a file "aut_diffmetrics.csv"
#     with the calculated metrics for each case. The file is left in
#     the same directory, together with the case files.
#
#
# NOTES: These are the metrics considered here. STRICT means the
# differences are calculated individually by matched device. RELAXED
# means it is calculated at the level of the whole bus, using some
# grouping heuristic (this is the case of Load-Transformers, because
# the the presence of merged loads in Dynawo precludes a comparison
# at the device level).
#
#   * For Transmission Transformer events "TapUp/TapDown": (STRICT)
#       - tap_netchanges: diffs in the amount of net change after transient
#       - tap_maxchanges: diffs in the amount of peak-to-peak change
#       - tap_numchanges: diffs in the total number of changes
#
#    * For Shunt events "ShuntConnected/ShuntDisconnected": (STRICT)
#       - shunt_netchanges: diffs in the amount of net change a. t. (binary)
#       - shunt_numchanges: diffs in the total number of changes
#
#    * For Load-Transformer events "TapUp/TapDown": (RELAXED)
#       - tap_netchanges_ltperbus: diffs in the amount of net change after transient
#
# In this last case, Load-Transformers, the heuristic is the
# following: calculate the "amount-of-net-change-after-transient" for
# each load-transformer on the same bus, and keep the abs(max()) as
# the value for the bus. Then compare each bus and apply the L1 norm.
#


import sys
import os
import glob
from collections import namedtuple
from pathlib import Path
import pandas as pd

# from lxml import etree


AST_SUFFIX = "-AstreAutomata.csv.xz"
DWO_SUFFIX = "-DynawoAutomata.csv.xz"

verbose = False
pd.set_option("display.max_rows", 10)


def main():

    if len(sys.argv) != 4:
        print("\nUsage: %s AUT_DIR PREFIX BASECASE\n" % sys.argv[0])
        return 2
    aut_dir = sys.argv[1]
    prefix = sys.argv[2]
    base_case = sys.argv[3]

    # Check all needed dirs are in place, and get the list of files to process
    file_list = check_inputfiles(aut_dir, prefix, base_case)
    print("Calculating diffmetrics for automata changes in: %s" % aut_dir)

    # For each case, compute the metrics
    metrics_rowdata = []
    for case_label in file_list:
        if verbose:
            print("   processing: " + prefix + case_label)
        ast_file = file_list[case_label].ast
        dwo_file = file_list[case_label].dwo
        metrics = calc_metrics(ast_file, dwo_file)
        if verbose:
            print("      ", metrics)
        metrics_rowdata.append({"contg_case": case_label, **metrics})

    # Save the metrics to file
    df = pd.DataFrame(metrics_rowdata, columns=list(metrics_rowdata[0].keys()))
    metrics_dir = aut_dir + "/../metrics"
    Path(metrics_dir).mkdir(parents=False, exist_ok=True)
    df.to_csv(metrics_dir + "/aut_diffmetrics.csv", sep=";", index=False)
    print("Saved diffmetrics for automata changes in: %s" % metrics_dir)

    return 0


def check_inputfiles(aut_dir, prefix, base_case):
    if not os.path.isdir(aut_dir):
        raise ValueError("input directory %s not found" % aut_dir)

    if not os.path.isdir(base_case):
        raise ValueError("basecase directory %s not found" % base_case)

    if not (
        os.path.isfile(base_case + "/Astre/donneesModelesEntree.xml")
        and os.path.isfile(base_case + "/tFin/fic_IIDM.xml")
        and os.path.isfile(base_case + "/tFin/fic_DYD.xml")
        and os.path.isfile(base_case + "/tFin/fic_PAR.xml")
        and os.path.isfile(base_case + "/tFin/fic_CRV.xml")
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
            raise ValueError("Dinawo data file not found for %s\n" % ast_file)
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
        print()

    return file_list


def calc_metrics(ast_file, dwo_file):
    ast_df = pd.read_csv(ast_file, sep=";")
    dwo_df = pd.read_csv(dwo_file, sep=";")

    xfmr_metrics = calc_xfmr_metrics(ast_df, dwo_df)
    shunt_metrics = calc_shunt_metrics(ast_df, dwo_df, dwo_file)

    return {**xfmr_metrics, **shunt_metrics}


#################################################
# TRANSFORMERS (only transmission transformers)
#################################################
def calc_xfmr_metrics(ast_df, dwo_df):
    # Shortcut: a vast majority of cases have no relevant events
    if ast_df.empty and dwo_df.empty:
        return {"tap_netchanges": 0, "tap_maxchanges": 0, "tap_numchanges": 0}

    # Auxiliary counts of Tap changer events
    rows = ["Transformer"]
    cols = ["DEVICE", "EVENT"]
    ast_taps_up = event_counts(ast_df, rows, cols, "TapUp")
    ast_taps_down = event_counts(ast_df, rows, cols, "TapDown")
    dwo_taps_up = event_counts(dwo_df, rows, cols, "TapUp")
    dwo_taps_down = event_counts(dwo_df, rows, cols, "TapDown")

    # Tap changer metric: "diff in net change" (STRICT)
    ast_netchanges = ast_taps_up.sub(ast_taps_down, fill_value=0)
    dwo_netchanges = dwo_taps_up.sub(dwo_taps_down, fill_value=0)
    netchange_diffs = ast_netchanges.sub(dwo_netchanges, fill_value=0)
    tap_netchanges_metric = netchange_diffs["EVENT"].abs().sum()  # L1 norm

    # Tap changer metric: "diff in peak-to-peak change" (STRICT)
    tap_maxchanges_metric = calc_tap_maxchanges_metric(ast_df, dwo_df)

    # Tap changer metric: "diff in the total number of changes" (STRICT)
    ast_numchanges = ast_taps_up.add(ast_taps_down, fill_value=0)
    dwo_numchanges = dwo_taps_up.add(dwo_taps_down, fill_value=0)
    numchange_diffs = ast_numchanges.sub(dwo_numchanges, fill_value=0)
    tap_numchanges_metric = numchange_diffs["EVENT"].abs().sum()  # L1 norm

    metrics = {
        "tap_netchanges": tap_netchanges_metric,
        "tap_maxchanges": tap_maxchanges_metric,
        "tap_numchanges": tap_numchanges_metric,
    }

    return metrics


#################################################
# SHUNTS
#################################################
def calc_shunt_metrics(ast_df, dwo_df, dwo_file):
    # Shortcut: a vast majority of cases have no relevant events
    if ast_df.empty and dwo_df.empty:
        return {"shunt_netchanges": 0, "shunt_numchanges": 0}

    # Auxiliary counts of Shunt connection/disconnection events
    rows = ["Shunt"]
    cols = ["DEVICE", "EVENT"]
    ast_shunts_on = event_counts(ast_df, rows, cols, "ShuntConnected")
    ast_shunts_off = event_counts(ast_df, rows, cols, "ShuntDisconnected")
    dwo_shunts_on = event_counts(dwo_df, rows, cols, "ShuntConnected")
    dwo_shunts_off = event_counts(dwo_df, rows, cols, "ShuntDisconnected")

    # Shunt metric: "diff in net change" (STRICT)
    ast_netchanges = ast_shunts_on.sub(ast_shunts_off, fill_value=0)
    dwo_netchanges = dwo_shunts_on.sub(dwo_shunts_off, fill_value=0)
    netchange_diffs = ast_netchanges.sub(dwo_netchanges, fill_value=0)
    shunt_netchanges_metric = netchange_diffs["EVENT"].abs().sum()  # L1 norm

    # Shunt metric: "diff in the total number of changes" (STRICT)
    ast_numchanges = ast_shunts_on.add(ast_shunts_off, fill_value=0)
    dwo_numchanges = dwo_shunts_on.add(dwo_shunts_off, fill_value=0)
    numchange_diffs = ast_numchanges.sub(dwo_numchanges, fill_value=0)
    shunt_numchanges_metric = numchange_diffs["EVENT"].abs().sum()  # L1 norm

    # We need to introduce a correction here: if the Dynawo case is a
    # Shunt contingency, then there is a ShuntDisconnected event in
    # the Dynawo timeline that does not have a counterpart in Astre
    # (the contingency shunt itself!). We correct this by subtracting
    # exactly 1 from each metric.
    filename = os.path.basename(dwo_file)
    if filename[:6] == "shunt_":
        shunt_netchanges_metric += -1
        shunt_numchanges_metric += -1

    metrics = {
        "shunt_netchanges": shunt_netchanges_metric,
        "shunt_numchanges": shunt_numchanges_metric,
    }

    return metrics


def event_counts(df, rows, cols, event):
    row_filter = df["DEVICE_TYPE"].isin(rows) & (df["EVENT"] == event)
    filtered_df = df.loc[row_filter, cols]
    counts_df = filtered_df.groupby(by="DEVICE", as_index=True).count()
    return counts_df


def calc_tap_maxchanges_metric(ast_df, dwo_df):
    # This "peak-to-peak" change cannot be calculated via vector
    # operations, since the detection of such peaks can only be done
    # by following the sequence of changes. We have to do it via a
    # good-old loop.

    # Filter for transmission transformers
    rows = ["Transformer"]
    cols = ["DEVICE", "TIME", "EVENT"]
    row_filter = ast_df["DEVICE_TYPE"].isin(rows)
    ast_xfmrs = ast_df.loc[row_filter, cols]
    row_filter = dwo_df["DEVICE_TYPE"].isin(rows)
    dwo_xfmrs = dwo_df.loc[row_filter, cols]

    # Don't trust that the input is sorted by time; do it just in case
    sort_fields = ["DEVICE", "TIME"]
    sort_order = [True, True]
    ast_xfmrs = ast_xfmrs.sort_values(
        by=sort_fields, ascending=sort_order, inplace=False, na_position="first"
    )
    dwo_xfmrs = dwo_xfmrs.sort_values(
        by=sort_fields, ascending=sort_order, inplace=False, na_position="first"
    )

    # Now follow the sequences and catch min & max peaks
    ast_devices = ast_xfmrs["DEVICE"].unique()
    dwo_devices = dwo_xfmrs["DEVICE"].unique()
    devices = list(set(ast_devices) | set(dwo_devices))
    devices.sort()

    tap_maxchanges_metric = 0
    for dev in devices:
        ast_dev_events = ast_xfmrs.loc[
            (ast_xfmrs["DEVICE"] == dev), "EVENT"
        ].values.tolist()
        dwo_dev_events = dwo_xfmrs.loc[
            (dwo_xfmrs["DEVICE"] == dev), "EVENT"
        ].values.tolist()
        # Using the L1 norm
        tap_maxchanges_metric += abs(
            peak2peak(ast_dev_events, ["TapUp", "TapDown"])
            - peak2peak(dwo_dev_events, ["TapUp", "TapDown"])
        )

    return tap_maxchanges_metric


def peak2peak(events, binary_event_names):
    # Only contemplates events of type plus--minus (i.e. taps and shunts)
    plus = binary_event_names[0]
    minus = binary_event_names[1]
    max_peak = 0
    min_peak = 0
    curve = 0
    for event in events:
        if event == plus:
            curve = curve + 1
            max_peak = max(curve, max_peak)
        elif event == minus:
            curve = curve - 1
            min_peak = min(curve, min_peak)

    return max_peak - min_peak


if __name__ == "__main__":
    sys.exit(main())
