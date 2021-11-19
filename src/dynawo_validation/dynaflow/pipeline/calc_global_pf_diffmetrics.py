#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
#

import glob
import pandas as pd
from tqdm import tqdm
import sys
from pathlib import Path
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument(
    "pfsoldir",
    help="PF_SOL_DIR directory",
)

parser.add_argument(
    "prefix",
    help="Contingency prefix",
)

parser.add_argument(
    "isout",
    help="The output is redirected to txt or not",
)
args = parser.parse_args()


def main():
    # Parameter management
    PF_SOL_DIR = args.pfsoldir

    PREFIX = args.prefix

    files = list(glob.iglob(PF_SOL_DIR + "/" + PREFIX + "*-pfsolution_AB.csv.xz"))
    print(f"Processing {len(files)} cases.")
    res = []

    PF_METRICS_DIR = PF_SOL_DIR + "/../pf_metrics"

    Path(PF_METRICS_DIR).mkdir(parents=False, exist_ok=True)

    if args.isout == "0":
        for filepath in tqdm(files):
            # Depending on the path
            # cont = filepath.split('_')[3].split('-')[0]
            cont = filepath.split("_")[2].split("-")[0]
            # print(cont)
            delta = pd.read_csv(filepath, sep=";", index_col=False, compression="infer")
            delta["DIFF"] = delta.VALUE_A - delta.VALUE_B
            delta_max = delta.groupby("VAR").max()
            delta_mean = delta.groupby("VAR").mean()
            res1 = (
                [cont]
                + ["ALL"]
                + list(delta_max["DIFF"].values)
                + list(delta_mean["DIFF"].values)
            )
            res = res + [res1]
            volt_levels = np.sort(delta["VOLT_LEVEL"].unique())
            for volt_level in volt_levels:
                temp_df = delta.loc[(delta.VOLT_LEVEL == volt_level)]
                temp_df_max = temp_df.groupby("VAR").max()
                temp_df_mean = temp_df.groupby("VAR").mean()
                res2 = (
                    [cont]
                    + [str(volt_level)]
                    + list(temp_df_max["DIFF"].values)
                    + list(temp_df_mean["DIFF"].values)
                )
                res = res + [res2]
    else:
        for filepath in files:
            # Depending on the path
            # cont = filepath.split('_')[3].split('-')[0]
            cont = filepath.split("_")[2].split("-")[0]
            # print(cont)
            delta = pd.read_csv(filepath, sep=";", index_col=False, compression="infer")
            delta["DIFF"] = delta.VALUE_A - delta.VALUE_B
            delta_max = delta.groupby("VAR").max()
            delta_mean = delta.groupby("VAR").mean()
            res1 = (
                [cont]
                + ["ALL"]
                + list(delta_max["DIFF"].values)
                + list(delta_mean["DIFF"].values)
            )
            res = res + [res1]
            volt_levels = np.sort(delta["VOLT_LEVEL"].unique())
            for volt_level in volt_levels:
                temp_df = delta.loc[(delta.VOLT_LEVEL == volt_level)]
                temp_df_max = temp_df.groupby("VAR").max()
                temp_df_mean = temp_df.groupby("VAR").mean()
                res2 = (
                    [cont]
                    + [str(volt_level)]
                    + list(temp_df_max["DIFF"].values)
                    + list(temp_df_mean["DIFF"].values)
                )
                res = res + [res2]

    df = pd.DataFrame(
        res,
        columns=["cont"]
        + ["volt_level"]
        + list(delta_max.index + "_max")
        + list(delta_mean.index + "_mean"),
    )
    df.to_csv(PF_METRICS_DIR + "/metrics.csv.xz", compression="xz")

    return 0


if __name__ == "__main__":
    sys.exit(main())
