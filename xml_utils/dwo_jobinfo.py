#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# dwo_jobinfo.py: common functions for obtaining paths and other relevant parameters
# for a given Dynawo case:
#
#  * get_dwo_jobpaths() takes a directory containing a Dynawo case, looks for the JOB
#    file, and returns all relevant paths to the output files (from the *last* job in
#    the JOB file). This avoids hard-wiring any paths, such as "tFin/fic_DYD.xml",
#    "tFin/outputs", etc.
#
#  * get_dwo_tparams() takes a directory containing a Dynawo case, looks for the JOB
#    file, and returns the three time parameters of the simulation (again, of the *last*
#    job in the JOB file): "startTime", "stopTime", and "event_tEvent".
#
# All we assume here is that the given directory contains only *one* Dynawo case,
# and that its job file has a name matching the pattern ".*JOB.*\.xml" (case
# insensitive).
#
#

import os
import re
import sys
from collections import namedtuple
from pathlib import Path
from lxml import etree


def get_dwo_jobpaths(dwo_case):
    casedir = Path(dwo_case)
    if not os.path.isdir(casedir):
        raise ValueError("Dynawo case directory %s not found" % casedir)
    jobfile_pattern = re.compile(r"JOB.*?\.xml$", re.IGNORECASE)
    matches = [n for n in os.listdir(casedir) if jobfile_pattern.search(n)]
    if len(matches) == 0:
        raise ValueError("No JOB file found in Dynawo case directory %s" % casedir)
    if len(matches) > 1:
        raise ValueError("More than one JOB file found in %s: %s" % (casedir, matches))

    job_file = casedir / matches[0]
    tree = etree.parse(str(job_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    jobs = root.findall("{%s}job" % ns)
    last_job = jobs[-1]  # contemplate only the last job, in case there are several

    modeler = last_job.find("{%s}modeler" % ns)
    network = modeler.find("{%s}network" % ns)
    iidmFile = network.get("iidmFile")
    parFile = network.get("parFile")

    dynModels = modeler.find("{%s}dynModels" % ns)
    dydFile = dynModels.get("dydFile")

    outputs = last_job.find("{%s}outputs" % ns)
    outputs_directory = outputs.get("directory")

    curves = outputs.find("{%s}curves" % ns)
    curves_inputFile = curves.get("inputFile")

    dwo_jobpaths = namedtuple(
        "dwo_jobpaths",
        "job_file, iidmFile, parFile, dydFile, curves_inputFile, outputs_directory",
    )

    return dwo_jobpaths(
        job_file=job_file,
        iidmFile=iidmFile,
        parFile=parFile,
        dydFile=dydFile,
        curves_inputFile=curves_inputFile,
        outputs_directory=outputs_directory,
    )


def get_dwo_tparams(dwo_case):
    # Read the JOB file to obtain the start and stop times of the simulation
    dwo_paths = get_dwo_jobpaths(dwo_case)
    job_file = dwo_paths.job_file
    tree = etree.parse(str(job_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    jobs = root.findall("{%s}job" % ns)
    last_job = jobs[-1]  # contemplate only the last job, in case there are several
    simulation = last_job.find("simulation", root.nsmap)
    startTime = float(simulation.get("startTime"))
    stopTime = float(simulation.get("stopTime"))

    # Read the DYD file to obtain the first Event
    casedir = Path(dwo_case)
    dyd_file = casedir / dwo_paths.dydFile
    tree = etree.parse(str(dyd_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    parFile = None
    parId = None
    for bbm in root.iterfind("./blackBoxModel", root.nsmap):
        if bbm.get("lib")[0:5] == "Event":
            parFile = bbm.get("parFile")
            parId = bbm.get("parId")
            break
    if parFile is None or parId is None:
        raise ValueError("No Event found in Dynawo DYD file %s" % dyd_file)

    # Read the PAR file to obtain its corresponding tEvent
    par_file = casedir / parFile
    tree = etree.parse(str(par_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    event_tEvent = None
    for par_set in root.iterfind("./set", root.nsmap):
        if par_set.get("id") == parId:
            for par in par_set.iterfind("./par", root.nsmap):
                if par.get("name") == "event_tEvent":
                    event_tEvent = float(par.get("value"))
                    break
                break
    if event_tEvent is None:
        raise ValueError(
            "No tEvent found in Dynawo PAR file %s (for parID=%s)" % (par_file, parId)
        )

    dwo_tparams = namedtuple("dwo_tparams", "startTime, stopTime, event_tEvent")

    return dwo_tparams(
        startTime=startTime, stopTime=stopTime, event_tEvent=event_tEvent
    )


def main():
    if len(sys.argv) != 2:
        print("\nUsage: %s dwo_case\n" % sys.argv[0])
        print(
            "   The Dynawo casedir should contain one JOB file (with pattern "
            "*JOB*.xml). If the JOB file contains several jobs, only the last one "
            "will be read.\n"
        )
        return 2
    dwo_case = sys.argv[1]

    jobpaths = get_dwo_jobpaths(dwo_case)
    print("job_file=%s" % jobpaths.job_file)
    print("iidmFile=%s" % jobpaths.iidmFile)
    print("parFile=%s" % jobpaths.parFile)
    print("dydFile=%s" % jobpaths.dydFile)
    print("curves_inputFile=%s" % jobpaths.curves_inputFile)
    print("outputs_directory=%s" % jobpaths.outputs_directory)

    tparams = get_dwo_tparams(dwo_case)
    print("startTime=%s" % tparams.startTime)
    print("stopTime=%s" % tparams.stopTime)
    print("event_tEvent=%s" % tparams.event_tEvent)

    return 0


if __name__ == "__main__":
    sys.exit(main())
