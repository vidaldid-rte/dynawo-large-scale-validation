#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
#
# generate_notebooks.py: a simple script to generate a Notebook per CASE. You only
# need to provide the base directory that contains the cases that have been run.
#

import sys
import argparse
import os
from pathlib import Path
import re

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("results_dir", help="enter case directory")
parser.add_argument("base_case", help="enter base case directory")
parser.add_argument("contg_type", help="enter contingency type")

args = parser.parse_args()

def main():
    results_dir = args.results_dir
    base_case = args.base_case
    contg_type = args.contg_type

    if contg_type[-1] == "_":
        contg_type = contg_type[:-1]
    if base_case[-1] == "/":
        base_case = base_case[:-1]
    if results_dir[-1] != "/":
        results_dir = results_dir + "/"

    fin = open(sys.path[0] + "/Dynawo-Dynawo Comparison.template.ipynb", "rt")
    # output file to write the result to
    fout = open(sys.path[0] + "/Dynawo-Dynawo Comparison.template_final.ipynb", "wt")
    # for each line in the input file
    for line in fin:
        # read replace the string and write to output file
        if "CHANGE_0" in line:
            fout.write(line.replace("CHANGE_0", results_dir+'/crv/'))
        elif "CHANGE_1" in line:
            fout.write(line.replace("CHANGE_1", contg_type+'_'))
        else:
            fout.write(line)
    # close input and output files
    fin.close()
    fout.close()


if __name__ == "__main__":
    sys.exit(main())
