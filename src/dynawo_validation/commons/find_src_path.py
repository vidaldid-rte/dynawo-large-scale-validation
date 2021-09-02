#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
import sys


def find_path():
    file_path = os.path.abspath(os.path.dirname(__file__) + "/..")
    print(file_path)
