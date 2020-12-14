#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
#
# generate_notebooks.py: a simple script to generate a Notebook per CASE. You only
# need to provide the base directory that contains the case results.
#

import sys
import os
import nbformat as nbf
# import glob
from pathlib import Path

# You only need to edit this (use the "/" operator to be cross-platform)
BASE_DIR = Path.home() / "work"

# And, typically, you won't need to change these two
RESULTS_PATTERN = "*/*.FALCON_RESULTS"
DEV_PREFIXES = {"gens": "gen_", "loads": "load_", "shunts": "shunt_"}


def main():
    # Scan the work directory for Results dirs
    dirlist = BASE_DIR.glob(RESULTS_PATTERN)

    # Read master Notebook
    nb = nbf.read("Dynawo-Astre Comparison.template.ipynb", as_version=4)
    # Generate them
    for results_dir in dirlist:
        for device in DEV_PREFIXES:
            src = (
                "# Case selection (adapt CRV_DIR as needed)\n"
                + "CRV_DIR = '%s/%s/crv'\n" % (results_dir, device)
                + "PREFIX = '%s'" % DEV_PREFIXES[device]
            )
            nb["cells"][0]["source"] = src
            name = os.path.normpath(results_dir).split(os.sep)
            filename = name[-2] + "_" + name[-1] + "_" + device + ".ipynb"
            print("Generating notebook: %s" % filename)
            nbf.write(nb, filename)


if __name__ == "__main__":
    sys.exit(main())
