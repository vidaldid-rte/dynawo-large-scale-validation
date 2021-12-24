#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
import os.path
import pandas as pd
import sys
import argparse
from lxml import etree


parser = argparse.ArgumentParser()
parser.add_argument(
    "job_path",
    help="Enter JOB file",
)
parser.add_argument(
    "basecase_dir",
    help="Enter basecase dir relative to the contingencies path",
)

args = parser.parse_args()


def main():
    job_path = args.job_path
    basecase_dir = args.basecase_dir

    if basecase_dir[-1] != "/":
        basecase_dir = basecase_dir + "/"

    tree = etree.parse(str(job_path), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace

    for dyd_file in root.iter(f"{{{ns}}}dynModels"):
        dir_dyd_file = dyd_file.get("dydFile")
        dir_dyd = os.path.dirname(dir_dyd_file)
        if len(dir_dyd) != 0:
            dir_dyd = dir_dyd + "/"
        dir_dyd_contg = dir_dyd + "contingency.dyd"
        event = etree.SubElement(dyd_file.getparent(), f"{{{ns}}}dynModels")
        event.set("dydFile", dir_dyd_contg)
        dyd_file.set("dydFile", basecase_dir+dir_dyd_file)

    for iidm_file in root.iter(f"{{{ns}}}network"):
        dir_iidm_file = iidm_file.get("iidmFile")
        iidm_file.set("iidmFile", basecase_dir+dir_iidm_file)

    tree.write(
        job_path,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )


if __name__ == "__main__":
    sys.exit(main())
