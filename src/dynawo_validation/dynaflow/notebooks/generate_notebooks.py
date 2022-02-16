#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
#
# generate_notebooks.py: a simple script to generate a Notebook per CASE. You only
# need to provide the base directory that contains the cases that have been run.
#

import sys
import argparse
import os
from pathlib import Path
import re
import pandas as pd

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("case_dir", help="enter case directory")
parser.add_argument("base_case", help="enter base case directory")
parser.add_argument("contg_type", help="enter contingency type")
parser.add_argument("csv_weights", help="enter csv to extract weights")

args = parser.parse_args()


def is_dwohds(case):
    """Return true if an Hades subdirectory exists (Dynawo-vs-Hades case)"""
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Case directory %s not found" % casedir)
    return os.path.isdir(casedir / "Hades")


def is_dwodwo(case):
    """Return true if one JOB_A and one JOB_B files exist (Dynawo-vs-Dynawo case)"""
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Case directory %s not found" % casedir)
    jobfile_patternA = re.compile(r"JOB_A.*?\.xml$", re.IGNORECASE)
    match_A = [n for n in os.listdir(casedir) if jobfile_patternA.search(n)]
    jobfile_patternB = re.compile(r"JOB_B.*?\.xml$", re.IGNORECASE)
    match_B = [n for n in os.listdir(casedir) if jobfile_patternB.search(n)]
    return len(match_A) == 1 and len(match_B) == 1


def get_weights(csv_weights):
    df_weights = pd.read_csv(csv_weights, sep=";")
    w_V = df_weights["W_V"].to_list()[0]
    w_P = df_weights["W_P"].to_list()[0]
    w_Q = df_weights["W_Q"].to_list()[0]
    w_T = df_weights["W_T"].to_list()[0]
    max_THRESH = df_weights["MAX_THRESH"].to_list()[0]
    p95_THRESH = df_weights["P95_THRESH"].to_list()[0]
    mean_THRESH = df_weights["MEAN_THRESH"].to_list()[0]

    return w_V, w_P, w_Q, w_T, max_THRESH, p95_THRESH, mean_THRESH


def main():
    case_dir = args.case_dir
    base_case = args.base_case
    contg_type = args.contg_type
    csv_weights = args.csv_weights
    w_V, w_P, w_Q, w_T, max_THRESH, p95_THRESH, mean_THRESH = get_weights(csv_weights)

    if is_dwohds(base_case):
        dwo_dwo = "0"
    elif is_dwodwo(base_case):
        dwo_dwo = "1"
    else:
        raise ValueError(f"Case {base_case} is neither an dwo-hds nor a dwo-dwo case")

    if contg_type[-1] == "_":
        contg_type = contg_type[:-1]
    if base_case[-1] == "/":
        base_case = base_case[:-1]
    if case_dir[-1] != "/":
        case_dir = case_dir + "/"

    fin = open(sys.path[0] + "/simulator_A_vs_simulator_B.ipynb", "rt")
    # output file to write the result to
    fout = open(sys.path[0] + "/simulator_A_vs_simulator_B_final.ipynb", "wt")
    # for each line in the input file
    for line in fin:
        # read replace the string and write to output file
        if "PLACEHOLDER_RESULTS_DIR" in line:
            fout.write(line.replace("PLACEHOLDER_RESULTS_DIR", case_dir))
        elif "PLACEHOLDER_BASECASE" in line:
            fout.write(line.replace("PLACEHOLDER_BASECASE", base_case))
        elif "PLACEHOLDER_PREFIX" in line:
            fout.write(line.replace("PLACEHOLDER_PREFIX", contg_type))
        elif "PLACEHOLDER_DWO_DWO" in line:
            fout.write(line.replace("PLACEHOLDER_DWO_DWO", dwo_dwo))
        elif "PLACEHOLDER_W_V" in line:
            fout.write(line.replace("PLACEHOLDER_W_V", str(w_V)))
        elif "PLACEHOLDER_W_P" in line:
            fout.write(line.replace("PLACEHOLDER_W_P", str(w_P)))
        elif "PLACEHOLDER_W_Q" in line:
            fout.write(line.replace("PLACEHOLDER_W_Q", str(w_Q)))
        elif "PLACEHOLDER_W_T" in line:
            fout.write(line.replace("PLACEHOLDER_W_T", str(w_T)))
        elif "PLACEHOLDER_MAX_THRESH" in line:
            fout.write(line.replace("PLACEHOLDER_MAX_THRESH", str(max_THRESH)))
        elif "PLACEHOLDER_P95_THRESH" in line:
            fout.write(line.replace("PLACEHOLDER_P95_THRESH", str(p95_THRESH)))
        elif "PLACEHOLDER_MEAN_THRESH" in line:
            fout.write(line.replace("PLACEHOLDER_MEAN_THRESH", str(mean_THRESH)))
        else:
            fout.write(line)
    # close input and output files
    fin.close()
    fout.close()


if __name__ == "__main__":
    sys.exit(main())
