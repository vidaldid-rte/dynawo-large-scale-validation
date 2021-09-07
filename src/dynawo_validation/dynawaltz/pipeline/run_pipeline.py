#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
import sys
from subprocess import run


def run_pipeline(base_case, results_dir, launcherA="dynawo.sh", launcherB="dynawo.sh", allcontg=False):
    file_path = os.path.abspath(os.path.dirname(__file__))
    if allcontg:
        Process = run(
            file_path
            + "/run_pipeline.sh -A %s -B %s -a %s %s"
            % (launcherA, launcherB, base_case, results_dir),
            shell=True,
        )
    else:
        Process = run(
            file_path
            + "/run_pipeline.sh -A %s -B %s %s %s"
            % (launcherA, launcherB, base_case, results_dir),
            shell=True,
        )
