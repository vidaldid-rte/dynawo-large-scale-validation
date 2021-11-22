#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#
#
# create_gen_contg.py:
#
# This script creates a graph corresponding to the components of the xiidm file,
# rendering the buses as nodes and the lines, transforms and the HVDCLines as edges.

import math
import sys
from lxml import etree
import networkx as nx
import numpy as np
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("iidm_file", help="iidm file to create graph")

parser.add_argument("path_to_save", help="path to save distance matrix")
args = parser.parse_args()


def main():
    xiidm_file = args.iidm_file

    # Remove a possible trailing slash
    if xiidm_file[-1] == "/":
        xiidm_file = xiidm_file[:-1]

    # Parse XML file
    iidmTree = etree.parse(xiidm_file, etree.XMLParser(remove_blank_text=True))

    # Create the graph
    G = nx.Graph()

    # Call the function that will insert all the buses as nodes of the graph
    G = insert_buses(iidmTree, G)

    print("Number of nodes found in the iidm file: %d\n" % G.number_of_nodes())

    # Call the function that will insert the lines as edges
    G = insert_lines(iidmTree, G)

    # Call the function that will insert the transformers as edges
    n_edges = G.number_of_edges()
    G = insert_transformers(iidmTree, G, n_edges)

    # Call the function that will insert the HVDCLines as edges
    n_edges = G.number_of_edges()
    G = insert_HVDCLines(iidmTree, G, n_edges)

    print("Number of edges found in the iidm file: %d\n" % G.number_of_edges())

    distance_matrix = create_distance_matrix(G)

    np.savetxt(args.path_to_save + "/distance_matrix.txt", distance_matrix)

    return 0


def insert_buses(iidm_tree, G):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all buses and put them in the graph
    for bus in root.iter("{%s}bus" % ns):
        idb = bus.get("id")
        if idb is not None:
            G.add_node(idb)
    print("\nNumber of buses found in the iidm file: %d\n" % G.number_of_nodes())

    return G


def insert_lines(iidm_tree, G):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all lines and put them in the graph
    for line in root.iter("{%s}line" % ns):
        bus1 = line.get("bus1")
        if bus1 is not None:
            bus2 = line.get("bus2")
            if bus2 is not None:
                imp = complex(float(line.get("r")), float(line.get("x")))
                adm = 1 / (math.sqrt(pow(imp.real, 2) + pow(imp.imag, 2)))
                p1 = abs(float(line.get("p1")))
                line_id = line.get("id")
                if (bus1, bus2) not in G.edges:
                    G.add_edge(bus1, bus2, value=adm, id=line_id, pa=p1, imp=1 / adm)
                else:
                    prev_dict = G.get_edge_data(bus1, bus2)
                    G.add_edge(
                        bus1,
                        bus2,
                        value=adm + prev_dict["value"],
                        id=prev_dict["id"] + "__" + line_id,
                        pa=p1 + prev_dict["pa"],
                        imp=1 / (adm + prev_dict["value"]),
                    )

    print("Number of lines found in the iidm file: %d\n" % G.number_of_edges())

    return G


def insert_transformers(iidm_tree, G, n_edges):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all transformers and put them in the graph
    for trans in root.iter("{%s}twoWindingsTransformer" % ns):
        bus1 = trans.get("bus1")
        if bus1 is not None:
            bus2 = trans.get("bus2")
            if bus2 is not None:
                imp = complex(float(trans.get("r")), float(trans.get("x")))
                adm = 1 / (math.sqrt(pow(imp.real, 2) + pow(imp.imag, 2)))
                trans_id = trans.get("id")
                p1 = abs(float(trans.get("p1")))
                if (bus1, bus2) not in G.edges:
                    G.add_edge(bus1, bus2, value=adm, id=trans_id, pa=p1, imp=1 / adm)
                else:
                    prev_dict = G.get_edge_data(bus1, bus2)
                    G.add_edge(
                        bus1,
                        bus2,
                        value=adm + prev_dict["value"],
                        id=prev_dict["id"] + "__" + trans_id,
                        pa=p1 + prev_dict["pa"],
                        imp=1 / (adm + prev_dict["value"]),
                    )

    print(
        "Number of transformers found in the iidm file: %d\n"
        % (G.number_of_edges() - n_edges)
    )
    return G


def insert_HVDCLines(iidm_tree, G, n_edges):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all HVDCLines and put them in the graph
    for hvdc in root.iter("{%s}hvdcLine" % ns):
        converterStation1 = hvdc.get("converterStation1")
        if converterStation1 is not None:
            connected = False
            for converterStation in root.iter("{%s}vscConverterStation" % ns):
                if converterStation1 == converterStation.get("id"):
                    bus1 = converterStation.get("bus")
                    if bus1 is not None:
                        p1 = abs(float(converterStation.get("p")))
                        connected = True

            if connected:
                converterStation2 = hvdc.get("converterStation2")
                if converterStation2 is not None:
                    connected = False
                    for converterStation in root.iter("{%s}vscConverterStation" % ns):
                        if converterStation2 == converterStation.get("id"):
                            bus2 = converterStation.get("bus")
                            if bus2 is not None:
                                connected = True

                    if connected:
                        adm = 1 / float(hvdc.get("r"))
                        hvdc_id = hvdc.get("id")
                        if (bus1, bus2) not in G.edges:
                            G.add_edge(
                                bus1, bus2, value=adm, id=hvdc_id, pa=p1, imp=1 / adm
                            )
                        else:
                            prev_dict = G.get_edge_data(bus1, bus2)
                            G.add_edge(
                                bus1,
                                bus2,
                                value=adm + prev_dict["value"],
                                id=prev_dict["id"] + "__" + hvdc_id,
                                pa=p1 + prev_dict["pa"],
                                imp=1 / (adm + prev_dict["value"]),
                            )

    print(
        "Number of HVDCLines found in the iidm file: %d\n"
        % (G.number_of_edges() - n_edges)
    )
    return G


def create_distance_matrix(G):

    distance_matrix = nx.floyd_warshall_numpy(G, weight="imp")
    return distance_matrix


if __name__ == "__main__":
    sys.exit(main())
