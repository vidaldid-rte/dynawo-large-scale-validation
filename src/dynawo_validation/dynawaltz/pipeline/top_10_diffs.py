#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# top_10_diffs.py
#

import os
import random
import re
import sys
import pandas as pd
from frozendict import frozendict
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("crv_reduced_params", help="enter crv_reduced_params directory")
parser.add_argument("results_dir", help="enter results_dir directory")
args = parser.parse_args()


def main():
    delta = pd.read_csv(args.crv_reduced_params)
    delta.fillna(-1, inplace=True)
    '''
    delta["typevar"] = ""
    delta.loc[delta.vars.str.contains("_U_IMPIN"), "typevar"] = "V"
    delta.loc[delta.vars.str.contains("_Upu_"), "typevar"] = "V"
    delta.loc[delta.vars.str.contains("_levelK_"), "typevar"] = "K"
    delta.loc[delta.vars.str.contains("_PGen"), "typevar"] = "P"
    delta.loc[delta.vars.str.contains("_QGen"), "typevar"] = "Q"
    d_threshold = {"V": V_THRESH, "K": K_THRESH, "P": P_THRESH, "Q": Q_THRESH}
    delta["threshold"] = delta.typevar.replace(d_threshold)
    delta["delta_dSS"] = delta["dSS_ast"] - delta["dSS_dwo"]
    delta["dSS_pass"] = delta.delta_dSS.abs() < delta.threshold
    delta["delta_dPP"] = delta["dPP_ast"] - delta["dPP_dwo"]
    delta["dPP_pass"] = delta.delta_dPP.abs() < delta.threshold
    
    scores = delta[
        [
            "dev",
            "vars",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "dSS_pass",
            "dPP_pass",
        ]
    ].copy()
    scores.columns = [
        "Contg_case",
        "Variable",
        "pre_ast",
        "pre_dwo",
        "post_ast",
        "post_dwo",
        "dSS_pass",
        "dPP_pass",
    ]
    scores["global_crv"] = 0
    metrics = ["dSS", "dPP", "TT", "period", "damp"]
    wmetric = [0.6, 0.2, 0.1, 0.05, 0.05]
    for metr in metrics:
        scores[metr] = (delta[metr + "_ast"] - delta[metr + "_dwo"]) / abs(
            delta[[metr + "_ast", metr + "_dwo"]].abs().max(axis=1)
        )
    scores = scores.fillna(0)
    for i, metr in enumerate(metrics):
        scores["global_crv"] += abs(scores[metr]) * wmetric[i]

    scores = scores.set_index(["Contg_case", "Variable"])
    '''
    file=open(args.results_dir + "top_10_errors.txt", "w+")
    file.write(str(scores[:15]))
        
    '''datasorteddiff = data.sort_values("DIFF", ascending=False)
    pd.get_option("display.max_columns")
    
    print("TOP 10 VALUES OF POSITIVE DIFF") 
    print()
    print(datasorteddiff[:10])
    print()
    print("TOP 10 VALUES OF NEGATIVE DIFF") 
    print()
    print(datasorteddiff[-10:])

    datasortedabs = data.sort_values("ABS_ERR", ascending=False)

    print()
    print("TOP 10 VALUES OF ABS_ERR") 
    print()
    print(datasortedabs[:10])

    datasortedrel = data.sort_values("REL_ERR", ascending=False)
 
    print()
    print("TOP 10 VALUES OF REL_ERR") 
    print()
    print(datasortedrel[:10])

    file=open(args.results_dir+ args.prefix + "-top_10_errors.txt", "w+")

    file.write("TOP 10 VALUES OF POSITIVE DIFF\n")
    file.write(str(datasorteddiff[:10]))
    file.write("\n\nTOP 10 VALUES OF NEGATIVE DIFF\n")
    file.write(str(datasorteddiff[-10:]))

    file.write("TOP 10 VALUES OF ABS_ERR\n")
    file.write(str(datasortedabs[:10]))
    file.write("\n\nTOP 10 VALUES OF REL_ERR\n")
    file.write(str(datasortedrel[:10]))
    file.close()
    '''
    

if __name__ == "__main__":
    sys.exit(main())
