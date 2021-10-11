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
parser.add_argument("pf_solutions_dir", help="enter pf_solutions_dir directory")
parser.add_argument("results_dir", help="enter results_dir directory")
parser.add_argument("prefix", help="enter prefix name")
args = parser.parse_args()


def main():
    pf_solutions_dir = args.pf_solutions_dir
    data = read_case(pf_solutions_dir)
    datasorteddiff = data.sort_values("DIFF", ascending=False)
    '''
    print("TOP 10 VALUES OF POSITIVE DIFF") 
    print()
    print(datasorteddiff[:10])
    print()
    print("TOP 10 VALUES OF NEGATIVE DIFF") 
    print()
    print(datasorteddiff[-10:])
    '''
    datasortedabs = data.sort_values("ABS_ERR", ascending=False)
    '''
    print()
    print("TOP 10 VALUES OF ABS_ERR") 
    print()
    print(datasortedabs[:10])
    '''
    datasortedrel = data.sort_values("REL_ERR", ascending=False)
    '''
    print()
    print("TOP 10 VALUES OF REL_ERR") 
    print()
    print(datasortedrel[:10])
    '''
    #TODO: val abs y val rel - value A value B
    file=open(args.results_dir+ args.prefix + "-top_10_errors.txt", "w+")
    file.write("\n\nTOP 10 VALUES OF POSITIVE DIFF\n")
    file.write(str(datasorteddiff[:10]))
    file.write("\n\nTOP 10 VALUES OF NEGATIVE DIFF\n")
    file.write(str(datasorteddiff[-10:]))
    file.write("\n\nTOP 10 VALUES OF ABS_ERR\n")
    file.write(str(datasortedabs[:10]))
    file.write("\n\nTOP 10 VALUES OF REL_ERR\n")
    file.write(str(datasortedrel[:10]))
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
