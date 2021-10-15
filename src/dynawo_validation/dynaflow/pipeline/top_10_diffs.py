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
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("pf_solutions_dir", help="enter pf_solutions_dir directory")
parser.add_argument("results_dir", help="enter results_dir directory")
parser.add_argument("prefix", help="enter prefix name")
args = parser.parse_args()


def main():
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)
    pf_solutions_dir = args.pf_solutions_dir
    data = read_case(pf_solutions_dir)
    
    
    databusvolt = data.loc[(data.VAR == "v") & (data.ELEMENT_TYPE == "bus")]
    databusvoltsortedabs = databusvolt.sort_values("ABS_ERR", ascending=False)
    databusvoltsortedrel = databusvolt.sort_values("REL_ERR", ascending=False)
    
    databranchp = data.loc[((data.VAR == "p1") | (data.VAR == "p2")) & (data.ELEMENT_TYPE != "bus")]
    databranchpsortedabs = databranchp.sort_values("ABS_ERR", ascending=False)
    databranchpsortedrel = databranchp.sort_values("REL_ERR", ascending=False)
    
    databusp = data.loc[(data.VAR == "p") & (data.ELEMENT_TYPE == "bus")]
    databuspsortedabs = databusp.sort_values("ABS_ERR", ascending=False)
    databuspsortedrel = databusp.sort_values("REL_ERR", ascending=False)
    
    databusq = data.loc[(data.VAR == "q") & (data.ELEMENT_TYPE == "bus")]
    databusqsortedabs = databusq.sort_values("ABS_ERR", ascending=False)
    databusqsortedrel = databusq.sort_values("REL_ERR", ascending=False)
   
    
    file = open(args.results_dir + "/" + args.prefix + "-top_10_errors.txt", "w+")
    file.write("TOP 10 VALUES BUS-V OF ABS_ERR\n")
    file.write(str(databusvoltsortedabs[:10]))
    file.write("\n\nTOP 10 VALUES BUS-V OF REL_ERR\n")
    file.write(str(databusvoltsortedrel[:10]))
    file.write("\n\n\n\nTOP 10 VALUES BRANCH-P OF ABS_ERR\n")
    file.write(str(databranchpsortedabs[:10]))
    file.write("\n\nTOP 10 VALUES BRANCH-P OF REL_ERR\n")
    file.write(str(databranchpsortedrel[:10]))
    file.write("\n\n\n\nTOP 10 VALUES BUS-P OF ABS_ERR\n")
    file.write(str(databuspsortedabs[:10]))
    file.write("\n\nTOP 10 VALUES BUS-P OF REL_ERR\n")
    file.write(str(databuspsortedrel[:10]))
    file.write("\n\n\n\nTOP 10 VALUES BUS-Q OF ABS_ERR\n")
    file.write(str(databusqsortedabs[:10]))
    file.write("\n\nTOP 10 VALUES BUS-Q OF REL_ERR\n")
    file.write(str(databusqsortedrel[:10]))
    
    file.close()


# Read a specific contingency
def read_case(pf_solutions_dir):
    data = pd.read_csv(pf_solutions_dir, sep=";", index_col=False, compression="infer")
    data["DIFF"] = data.VALUE_A - data.VALUE_B
    data = calculate_error(data)
    return data


# Calculate absolute and relative error
def calculate_error(df1):
    REL_ERR_CLIPPING = 0.1
    # df1["VOLT_LEVEL"] = df1["VOLT_LEVEL"].astype(str)
    # to force "discrete colors" in Plotly Express
    df1["ABS_ERR"] = (df1["VALUE_A"] - df1["VALUE_B"]).abs()
    df1["REL_ERR"] = df1["ABS_ERR"] / df1["VALUE_A"].abs().clip(lower=REL_ERR_CLIPPING)
    return df1


if __name__ == "__main__":
    sys.exit(main())
