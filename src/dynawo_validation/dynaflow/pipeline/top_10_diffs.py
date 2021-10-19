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
import copy


parser = argparse.ArgumentParser()
parser.add_argument("pf_solutions_dir", help="enter pf_solutions_dir directory")
parser.add_argument("--regex", nargs = "+", help="enter prefix name", default=[".*"])
args = parser.parse_args()


def main():
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)
    pf_solutions_dir = args.pf_solutions_dir
    data_files = os.listdir(pf_solutions_dir)
    first_iteration = True
    
    data_files_list = []
    for i in data_files:
        for j in args.regex:
            if i not in data_files_list and re.match(j+"-pfsolution_AB.csv.xz", i):
                data_files_list.append(i)
                 
    
    for i in data_files_list:
        if first_iteration:
            first_iteration = False
            data = read_case(pf_solutions_dir+i)
            data.insert(0,'CONTG_ID', i[:-21])
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
            data = read_case(pf_solutions_dir+i)
            data.insert(0,'CONTG_ID', i[:-21])
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
            
            databusvoltsortedabstotal = pd.concat([databusvoltsortedabstotal, databusvoltsortedabs[:10]])
            databusvoltsortedreltotal = pd.concat([databusvoltsortedreltotal, databusvoltsortedrel[:10]])
            databranchpsortedabstotal = pd.concat([databranchpsortedabstotal, databranchpsortedabs[:10]])
            databranchpsortedreltotal = pd.concat([databranchpsortedreltotal, databranchpsortedrel[:10]])
            databuspsortedabstotal = pd.concat([databuspsortedabstotal, databuspsortedabs[:10]])
            databuspsortedreltotal = pd.concat([databuspsortedreltotal, databuspsortedrel[:10]])
            databusqsortedabstotal = pd.concat([databusqsortedabstotal, databusqsortedabs[:10]])
            databusqsortedreltotal = pd.concat([databusqsortedreltotal, databusqsortedrel[:10]])

    
    databusvoltsortedabstotal = databusvoltsortedabstotal.sort_values("ABS_ERR", ascending=False)
    databusvoltsortedreltotal = databusvoltsortedreltotal.sort_values("REL_ERR", ascending=False)
    databranchpsortedabstotal = databranchpsortedabstotal.sort_values("ABS_ERR", ascending=False)
    databranchpsortedreltotal = databranchpsortedreltotal.sort_values("REL_ERR", ascending=False)
    databuspsortedabstotal = databuspsortedabstotal.sort_values("ABS_ERR", ascending=False)
    databuspsortedreltotal = databuspsortedreltotal.sort_values("REL_ERR", ascending=False)
    databusqsortedabstotal = databusqsortedabstotal.sort_values("ABS_ERR", ascending=False)
    databusqsortedreltotal = databusqsortedreltotal.sort_values("REL_ERR", ascending=False)
    

    print("TOP 10 VALUES BUS-V OF ABS_ERR\n")
    print(str(databusvoltsortedabstotal[:10]))
    print("\n\nTOP 10 VALUES BUS-V OF REL_ERR\n")
    print(str(databusvoltsortedreltotal[:10]))
    print("\n\n\n\nTOP 10 VALUES BRANCH-P OF ABS_ERR\n")
    print(str(databranchpsortedabstotal[:10]))
    print("\n\nTOP 10 VALUES BRANCH-P OF REL_ERR\n")
    print(str(databranchpsortedreltotal[:10]))
    print("\n\n\n\nTOP 10 VALUES BUS-P OF ABS_ERR\n")
    print(str(databuspsortedabstotal[:10]))
    print("\n\nTOP 10 VALUES BUS-P OF REL_ERR\n")
    print(str(databuspsortedreltotal[:10]))
    print("\n\n\n\nTOP 10 VALUES BUS-Q OF ABS_ERR\n")
    print(str(databusqsortedabstotal[:10]))
    print("\n\nTOP 10 VALUES BUS-Q OF REL_ERR\n")
    print(str(databusqsortedreltotal[:10]))



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
