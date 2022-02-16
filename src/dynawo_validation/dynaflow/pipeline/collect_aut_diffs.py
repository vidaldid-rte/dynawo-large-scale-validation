#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
#
# collect_aut_diffs.py:
#
# This script extracts the differences between case A and case B and saves them in
# csv.xz format

import copy
import pandas as pd
import sys
import argparse
import os
from dynawo_validation.dynaflow.pipeline.dwo_jobinfo import is_dwohds
import re
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

parser = argparse.ArgumentParser()
parser.add_argument(
    "aut_dir",
    help="aut_dir directory",
)
parser.add_argument(
    "results_dir",
    help="results_dir directory",
)
parser.add_argument(
    "basecase",
    help="basecase directory",
)


args = parser.parse_args()


def find_launchers(pathtofiles):
    launcherA = None
    launcherB = None
    for file in os.listdir(pathtofiles):
        basefile = os.path.basename(file)
        if ".LAUNCHER_A_WAS_" == basefile[:16] and launcherA is None:
            launcherA = basefile[16:]
        elif ".LAUNCHER_A_WAS_" == basefile[:16]:
            raise ValueError(f"Two or more .LAUNCHER_WAS_A in results dir")
        elif ".LAUNCHER_B_WAS_" == basefile[:16] and launcherB is None:
            launcherB = basefile[16:]
        elif ".LAUNCHER_B_WAS_" == basefile[:16]:
            raise ValueError(f"Two or more .LAUNCHER_WAS_A in results dir")
    return launcherA, launcherB


def main():
    aut_dir = args.aut_dir
    results_dir = args.results_dir
    basecase = args.basecase

    if aut_dir[-1] != "/":
        aut_dir = aut_dir + "/"
    if results_dir[-1] != "/":
        results_dir = results_dir + "/"
    if basecase[-1] != "/":
        basecase = basecase + "/"

    launcherA, launcherB = find_launchers(results_dir)

    data_files_list_sim_A = []
    data_files_list_sim_B = []
    data_files_list_sim_A_TAP_changes = []
    data_files_list_sim_B_TAP_changes = []
    data_files_list_sim_A_PSTAP_changes = []
    data_files_list_sim_B_PSTAP_changes = []
    data_files = os.listdir(aut_dir)

    if is_dwohds(basecase):
        if launcherA[:5] == "hades":
            whatis = len("-Hades-aut-diff_TAP_changes.csv")
            whatis2 = len("-Hades-aut-diff_PSTAP_changes.csv")
            rest_A = -19
            rest_B = -20
            for i in data_files:
                if i not in data_files_list_sim_A and re.match(
                    ".*-Hades-aut-diff.csv", i
                ):
                    data_files_list_sim_A.append(i)

                if i not in data_files_list_sim_A_TAP_changes and re.match(
                    ".*-Hades-aut-diff_TAP_changes.csv", i
                ):
                    data_files_list_sim_A_TAP_changes.append(i)
                if i not in data_files_list_sim_A_PSTAP_changes and re.match(
                    ".*-Hades-aut-diff_PSTAP_changes.csv", i
                ):
                    data_files_list_sim_A_PSTAP_changes.append(i)

            for i in data_files:
                if i not in data_files_list_sim_B and re.match(
                    ".*-Dynawo-aut-diff.csv", i
                ):
                    data_files_list_sim_B.append(i)

                if i not in data_files_list_sim_B_TAP_changes and re.match(
                    ".*-Dynawo-aut-diff_TAP_changes.csv", i
                ):
                    data_files_list_sim_B_TAP_changes.append(i)
                if i not in data_files_list_sim_B_PSTAP_changes and re.match(
                    ".*-Dynawo-aut-diff_PSTAP_changes.csv", i
                ):
                    data_files_list_sim_B_PSTAP_changes.append(i)

        else:
            whatis = len("-Dynawo-aut-diff_TAP_changes.csv")
            whatis2 = len("-Dynawo-aut-diff_PSTAP_changes.csv")
            rest_A = -20
            rest_B = -19
            for i in data_files:
                if i not in data_files_list_sim_A and re.match(
                    ".*-Dynawo-aut-diff.csv", i
                ):
                    data_files_list_sim_A.append(i)

                if i not in data_files_list_sim_A_TAP_changes and re.match(
                    ".*-Dynawo-aut-diff_TAP_changes.csv", i
                ):
                    data_files_list_sim_A_TAP_changes.append(i)
                if i not in data_files_list_sim_A_PSTAP_changes and re.match(
                    ".*-Dynawo-aut-diff_PSTAP_changes.csv", i
                ):
                    data_files_list_sim_A_PSTAP_changes.append(i)

            for i in data_files:
                if i not in data_files_list_sim_B and re.match(
                    ".*-Hades-aut-diff.csv", i
                ):
                    data_files_list_sim_B.append(i)

                if i not in data_files_list_sim_B_TAP_changes and re.match(
                    ".*-Hades-aut-diff_TAP_changes.csv", i
                ):
                    data_files_list_sim_B_TAP_changes.append(i)
                if i not in data_files_list_sim_B_PSTAP_changes and re.match(
                    ".*-Hades-aut-diff_PSTAP_changes.csv", i
                ):
                    data_files_list_sim_B_PSTAP_changes.append(i)
    else:
        whatis = len("-DynawoA-aut-diff_TAP_changes.csv")
        whatis2 = len("-DynawoA-aut-diff_PSTAP_changes.csv")
        rest_A = -21
        rest_B = -21
        for i in data_files:
            if i not in data_files_list_sim_A and re.match(
                ".*-DynawoA-aut-diff.csv", i
            ):
                data_files_list_sim_A.append(i)

            if i not in data_files_list_sim_A_TAP_changes and re.match(
                ".*-DynawoA-aut-diff_TAP_changes.csv", i
            ):
                data_files_list_sim_A_TAP_changes.append(i)
            if i not in data_files_list_sim_A_PSTAP_changes and re.match(
                ".*-DynawoA-aut-diff_PSTAP_changes.csv", i
            ):
                data_files_list_sim_A_PSTAP_changes.append(i)

        for i in data_files:
            if i not in data_files_list_sim_B and re.match(
                ".*-DynawoB-aut-diff.csv", i
            ):
                data_files_list_sim_B.append(i)

            if i not in data_files_list_sim_B_TAP_changes and re.match(
                ".*-DynawoB-aut-diff_TAP_changes.csv", i
            ):
                data_files_list_sim_B_TAP_changes.append(i)
            if i not in data_files_list_sim_B_PSTAP_changes and re.match(
                ".*-DynawoB-aut-diff_PSTAP_changes.csv", i
            ):
                data_files_list_sim_B_PSTAP_changes.append(i)

    df_temp = read_aut_changes(aut_dir + data_files_list_sim_A[0])
    temp_ind = list(df_temp.index)
    temp_bus = list(df_temp.index)
    for x in range(len(temp_ind)):
        temp_ind[x] = data_files_list_sim_A[0][:rest_A] + "-" + temp_ind[x]
        temp_bus[x] = data_files_list_sim_A[0][:rest_A]

    df_temp["ID"] = temp_ind
    df_temp["CONTG"] = temp_bus
    df_temp.set_index("ID", inplace=True)
    dataframeA = df_temp
    os.remove(aut_dir + data_files_list_sim_A[0])

    for j in data_files_list_sim_A[1:]:
        df_temp = read_aut_changes(aut_dir + j)
        temp_ind = list(df_temp.index)
        temp_bus = list(df_temp.index)
        for x in range(len(temp_ind)):
            temp_ind[x] = j[:rest_A] + "-" + temp_ind[x]
            temp_bus[x] = j[:rest_A]
        df_temp["ID"] = temp_ind
        df_temp["CONTG"] = temp_bus
        df_temp.set_index("ID", inplace=True)
        dataframeA = pd.concat([dataframeA, df_temp], axis=0, join="outer")
        os.remove(aut_dir + j)

    df_temp = read_aut_changes(aut_dir + data_files_list_sim_B[0])
    temp_ind = list(df_temp.index)
    temp_bus = list(df_temp.index)
    for x in range(len(temp_ind)):
        temp_ind[x] = data_files_list_sim_B[0][:rest_B] + "-" + temp_ind[x]
        temp_bus[x] = data_files_list_sim_B[0][:rest_B]
    df_temp["ID"] = temp_ind
    df_temp["CONTG"] = temp_bus
    df_temp.set_index("ID", inplace=True)
    dataframeB = df_temp
    os.remove(aut_dir + data_files_list_sim_B[0])

    for j in data_files_list_sim_B[1:]:
        df_temp = read_aut_changes(aut_dir + j)
        temp_ind = list(df_temp.index)
        temp_bus = list(df_temp.index)
        for x in range(len(temp_ind)):
            temp_ind[x] = j[:rest_B] + "-" + temp_ind[x]
            temp_bus[x] = j[:rest_B]
        df_temp["ID"] = temp_ind
        df_temp["CONTG"] = temp_bus
        df_temp.set_index("ID", inplace=True)
        dataframeB = pd.concat([dataframeB, df_temp], axis=0, join="outer")
        os.remove(aut_dir + j)

    dataframeA.to_csv(aut_dir + "SIMULATOR_A_AUT_CHANGES.csv", sep=";")

    dataframeB.to_csv(aut_dir + "SIMULATOR_B_AUT_CHANGES.csv", sep=";")

    # TODO: Fix so that the order does not matter and the initial state is not supposed
    data_files_list_sim_A_TAP_changes.sort()
    data_files_list_sim_B_TAP_changes.sort()
    data_files_list_sim_A_PSTAP_changes.sort()
    data_files_list_sim_B_PSTAP_changes.sort()

    x_valuesTAP = []
    y_valuesTAP = []
    namesTAP = []
    for k in range(len(data_files_list_sim_A_TAP_changes)):
        contgname = data_files_list_sim_A_TAP_changes[k][:-whatis]
        df_A = read_aut_changes(aut_dir + data_files_list_sim_A_TAP_changes[k])
        df_B = read_aut_changes(aut_dir + data_files_list_sim_B_TAP_changes[k])
        names_A = list(df_A.index)
        names_B = list(df_B.index)
        names_B_aux = copy.deepcopy(names_B)
        for i in range(len(names_A)):
            if names_A[i] not in names_B:
                x_valuesTAP.append(df_A.iloc[i, 1])
                y_valuesTAP.append(df_A.iloc[i, 0])
                namesTAP.append(contgname + "#" + names_A[i])
            else:
                for j in range(len(names_B)):
                    if names_B[j] == names_A[i]:
                        x_valuesTAP.append(df_A.iloc[i, 1])
                        y_valuesTAP.append(df_B.iloc[j, 1])
                        namesTAP.append(contgname + "#" + names_A[i])
                        names_B_aux[j] = 0
                        break

        for i in range(len(names_B_aux)):
            if names_B_aux[i] != 0:
                x_valuesTAP.append(df_B.iloc[i, 0])
                y_valuesTAP.append(df_B.iloc[i, 1])
                namesTAP.append(contgname + "#" + names_B[i])
        os.remove(aut_dir + data_files_list_sim_A_TAP_changes[k])
        os.remove(aut_dir + data_files_list_sim_B_TAP_changes[k])

    x_valuesPSTAP = []
    y_valuesPSTAP = []
    namesPSTAP = []
    for k in range(len(data_files_list_sim_A_PSTAP_changes)):
        contgname = data_files_list_sim_A_PSTAP_changes[k][:-whatis2]
        df_A = read_aut_changes(aut_dir + data_files_list_sim_A_PSTAP_changes[k])
        df_B = read_aut_changes(aut_dir + data_files_list_sim_B_PSTAP_changes[k])
        names_A = list(df_A.index)
        names_B = list(df_B.index)
        for i in range(len(names_A)):
            if names_A[i] not in names_B:
                x_valuesPSTAP.append(df_A.iloc[i, 1])
                y_valuesPSTAP.append(df_A.iloc[i, 0])
                namesPSTAP.append(contgname + "#" + names_A[i])
            else:
                for j in range(len(names_B)):
                    if names_B[j] == names_A[i]:
                        x_valuesPSTAP.append(df_A.iloc[i, 1])
                        y_valuesPSTAP.append(df_B.iloc[j, 1])
                        namesPSTAP.append(contgname + "#" + names_A[i])
                        del names_B[j]
                        break
        for i in range(len(names_B)):
            x_valuesPSTAP.append(df_B.iloc[i, 0])
            y_valuesPSTAP.append(df_B.iloc[i, 1])
            namesPSTAP.append(contgname + "#" + names_B[i])
        os.remove(aut_dir + data_files_list_sim_A_PSTAP_changes[k])
        os.remove(aut_dir + data_files_list_sim_B_PSTAP_changes[k])

    dataTAP = {"sim_A": x_valuesTAP, "sim_B": y_valuesTAP}
    dataPSTAP = {"sim_A": x_valuesPSTAP, "sim_B": y_valuesPSTAP}
    df_TAP = pd.DataFrame(data=dataTAP, index=namesTAP)
    df_PSTAP = pd.DataFrame(data=dataPSTAP, index=namesPSTAP)

    df_TAP.to_csv(aut_dir + "TAP_CHANGES.csv", sep=";")
    df_PSTAP.to_csv(aut_dir + "PSTAP_CHANGES.csv", sep=";")


def read_aut_changes(aut_dir):
    data = pd.read_csv(aut_dir, sep=";", index_col=0, compression="infer")
    return data


if __name__ == "__main__":
    sys.exit(main())
