#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     omsg@aia.es
#     marinjl@aia.es
#

import pandas as pd
import sys
import argparse
from lxml import etree
import networkx as nx
import math
from dynawo_validation.dynaflow.pipeline.dwo_jobinfo import (
    get_dwo_jobpaths,
    get_dwodwo_jobpaths,
)

THRESHOLD = 100

parser = argparse.ArgumentParser()
parser.add_argument(
    "dynawoautomata",
    help="Enter Dynawo Automata csv.xz file",
)

parser.add_argument(
    "basecase",
    help="Enter basecase dir",
)

parser.add_argument(
    "save_file",
    help="Enter the path and the name of the file to save",
)

parser.add_argument(
    "basecase_type",
    help="Enter 0 for dwo, 1 for dwoA or 2 for dwoB",
)

args = parser.parse_args()


def main():
    dynawoautomata = args.dynawoautomata
    basecase_dir = args.basecase
    basecase_type = args.basecase_type

    if basecase_dir[-1] != "/":
        basecase_dir = basecase_dir + "/"

    if basecase_type != "0" and basecase_type != "1" and basecase_type != "2":
        raise ValueError("Non-valid value for basecase_type")
    else:
        basecase_type = int(basecase_type)

    if basecase_type == 0:
        dwo_jobpaths = get_dwo_jobpaths(basecase_dir)
        iidm_file = basecase_dir + dwo_jobpaths.iidmFile
    elif basecase_type == 1:
        dwo_jobpathsA, dwo_jobpathsB = get_dwodwo_jobpaths(basecase_dir)
        iidm_file = basecase_dir + dwo_jobpathsA.iidmFile
    else:
        dwo_jobpathsA, dwo_jobpathsB = get_dwodwo_jobpaths(basecase_dir)
        iidm_file = basecase_dir + dwo_jobpathsB.iidmFile

    df = read_aut_changes(dynawoautomata)
    aut_df = filter_dwo_events(df)
    aut_df["BUS"] = define_buses(aut_df, iidm_file)
    for i in range(len(aut_df.index)):
        if len(aut_df.loc[i, "BUS"].split("%")) != 1:
            list_bus = aut_df.loc[i, "BUS"].split("%")
            aut_df.loc[i, "BUS"] = list_bus[0]
            aut_df.loc[len(aut_df.index)] = aut_df.loc[i, :]
            aut_df.loc[len(aut_df.index) - 1, "BUS"] = list_bus[1]

    graph = create_graph(iidm_file)
    small_distance_matrix = create_distance_matrix(graph, aut_df)
    groups = group_dwo_events(aut_df, small_distance_matrix)

    data_list = {
        "GROUP": [],
        "DEVICE_TYPE": [],
        "DEVICE": [],
        "TIME": [],
        "EVENT": [],
        "EVENT_MESSAGE": [],
        "BUS": [],
    }

    for i in range(len(groups)):
        for j in range(len(groups[i])):
            data_list["GROUP"].append(i)
            data_list["DEVICE_TYPE"].append(aut_df.loc[groups[i][j], "DEVICE_TYPE"])
            data_list["DEVICE"].append(
                aut_df.loc[groups[i][j], "DEVICE"] + "_" + str(i)
            )
            data_list["TIME"].append(aut_df.loc[groups[i][j], "TIME"])
            data_list["EVENT"].append(aut_df.loc[groups[i][j], "EVENT"])
            data_list["EVENT_MESSAGE"].append(aut_df.loc[groups[i][j], "EVENT_MESSAGE"])
            data_list["BUS"].append(aut_df.loc[groups[i][j], "BUS"])

    df_groups = pd.DataFrame(
        data=data_list,
    )

    save_file = args.save_file

    if save_file[-4:] != ".csv":
        save_file = save_file + ".csv"

    df_groups.to_csv(save_file, sep=";")


def read_aut_changes(aut_dir):
    data = pd.read_csv(aut_dir, sep=";")
    return data


def filter_dwo_events(df):
    aut_df = df.loc[
        (df.DEVICE_TYPE == "Transformer")
        | (df.DEVICE_TYPE == "Shunt")
        | (df.DEVICE_TYPE == "Generator")
        | (df.DEVICE_TYPE == "Line")
        | (df.DEVICE_TYPE == "Load")
    ]
    return aut_df


def define_buses(aut_df, iidm_file):
    iidmTree = etree.parse(iidm_file, etree.XMLParser(remove_blank_text=True))
    root = iidmTree.getroot()
    ns = etree.QName(root).namespace

    bus_names = []
    for df_i in range(len(aut_df.index)):
        if aut_df.loc[df_i, "DEVICE_TYPE"] == "Line":
            for line in root.iter("{%s}line" % ns):
                if line.get("id") == aut_df.loc[df_i, "DEVICE"]:
                    bus1 = line.get("connectableBus1")
                    if bus1 is not None:
                        bus2 = line.get("connectableBus2")
                        if bus2 is not None:
                            bus_names.append(bus1 + "%" + bus2)

        if aut_df.loc[df_i, "DEVICE_TYPE"] == "Transformer":
            for trans in root.iter("{%s}twoWindingsTransformer" % ns):
                if trans.get("id") == aut_df.loc[df_i, "DEVICE"]:
                    bus1 = trans.get("connectableBus1")
                    if bus1 is not None:
                        bus2 = trans.get("connectableBus2")
                        if bus2 is not None:
                            bus_names.append(bus1 + "%" + bus2)

        if aut_df.loc[df_i, "DEVICE_TYPE"] == "Shunt":
            for shunt in root.iter("{%s}shunt" % ns):
                if shunt.get("id") == aut_df.loc[df_i, "DEVICE"]:
                    bus = shunt.get("connectableBus")
                    if bus is not None:
                        bus_names.append(bus)

        if aut_df.loc[df_i, "DEVICE_TYPE"] == "Generator":
            for gen in root.iter("{%s}generator" % ns):
                if gen.get("id") == aut_df.loc[df_i, "DEVICE"]:
                    bus = gen.get("connectableBus")
                    if bus is not None:
                        bus_names.append(bus)

        if aut_df.loc[df_i, "DEVICE_TYPE"] == "Load":
            for load in root.iter("{%s}load" % ns):
                if load.get("id") == aut_df.loc[df_i, "DEVICE"]:
                    bus = load.get("connectableBus")
                    if bus is not None:
                        bus_names.append(bus)

    if len(bus_names) != len(aut_df.index):
        raise Exception("Some AUT IDs not found or disconnected in input file.")

    return bus_names


def create_graph(iidm_file):
    iidmTree = etree.parse(iidm_file, etree.XMLParser(remove_blank_text=True))

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

    return G


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


def create_distance_matrix(graph, aut_df):
    distance_matrix = []
    bool_error = False
    for df_i in range(len(aut_df.index)):
        distance_matrix.append([])
        for df_j in range(len(aut_df.index)):
            try:
                shortest_path = nx.shortest_path_length(
                    graph,
                    source=aut_df.loc[df_i, "BUS"],
                    target=aut_df.loc[df_j, "BUS"],
                    weight="imp",
                )
                distance_matrix[df_i].append(shortest_path)
            except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
                distance_matrix[df_i].append(float("Inf"))
                bool_error = True

    if bool_error:
        print(
            f"   WARNING: group_dwo_events: some nodes were unreachable (probably disconnected islands)"
        )

    return distance_matrix


def group_dwo_events(aut_df, small_distance_matrix):
    temp_list = list(range(len(aut_df.index)))
    fix_list = list(range(len(aut_df.index)))
    groups = []
    n_groups = 0
    for i in range(len(temp_list)):
        if temp_list[i] != "x":
            groups.append([])
            for j in range(len(aut_df.index)):
                if small_distance_matrix[fix_list[i]][j] < THRESHOLD:
                    temp_list[j] = "x"
                    groups[n_groups].append(j)
            n_groups += 1

    return groups


if __name__ == "__main__":
    sys.exit(main())
