#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
#
# extract_case_comparison.py:
#
# This script extracts the differences between case A and case B and saves them in csv.xz format

import glob
import pandas as pd
from tqdm import tqdm
import sys
from pathlib import Path


def main():
    # Parameter management
    if len(sys.argv) < 2:
        print(
            "\nUsage: %s directory_of_pf_sol \n" % sys.argv[0]
        )
        return 2

    PF_SOL_DIR = sys.argv[1]

    PREFIX = sys.argv[2]

    files = list(glob.iglob(PF_SOL_DIR + '/'+ PREFIX + '*-pfsolution_AB.csv.xz'))
    print(f"Processing {len(files)} cases.")
    res = []

    PF_METRICS_DIR = PF_SOL_DIR + '/../pf_metrics'
 
    Path(PF_METRICS_DIR).mkdir(parents=False, exist_ok=True)

    for filepath in tqdm(files):
        # Depending on the path
        # cont = filepath.split('_')[3].split('-')[0]
        cont = filepath.split('_')[2].split('-')[0]
        # print(cont)
        delta = pd.read_csv(filepath, sep=";", index_col=False, compression="infer")
        delta['diff'] = abs(delta.VALUE_A - delta.VALUE_B)
        delta_max = delta.groupby('VAR').max()
        delta_mean = delta.groupby('VAR').mean()
        res1 = [cont] + list(delta_max['diff'].values) + list(delta_mean['diff'].values)
        res = res + [res1]


    df = pd.DataFrame(res, columns=['cont'] + list(delta_max.index + '_max') + list(delta_mean.index + '_mean'))
    df.to_csv(PF_METRICS_DIR + '/metrics.csv.xz', compression='xz')

    return 0


if __name__ == "__main__":
    sys.exit(main())
