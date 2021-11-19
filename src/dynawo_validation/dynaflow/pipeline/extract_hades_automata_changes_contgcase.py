#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# extract_hades_tap_changes.py

import os
import sys
import pandas as pd
import copy
import argparse
import lzma
from lxml import etree

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("xml_CONTGCASE", help="enter xml contg case of Hades")
parser.add_argument("basecase_files_path", help="enter basecase_files_path")
parser.add_argument("hades_basecase_xml", help="enter hades_basecase_xml")
parser.add_argument(
    "-s", "--save", help="File to save csv instead of print", default="None"
)

args = parser.parse_args()


def main():
    xml_CONTGCASE = args.xml_CONTGCASE

    tree = etree.parse(args.hades_basecase_xml)
    root = tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesQuadripoles = reseau.find("./donneesQuadripoles", root.nsmap)
    tap2xfmr = dict()
    pstap2xfmr = dict()
    for branch in donneesQuadripoles.iterfind("./quadripole", root.nsmap):
        tap_ID = branch.get("ptrregleur")
        if tap_ID != "0" and tap_ID is not None:
            tap2xfmr[tap_ID] = branch.get("nom")
        pstap_ID = branch.get("ptrdepha")
        if pstap_ID != "0" and pstap_ID is not None:
            pstap2xfmr[pstap_ID] = branch.get("nom")

    hds_contgcase_tree = etree.parse(
        lzma.open(xml_CONTGCASE), etree.XMLParser(remove_blank_text=True)
    )

    # CONTG

    root = hds_contgcase_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesRegleurs = reseau.find("./donneesRegleurs", root.nsmap)
    hades_regleurs_contg = dict()
    for regleur in donneesRegleurs.iterfind("./regleur", root.nsmap):
        for variable in regleur.iterfind("./variables", root.nsmap):
            regleur_id = tap2xfmr[variable.getparent().get("num")]
            if regleur_id not in hades_regleurs_contg:
                hades_regleurs_contg[regleur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    hades_dephaseurs_contg = dict()
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        for variable in dephaseur.iterfind("./variables", root.nsmap):
            dephaseur_id = pstap2xfmr[variable.getparent().get("num")]
            if dephaseur_id not in hades_dephaseurs_contg:
                hades_dephaseurs_contg[dephaseur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    # MATCHING
    save_path = args.basecase_files_path
    if save_path[-1] != "/":
        save_path = save_path + "/"

    df_hades_regleurs_basecase = pd.read_csv(
        save_path + "df_hades_regleurs_basecase.csv", sep=";", index_col=0
    )
    df_hades_dephaseurs_basecase = pd.read_csv(
        save_path + "df_hades_dephaseurs_basecase.csv", sep=";", index_col=0
    )

    data_keys = hades_regleurs_contg.keys()
    data_list = hades_regleurs_contg.values()
    df_hades_regleurs_contg = pd.DataFrame(
        data=data_list, index=data_keys, columns=["AUT_VAL"]
    )

    data_keys = hades_dephaseurs_contg.keys()
    data_list = hades_dephaseurs_contg.values()
    df_hades_dephaseurs_contg = pd.DataFrame(
        data=data_list, index=data_keys, columns=["AUT_VAL"]
    )

    df_hades_regleurs_diff = copy.deepcopy(df_hades_regleurs_basecase)

    df_hades_dephaseurs_diff = copy.deepcopy(df_hades_dephaseurs_basecase)

    df_hades_regleurs_diff = df_hades_regleurs_diff.rename(
        columns={"AUT_VAL": "BC_VAL"}
    )
    df_hades_regleurs_diff["CG_VAL"] = df_hades_regleurs_contg["AUT_VAL"]

    df_hades_dephaseurs_diff = df_hades_dephaseurs_diff.rename(
        columns={"AUT_VAL": "BC_VAL"}
    )
    df_hades_dephaseurs_diff["CG_VAL"] = df_hades_dephaseurs_contg["AUT_VAL"]

    df_hades_regleurs_diff["DIFF"] = (
        df_hades_regleurs_contg["AUT_VAL"] - df_hades_regleurs_basecase["AUT_VAL"]
    )

    df_hades_regleurs_diff["ABS_DIFF"] = df_hades_regleurs_diff["DIFF"].abs()

    df_hades_regleurs_diff.loc[
        df_hades_regleurs_diff["ABS_DIFF"] != 0, "NUM_CHANGES"
    ] = 1
    df_hades_regleurs_diff.loc[
        df_hades_regleurs_diff["ABS_DIFF"] == 0, "NUM_CHANGES"
    ] = 0

    df_hades_regleurs_diff["POS_DIFF"] = df_hades_regleurs_diff["DIFF"]
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff["DIFF"] <= 0, "POS_DIFF"] = 0

    df_hades_regleurs_diff["NEG_DIFF"] = df_hades_regleurs_diff["DIFF"]
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff["DIFF"] >= 0, "NEG_DIFF"] = 0

    df_hades_dephaseurs_diff["DIFF"] = (
        df_hades_dephaseurs_contg["AUT_VAL"] - df_hades_dephaseurs_basecase["AUT_VAL"]
    )

    df_hades_dephaseurs_diff["ABS_DIFF"] = df_hades_dephaseurs_diff["DIFF"].abs()

    df_hades_dephaseurs_diff.loc[
        df_hades_dephaseurs_diff["ABS_DIFF"] != 0, "NUM_CHANGES"
    ] = 1
    df_hades_dephaseurs_diff.loc[
        df_hades_dephaseurs_diff["ABS_DIFF"] == 0, "NUM_CHANGES"
    ] = 0

    df_hades_dephaseurs_diff["POS_DIFF"] = df_hades_dephaseurs_diff["DIFF"]
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff["DIFF"] <= 0, "POS_DIFF"] = 0

    df_hades_dephaseurs_diff["NEG_DIFF"] = df_hades_dephaseurs_diff["DIFF"]
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff["DIFF"] >= 0, "NEG_DIFF"] = 0

    has_changed_regleurs = df_hades_regleurs_diff.loc[
        (df_hades_regleurs_diff.NUM_CHANGES != 0)
    ]
    has_changed_dephaseurs = df_hades_dephaseurs_diff.loc[
        (df_hades_dephaseurs_diff.NUM_CHANGES != 0)
    ]

    if args.save != "None":
        save_csv = args.save
        if save_csv[-4:] != ".csv":
            save_csv = save_csv + ".csv"
        cols = ["ABS_DIFF", "NUM_CHANGES", "POS_DIFF", "NEG_DIFF"]
        ind = ["ratioTapChanger", "phaseTapChanger"]
        vals = [
            [
                sum(df_hades_regleurs_diff["ABS_DIFF"]),
                sum(df_hades_regleurs_diff["NUM_CHANGES"]),
                sum(df_hades_regleurs_diff["POS_DIFF"]),
                sum(df_hades_regleurs_diff["NEG_DIFF"]),
            ],
            [
                sum(df_hades_dephaseurs_diff["ABS_DIFF"]),
                sum(df_hades_dephaseurs_diff["NUM_CHANGES"]),
                sum(df_hades_dephaseurs_diff["POS_DIFF"]),
                sum(df_hades_dephaseurs_diff["NEG_DIFF"]),
            ],
        ]

        df_to_save = pd.DataFrame(data=vals, index=ind, columns=cols)

        df_to_save.to_csv(save_csv, sep=";")
        has_changed_regleurs.to_csv(save_csv[:-4] + "_TAP_changes.csv", sep=";")
        has_changed_dephaseurs.to_csv(save_csv[:-4] + "_PSTAP_changes.csv", sep=";")

    else:
        print("TOTAL DIFFS REGLEURS")
        print(sum(df_hades_regleurs_diff["ABS_DIFF"]))
        print("TOTAL CHANGES REGLEURS")
        print(sum(df_hades_regleurs_diff["NUM_CHANGES"]))
        print("TOTAL POSITIVE DIFFS REGLEURS")
        print(sum(df_hades_regleurs_diff["POS_DIFF"]))
        print("TOTAL NEGATIVE DIFFS REGLEURS")
        print(sum(df_hades_regleurs_diff["NEG_DIFF"]))

        print("\n\n\nTOTAL DIFFS DEPHASEURS")
        print(sum(df_hades_dephaseurs_diff["ABS_DIFF"]))
        print("TOTAL CHANGES DEPHASEURS")
        print(sum(df_hades_dephaseurs_diff["NUM_CHANGES"]))
        print("TOTAL POSITIVE DIFFS DEPHASEURS")
        print(sum(df_hades_dephaseurs_diff["POS_DIFF"]))
        print("TOTAL NEGATIVE DIFFS DEPHASEURS")
        print(sum(df_hades_dephaseurs_diff["NEG_DIFF"]))


if __name__ == "__main__":
    sys.exit(main())
