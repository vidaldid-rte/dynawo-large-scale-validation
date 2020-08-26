#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from lxml import etree


def main():
    if len(sys.argv) != 2:
        print("\nUsage: %s xmlfile\n" % sys.argv[0])
        return 2

    tree = etree.parse(sys.argv[1])
    # DEBUG: print(etree.tostring(tree, pretty_print=True, encoding='unicode'))

    root = tree.getroot()
    print("# List of all Loads:")
    for element in root.iter(tag=etree.Element):
        tag = etree.QName(element).localname
        if tag == "dynanoeud":  # Astre loads?
            print(xstr(element.getparent().get("nom")))

    return 0


def xstr(s):
    if s is None:
        return ""
    return '"' + str(s) + '"'


if __name__ == "__main__":
    sys.exit(main())
