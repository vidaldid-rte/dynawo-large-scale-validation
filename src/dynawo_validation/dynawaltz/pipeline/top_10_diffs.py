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
parser.add_argument("crv_reducedparams_dir", help="enter crv_reducedparams_dir directory")
parser.add_argument("results_dir", help="enter results_dir directory")
args = parser.parse_args()


def main():
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)
    crv_reducedparams_dir = args.crv_reducedparams_dir
    data = read_case(crv_reducedparams_dir)
    
    
    datafirstfalse = data.loc[(data.is_preStab_ast == "False") | (data.is_preStab_dwo == "False")]
    datafirstfalsesorted = datafirstfalse.sort_values("dev", ascending=False)
    
    datafinalfalse = data.loc[(data.is_postStab_ast == "False") | (data.is_postStab_dwo == "False")]
    datafinalfalsesorted = datafinalfalse.sort_values("dev", ascending=False)
    
    data_U_IMPIN_value = copy.deepcopy(data)
    data_U_IMPIN_value["DIFF_dSS_U_IMPIN"] = (data_U_IMPIN_value["dSS_ast"] - data_U_IMPIN_value["dSS_dwo"]).abs()
    data_U_IMPIN_value_fil = data_U_IMPIN_value.loc[lambda x: x['vars'].str.contains(r'U_IMPIN_value', regex = True)]
    data_U_IMPIN_valuesorted = data_U_IMPIN_value_fil.sort_values("DIFF_dSS_U_IMPIN", ascending=False)
    
    data_levelK_value = copy.deepcopy(data)
    data_levelK_value["DIFF_dPP_levelK"] = (data_levelK_value["dPP_ast"] - data_levelK_value["dPP_dwo"]).abs()
    data_levelK_value_fil = data_levelK_value.loc[lambda x: x['vars'].str.contains(r'levelK_value', regex = True)]
    data_levelK_valuesorted = data_levelK_value_fil.sort_values("DIFF_dPP_levelK", ascending=False)
    
    PGen_value = copy.deepcopy(data)
    PGen_value["DIFF_dSS_PGen"] = (PGen_value["dSS_ast"] - PGen_value["dSS_dwo"]).abs()
    PGen_value_fil = PGen_value.loc[lambda x: x['vars'].str.contains(r'_PGen', regex = True)]
    PGen_valuesorted = PGen_value_fil.sort_values("DIFF_dSS_PGen", ascending=False)
    
    QGen_value = copy.deepcopy(data)
    QGen_value["DIFF_dSS_QGen"] = (QGen_value["dSS_ast"] - QGen_value["dSS_dwo"]).abs()
    QGen_value_fil = QGen_value.loc[lambda x: x['vars'].str.contains(r'_QGen', regex = True)]
    QGen_valuesorted = QGen_value_fil.sort_values("DIFF_dSS_QGen", ascending=False)
    

    file = open(args.results_dir + "/top_10_errors.txt", "w+")
    file.write("START STABLE CONTG\n")
    file.write(str(datafirstfalsesorted[:10]))
    file.write("\n\nFINAL STABLE CONTG\n")
    file.write(str(datafinalfalsesorted[:10]))
    file.write("\n\nDIFF dSS U_IMPIN_value\n")
    file.write(str(data_U_IMPIN_valuesorted[:10]))
    file.write("\n\nDIFF dPP levelK_value\n")
    file.write(str(data_levelK_valuesorted[:10]))
    file.write("\n\nDIFF dSS PGen\n")
    file.write(str(PGen_valuesorted[:10]))
    file.write("\n\nDIFF dSS QGen\n")
    file.write(str(QGen_valuesorted[:10]))
    

    file.close()


# Read a specific contingency
def read_case(crv_reducedparams_dir):
    data = pd.read_csv(crv_reducedparams_dir, sep=";", index_col=False, compression="infer")
    return data


if __name__ == "__main__":
    sys.exit(main())
