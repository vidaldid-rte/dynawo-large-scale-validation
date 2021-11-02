#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# extract_dynawo_automata_changes.py

import os
import math
import sys
import pandas as pd
import copy
import argparse
import lzma
from lxml import etree
from collections import namedtuple

sys.path.insert(
    1, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

parser = argparse.ArgumentParser()

parser.add_argument("xml_BASECASE", help="enter xml base case of Hades")
parser.add_argument("xml_CONTGCASE", help="enter xml contg case of Hades")

args = parser.parse_args()


def main():
    xml_BASECASE = args.xml_BASECASE
    xml_CONTGCASE = args.xml_CONTGCASE

    dwo_basecase_tree = etree.parse(
        xml_BASECASE, etree.XMLParser(remove_blank_text=True)
    )
    dwo_contgcase_tree = etree.parse(
        lzma.open(xml_CONTGCASE), etree.XMLParser(remove_blank_text=True)
    )

    # BASECASE

    root = dwo_basecase_tree.getroot()
    ns = etree.QName(root).namespace

    dynawo_ratioTapChanger_basecase = dict()
    for ratioTapChanger in root.iter("{%s}ratioTapChanger" % ns):
        ratioTapChanger_id = ratioTapChanger.getparent().get("id")
        if ratioTapChanger_id not in dynawo_ratioTapChanger_basecase:
            dynawo_ratioTapChanger_basecase[ratioTapChanger_id] = int(ratioTapChanger.get("tapPosition"))
        else:
            raise ValueError(f"Tap ID repeated")

    dynawo_phaseTapChanger_basecase = dict()
    for phaseTapChanger in root.iter("{%s}phaseTapChanger" % ns):
        phaseTapChanger_id = phaseTapChanger.getparent().get("id")
        if phaseTapChanger_id not in dynawo_phaseTapChanger_basecase:
            dynawo_phaseTapChanger_basecase[phaseTapChanger_id] = int(phaseTapChanger.get("tapPosition"))
        else:
            raise ValueError(f"Tap ID repeated")
    
    dynawo_shunt_basecase = dict()     
    for shunt in root.iter("{%s}shunt" % ns):
        if shunt.get("bus") is not None:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_basecase:
                dynawo_shunt_basecase[shunt_id] = 1
            else:
                raise ValueError(f"Tap ID repeated")
        else:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_basecase:
                dynawo_shunt_basecase[shunt_id] = 0
            else:
                raise ValueError(f"Tap ID repeated")
     
    dynawo_branch_basecase_bus1 = dict()  
    dynawo_branch_basecase_bus2 = dict()     
    for line in root.iter("{%s}line" % ns):
        temp = [0,0]
        line_id = line.get("id")
        if line.get("bus1") is not None:
            temp[0] = 1
        if line.get("bus2") is not None:
            temp[1] = 1
        if line_id not in dynawo_branch_basecase_bus1:
            dynawo_branch_basecase_bus1[line_id] = temp[0]  
        else:
            raise ValueError(f"Tap ID repeated")
        if line_id not in dynawo_branch_basecase_bus2:
            dynawo_branch_basecase_bus2[line_id] = temp[1]  
        else:
            raise ValueError(f"Tap ID repeated")
      
    for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
        temp = [0,0]
        twoWindingsTransformer_id = twoWindingsTransformer.get("id")
        if twoWindingsTransformer.get("bus1") is not None:
            temp[0] = 1
        if twoWindingsTransformer.get("bus2") is not None:
            temp[1] = 1
        if twoWindingsTransformer_id not in dynawo_branch_basecase_bus1:
            dynawo_branch_basecase_bus1[twoWindingsTransformer_id] = temp[0]  
        else:
            raise ValueError(f"Tap ID repeated")
        if twoWindingsTransformer_id not in dynawo_branch_basecase_bus2:
            dynawo_branch_basecase_bus2[twoWindingsTransformer_id] = temp[1]  
        else:
            raise ValueError(f"Tap ID repeated")       

    # CONTG
    
    root = dwo_contgcase_tree.getroot()
    ns = etree.QName(root).namespace

    dynawo_ratioTapChanger_contgcase = dict()
    for ratioTapChanger in root.iter("{%s}ratioTapChanger" % ns):
        ratioTapChanger_id = ratioTapChanger.getparent().get("id")
        if ratioTapChanger_id not in dynawo_ratioTapChanger_contgcase:
            dynawo_ratioTapChanger_contgcase[ratioTapChanger_id] = int(ratioTapChanger.get("tapPosition"))
        else:
            raise ValueError(f"Tap ID repeated")

    dynawo_phaseTapChanger_contgcase = dict()
    for phaseTapChanger in root.iter("{%s}phaseTapChanger" % ns):
        phaseTapChanger_id = phaseTapChanger.getparent().get("id")
        if phaseTapChanger_id not in dynawo_phaseTapChanger_contgcase:
            dynawo_phaseTapChanger_contgcase[phaseTapChanger_id] = int(phaseTapChanger.get("tapPosition"))
        else:
            raise ValueError(f"Tap ID repeated")
    
    dynawo_shunt_contgcase = dict()     
    for shunt in root.iter("{%s}shunt" % ns):
        if shunt.get("bus") is not None:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_contgcase:
                dynawo_shunt_contgcase[shunt_id] = 1
            else:
                raise ValueError(f"Tap ID repeated")
        else:
            shunt_id = shunt.get("id")
            if shunt_id not in dynawo_shunt_contgcase:
                dynawo_shunt_contgcase[shunt_id] = 0
            else:
                raise ValueError(f"Tap ID repeated")
     
    dynawo_branch_contgcase_bus1 = dict()  
    dynawo_branch_contgcase_bus2 = dict()     
    for line in root.iter("{%s}line" % ns):
        temp = [0,0]
        line_id = line.get("id")
        if line.get("bus1") is not None:
            temp[0] = 1
        if line.get("bus2") is not None:
            temp[1] = 1
        if line_id not in dynawo_branch_contgcase_bus1:
            dynawo_branch_contgcase_bus1[line_id] = temp[0]  
        else:
            raise ValueError(f"Tap ID repeated")
        if line_id not in dynawo_branch_contgcase_bus2:
            dynawo_branch_contgcase_bus2[line_id] = temp[1]  
        else:
            raise ValueError(f"Tap ID repeated")
      
    for twoWindingsTransformer in root.iter("{%s}twoWindingsTransformer" % ns):
        temp = [0,0]
        twoWindingsTransformer_id = twoWindingsTransformer.get("id")
        if twoWindingsTransformer.get("bus1") is not None:
            temp[0] = 1
        if twoWindingsTransformer.get("bus2") is not None:
            temp[1] = 1
        if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus1:
            dynawo_branch_contgcase_bus1[twoWindingsTransformer_id] = temp[0]  
        else:
            raise ValueError(f"Tap ID repeated")
        if twoWindingsTransformer_id not in dynawo_branch_contgcase_bus2:
            dynawo_branch_contgcase_bus2[twoWindingsTransformer_id] = temp[1]  
        else:
            raise ValueError(f"Tap ID repeated")
            

    # MATCHING
    data_keys = dynawo_ratioTapChanger_basecase.keys()
    data_list = dynawo_ratioTapChanger_basecase.values()
    df_dynawo_ratioTapChanger_basecase = pd.DataFrame(data=data_list, index=data_keys, columns=["TAP_VAL"])
    
    data_keys = dynawo_phaseTapChanger_basecase.keys()
    data_list = dynawo_phaseTapChanger_basecase.values()
    df_dynawo_phaseTapChanger_basecase = pd.DataFrame(data=data_list, index=data_keys, columns=["PSTAP_VAL"])
    
    data_keys = dynawo_shunt_basecase.keys()
    data_list = dynawo_shunt_basecase.values()
    df_dynawo_shunt_basecase = pd.DataFrame(data=data_list, index=data_keys, columns=["SHUNT_CHG_VAL"])
    
    data_keys = dynawo_branch_basecase_bus1.keys()
    data_list = dynawo_branch_basecase_bus1.values()
    df_dynawo_branch_basecase_bus1 = pd.DataFrame(data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"])
    
    data_keys = dynawo_branch_basecase_bus2.keys()
    data_list = dynawo_branch_basecase_bus2.values()
    df_dynawo_branch_basecase_bus2 = pd.DataFrame(data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"])
    
    data_keys = dynawo_ratioTapChanger_contgcase.keys()
    data_list = dynawo_ratioTapChanger_contgcase.values()
    df_dynawo_ratioTapChanger_contgcase = pd.DataFrame(data=data_list, index=data_keys, columns=["TAP_VAL"])
    
    data_keys = dynawo_phaseTapChanger_contgcase.keys()
    data_list = dynawo_phaseTapChanger_contgcase.values()
    df_dynawo_phaseTapChanger_contgcase = pd.DataFrame(data=data_list, index=data_keys, columns=["PSTAP_VAL"])
    
    data_keys = dynawo_shunt_contgcase.keys()
    data_list = dynawo_shunt_contgcase.values()
    df_dynawo_shunt_contgcase = pd.DataFrame(data=data_list, index=data_keys, columns=["SHUNT_CHG_VAL"])
    
    data_keys = dynawo_branch_contgcase_bus1.keys()
    data_list = dynawo_branch_contgcase_bus1.values()
    df_dynawo_branch_contgcase_bus1 = pd.DataFrame(data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_1"])
    
    data_keys = dynawo_branch_contgcase_bus2.keys()
    data_list = dynawo_branch_contgcase_bus2.values()
    df_dynawo_branch_contgcase_bus2 = pd.DataFrame(data=data_list, index=data_keys, columns=["TOPO_CHG_VAL_2"])    
    
    
    df_dynawo_ratioTapChanger_diff = copy.deepcopy(df_dynawo_ratioTapChanger_basecase)
    
    df_dynawo_phaseTapChanger_diff = copy.deepcopy(df_dynawo_phaseTapChanger_basecase)
    
    df_dynawo_shunt_diff = copy.deepcopy(df_dynawo_shunt_basecase)
    
    df_dynawo_branch_diff_1 = copy.deepcopy(df_dynawo_branch_contgcase_bus1)
    
    df_dynawo_branch_diff_2 = copy.deepcopy(df_dynawo_branch_contgcase_bus2)




    df_dynawo_ratioTapChanger_diff["DIFF"] = df_dynawo_ratioTapChanger_basecase["TAP_VAL"] - df_dynawo_ratioTapChanger_contgcase["TAP_VAL"]
    
    df_dynawo_ratioTapChanger_diff["DIFF_ABS"] = df_dynawo_ratioTapChanger_diff["DIFF"].abs()
    
    df_dynawo_ratioTapChanger_diff.loc[df_dynawo_ratioTapChanger_diff['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_dynawo_ratioTapChanger_diff.loc[df_dynawo_ratioTapChanger_diff['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_dynawo_ratioTapChanger_diff["DIFF_POS"] = df_dynawo_ratioTapChanger_diff['DIFF']
    df_dynawo_ratioTapChanger_diff.loc[df_dynawo_ratioTapChanger_diff['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_dynawo_ratioTapChanger_diff["DIFF_NEG"] = df_dynawo_ratioTapChanger_diff['DIFF'] 
    df_dynawo_ratioTapChanger_diff.loc[df_dynawo_ratioTapChanger_diff['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    
    
    df_dynawo_phaseTapChanger_diff["DIFF"] = df_dynawo_phaseTapChanger_basecase["PSTAP_VAL"] - df_dynawo_phaseTapChanger_contgcase["PSTAP_VAL"]
    
    df_dynawo_phaseTapChanger_diff["DIFF_ABS"] = df_dynawo_phaseTapChanger_diff["DIFF"].abs()
    
    df_dynawo_phaseTapChanger_diff.loc[df_dynawo_phaseTapChanger_diff['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_dynawo_phaseTapChanger_diff.loc[df_dynawo_phaseTapChanger_diff['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_dynawo_phaseTapChanger_diff["DIFF_POS"] = df_dynawo_phaseTapChanger_diff['DIFF']
    df_dynawo_phaseTapChanger_diff.loc[df_dynawo_phaseTapChanger_diff['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_dynawo_phaseTapChanger_diff["DIFF_NEG"] = df_dynawo_phaseTapChanger_diff['DIFF'] 
    df_dynawo_phaseTapChanger_diff.loc[df_dynawo_phaseTapChanger_diff['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    
    
    df_dynawo_shunt_diff["DIFF"] = df_dynawo_shunt_basecase["SHUNT_CHG_VAL"] - df_dynawo_shunt_contgcase["SHUNT_CHG_VAL"]
    
    df_dynawo_shunt_diff["DIFF_ABS"] = df_dynawo_shunt_diff["DIFF"].abs()
    
    df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_dynawo_shunt_diff["DIFF_POS"] = df_dynawo_shunt_diff['DIFF']
    df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_dynawo_shunt_diff["DIFF_NEG"] = df_dynawo_shunt_diff['DIFF'] 
    df_dynawo_shunt_diff.loc[df_dynawo_shunt_diff['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    
    
    df_dynawo_branch_diff_1["DIFF"] = df_dynawo_branch_basecase_bus1["TOPO_CHG_VAL_1"] - df_dynawo_branch_contgcase_bus1["TOPO_CHG_VAL_1"]
    
    df_dynawo_branch_diff_1["DIFF_ABS"] = df_dynawo_branch_diff_1["DIFF"].abs()
    
    df_dynawo_branch_diff_1.loc[df_dynawo_branch_diff_1['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_dynawo_branch_diff_1.loc[df_dynawo_branch_diff_1['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_dynawo_branch_diff_1["DIFF_POS"] = df_dynawo_branch_diff_1['DIFF']
    df_dynawo_branch_diff_1.loc[df_dynawo_branch_diff_1['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_dynawo_branch_diff_1["DIFF_NEG"] = df_dynawo_branch_diff_1['DIFF'] 
    df_dynawo_branch_diff_1.loc[df_dynawo_branch_diff_1['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    
    
    df_dynawo_branch_diff_2["DIFF"] = df_dynawo_branch_basecase_bus2["TOPO_CHG_VAL_2"] - df_dynawo_branch_contgcase_bus2["TOPO_CHG_VAL_2"]
    
    df_dynawo_branch_diff_2["DIFF_ABS"] = df_dynawo_branch_diff_2["DIFF"].abs()
    
    df_dynawo_branch_diff_2.loc[df_dynawo_branch_diff_2['DIFF_ABS'] != 0, 'HAS_CHANGED'] = 1 
    df_dynawo_branch_diff_2.loc[df_dynawo_branch_diff_2['DIFF_ABS'] == 0, 'HAS_CHANGED'] = 0
    
    df_dynawo_branch_diff_2["DIFF_POS"] = df_dynawo_branch_diff_2['DIFF']
    df_dynawo_branch_diff_2.loc[df_dynawo_branch_diff_2['DIFF'] <= 0, 'DIFF_POS'] = 0
    
    df_dynawo_branch_diff_2["DIFF_NEG"] = df_dynawo_branch_diff_2['DIFF'] 
    df_dynawo_branch_diff_2.loc[df_dynawo_branch_diff_2['DIFF'] >= 0, 'DIFF_NEG'] = 0 
    
    
    
    print("TOTAL DIFFS ratioTapChanger")
    print(sum(df_dynawo_ratioTapChanger_diff["DIFF_ABS"]))
    print("TOTAL CHANGES ratioTapChanger")
    print(sum(df_dynawo_ratioTapChanger_diff["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS ratioTapChanger")
    print(sum(df_dynawo_ratioTapChanger_diff["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS ratioTapChanger")
    print(sum(df_dynawo_ratioTapChanger_diff["DIFF_NEG"]))
    
    print("\n\n\nTOTAL DIFFS phaseTapChanger")
    print(sum(df_dynawo_phaseTapChanger_diff["DIFF_ABS"]))
    print("TOTAL CHANGES phaseTapChanger")
    print(sum(df_dynawo_phaseTapChanger_diff["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS phaseTapChanger")
    print(sum(df_dynawo_phaseTapChanger_diff["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS phaseTapChanger")
    print(sum(df_dynawo_phaseTapChanger_diff["DIFF_NEG"]))
    
    print("\n\n\nTOTAL DIFFS shunt")
    print(sum(df_dynawo_shunt_diff["DIFF_ABS"]))
    print("TOTAL CHANGES shunt")
    print(sum(df_dynawo_shunt_diff["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS shunt")
    print(sum(df_dynawo_shunt_diff["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS shunt")
    print(sum(df_dynawo_shunt_diff["DIFF_NEG"]))
    
    print("\n\n\nTOTAL DIFFS branch_bus1")
    print(sum(df_dynawo_branch_diff_1["DIFF_ABS"]))
    print("TOTAL CHANGES branch_bus1")
    print(sum(df_dynawo_branch_diff_1["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS branch_bus1")
    print(sum(df_dynawo_branch_diff_1["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS branch_bus1")
    print(sum(df_dynawo_branch_diff_1["DIFF_NEG"]))
    
    print("\n\n\nTOTAL DIFFS branch_bus2")
    print(sum(df_dynawo_branch_diff_2["DIFF_ABS"]))
    print("TOTAL CHANGES branch_bus2")
    print(sum(df_dynawo_branch_diff_2["HAS_CHANGED"]))
    print("TOTAL POSITIVE DIFFS branch_bus2")
    print(sum(df_dynawo_branch_diff_2["DIFF_POS"]))
    print("TOTAL NEGATIVE DIFFS branch_bus2")
    print(sum(df_dynawo_branch_diff_2["DIFF_NEG"]))

    
if __name__ == "__main__":
    sys.exit(main())
