#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
# In this script, the necessary calculations are performed to find the largest
# differences between the two cases executed and through the top 10 of several
# metrics, we can see the contingencies that diverge the most between the two simulators.
#
# top_10_diffs.py
#

import os
import random
import re
import sys
import pandas as pd
import argparse
import copy


parser = argparse.ArgumentParser()
parser.add_argument(
    "crv_reducedparams_dir", help="enter crv_reducedparams_dir directory"
)
args = parser.parse_args()


def main():
    # Display format
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)

    # Argument management
    crv_reducedparams_dir = args.crv_reducedparams_dir

    # Reading the cases and organizing the values ​​according to the different metrics
    # Removing columns that are not part of the selected metric
    data = read_case(crv_reducedparams_dir)
    
    data = data.rename(columns={"dev":"CONTG_CASE"})

    datafirstfalse = data.loc[
        (data.is_preStab_ast == "False") | (data.is_preStab_dwo == "False")
    ]
    datafirstfalsesorted = datafirstfalse.sort_values("CONTG_CASE", ascending=False)
    datafirstfalsesorted = datafirstfalsesorted.drop(
        [
            "dPP_ast",
            "dPP_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "dSS_ast",
            "dSS_dwo",
        ],
        axis=1,
    )

    datafinalfalse = data.loc[
        (data.is_postStab_ast == "False") | (data.is_postStab_dwo == "False")
    ]
    datafinalfalsesorted = datafinalfalse.sort_values("CONTG_CASE", ascending=False)
    datafinalfalsesorted = datafinalfalsesorted.drop(
        [
            "dPP_ast",
            "dPP_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "dSS_ast",
            "dSS_dwo",
        ],
        axis=1,
    )

    data_U_IMPIN_value = copy.deepcopy(data)
    data_U_IMPIN_value["DIFF_dSS_U_IMPIN"] = (
        data_U_IMPIN_value["dSS_ast"] - data_U_IMPIN_value["dSS_dwo"]
    ).abs()
    data_U_IMPIN_value_fil = data_U_IMPIN_value.loc[
        lambda x: x["vars"].str.contains(r"U_IMPIN_value", regex=True)
    ]
    data_U_IMPIN_valuesorted = data_U_IMPIN_value_fil.sort_values(
        "DIFF_dSS_U_IMPIN", ascending=False
    )
    data_U_IMPIN_valuesorted = data_U_IMPIN_valuesorted.drop(
        [
            "dPP_ast",
            "dPP_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "is_crv_time_matching",
        ],
        axis=1,
    )

    data_levelK_value = copy.deepcopy(data)
    data_levelK_value["DIFF_dPP_levelK"] = (
        data_levelK_value["dPP_ast"] - data_levelK_value["dPP_dwo"]
    ).abs()
    data_levelK_value_fil = data_levelK_value.loc[
        lambda x: x["vars"].str.contains(r"levelK_value", regex=True)
    ]
    data_levelK_valuesorted = data_levelK_value_fil.sort_values(
        "DIFF_dPP_levelK", ascending=False
    )
    data_levelK_valuesorted = data_levelK_valuesorted.drop(
        [
            "dSS_ast",
            "dSS_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "is_crv_time_matching",
        ],
        axis=1,
    )

    PGen_value = copy.deepcopy(data)
    PGen_value["DIFF_dSS_PGen"] = (PGen_value["dSS_ast"] - PGen_value["dSS_dwo"]).abs()
    PGen_value_fil = PGen_value.loc[
        lambda x: x["vars"].str.contains(r"_PGen", regex=True)
    ]
    PGen_valuesorted = PGen_value_fil.sort_values("DIFF_dSS_PGen", ascending=False)
    PGen_valuesorted = PGen_valuesorted.drop(
        [
            "dPP_ast",
            "dPP_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "is_crv_time_matching",
        ],
        axis=1,
    )

    QGen_value = copy.deepcopy(data)
    QGen_value["DIFF_dSS_QGen"] = (QGen_value["dSS_ast"] - QGen_value["dSS_dwo"]).abs()
    QGen_value_fil = QGen_value.loc[
        lambda x: x["vars"].str.contains(r"_QGen", regex=True)
    ]
    QGen_valuesorted = QGen_value_fil.sort_values("DIFF_dSS_QGen", ascending=False)
    QGen_valuesorted = QGen_valuesorted.drop(
        [
            "dPP_ast",
            "dPP_dwo",
            "TT_ast",
            "TT_dwo",
            "period_ast",
            "period_dwo",
            "damp_ast",
            "damp_dwo",
            "is_preStab_ast",
            "is_preStab_dwo",
            "is_postStab_ast",
            "is_postStab_dwo",
            "is_crv_time_matching",
        ],
        axis=1,
    )

    # Display the results
    print("START STABLE CONTG\n")
    print(datafirstfalsesorted[:10].to_string(index=False))
    print("\n\nFINAL STABLE CONTG\n")
    print(datafinalfalsesorted[:10].to_string(index=False))
    print("\n\nDIFF dSS U_IMPIN_value\n")
    print(data_U_IMPIN_valuesorted[:10].to_string(index=False))
    print("\n\nDIFF dPP levelK_value\n")
    print(data_levelK_valuesorted[:10].to_string(index=False))
    print("\n\nDIFF dSS PGen\n")
    print(PGen_valuesorted[:10].to_string(index=False))
    print("\n\nDIFF dSS QGen\n")
    print(QGen_valuesorted[:10].to_string(index=False))


# Read a specific contingency
def read_case(crv_reducedparams_dir):
    data = pd.read_csv(
        crv_reducedparams_dir, sep=";", index_col=False, compression="infer"
    )
    return data


if __name__ == "__main__":
    sys.exit(main())
