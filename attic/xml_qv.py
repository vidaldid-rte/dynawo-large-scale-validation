#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from lxml import etree


def main():
    if len(sys.argv) != 2:
        print("\nUsage: %s xmlfile\n" % sys.argv[0])
        return 2

    only_with_IDs = False

    tree = etree.parse(sys.argv[1])
    # DEBUG: print(etree.tostring(tree, pretty_print=True, encoding='unicode'))

    root = tree.getroot()

    print("\nTHE WHOLE TREE:")
    tag = etree.QName(root)
    print(tag.localname)
    print_xmltree(root, only_with_IDs=only_with_IDs)

    return 0


def print_xmltree(node, level=1, only_with_IDs=False):
    for child in node:
        if not isinstance(
            child.tag, str
        ):  # skip ProcessingInstructions, Comments, Entities
            continue
        if (
            only_with_IDs
            and level > 5
            and (child.get("id") is None and child.get("nom") is None)
        ):
            continue
        tag = etree.QName(child)
        print(
            "   " * level
            + tag.localname
            + xstr(child.get("id"))
            + xstr(child.get("nom"))
            + xstr(child.get("lib"))
        )
        if len(child):
            print_xmltree(child, level + 1, only_with_IDs)


def xstr(s):
    if s is None:
        return ""
    return '  "' + str(s) + '"'


if __name__ == "__main__":
    sys.exit(main())
