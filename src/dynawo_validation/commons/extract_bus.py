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
    print("LOADS:")
    for load in root.iter("{%s}load" % ns):
        bus = load.get("connectableBus")
        if bus == bus_name:
            if load.get("bus") == bus_name:
                is_connected = "CONNECTED"
                find = True
            else:
                is_connected = "NOT CONNECTED"
            print("Load id = " + load.get("id") + " - " + is_connected)

    print("GENS:")
    for gen in root.iter("{%s}generator" % ns):
        bus = gen.get("connectableBus")
        if bus == bus_name:
            if gen.get("bus") == bus_name:
                is_connected = "CONNECTED"
                find = True
            else:
                is_connected = "NOT CONNECTED"
            print("Generator id = " + gen.get("id") + " - " + is_connected)

    print("SHUNTS:")
    for shunt in root.iter("{%s}shunt" % ns):
        bus = shunt.get("connectableBus")
        if bus == bus_name:
            if shunt.get("bus") == bus_name:
                is_connected = "CONNECTED"
                find = True
            else:
                is_connected = "NOT CONNECTED"
            print("Shunt id = " + shunt.get("id") + " - " + is_connected)

    print("BRANCHES:")
    for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
        bus1 = twoWindingsTransformer.get("connectableBus1")
        bus2 = twoWindingsTransformer.get("connectableBus2")
        if bus1 == bus_name or bus2 == bus_name:
            if (
                twoWindingsTransformer.get("bus1") == bus_name
                or twoWindingsTransformer.get("bus2") == bus_name
            ):
                is_connected = "CONNECTED"
                find = True
            else:
                is_connected = "NOT CONNECTED"
            print(
                "TwoWindingsTransformer id = "
                + twoWindingsTransformer.get("id")
                + " - "
                + is_connected
            )
    for line in root.iter("{%s}line" % ns):
        bus1 = line.get("connectableBus1")
        bus2 = line.get("connectableBus2")
        if bus1 == bus_name or bus2 == bus_name:
            if line.get("bus1") == bus_name or line.get("bus2") == bus_name:
                is_connected = "CONNECTED"
                find = True
            else:
                is_connected = "NOT CONNECTED"
            print("Line id = " + line.get("id") + " - " + is_connected)
    for vscConverterStation in root.iter("{%s}vscConverterStation" % ns):
        bus = vscConverterStation.get("connectableBus")
        if bus == bus_name:
            csid = vscConverterStation.get("id")
            for hvdc in root.iter("{%s}hvdcLine" % ns):
                hvdccsid1 = hvdc.get("converterStation1")
                hvdccsid2 = hvdc.get("converterStation2")
                if hvdccsid2 == csid or hvdccsid1 == csid:
                    find = True
                    print("HvdcLine = " + hvdc.get("id"))

    if find == False:
        exists = False
        for bus in root.iter("{%s}bus" % ns):
            busid = bus.get("id")
            if bus_name == busid:
                exists = True
        if exists:
            print("WARNING: This bus exists but is not connected to anything.")
        else:
            raise ValueError(f"Bus doesn't exist")
