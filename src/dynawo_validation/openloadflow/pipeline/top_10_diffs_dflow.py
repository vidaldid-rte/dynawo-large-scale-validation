#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# adapted from dynaflow/top_10_diffs_dflow.py
#
# In this script, the necessary calculations are performed to find the largest
# differences between the two cases executed and through the top 10 of several
# metrics, we can see the contingencies that diverge the most between the two
# simulators.
#
# top_10_diffs.py
#

import os
import re
import sys
import pandas as pd
import argparse
from dynawo_validation.dynaflow.pipeline.common_funcs import calc_global_score


parser = argparse.ArgumentParser()
parser.add_argument("pf_solutions_dir", help="enter pf_solutions_dir directory")
parser.add_argument("pf_metrics_dir", help="enter pf_metrics_dir directory")
parser.add_argument("--regex", nargs="+", help="enter prefix name", default=[".*"])
parser.add_argument("--filter", help="enter fitler file", default=None)
args = parser.parse_args()

def read_filter(filter_file) :
    file = open(filter_file, 'r')
    return [l.strip() for l in file.readlines()]


def main():
    # display format
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)

    # argument management
    pf_solutions_dir = args.pf_solutions_dir

    filter_file = args.filter

    filters = read_filter(filter_file) if filter_file is not None else []

    if pf_solutions_dir[-1] != "/":
        pf_solutions_dir = pf_solutions_dir + "/"

    pf_metrics_dir = args.pf_metrics_dir

    if pf_metrics_dir[-1] != "/":
        pf_metrics_dir = pf_metrics_dir + "/"

    data_files = os.listdir(pf_solutions_dir)
    first_iteration = True

    # regex list
    data_files_list = []
    for i in data_files:
        for j in args.regex:
            if i not in data_files_list and re.match(j + "_pfsolutionHO.csv.xz", i):
                data_files_list.append(i)

    convergence_mismatch = []
    noconv=[]
    databusvoltsortedabstotal = None
    databusvoltsortedreltotal = None
    databranchpsortedabstotal = None
    databranchpsortedreltotal = None
    databuspsortedabstotal = None
    databuspsortedreltotal = None
    databusqsortedabstotal = None
    databusqsortedreltotal = None
    databranchqsortedabstotal = None
    databranchqsortedreltotal = None
    for i in data_files_list:

        # Reading the cases and ordering the values according to the metrics
        data = read_case(pf_solutions_dir + i)
        if len(filters) > 0:
            data.drop(data[data['ID'].isin(filters)].index, inplace = True)

        split_contg = i[:-20].split("#")[-1]
        data.insert(0, "CONTG_ID", split_contg)

        databusvolt = data.loc[(data.VAR == "v") & (data.ELEMENT_TYPE == "bus")]
        databusvoltsortedabs = databusvolt.sort_values("ABS_ERR", ascending=False)
        databusvoltsortedrel = databusvolt.sort_values("REL_ERR", ascending=False)
        databusvoltsortedabstotal = add_top_ten(databusvoltsortedabs, databusvoltsortedabstotal)
        databusvoltsortedreltotal = add_top_ten(databusvoltsortedrel, databusvoltsortedreltotal)

        databranchp = data.loc[
            ((data.VAR == "p1") | (data.VAR == "p2")) & (data.ELEMENT_TYPE != "bus")
            ]
        databranchpsortedabs = databranchp.sort_values("ABS_ERR", ascending=False)
        databranchpsortedrel = databranchp.sort_values("REL_ERR", ascending=False)
        databranchpsortedabstotal = add_top_ten(databranchpsortedabs, databranchpsortedabstotal)
        databranchpsortedreltotal = add_top_ten(databranchpsortedrel, databranchpsortedreltotal)

        databusp = data.loc[(data.VAR == "p") & (data.ELEMENT_TYPE == "bus")]
        databuspsortedabs = databusp.sort_values("ABS_ERR", ascending=False)
        databuspsortedrel = databusp.sort_values("REL_ERR", ascending=False)
        databuspsortedabstotal = add_top_ten(databuspsortedabs, databuspsortedabstotal)
        databuspsortedreltotal = add_top_ten(databuspsortedrel, databuspsortedreltotal)

        databusq = data.loc[(data.VAR == "q") & (data.ELEMENT_TYPE == "bus")]
        databusqsortedabs = databusq.sort_values("ABS_ERR", ascending=False)
        databusqsortedrel = databusq.sort_values("REL_ERR", ascending=False)
        databusqsortedabstotal = add_top_ten(databusqsortedabs, databusqsortedabstotal)
        databusqsortedreltotal = add_top_ten(databusqsortedrel, databusqsortedreltotal)

        databranchq = data.loc[
            ((data.VAR == "q1") | (data.VAR == "q2")) & (data.ELEMENT_TYPE != "bus")
            ]
        databranchqsortedabs = databranchq.sort_values("ABS_ERR", ascending=False)
        databranchqsortedrel = databranchq.sort_values("REL_ERR", ascending=False)
        databranchqsortedabstotal = add_top_ten(databranchqsortedabs, databranchqsortedabstotal)
        databranchqsortedreltotal = add_top_ten(databranchqsortedrel, databranchqsortedreltotal)

        status_df = data[data.ID == "status#code"]
        if status_df.iloc[0]["ABS_ERR"] > 0:
            convergence_mismatch.append([split_contg,
                                         status_df.iloc[0]["VALUE_HADES"],
                                         status_df.iloc[0]["VALUE_OLF"]])
        elif status_df.iloc[0]["VALUE_HADES"] > 0:
            noconv.append([split_contg,
                           status_df.iloc[0]["VALUE_HADES"],
                           status_df.iloc[0]["VALUE_OLF"]])

    if databusvoltsortedabstotal is None:
        raise ValueError(
            f"Neither regular expression matches or there are no cases defined"
        )

    databusvoltsortedabstotal = databusvoltsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
    databusvoltsortedreltotal = databusvoltsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
    databranchpsortedabstotal = databranchpsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
    databranchpsortedreltotal = databranchpsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
    databuspsortedabstotal = databuspsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
    databuspsortedreltotal = databuspsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
    databusqsortedabstotal = databusqsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
    databusqsortedreltotal = databusqsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
    databranchqsortedabstotal = databranchqsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]


    metrics_file = "metrics.csv.xz" if filter_file is None else "metrics_filtered.csv.xz"
    df_metrics = pd.read_csv(pf_metrics_dir + metrics_file, index_col=0)
    df_weights = pd.read_csv(
        pf_metrics_dir + "../../score_weights.csv", sep=";", index_col=0
    )

    datascore, max_n_pass, p95_n_pass, mean_n_pass, total_n_pass = calc_global_score(
        df_metrics,
        df_weights["W_V"].to_list()[0],
        df_weights["W_P"].to_list()[0],
        df_weights["W_Q"].to_list()[0],
        df_weights["W_T"].to_list()[0],
        df_weights["MAX_THRESH"].to_list()[0],
        df_weights["MEAN_THRESH"].to_list()[0],
        df_weights["P95_THRESH"].to_list()[0],
    )

    datascore_max = datascore.sort_values("MAX_SCORE", ascending=False)
    datascore_p95 = datascore.sort_values("P95_SCORE", ascending=False)
    datascore_mean = datascore.sort_values("MEAN_SCORE", ascending=False)


    datascore_max_total = datascore_max[:10]
    datascore_p95_total = datascore_p95[:10]
    datascore_mean_total = datascore_mean[:10]

    # Print results on screen
    print("WEIGHTS AND THRESHOLDS USED FOR SCORE CALCULATIONS:")
    print(
        "\nW_V = "
        + str(df_weights["W_V"].to_list()[0])
        + "\nW_P = "
        + str(df_weights["W_P"].to_list()[0])
        + "\nW_Q = "
        + str(df_weights["W_Q"].to_list()[0])
        + "\nW_T = "
        + str(df_weights["W_T"].to_list()[0])
        + "\nMAX_THRESH = "
        + str(df_weights["MAX_THRESH"].to_list()[0])
        + "\nMEAN_THRESH = "
        + str(df_weights["MEAN_THRESH"].to_list()[0])
        + "\nP95_THRESH = "
        + str(df_weights["P95_THRESH"].to_list()[0])
        + "\n"
    )
    if len(noconv) > 0:
        print(
        "\n\nCONTINGENCES THAT DID NOT CONVERGE"
        )
        print(pd.DataFrame(noconv, columns=["Case", "Hades Status", "OLF Status"]).to_string(index=False))

    if len(convergence_mismatch) > 0:
        print(
        "\n\nCONVERGENCE ISSUE: CASES WITH DIFFERENT CONVERGENCE STATUS in HADES and OLF "
        )
        print(pd.DataFrame(convergence_mismatch, columns=["Case", "Hades Status", "OLF Status"]).to_string(index=False))

    print(
        "\n\nCOMPOUND SCORES: TOP 10 MAX METRIC --- # of cases exceeding threshold = "
        + str(max_n_pass)
        + "\n"
    )
    print(datascore_max_total.to_string(index=False))
    # print(
    #     "\n\nCOMPOUND SCORES: TOP 10 P95 METRIC --- # of cases exceeding threshold = "
    #     + str(p95_n_pass)
    #     + "\n"
    # )
    # print(datascore_p95_total.to_string(index=False))
    # print(
    #     "\n\nCOMPOUND SCORES: TOP 10 MEAN METRIC --- # of cases exceeding threshold = "
    #     + str(mean_n_pass)
    #     + "\n"
    # )
    # print(datascore_mean_total.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BUS-V OF ABS_ERR\n")
    print(databusvoltsortedabstotal.to_string(index=False))
    # print("\n\nTOP 10 VALUES BUS-V OF REL_ERR\n")
    # print(databusvoltsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BRANCH-P OF ABS_ERR\n")
    print(databranchpsortedabstotal.to_string(index=False))
    # print("\n\nTOP 10 VALUES BRANCH-P OF REL_ERR\n")
    # print(databranchpsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BUS-P OF ABS_ERR\n")
    print(databuspsortedabstotal.to_string(index=False))
    # print("\n\nTOP 10 VALUES BUS-P OF REL_ERR\n")
    # print(databuspsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BUS-Q OF ABS_ERR\n")
    print(databusqsortedabstotal.to_string(index=False))
    # print("\n\nTOP 10 VALUES BUS-Q OF REL_ERR\n")
    # print(databusqsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BRANCH-Q OF ABS_ERR\n")
    print(databranchqsortedabstotal.to_string(index=False))


# Read a specific contingency
def read_case(pf_solutions_dir):
    data = pd.read_csv(pf_solutions_dir, sep=";", index_col=False, compression="infer")
    data["DIFF"] = data.VALUE_HADES - data.VALUE_OLF
    data = calculate_error(data)
    return data


# Calculate absolute and relative error
def calculate_error(df1):
    REL_ERR_CLIPPING = 0.1
    df1["ABS_ERR"] = (df1["VALUE_HADES"] - df1["VALUE_OLF"]).abs()
    df1["REL_ERR"] = df1["ABS_ERR"] / df1["VALUE_HADES"].abs().clip(lower=REL_ERR_CLIPPING)
    return df1


def add_top_ten(new_df, previous_df):
    return new_df[:10] if previous_df is None else pd.concat([previous_df, new_df[:10]])


if __name__ == "__main__":
    sys.exit(main())
