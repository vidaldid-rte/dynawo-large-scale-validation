import argparse
import os
import sys
import shutil

from lxml import etree


HDS_INPUT = "entreeHades.xml"
OLF_INPUT = "entreeOLF.xiidm"

parser = argparse.ArgumentParser()

parser.add_argument(
    "preprocess_file",
    help="file containing the preprocessing directives (list of groups to remove from voltage control)"
)

parser.add_argument(
    "case_dir",
    help="directory containing the network case"
)

args = parser.parse_args()

preprocess_file = args.preprocess_file
case_dir = args.case_dir

def main():
    toRemove = set(read_preprocess(preprocess_file))
    print("Groups to remove from voltage control: ", toRemove)
    hades_file =  os.path.join(case_dir, HDS_INPUT)
    olf_file =  os.path.join(case_dir, OLF_INPUT)
    shutil.copyfile(hades_file, hades_file + ".orig")
    shutil.copyfile(olf_file, olf_file + ".orig")
    hades_tree = etree.parse(hades_file, etree.XMLParser(remove_blank_text=True))

    root = hades_tree.getroot()
    reseau = root.find("./reseau", root.nsmap)
    donneesGroupes = reseau.find("./donneesGroupes", root.nsmap)
    for g in donneesGroupes.iterfind("./groupe", root.nsmap):
        if g.get("nom") in toRemove:
            print("Found " + g.get("nom"))
            g.set("regten", "false")
            g.set("regRemote", "false")

    hades_tree.write(
            hades_file,
            pretty_print=True,
            xml_declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
            encoding="ISO-8859-1",
            standalone=False,
    )

    olf_tree = etree.parse(olf_file, etree.XMLParser(remove_blank_text=True))
    root = olf_tree.getroot()
    for generator in root.iterfind(".//iidm:generator", root.nsmap):
        if generator.get("id") in toRemove:
            print("Found " + generator.get("id"))
            generator.set("voltageRegulatorOn", "false")

    olf_tree.write(
        olf_file,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
        standalone=False,
    )

def read_preprocess(preprocess_file) :
    file = open(preprocess_file, 'r')
    tokens = [l.strip() for l in file.readlines()]
    return [t for t in tokens if len(t) > 0 and t[0] != '#']


if __name__ == "__main__":
    sys.exit(main())