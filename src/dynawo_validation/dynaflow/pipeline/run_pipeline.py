#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
from subprocess import run


def run_pipeline(
    base_case,
    results_dir,
    launcherA="dynawo.sh",
    launcherB="dynawo.sh",
    allcontg=False,
    regexlist=None,
    random=False,
    sequential=False,
    debug=False,
    cleanup=False,
    randomseed=None,
    weights=None,
):
    file_path = os.path.abspath(os.path.dirname(__file__))
    runallopts = ""
    if sequential:
        runallopts += "-s "

    if debug:
        runallopts += "-d "

    if cleanup:
        runallopts += "-c "

    if random:
        runallopts += "-r "

    if weights is not None:
        runallopts += "-w %s " % (weights)

    if allcontg:
        if regexlist is None:
            if randomseed is not None:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -a -p %s %s %s"
                    % (launcherA, launcherB, randomseed, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -a %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
        else:
            if randomseed is not None:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -a -l %s -p %s %s %s"
                    % (
                        launcherA,
                        launcherB,
                        regexlist,
                        randomseed,
                        base_case,
                        results_dir,
                    ),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -a -l %s %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
    else:
        if regexlist is None:
            if randomseed is not None:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -p %s %s %s"
                    % (launcherA, launcherB, randomseed, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
        else:
            if randomseed is not None:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -l %s -p %s %s %s"
                    % (
                        launcherA,
                        launcherB,
                        regexlist,
                        randomseed,
                        base_case,
                        results_dir,
                    ),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh "
                    + runallopts
                    + "-A %s -B %s -l %s %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
