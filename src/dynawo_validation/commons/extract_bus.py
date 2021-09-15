#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es


import os
import sys
from lxml import etree


def extract_bus(iidm_file, bus_name):
    if os.path.isfile(iidm_file) == False:
        raise ValueError(f"Iidm file doesn't exist")
    iidmTree = etree.parse(
            iidm_file,
            etree.XMLParser(remove_blank_text=True),
        )
    root = iidmTree.getroot()
    ns = etree.QName(root).namespace 
    find = False
    for line in root.iter("{%s}line" % ns):
        bus1 = line.get("connectableBus1")
        bus2 = line.get("connectableBus2")
        if bus1 == bus_name or bus2 == bus_name: 
            find = True
            print("Branch id = " + line.get("id")) 
    for load in root.iter("{%s}load" % ns):
        bus = load.get("connectableBus")
        if bus == bus_name: 
            find = True
            print("Load id = " + load.get("id"))
    for gen in root.iter("{%s}generator" % ns):
        bus = gen.get("connectableBus")
        if bus == bus_name: 
            find = True
            print("Generator id = " + gen.get("id"))
    for shunt in root.iter("{%s}shunt" % ns):
        bus = shunt.get("connectableBus")
        if bus == bus_name: 
            find = True
            print("Shunt id = " + shunt.get("id")) 
    for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
        bus1 = twoWindingsTransformer.get("connectableBus1")
        bus2 = twoWindingsTransformer.get("connectableBus2")
        if bus1 == bus_name or bus2 == bus_name:  
            find = True
            print("TwoWindingsTransformer id = " + twoWindingsTransformer.get("id"))                      
    if find == False:
        raise ValueError(f"Bus doesn't exist")
    
                

