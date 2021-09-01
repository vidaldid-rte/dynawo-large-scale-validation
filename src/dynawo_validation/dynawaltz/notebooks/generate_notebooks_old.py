#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
#
# generate_notebooks.py: a simple script to generate a Notebook per CASE. You only
# need to provide the base directory that contains the cases that have been run.
#

import sys
import os
import nbformat as nbf
from pathlib import Path


# Default list of contingency types
DEV_PREFIXES = {
    "gens": "gen_",
    "loads": "load_",
    "shunts": "shunt_",
    "branchBs": "branchB_",
    "branchFs": "branchF_",
    "branchTs": "branchT_",
}


def main():

    # Default pattern for case results directories
    RESULTS_PATTERN = "*/*.RESULTS"

    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("\nUsage: %s BASE_DIR ['RESULTS_PATTERN']" % sys.argv[0])
        print("(default RESULTS_PATTERN = '%s'" % RESULTS_PATTERN)
        print(
            "\nExample:\n   %s %s 'PtFige.*/*.RESULTS'"
            % (sys.argv[0], str(Path.home() / "work"))
        )
        print("   (enclose the pattern in quotes)")
        return 2
    BASE_DIR = Path(sys.argv[1])
    if len(sys.argv) > 2:
        RESULTS_PATTERN = sys.argv[2]
    else:
        print("   Using default RESULTS_PATTERN = '%s'" % RESULTS_PATTERN)

    # Scan the work directory for results directories
    dirlist = BASE_DIR.glob(RESULTS_PATTERN)

    # Read the master template
    nb = nbf.read("Dynawo-Astre Comparison.template.ipynb", as_version=4)
    # Generate the notebooks
    for results_dir in dirlist:
        for device in DEV_PREFIXES:
            src = (
                "# Case selection (adapt CRV_DIR as needed)\n"
                + "CRV_DIR = '%s'\n" % str(results_dir / device / "crv")
                + "PREFIX = '%s'" % DEV_PREFIXES[device]
            )
            # rewrite the first cell
            nb["cells"][0]["source"] = src
            name = os.path.normpath(results_dir).split(os.sep)
            filename = name[-2] + "_" + name[-1] + "_" + device + ".ipynb"
            print("Generating notebook: %s" % filename)
            nbf.write(nb, filename)


if __name__ == "__main__":
    sys.exit(main())
