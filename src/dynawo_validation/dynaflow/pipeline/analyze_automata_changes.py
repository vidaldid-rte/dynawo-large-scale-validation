#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
# In this script, the necessary calculations are performed to find the largest differences
# between the two cases executed and through the top 10 of several metrics, we can see the
# contingencies that diverge the most between the two simulators.
#
# analyze_automata_changes.py
#

import os
import random
import re
import sys
import pandas as pd
import argparse
import copy

TIME_THRESH = 30.0
ELECTRIC_THRESH = 70.0

parser = argparse.ArgumentParser()
parser.add_argument("aut_dir", help="enter aut_dir directory")
parser.add_argument("--regex", nargs="+", help="enter prefix name", default=[".*"])
args = parser.parse_args()


def main():
    # display format
    pd.set_option("display.max_columns", 999)
    pd.set_option("display.width", 999)

    # argument management
    aut_dir = args.aut_dir
    data_files = os.listdir(aut_dir)
    first_iteration = True

    # regex list
    data_files_list = []
    for i in data_files:
        for j in args.regex:
            if i not in data_files_list and re.match(j + "-DynawoAutomata.csv.xz", i):
                data_files_list.append(i)

    for i in data_files_list:
        data = read_aut_changes(aut_dir + i)
        datatimefilter = data.loc[data.TIME >= 100.0]
        datatimefiltersort = datatimefilter.sort_values("TIME", ascending=True)

        electric_groups = []
        # TODO: First filter with electric distance
        # TODO: Adapt it when we introduce separated dyd and par files contg
        # Parametrize 100 with JOB.xml --> JOB --> dyd --> par

        """
        time_gruops = []
        for x in data:
            for y in data:
                if (y["TIME"] - x["TIME"]) <= TIME_THRESH and :
        """

        print(i)
        print(str(datatimefilter))
        print()


# Read a specific contingency
def read_aut_changes(aut_dir):
    data = pd.read_csv(aut_dir, sep=";", index_col=False, compression="infer")
    return data


if __name__ == "__main__":
    sys.exit(main())
