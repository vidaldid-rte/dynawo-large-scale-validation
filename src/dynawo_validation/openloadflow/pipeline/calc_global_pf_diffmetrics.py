#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# adapted from the dynaflow pipeline
#
#

import glob
import math
import os.path

import pandas as pd
import sys
from pathlib import Path
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("pfsoldir", help="PF_SOL_DIR directory")
parser.add_argument("prefix", help="Contingency prefix")
parser.add_argument("--filter", help="enter fitler file", default=None)
args = parser.parse_args()

def read_filter(filter_file) :
    file = open(filter_file, 'r')
    return [l.strip() for l in file.readlines()]
def main():
    PF_SOL_DIR = args.pfsoldir
    PREFIX = args.prefix

    PF_METRICS_DIR = PF_SOL_DIR + "/../pf_metrics"
    Path(PF_METRICS_DIR).mkdir(parents=False, exist_ok=True)

    filter_file = args.filter

    filters = read_filter(filter_file) if filter_file is not None else []

    all_tap_score = []
    noconv= []
    res = []
    files = list(glob.iglob(PF_SOL_DIR + "/" + PREFIX + "*_pfsolutionHO.csv.xz"))
    print(f"Processing {len(files)} cases: ", end="", flush=True)

    for filepath in files:
        contg = filepath.split("/")[-1].split("#")[-1].split("_pfsolution")[-2]
        delta = pd.read_csv(filepath, sep=";", index_col=False, compression="infer")
        score_filepath= filepath[:-len("pfsolutionHO.csv.xz")] + "tapScore.csv"
        tap_score = pd.read_csv(score_filepath, sep=";", index_col=False)
        tap_score.insert(0, "contg", contg)

        if len(filters) > 0:
            delta.drop(delta[delta['ID'].isin(filters)].index, inplace = True)

        all_tap_score.append(tap_score)

        status_df = delta[delta.ID == "status#code"]
        if status_df.iloc[0]["VALUE_OLF"] > 0 and status_df.iloc[0]["VALUE_HADES"] > 0:
            noconv.append([contg,
                           status_df.iloc[0]["VALUE_HADES"],
                           status_df.iloc[0]["VALUE_OLF"]])
            # Both solver failed - no data
            continue


        delta["DIFF"] = delta.VALUE_HADES - delta.VALUE_OLF
        delta["DIFF_ABS"] = abs(delta.VALUE_HADES - delta.VALUE_OLF)
        delta_mean = delta.groupby("VAR").mean(numeric_only=True).sort_values("VAR")
        delta_p95 = delta.groupby("VAR").quantile(0.95, numeric_only=True).sort_values("VAR")
        delta_max = delta.groupby("VAR").max(numeric_only=True).sort_values("VAR")

        res1 = (
                [contg]
                + ["ALL"]
                + delta_max["DIFF_ABS"].to_list()
                + delta_p95["DIFF_ABS"].to_list()
                + delta_mean["DIFF_ABS"].to_list()
        )
        res = res + [res1]

        volt_levels = np.sort(delta["VOLT_LEVEL"].unique())

        for volt_level in volt_levels:
            if math.isnan(volt_level):
                continue
            delta_vl = delta[delta.VOLT_LEVEL == volt_level].copy().reset_index()
            # Ensure there is at least a Nan for all VARs to make sure we have the right number of aggregates
            for VAR in delta.VAR.unique():
                delta_vl.loc[len(delta_vl)] = [None] * delta_vl.shape[1]
                delta_vl.at[len(delta_vl) - 1, "VAR"] = VAR
                delta_vl.at[len(delta_vl) - 1, "VOLT_LEVEL"] = volt_level

            delta_vl_mean = delta_vl.groupby("VAR").mean(numeric_only=True).sort_values("VAR")
            delta_vl_p95 = delta_vl.groupby("VAR").quantile(0.95, numeric_only=True).sort_values("VAR")
            delta_vl_max = delta_vl.groupby("VAR").max(numeric_only=True).sort_values("VAR")

            res2 = (
                [contg]
                + [str(volt_level)]
                + delta_vl_max["DIFF_ABS"].to_list()
                + delta_vl_p95["DIFF_ABS"].to_list()
                + delta_vl_mean["DIFF_ABS"].to_list()
            )
            res = res + [res2]

        # (end of main for loop, file processed)
        print(".", end="", flush=True)

    print(" Done", end="", flush=True)

    df = pd.DataFrame(
        res,
        columns=["contg_case"]
        + ["volt_level"]
        + list(delta_max.index + "_max")
        + list(delta_p95.index + "_p95")
        + list(delta_mean.index + "_mean"),
    )
    fileName = os.path.join(PF_METRICS_DIR, "metrics.csv.xz")
    df.to_csv(fileName, compression="xz")

    all_tap_score_df = pd.concat(all_tap_score, ignore_index=True)
    all_tap_score_df.insert(1, "warning", None)
    all_tap_score_df.warning=(all_tap_score_df.max_tap_diff > 1).astype(int) + \
        (all_tap_score_df.nb_tap_diff > all_tap_score_df.computed_tap*0.11).astype(int) + \
        (all_tap_score_df.max_q1_diff >= 10).astype(int) + \
        (all_tap_score_df.q1_2_count > 5 * all_tap_score_df.nb_tap_diff).astype(int) + \
        (all_tap_score_df.max_p1_diff >= 2).astype(int)
    all_tap_score_df.sort_values(by=["warning"], inplace=True, ascending=False)
    all_tap_score_df.to_csv(os.path.join(PF_METRICS_DIR, "tap_score.csv"))

    noconv_df = pd.DataFrame(noconv, columns=["contg_case", "VALUE_HADES", "VALUE_OLF"])
    fileName = os.path.join(PF_METRICS_DIR, "noconv.csv.xz")
    noconv_df.to_csv(fileName, compression="xz")

    print(" (saved to file OK).", fileName)

    return 0


if __name__ == "__main__":
    sys.exit(main())
