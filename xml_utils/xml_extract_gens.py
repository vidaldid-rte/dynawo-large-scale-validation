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
    print("# List of all Generators:")
    for element in root.iter(tag=etree.Element):
        tag = etree.QName(element).localname
        #if tag == "generator" and float(element.get("p")) > 80.0:  # Dynawo IIDM
        if tag == "generator":  # Dynawo IIDM
            print(
                xstr(element.get("id"))
                #+ "   (p=%s, q=%s)" % (element.get("p"), element.get("q"))
            )
        elif tag == "blackBoxModel" and element.get("lib")[0:9] == "Generator":  # Dynawo DYD
            print(
                 xstr(element.get("id"))
                 #+ "   (" + element.get("lib") + ")"
                 )
        elif tag == "groupe":  # Astre
            print(xstr(element.get("nom")))

    return 0


def xstr(s):
    if s is None:
        return ""
    return '"' + str(s) + '"'


if __name__ == "__main__":
    sys.exit(main())
