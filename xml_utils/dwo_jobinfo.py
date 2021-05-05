#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# dwo_jobinfo.py:
#
# Common functions for obtaining paths and other relevant parameters for a given
# Dynawo case.  This avoids having any hard-wired paths in the code, such as
# "tFin/fic_DYD.xml", "tFin/outputs", etc., as well as some key parameters such as
# simulation times.
#
#   * is_astdwo() and is_dwodwo() are used to detect whether the case is an
#     Astre-vs-Dynawo or a Dynawo-vs-Dynawo case.
#
#   * If it is an Astre-vs-Dynawo case:
#       - get_dwo_jobpaths() looks for the Dynawo JOB file and returns all relevant
#         paths to the output files (from the *last* job inside the JOB file).
#       - get_dwo_tparams() looks for the Dynawo JOB file and returns the three time
#         parameters of the simulation: "startTime", "stopTime", and "event_tEvent"
#         (again, for the *last* job inside the JOB file)
#
#   * If it is a Dynawo-vs-Dynawo case: do the same thing as above, but for *two*
#     Dynawo job files which are expected to be named "*JOB_A*.xml" and "*JOB_B*.xml".
#
#

import os
import re
import sys
from collections import namedtuple
from pathlib import Path
from lxml import etree


def is_astdwo(case):
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Case directory %s not found" % casedir)
    # If an Astre subdirectory exists, then it is an Astre-vs-Dynawo case
    if os.path.isdir(casedir / "Astre"):
        return True
    else:
        return False


def is_dwodwo(case):
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Case directory %s not found" % casedir)
    # If *only* one JOB_A and one JOB_B files exist, then it is a Dynawo-vs-Dynawo case
    jobfile_patternA = re.compile(r"JOB_A.*?\.xml$", re.IGNORECASE)
    match_A = [n for n in os.listdir(casedir) if jobfile_patternA.search(n)]
    jobfile_patternB = re.compile(r"JOB_B.*?\.xml$", re.IGNORECASE)
    match_B = [n for n in os.listdir(casedir) if jobfile_patternB.search(n)]
    if len(match_A) == 1 and len(match_B) == 1:
        return True
    else:
        return False


def get_jobpaths(job_file):
    tree = etree.parse(str(job_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    jobs = root.findall("{%s}job" % ns)
    last_job = jobs[-1]  # contemplate only the *last* job, in case there are several

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

    Dwo_jobpaths = namedtuple(
        "Dwo_jobpaths",
        "job_file, iidmFile, parFile, dydFile, curves_inputFile, outputs_directory",
    )

    return Dwo_jobpaths(
        job_file=job_file,
        iidmFile=iidmFile,
        parFile=parFile,
        dydFile=dydFile,
        curves_inputFile=curves_inputFile,
        outputs_directory=outputs_directory,
    )


def get_tparams(case, dwo_jobpaths):
    # Read the JOB file to obtain the start and stop times of the simulation
    job_file = dwo_jobpaths.job_file
    tree = etree.parse(str(job_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    jobs = root.findall("{%s}job" % ns)
    last_job = jobs[-1]  # contemplate only the *last* job, in case there are several
    simulation = last_job.find("{%s}simulation" % ns)
    startTime = float(simulation.get("startTime"))
    stopTime = float(simulation.get("stopTime"))

    # Read the DYD file to obtain the first Event
    casedir = Path(case)
    dyd_file = casedir / dwo_jobpaths.dydFile
    tree = etree.parse(str(dyd_file), etree.XMLParser(remove_blank_text=True))
    root = tree.getroot()
    ns = etree.QName(root).namespace
    parFile = None
    parId = None
    for bbm in root.iterfind("./{%s}blackBoxModel" % ns):
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
    ns = etree.QName(root).namespace
    event_tEvent = None
    for par_set in root.iterfind("./{%s}set" % ns):
        if par_set.get("id") == parId:
            for par in par_set.iterfind("./{%s}par" % ns):
                if par.get("name") == "event_tEvent":
                    event_tEvent = float(par.get("value"))
                    break
                break
    if event_tEvent is None:
        raise ValueError(
            "No tEvent found in Dynawo PAR file %s (for parID=%s)" % (par_file, parId)
        )

    Dwo_tparams = namedtuple("Dwo_tparams", "startTime, stopTime, event_tEvent")

    return Dwo_tparams(
        startTime=startTime, stopTime=stopTime, event_tEvent=event_tEvent
    )


def get_dwo_jobpaths(case):
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Dynawo case directory %s not found" % casedir)
    jobfile_pattern = re.compile(r"JOB.*?\.xml$", re.IGNORECASE)
    matches = [n for n in os.listdir(casedir) if jobfile_pattern.search(n)]
    if len(matches) == 0:
        raise ValueError("No JOB file found in Dynawo case directory %s" % casedir)
    if len(matches) > 1:
        raise ValueError("More than one JOB file found in %s: %s" % (casedir, matches))
    job_file = casedir / matches[0]
    return get_jobpaths(job_file)


def get_dwodwo_jobpaths(case):
    casedir = Path(case)
    if not os.path.isdir(casedir):
        raise ValueError("Dynawo case directory %s not found" % casedir)
    jobfile_patternA = re.compile(r"JOB_A.*?\.xml$", re.IGNORECASE)
    match_A = [n for n in os.listdir(casedir) if jobfile_patternA.search(n)]
    jobfile_patternB = re.compile(r"JOB_B.*?\.xml$", re.IGNORECASE)
    match_B = [n for n in os.listdir(casedir) if jobfile_patternB.search(n)]
    if len(match_A) != 1 or len(match_B) != 1:
        raise ValueError("There should be only a JOB_A and JOB_B file in %s" % casedir)
    job_fileA = casedir / match_A[0]
    job_fileB = casedir / match_B[0]
    return get_jobpaths(job_fileA), get_jobpaths(job_fileB)


def get_dwo_tparams(case):
    dwo_jobpaths = get_dwo_jobpaths(case)
    return get_tparams(case, dwo_jobpaths)


def get_dwodwo_tparams(case):
    dwo_jobpathsA, dwo_jobpathsB = get_dwodwo_jobpaths(case)
    return get_tparams(case, dwo_jobpathsA), get_tparams(case, dwo_jobpathsB)


def print_jobinfo(jobpaths, tparams, label=""):
    print(f"job_file{label}={jobpaths.job_file}")
    print(f"iidmFile{label}={jobpaths.iidmFile}")
    print(f"parFile{label}={jobpaths.parFile}")
    print(f"dydFile{label}={jobpaths.dydFile}")
    print(f"curves_inputFile{label}={jobpaths.curves_inputFile}")
    print(f"outputs_directory{label}={jobpaths.outputs_directory}")
    print(f"startTime{label}={tparams.startTime}")
    print(f"stopTime{label}={tparams.stopTime}")
    print(f"event_tEvent{label}={tparams.event_tEvent}")


def main():
    if len(sys.argv) != 2:
        print("\nUsage: %s CASE\n" % sys.argv[0])
        print(
            "   The CASE is detected either as an ast-dwo case if it contains an Astre "
            "directory, or as a dwo-dwo case if it contains exactly two job files "
            " '*JOB_A*.xml' and '*JOB_B*.xml'.\n"
        )
        return 2
    case = sys.argv[1]
    if is_astdwo(case):
        print("CASE_TYPE=astdwo")
        jobpaths = get_dwo_jobpaths(case)
        tparams = get_dwo_tparams(case)
        print_jobinfo(jobpaths, tparams)
    elif is_dwodwo(case):
        print("CASE_TYPE=dwodwo")
        jobpathsA, jobpathsB = get_dwodwo_jobpaths(case)
        tparamsA, tparamsB = get_dwodwo_tparams(case)
        print_jobinfo(jobpathsA, tparamsA, "A")
        print_jobinfo(jobpathsB, tparamsB, "B")
    else:
        raise ValueError("Case %s is neither an ast-dwo nor a dwo-dwo case" % case)
    return 0


if __name__ == "__main__":
    sys.exit(main())
