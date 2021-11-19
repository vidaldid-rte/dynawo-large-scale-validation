#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
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


parser = argparse.ArgumentParser()
parser.add_argument("pf_solutions_dir", help="enter pf_solutions_dir directory")
parser.add_argument("--regex", nargs="+", help="enter prefix name", default=[".*"])
args = parser.parse_args()


def main():
    # display format
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)

    # argument management
    pf_solutions_dir = args.pf_solutions_dir

    if pf_solutions_dir[-1] != "/":
        pf_solutions_dir = pf_solutions_dir + "/"

    data_files = os.listdir(pf_solutions_dir)
    first_iteration = True

    # regex list
    data_files_list = []
    for i in data_files:
        for j in args.regex:
            if i not in data_files_list and re.match(j + "-pfsolution_AB.csv.xz", i):
                data_files_list.append(i)

    for i in data_files_list:
        # If it is the first iteration, we must initialize all the total metrics
        if first_iteration:
            first_iteration = False
            # Reading the cases and ordering the values ​​according to the metrics
            data = read_case(pf_solutions_dir + i)
            data.insert(0, "CONTG_ID", i[:-21])
            databusvolt = data.loc[(data.VAR == "v") & (data.ELEMENT_TYPE == "bus")]
            databusvoltsortedabs = databusvolt.sort_values("ABS_ERR", ascending=False)
            databusvoltsortedrel = databusvolt.sort_values("REL_ERR", ascending=False)

            databranchp = data.loc[
                ((data.VAR == "p1") | (data.VAR == "p2")) & (data.ELEMENT_TYPE != "bus")
            ]
            databranchpsortedabs = databranchp.sort_values("ABS_ERR", ascending=False)
            databranchpsortedrel = databranchp.sort_values("REL_ERR", ascending=False)

            databusp = data.loc[(data.VAR == "p") & (data.ELEMENT_TYPE == "bus")]
            databuspsortedabs = databusp.sort_values("ABS_ERR", ascending=False)
            databuspsortedrel = databusp.sort_values("REL_ERR", ascending=False)

            databusq = data.loc[(data.VAR == "q") & (data.ELEMENT_TYPE == "bus")]
            databusqsortedabs = databusq.sort_values("ABS_ERR", ascending=False)
            databusqsortedrel = databusq.sort_values("REL_ERR", ascending=False)

            databusvoltsortedabstotal = databusvoltsortedabs[:10]
            databusvoltsortedreltotal = databusvoltsortedrel[:10]
            databranchpsortedabstotal = databranchpsortedabs[:10]
            databranchpsortedreltotal = databranchpsortedrel[:10]
            databuspsortedabstotal = databuspsortedabs[:10]
            databuspsortedreltotal = databuspsortedrel[:10]
            databusqsortedabstotal = databusqsortedabs[:10]
            databusqsortedreltotal = databusqsortedrel[:10]
        else:
            # Reading the cases and ordering the values ​​according to the metrics
            data = read_case(pf_solutions_dir + i)
            data.insert(0, "CONTG_ID", i[:-21])
            databusvolt = data.loc[(data.VAR == "v") & (data.ELEMENT_TYPE == "bus")]
            databusvoltsortedabs = databusvolt.sort_values("ABS_ERR", ascending=False)
            databusvoltsortedrel = databusvolt.sort_values("REL_ERR", ascending=False)

            databranchp = data.loc[
                ((data.VAR == "p1") | (data.VAR == "p2")) & (data.ELEMENT_TYPE != "bus")
            ]
            databranchpsortedabs = databranchp.sort_values("ABS_ERR", ascending=False)
            databranchpsortedrel = databranchp.sort_values("REL_ERR", ascending=False)

            databusp = data.loc[(data.VAR == "p") & (data.ELEMENT_TYPE == "bus")]
            databuspsortedabs = databusp.sort_values("ABS_ERR", ascending=False)
            databuspsortedrel = databusp.sort_values("REL_ERR", ascending=False)

            databusq = data.loc[(data.VAR == "q") & (data.ELEMENT_TYPE == "bus")]
            databusqsortedabs = databusq.sort_values("ABS_ERR", ascending=False)
            databusqsortedrel = databusq.sort_values("REL_ERR", ascending=False)

            # We check if the 10 largest values ​​in the current case belong to the biggest
            # general differences. To save computation, we check if they are greater than
            # the last value of the global list and if they are not, the following values ​​of
            # the current case will never be greater than those of the global list
            for i in range(10):
                if (
                    databusvoltsortedabs.iloc[i]["ABS_ERR"]
                    > databusvoltsortedabstotal.iloc[9]["ABS_ERR"]
                ):
                    databusvoltsortedabstotal = pd.concat(
                        [databusvoltsortedabstotal, databusvoltsortedabs[i : i + 1]]
                    )
                    databusvoltsortedabstotal = databusvoltsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databusvoltsortedrel.iloc[i]["REL_ERR"]
                    > databusvoltsortedreltotal.iloc[9]["REL_ERR"]
                ):
                    databusvoltsortedreltotal = pd.concat(
                        [databusvoltsortedreltotal, databusvoltsortedrel[i : i + 1]]
                    )
                    databusvoltsortedreltotal = databusvoltsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databranchpsortedabs.iloc[i]["ABS_ERR"]
                    > databranchpsortedabstotal.iloc[9]["ABS_ERR"]
                ):
                    databranchpsortedabstotal = pd.concat(
                        [databranchpsortedabstotal, databranchpsortedabs[i : i + 1]]
                    )
                    databranchpsortedabstotal = databranchpsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databranchpsortedrel.iloc[i]["REL_ERR"]
                    > databranchpsortedreltotal.iloc[9]["REL_ERR"]
                ):
                    databranchpsortedreltotal = pd.concat(
                        [databranchpsortedreltotal, databranchpsortedrel[i : i + 1]]
                    )
                    databranchpsortedreltotal = databranchpsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databuspsortedabs.iloc[i]["ABS_ERR"]
                    > databuspsortedabstotal.iloc[9]["ABS_ERR"]
                ):
                    databuspsortedabstotal = pd.concat(
                        [databuspsortedabstotal, databuspsortedabs[i : i + 1]]
                    )
                    databuspsortedabstotal = databuspsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databuspsortedrel.iloc[i]["REL_ERR"]
                    > databuspsortedreltotal.iloc[9]["REL_ERR"]
                ):
                    databuspsortedreltotal = pd.concat(
                        [databuspsortedreltotal, databuspsortedrel[i : i + 1]]
                    )
                    databuspsortedreltotal = databuspsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databusqsortedabs.iloc[i]["ABS_ERR"]
                    > databusqsortedabstotal.iloc[9]["ABS_ERR"]
                ):
                    databusqsortedabstotal = pd.concat(
                        [databusqsortedabstotal, databusqsortedabs[i : i + 1]]
                    )
                    databusqsortedabstotal = databusqsortedabstotal.sort_values(
                        "ABS_ERR", ascending=False
                    )[:10]
                else:
                    break

            for i in range(10):
                if (
                    databusqsortedrel.iloc[i]["REL_ERR"]
                    > databusqsortedreltotal.iloc[9]["REL_ERR"]
                ):
                    databusqsortedreltotal = pd.concat(
                        [databusqsortedreltotal, databusqsortedrel[i : i + 1]]
                    )
                    databusqsortedreltotal = databusqsortedreltotal.sort_values(
                        "REL_ERR", ascending=False
                    )[:10]
                else:
                    break

    if first_iteration:
        raise ValueError(
            f"Neither regular expression matches or there are no cases defined"
        )

    # Print results on screen
    print("TOP 10 VALUES BUS-V OF ABS_ERR\n")
    print(databusvoltsortedabstotal.to_string(index=False))
    print("\n\nTOP 10 VALUES BUS-V OF REL_ERR\n")
    print(databusvoltsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BRANCH-P OF ABS_ERR\n")
    print(databranchpsortedabstotal.to_string(index=False))
    print("\n\nTOP 10 VALUES BRANCH-P OF REL_ERR\n")
    print(databranchpsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BUS-P OF ABS_ERR\n")
    print(databuspsortedabstotal.to_string(index=False))
    print("\n\nTOP 10 VALUES BUS-P OF REL_ERR\n")
    print(databuspsortedreltotal.to_string(index=False))
    print("\n\n\n\nTOP 10 VALUES BUS-Q OF ABS_ERR\n")
    print(databusqsortedabstotal.to_string(index=False))
    print("\n\nTOP 10 VALUES BUS-Q OF REL_ERR\n")
    print(databusqsortedreltotal.to_string(index=False))


# Read a specific contingency
def read_case(pf_solutions_dir):
    data = pd.read_csv(pf_solutions_dir, sep=";", index_col=False, compression="infer")
    data["DIFF"] = data.VALUE_A - data.VALUE_B
    data = calculate_error(data)
    return data


# Calculate absolute and relative error
def calculate_error(df1):
    REL_ERR_CLIPPING = 0.1
    df1["ABS_ERR"] = (df1["VALUE_A"] - df1["VALUE_B"]).abs()
    df1["REL_ERR"] = df1["ABS_ERR"] / df1["VALUE_A"].abs().clip(lower=REL_ERR_CLIPPING)
    return df1


if __name__ == "__main__":
    sys.exit(main())
