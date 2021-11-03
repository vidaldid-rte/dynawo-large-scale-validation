#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# extract_hades_tap_changes.py

import os
import math
import sys
import pandas as pd
import copy
import argparse
import lzma
from lxml import etree
from collections import namedtuple

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("xml_BASECASE", help="enter xml base case of Hades")
parser.add_argument("path_to_save", help="enter path_to_save csv files")

args = parser.parse_args()


def main():
    xml_BASECASE = args.xml_BASECASE

    hds_basecase_tree = etree.parse(
        xml_BASECASE, etree.XMLParser(remove_blank_text=True)
    )

    # BASECASE

    root = hds_basecase_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)

    donneesRegleurs = reseau.find("./donneesRegleurs", root.nsmap)
    hades_regleurs_basecase = dict()
    for regleur in donneesRegleurs.iterfind("./regleur", root.nsmap):
        for variable in regleur.iterfind("./variables", root.nsmap):
            regleur_id = variable.getparent().get("num")
            if regleur_id not in hades_regleurs_basecase:
                hades_regleurs_basecase[regleur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    hades_dephaseurs_basecase = dict()
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        for variable in dephaseur.iterfind("./variables", root.nsmap):
            dephaseur_id = variable.getparent().get("num")
            if dephaseur_id not in hades_dephaseurs_basecase:
                hades_dephaseurs_basecase[dephaseur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    # MATCHING
    save_path = args.path_to_save
    if save_path[-1] != "/":
        save_path = save_path + "/"

    data_keys = hades_regleurs_basecase.keys()
    data_list = hades_regleurs_basecase.values()
    df_hades_regleurs_basecase = pd.DataFrame(
        data=data_list, index=data_keys, columns=["AUT_VAL"]
    )
    df_hades_regleurs_basecase.to_csv(
        save_path + "df_hades_regleurs_basecase.csv", sep=";"
    )

    data_keys = hades_dephaseurs_basecase.keys()
    data_list = hades_dephaseurs_basecase.values()
    df_hades_dephaseurs_basecase = pd.DataFrame(
        data=data_list, index=data_keys, columns=["AUT_VAL"]
    )
    df_hades_dephaseurs_basecase.to_csv(
        save_path + "df_hades_dephaseurs_basecase.csv", sep=";"
    )

    print("Automata changes of HADES_BASECASE saved")


if __name__ == "__main__":
    sys.exit(main())
