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
                hades_regleurs_basecase[regleur_id] = variable.get("plot")
            else:
                raise ValueError(f"Tap ID repeated")

    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    hades_dephaseurs_basecase = dict()
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        for variable in dephaseur.iterfind("./variables", root.nsmap):
            dephaseur_id = variable.getparent().get("num")
            if dephaseur_id not in hades_dephaseurs_basecase:
                hades_dephaseurs_basecase[dephaseur_id] = variable.get("plot")
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
                hades_regleurs_contg[regleur_id] = variable.get("plot")
            else:
                raise ValueError(f"Tap ID repeated")

    donneesDephaseurs = reseau.find("./donneesDephaseurs", root.nsmap)
    hades_dephaseurs_contg = dict()
    for dephaseur in donneesDephaseurs.iterfind("./dephaseur", root.nsmap):
        for variable in dephaseur.iterfind("./variables", root.nsmap):
            dephaseur_id = variable.getparent().get("num")
            if dephaseur_id not in hades_dephaseurs_contg:
                hades_dephaseurs_contg[dephaseur_id] = variable.get("plot")
            else:
                raise ValueError(f"Tap ID repeated")

    # MATCHING
    #TODO: pass to dataframe
    hades_regleurs_diff = dict()
    hades_dephaseurs_diff = dict()

    for key in hades_regleurs_basecase:
        if hades_regleurs_basecase[key] != hades_regleurs_contg[key]:
            hades_regleurs_diff[key] = [
                hades_regleurs_basecase[key],
                hades_regleurs_contg[key],
            ]

    for key in hades_dephaseurs_basecase:
        if hades_dephaseurs_basecase[key] != hades_dephaseurs_contg[key]:
            hades_dephaseurs_diff[key] = [
                hades_dephaseurs_basecase[key],
                hades_dephaseurs_contg[key],
            ]

    print("REGLEURS CHANGES")
    print(hades_regleurs_diff)
    print("\nTOTAL REGLEURS CHANGES")
    print(len(hades_regleurs_diff), " out of ", len(hades_regleurs_basecase))

    print("\n\n\n\nDEPHASEURS CHANGES")
    print(hades_dephaseurs_diff)
    print("\n\nTOTAL DEPHASEURS CHANGES")
    print(len(hades_dephaseurs_diff), " out of ", len(hades_dephaseurs_basecase))


if __name__ == "__main__":
    sys.exit(main())
