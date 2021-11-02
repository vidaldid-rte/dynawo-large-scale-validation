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
parser.add_argument("xml_CONTGCASE", help="enter xml contg case of Hades")

args = parser.parse_args()


def main():
    xml_BASECASE = args.xml_BASECASE
    xml_CONTGCASE = args.xml_CONTGCASE

    hds_basecase_tree = etree.parse(
        xml_BASECASE, etree.XMLParser(remove_blank_text=True)
    )
    hds_contgcase_tree = etree.parse(
        lzma.open(xml_CONTGCASE), etree.XMLParser(remove_blank_text=True)
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

    # CONTG

    root = hds_contgcase_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesRegleurs = reseau.find("./donneesRegleurs", root.nsmap)
    hades_regleurs_contg = dict()
    for regleur in donneesRegleurs.iterfind("./regleur", root.nsmap):
        for variable in regleur.iterfind("./variables", root.nsmap):
            regleur_id = variable.getparent().get("num")
            if regleur_id not in hades_regleurs_contg:
                hades_regleurs_contg[regleur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    hades_dephaseurs_contg = dict()
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        for variable in dephaseur.iterfind("./variables", root.nsmap):
            dephaseur_id = variable.getparent().get("num")
            if dephaseur_id not in hades_dephaseurs_contg:
                hades_dephaseurs_contg[dephaseur_id] = int(variable.get("plot"))
            else:
                raise ValueError(f"Tap ID repeated")

    # MATCHING
    data_keys = hades_regleurs_basecase.keys()
    data_list = hades_regleurs_basecase.values()
    df_hades_regleurs_basecase = pd.DataFrame(data=data_list, index=data_keys, columns=["AUT_VAL"])
    
    data_keys = hades_regleurs_contg.keys()
    data_list = hades_regleurs_contg.values()
    df_hades_regleurs_contg = pd.DataFrame(data=data_list, index=data_keys, columns=["AUT_VAL"])
    
    data_keys = hades_dephaseurs_basecase.keys()
    data_list = hades_dephaseurs_basecase.values()
    df_hades_dephaseurs_basecase = pd.DataFrame(data=data_list, index=data_keys, columns=["AUT_VAL"])
    
    data_keys = hades_dephaseurs_contg.keys()
    data_list = hades_dephaseurs_contg.values()
    df_hades_dephaseurs_contg = pd.DataFrame(data=data_list, index=data_keys, columns=["AUT_VAL"])
    
    
    df_hades_regleurs_diff = copy.deepcopy(df_hades_regleurs_basecase)
    
    df_hades_dephaseurs_diff = copy.deepcopy(df_hades_dephaseurs_basecase)

    
    df_hades_regleurs_diff["DIFF"] = df_hades_regleurs_basecase["AUT_VAL"] - df_hades_regleurs_contg["AUT_VAL"]
    
    df_hades_regleurs_diff["DIFF_ABS"] = df_hades_regleurs_diff["DIFF"].abs()
    
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_hades_regleurs_diff["DIFF_POS"] = df_hades_regleurs_diff['DIFF']
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_hades_regleurs_diff["DIFF_NEG"] = df_hades_regleurs_diff['DIFF'] 
    df_hades_regleurs_diff.loc[df_hades_regleurs_diff['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    df_hades_dephaseurs_diff["DIFF"] = df_hades_regleurs_basecase["AUT_VAL"] - df_hades_regleurs_contg["AUT_VAL"]
    
    df_hades_dephaseurs_diff["DIFF_ABS"] = df_hades_regleurs_diff["DIFF"].abs()
    
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_hades_dephaseurs_diff["DIFF_POS"] = df_hades_regleurs_diff['DIFF']
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_hades_dephaseurs_diff["DIFF_NEG"] = df_hades_regleurs_diff['DIFF'] 
    df_hades_dephaseurs_diff.loc[df_hades_dephaseurs_diff['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    print("TOTAL DIFFS REGLEURS")
    print(sum(df_hades_regleurs_diff["DIFF_ABS"]))
    print("TOTAL CHANGES REGLEURS")
    print(sum(df_hades_regleurs_diff["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS REGLEURS")
    print(sum(df_hades_regleurs_diff["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS REGLEURS")
    print(sum(df_hades_regleurs_diff["DIFF_NEG"]))
    
    print("TOTAL DIFFS DEPHASEURS")
    print(sum(df_hades_dephaseurs_diff["DIFF_ABS"]))
    print("TOTAL CHANGES DEPHASEURS")
    print(sum(df_hades_dephaseurs_diff["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS DEPHASEURS")
    print(sum(df_hades_dephaseurs_diff["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS DEPHASEURS")
    print(sum(df_hades_dephaseurs_diff["DIFF_NEG"]))
    

if __name__ == "__main__":
    sys.exit(main())
