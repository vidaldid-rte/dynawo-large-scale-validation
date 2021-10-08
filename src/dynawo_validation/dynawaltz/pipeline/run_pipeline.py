#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
import sys
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
):
    file_path = os.path.abspath(os.path.dirname(__file__))
    runallopts = ""
    if (sequential == True):
        runallopts+="-s "

    if (debug == True):
        runallopts+="-d "

    if (cleanup == True):
        runallopts+="-c "
        
    if allcontg:
        if regexlist is None:
            if random:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -a -r %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -a %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
        else:
            if random:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -a -l %s -r %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -a -l %s %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
    else:
        if regexlist is None:
            if random:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -r %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s %s %s"
                    % (launcherA, launcherB, base_case, results_dir),
                    shell=True,
                )
        else:
            if random:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -l %s -r %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
            else:
                Process = run(
                    file_path
                    + "/run_pipeline.sh " + runallopts + "-A %s -B %s -l %s %s %s"
                    % (launcherA, launcherB, regexlist, base_case, results_dir),
                    shell=True,
                )
