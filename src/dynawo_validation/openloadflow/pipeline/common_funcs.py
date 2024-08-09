# Common functions for all contingency-generating scripts
import os
import sys
import subprocess
from lxml import etree
from collections import namedtuple

def copy_basecase(base_case, iidm_file, hades_file, param_file, dest_case):
    """Make the subdirs for the Hades and OLF cases; then copy all non-changed
    files using symbolic links

    """
    # If the destination exists, first remove it
    if os.path.exists(dest_case):
        remove_case(dest_case)

    # In the result dir layout, base file and contingencies are at the same level
    # Using relative path enables to copy the result dir as a standalone thing
    case_dir = "../" + os.path.basename(base_case)
    iidm_source =  os.path.join(case_dir, iidm_file)
    hades_source = os.path.join(case_dir, hades_file)
    param_source = os.path.join(case_dir, param_file)

    # Compose and execute the shell commands
    bc = base_case
    full_command = (
        f" mkdir -p '{dest_case}'"
        f" && ln -s '{iidm_source}' '{dest_case}'"
        f" && ln -s '{hades_source}' '{dest_case}'"
        f" && ln -s '{param_source}' '{dest_case}'"
    )
    try:
        retcode = subprocess.call(full_command, shell=True)
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def remove_case(dest_case):
    try:
        retcode = subprocess.call("rm -rf '%s'" % dest_case, shell=True)
        if retcode < 0:
            raise ValueError("rm of bad case was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("rm of bad case returned error code: %d" % retcode)
    except OSError as e:
        print("call to rm failed: ", e, file=sys.stderr)
        raise


def parse_basecase(base_case, hades_file, olf_file):
    Parsed_case = namedtuple(
        "Parsed_case",
        "hades_tree olf_tree",
    )

    hades_tree = etree.parse(
        os.path.join(base_case, hades_file), etree.XMLParser(remove_blank_text=True)
    )

    olf_tree = etree.parse(
        os.path.join(base_case, olf_file),
        etree.XMLParser(remove_blank_text=True),
    )

    return Parsed_case(
        hades_tree=hades_tree,
        olf_tree=olf_tree,
    )

def disconnect_vl_item_from_node(vl_item, root):
    vl = vl_item.getparent()
    topoElt = vl.find(".//iidm:nodeBreakerTopology", root.nsmap)
    tag = etree.QName(root.nsmap.get("iidm"), "switch")
    switch = etree.SubElement(topoElt, tag)
    switch.set("id", "broken")
    switch.set("name", "broken")
    switch.set("node2", "999")
    switch.set("node1", "0")
    switch.set("open", "true")
    switch.set("retained", "false")
    switch.set("kind", "BREAKER")
    topoElt.append(switch)
    item_node = vl_item.get("node")
    vl_item.set("node", "999")
    return (switch, item_node)

def reconnect_vl_item_to_node(vl_item, switch, item_node):
    switch.getparent().remove(switch)
    vl_item.set("node", item_node)