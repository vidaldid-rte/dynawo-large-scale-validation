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
import copy
import math
import sys
from lxml import etree
import networkx as nx
from pyvis.network import Network


def main():
    if len(sys.argv) < 2:
        print("\nUsage: %s xiidm_file [id_node_subgraph]\n" % sys.argv[0])
        return 2
    subgraph = False
    if len(sys.argv) > 2:
        id_node_subgraph = sys.argv[2]
        subgraph = True

    xiidm_file = sys.argv[1]

    # remove a possible trailing slash
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

    # Call a function that allows us to du a subgraph focusing on a node
    if subgraph:
        C = make_subgraph(G, id_node_subgraph)
        # Visualize th graph
        visualize_graph(C, False, id_node_subgraph)
    else:
        # Visualize th graph
        visualize_graph(G, True)

    return 0


def insert_buses(iidm_tree, G):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all buses and put them in the graph
    for bus in root.iter("{%s}bus" % ns):
        idb = bus.get("id")
        if idb is not None:
            G.add_node(idb)
    print("Number of buses found in the iidm file: %d\n" % G.number_of_nodes())

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
                line_id = line.get("id")
                G.add_edge(bus1, bus2, weight=adm, id=line_id)

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
                G.add_edge(bus1, bus2, weight=adm, id=trans_id)

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
                        G.add_edge(bus1, bus2, weight=adm, id=hvdc_id)

    print(
        "Number of HVDCLines found in the iidm file: %d\n"
        % (G.number_of_edges() - n_edges)
    )
    return G


def make_subgraph(G, id_node_subgraph):
    Cedges = list(G.edges(id_node_subgraph))

    nearnodes = []
    for e in Cedges:
        if e[0] not in nearnodes:
            nearnodes.append(e[0])
        if e[1] not in nearnodes:
            nearnodes.append(e[1])
    nnearnodes = copy.deepcopy(nearnodes)
    for n in nearnodes:
        Cnedges = G.edges(n)
        for en in Cnedges:
            if en not in Cedges:
                Cedges.append(en)
                if en[0] not in nnearnodes:
                    nnearnodes.append(en[0])
                if en[1] not in nnearnodes:
                    nnearnodes.append(en[1])
    nearnodes = nnearnodes
    for n in nearnodes:
        Cnedges = G.edges(n)
        for en in Cnedges:
            if en not in Cedges:
                Cedges.append(en)
    C = nx.Graph()
    C.add_nodes_from(nearnodes)
    C.add_edges_from(Cedges)
    return C


def visualize_graph(G, all, idnode=None):
    net = Network(height="100%", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    if all:
        net.save_graph("graph_all.html")
    else:
        net.save_graph("graph_" + idnode + ".html")


if __name__ == "__main__":
    sys.exit(main())
