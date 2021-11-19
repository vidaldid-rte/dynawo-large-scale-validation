#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# extract_dynawo_automata_changes_basecase.py

import os
import sys
import pandas as pd
import argparse
from lxml import etree

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("xml_BASECASE", help="enter iidm of DWO")
parser.add_argument("path_to_save", help="enter path_to_save csv files")


args = parser.parse_args()


def main():
    xml_BASECASE = args.xml_BASECASE

    dwo_basecase_tree = etree.parse(
        xml_BASECASE, etree.XMLParser(remove_blank_text=True)
    )

    # BASECASE

    root = dwo_basecase_tree.getroot()
    ns = etree.QName(root).namespace

    dynawo_ratioTapChanger_basecase = dict()
    for ratioTapChanger in root.iter("{%s}ratioTapChanger" % ns):
        ratioTapChanger_id = ratioTapChanger.getparent().get("id")
        if ratioTapChanger_id not in dynawo_ratioTapChanger_basecase:
            dynawo_ratioTapChanger_basecase[ratioTapChanger_id] = int(
                ratioTapChanger.get("tapPosition")
            )
        else:
            raise ValueError(f"Tap ID repeated")

    dynawo_phaseTapChanger_basecase = dict()
    for phaseTapChanger in root.iter("{%s}phaseTapChanger" % ns):
        phaseTapChanger_id = phaseTapChanger.getparent().get("id")
        if phaseTapChanger_id not in dynawo_phaseTapChanger_basecase:
            dynawo_phaseTapChanger_basecase[phaseTapChanger_id] = int(
                phaseTapChanger.get("tapPosition")
            )
        else:
            raise ValueError(f"Tap ID repeated")

    dynawo_shunt_basecase = dict()
    for shunt in root.iter("{%s}shunt" % ns):
        if shunt.get("bus") is not None:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_basecase:
                dynawo_shunt_basecase[shunt_id] = 1
            else:
                raise ValueError(f"Tap ID repeated")
        else:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_basecase:
                dynawo_shunt_basecase[shunt_id] = 0
            else:
                raise ValueError(f"Tap ID repeated")

    dynawo_branch_basecase_bus1 = dict()
    dynawo_branch_basecase_bus2 = dict()
    for line in root.iter("{%s}line" % ns):
        temp = [0, 0]
        line_id = line.get("id")
        if line.get("bus1") is not None:
            temp[0] = 1
        if line.get("bus2") is not None:
            temp[1] = 1
        if line_id not in dynawo_branch_basecase_bus1:
            dynawo_branch_basecase_bus1[line_id] = temp[0]
        else:
            raise ValueError(f"Tap ID repeated")
        if line_id not in dynawo_branch_basecase_bus2:
            dynawo_branch_basecase_bus2[line_id] = temp[1]
        else:
            raise ValueError(f"Tap ID repeated")

    for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
        temp = [0, 0]
        twoWindingsTransformer_id = twoWindingsTransformer.get("id")
        if twoWindingsTransformer.get("bus1") is not None:
            temp[0] = 1
        if twoWindingsTransformer.get("bus2") is not None:
            temp[1] = 1
        if twoWindingsTransformer_id not in dynawo_branch_basecase_bus1:
            dynawo_branch_basecase_bus1[twoWindingsTransformer_id] = temp[0]
        else:
            raise ValueError(f"Tap ID repeated")
        if twoWindingsTransformer_id not in dynawo_branch_basecase_bus2:
            dynawo_branch_basecase_bus2[twoWindingsTransformer_id] = temp[1]
        else:
            raise ValueError(f"Tap ID repeated")

    # SAVING
    save_path = args.path_to_save
    if save_path[-1] != "/":
        save_path = save_path + "/"

    data_keys = dynawo_ratioTapChanger_basecase.keys()
    data_list = dynawo_ratioTapChanger_basecase.values()
    df_dynawo_ratioTapChanger_basecase = pd.DataFrame(
        data=data_list, index=data_keys, columns=["TAP_VAL"]
    )
    df_dynawo_ratioTapChanger_basecase.to_csv(
        save_path + "df_dynawo_ratioTapChanger_basecase.csv", sep=";"
    )

    data_keys = dynawo_phaseTapChanger_basecase.keys()
    data_list = dynawo_phaseTapChanger_basecase.values()
    df_dynawo_phaseTapChanger_basecase = pd.DataFrame(
        data=data_list, index=data_keys, columns=["PSTAP_VAL"]
    )
    df_dynawo_phaseTapChanger_basecase.to_csv(
        save_path + "df_dynawo_phaseTapChanger_basecase.csv", sep=";"
    )

    data_keys = dynawo_shunt_basecase.keys()
    data_list = dynawo_shunt_basecase.values()
    df_dynawo_shunt_basecase = pd.DataFrame(
        data=data_list, index=data_keys, columns=["SHUNT_CHG_VAL"]
    )
    df_dynawo_shunt_basecase.to_csv(save_path + "df_dynawo_shunt_basecase.csv", sep=";")

    data_keys = dynawo_branch_basecase_bus1.keys()
    data_list = dynawo_branch_basecase_bus1.values()
    df_dynawo_branch_basecase_bus1 = pd.DataFrame(
        data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"]
    )
    df_dynawo_branch_basecase_bus1.to_csv(
        save_path + "df_dynawo_branch_basecase_bus1.csv", sep=";"
    )

    data_keys = dynawo_branch_basecase_bus2.keys()
    data_list = dynawo_branch_basecase_bus2.values()
    df_dynawo_branch_basecase_bus2 = pd.DataFrame(
        data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"]
    )
    df_dynawo_branch_basecase_bus2.to_csv(
        save_path + "df_dynawo_branch_basecase_bus2.csv", sep=";"
    )

    print("Automata changes of DYNAWO_BASECASE saved")


if __name__ == "__main__":
    sys.exit(main())
