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
from pyvis.network import Network


def get_graph(xiidm_file, id_node_subgraph, subgraph_type, subgraph_value):
    # Remove a possible trailing slash
    if xiidm_file[-1] == "/":
        xiidm_file = xiidm_file[:-1]

    # Parse XML file
    iidmTree = etree.parse(xiidm_file, etree.XMLParser(remove_blank_text=True))

    # Create the graph
    G = nx.Graph()

    # Call the function that will insert all the buses as nodes of the graph
    G = insert_buses(iidmTree, G)

    # Call the function that will insert the lines as edges
    G = insert_lines(iidmTree, G)

    # Call the function that will insert the transformers as edges
    n_edges = G.number_of_edges()
    G = insert_transformers(iidmTree, G, n_edges)

    # Call the function that will insert the HVDCLines as edges
    n_edges = G.number_of_edges()
    G = insert_HVDCLines(iidmTree, G, n_edges)

    # Call a function that allows us to do a subgraph focusing on a node

    return G, get_subgraph(G, id_node_subgraph, subgraph_type, subgraph_value)


def get_subgraph(G, id_node_subgraph, subgraph_type, subgraph_value):
    C = make_subgraph(G, id_node_subgraph, subgraph_type, subgraph_value)
    net = Network(bgcolor="#222222", font_color="white", notebook=True, width="100%")
    net.from_nx(C)

    return net


def insert_buses(iidm_tree, G):
    root = iidm_tree.getroot()
    ns = etree.QName(root).namespace

    # We enumerate all buses and put them in the graph
    for bus in root.iter("{%s}bus" % ns):
        idb = bus.get("id")
        if idb is not None:
            G.add_node(idb)

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

    return G


def make_subgraph(G, id_node_subgraph, subgraph_type, subgraph_value):

    # Choose if we are going to use layers or Dijkstra
    if subgraph_type == 0:
        # Expand subgraph from node
        Cedges = list(G.edges(id_node_subgraph))
        nearnodes = []
        for e in Cedges:
            if e[0] not in nearnodes:
                nearnodes.append(e[0])
            if e[1] not in nearnodes:
                nearnodes.append(e[1])
        for i in range(int(subgraph_value) - 1):
            for n in nearnodes:
                Cnedges = G.edges(n)
                for en in Cnedges:
                    if en not in Cedges:
                        Cedges.append(en)
            for e in Cedges:
                if e[0] not in nearnodes:
                    nearnodes.append(e[0])
                if e[1] not in nearnodes:
                    nearnodes.append(e[1])

        C = nx.Graph()
        C.add_nodes_from(nearnodes)
        C.add_edges_from(Cedges)

        # Get edge properties
        # Get range color
        max_pa = 0
        min_pa = 99999999
        for s, d in C.edges():
            prev_dict = G.get_edge_data(s, d)
            if prev_dict["pa"] > max_pa:
                max_pa = prev_dict["pa"]
            if prev_dict["pa"] < min_pa:
                min_pa = prev_dict["pa"]

        max_pa -= min_pa
        for s, d in C.edges():
            prev_dict = G.get_edge_data(s, d)

            c = prev_dict["pa"] - min_pa
            g = 256 - (c / max_pa) * 256
            r = 255
            b = 0

            str_rgb = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"

            C.add_edge(
                s, d, value=prev_dict["value"], id=prev_dict["id"], color=str_rgb
            )

        for n in nearnodes:
            title = ""
            Cnedges = C.edges(n)
            for e in Cnedges:
                prev_dict = G.get_edge_data(e[0], e[1])
                title = (
                    title
                    + "("
                    + e[0]
                    + ","
                    + e[1]
                    + "): id = "
                    + prev_dict["id"]
                    + ", Y = "
                    + str(prev_dict["value"])
                    + ", Pa = "
                    + str(prev_dict["pa"])
                    + "<br>"
                )
            C.nodes[n]["title"] = title

    if subgraph_type == 1:
        # Dijkstra
        nearnodes = dict()
        shortest_paths = nx.shortest_path_length(
            G, source=id_node_subgraph, weight="imp"
        )

        for k, v in shortest_paths.items():
            if v <= subgraph_value:
                nearnodes[k] = v

        Edges = []
        for node in nearnodes.keys():
            Edges += list(G.edges(node))

        Cedges = []
        for e in Edges:
            if e[0] in nearnodes.keys() and e[1] in nearnodes.keys():
                Cedges.append(e)

        C = nx.Graph()
        C.add_nodes_from(nearnodes)
        C.add_edges_from(Cedges)

        # Get edge properties
        # Get range color
        max_pa = 0
        min_pa = 99999999
        for s, d in C.edges():
            prev_dict = G.get_edge_data(s, d)
            if prev_dict["pa"] > max_pa:
                max_pa = prev_dict["pa"]
            if prev_dict["pa"] < min_pa:
                min_pa = prev_dict["pa"]

        max_pa -= min_pa
        for s, d in C.edges():
            prev_dict = G.get_edge_data(s, d)

            c = prev_dict["pa"] - min_pa
            g = 256 - (c / max_pa) * 256
            r = 255
            b = 0

            str_rgb = "rgb(" + str(r) + "," + str(g) + "," + str(b) + ")"

            C.add_edge(
                s, d, value=prev_dict["value"], id=prev_dict["id"], color=str_rgb
            )

        for n, v in nearnodes.items():
            title = "Impedance from the root = " + str(v) + "<br>"
            Cnedges = C.edges(n)
            for e in Cnedges:
                prev_dict = G.get_edge_data(e[0], e[1])
                title = (
                    title
                    + "("
                    + e[0]
                    + ","
                    + e[1]
                    + "): id = "
                    + prev_dict["id"]
                    + ", Y = "
                    + str(prev_dict["value"])
                    + ", Pa = "
                    + str(prev_dict["pa"])
                    + "<br>"
                )
            C.nodes[n]["title"] = title

    return C
