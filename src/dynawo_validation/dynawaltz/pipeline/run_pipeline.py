#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
import sys
from subprocess import run


def run_pipeline(base_case, results_dir):
    file_path = os.path.abspath(os.path.dirname(__file__))
    Process=run(file_path+'/run_pipeline.sh %s %s' % (base_case,results_dir,), shell=True)

