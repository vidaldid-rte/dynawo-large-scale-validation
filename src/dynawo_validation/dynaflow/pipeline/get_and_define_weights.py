#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
import os
import pandas as pd
import argparse
import sys


parser = argparse.ArgumentParser()
parser.add_argument(
    "-w",
    "--weights",
    help="enter file to define weights",
)
parser.add_argument(
    "save_dir",
    help="Enter the dir to save weights",
)

args = parser.parse_args()

# Default weights and thresholds to be used for compound scoring.
# These will be overriden by the user-provided ones, if any.
W_V = 1 / 2
W_P = 1 / 5
W_Q = 1 / 10
W_T = 1 / 3
MAX_THRESH = 25
P95_THRESH = 0.8
MEAN_THRESH = 0.05


def main():
    save_dir = args.save_dir
    if save_dir[-1] != "/":
        save_dir = save_dir + "/"

    weights_dict = {
        "W_V": W_V,
        "W_P": W_P,
        "W_Q": W_Q,
        "W_T": W_T,
        "MAX_THRESH": MAX_THRESH,
        "P95_THRESH": P95_THRESH,
        "MEAN_THRESH": MEAN_THRESH,
    }
    if args.weights:
        with open(args.weights) as f:
            weights_list = [x for x in f.read().split(os.linesep)]
        for w in weights_list:
            if len(w) > 0 and w[0] != "#":
                w_temp_split = w.replace(" ", "").split("=")
                if w_temp_split[0] in weights_dict.keys():
                    weights_dict[w_temp_split[0]] = float(w_temp_split[1])

    for key, value in weights_dict.items():
        print(key + " = " + str(value))

    df_weights = pd.DataFrame(weights_dict, index=[0])
    df_weights.to_csv(save_dir + "score_weights.csv", sep=";")


if __name__ == "__main__":
    sys.exit(main())
