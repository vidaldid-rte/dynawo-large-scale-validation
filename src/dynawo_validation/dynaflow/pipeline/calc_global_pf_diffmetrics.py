#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
#

import glob
import pandas as pd
import sys
from pathlib import Path
import argparse
import numpy as np

# Note: in the calculation of the p95 metrics, some aggregate
# functions on GroupBy objects raise a "future deprecation"
# warning. We suppress the warning for now, but it should be fixed by
# finding an alternative way to calculate the same thing.
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

parser = argparse.ArgumentParser()
parser.add_argument("pfsoldir", help="PF_SOL_DIR directory")
parser.add_argument("prefix", help="Contingency prefix")
args = parser.parse_args()


def main():
    PF_SOL_DIR = args.pfsoldir
    PREFIX = args.prefix

    PF_METRICS_DIR = PF_SOL_DIR + "/../pf_metrics"
    Path(PF_METRICS_DIR).mkdir(parents=False, exist_ok=True)

    res = []
    files = list(glob.iglob(PF_SOL_DIR + "/" + PREFIX + "*_pfsolutionAB.csv.xz"))
    print(f"Processing {len(files)} cases: ", end="", flush=True)

    for filepath in files:
        contg = filepath.split("#")[-1].split("_pfsolution")[-2]
        delta = pd.read_csv(filepath, sep=";", index_col=False, compression="infer")
        delta["DIFF"] = delta.VALUE_A - delta.VALUE_B

        max_dict = {
            "angle": None,
            "p": None,
            "p1": None,
            "p2": None,
            "pstap": None,
            "q": None,
            "q1": None,
            "q2": None,
            "tap": None,
            "v": None,
        }

        # Get abs max value with sign
        temp_var = list(delta["VAR"])
        temp_diff = list(delta["DIFF"])
        for i in range(len(delta.index)):
            x = temp_var[i]
            y = temp_diff[i]
            if max_dict[x] is None:
                max_dict[x] = y
            else:
                if abs(max_dict[x]) < abs(y):
                    max_dict[x] = y

        temp_df_max_list = []
        for i in max_dict.values():
            temp_df_max_list.append(i)

        delta_mean = delta.groupby("VAR").mean()
        # FIXME: find a workaround for Panda's future deprecation
        # warning that raises here:
        delta_p95 = delta.groupby("VAR").quantile(0.95)
        res1 = (
            [contg]
            + ["ALL"]
            + list(temp_df_max_list)
            + list(delta_p95["DIFF"].values)
            + list(delta_mean["DIFF"].values)
        )
        res = res + [res1]

        volt_levels = np.sort(delta["VOLT_LEVEL"].unique())

        for volt_level in volt_levels:
            index_list = [
                "angle",
                "p",
                "p1",
                "p2",
                "pstap",
                "q",
                "q1",
                "q2",
                "tap",
                "v",
            ]
            max_dict = {
                "angle": None,
                "p": None,
                "p1": None,
                "p2": None,
                "pstap": None,
                "q": None,
                "q1": None,
                "q2": None,
                "tap": None,
                "v": None,
            }
            temp_df = delta.loc[(delta.VOLT_LEVEL == volt_level)]

            # Get abs max value with sign
            temp_var = list(temp_df["VAR"])
            temp_diff = list(temp_df["DIFF"])
            for i in range(len(temp_df.index)):
                x = temp_var[i]
                y = temp_diff[i]
                if max_dict[x] is None:
                    max_dict[x] = y
                else:
                    if abs(max_dict[x]) < abs(y):
                        max_dict[x] = y

            temp_df_max_list = []
            for i in max_dict.values():
                temp_df_max_list.append(i)

            # temp_df_max = temp_df.groupby("VAR").max({"key": "abs"})
            temp_df_mean = temp_df.groupby("VAR").mean()
            temp_df_p95 = temp_df.groupby("VAR").quantile(0.95)
            real_index_list = list(temp_df_mean.index.values)
            # temp_df_max_dict = temp_df_max.to_dict("list")
            temp_df_mean_dict = temp_df_mean.to_dict("list")
            temp_df_p95_dict = temp_df_p95.to_dict("list")
            for i in range(len(index_list)):
                if index_list[i] == real_index_list[i]:
                    pass
                else:
                    real_index_list.insert(i, index_list[i])
                    # temp_df_max_dict["DIFF"].insert(i, None)
                    temp_df_p95_dict["DIFF"].insert(i, None)
                    temp_df_mean_dict["DIFF"].insert(i, None)

            # temp_df_max_list = list(temp_df_max_dict["DIFF"])
            temp_df_p95_list = list(temp_df_p95_dict["DIFF"])
            temp_df_mean_list = list(temp_df_mean_dict["DIFF"])

            res2 = (
                [contg]
                + [str(volt_level)]
                + temp_df_max_list
                + temp_df_p95_list
                + temp_df_mean_list
            )
            res = res + [res2]

        # (end of main for loop, file processed)
        print(".", end="", flush=True)

    print(" Done", end="", flush=True)

    df = pd.DataFrame(
        res,
        columns=["contg_case"]
        + ["volt_level"]
        + list(delta_mean.index + "_max")  # We assume that they have the same vars
        + list(delta_p95.index + "_p95")
        + list(delta_mean.index + "_mean"),
    )
    df.to_csv(PF_METRICS_DIR + "/metrics.csv.xz", compression="xz")
    print(" (saved to file OK).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
