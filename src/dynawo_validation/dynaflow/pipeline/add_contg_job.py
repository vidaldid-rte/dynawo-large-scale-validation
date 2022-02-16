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

args = parser.parse_args()


def main():
    job_path = args.job_path

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

    find = False
    for crv_file in root.iter(f"{{{ns}}}curves"):
        find = True

    if not find:
        for output in root.iter(f"{{{ns}}}outputs"):
            event = etree.SubElement(output, f"{{{ns}}}curves")
            event.set("exportMode", "CSV")
            event.set("inputFile", "standard_curves.crv")

    tree.write(
        job_path,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )


if __name__ == "__main__":
    sys.exit(main())
