#!/usr/bin/python3

import sys
import os
from lxml import etree
import csv

def create_curves(xmlname, csvname):

    if not os.path.isfile(xmlname):
        print(xmlname + " does not exist.")
        sys.exit(1)
    xml = etree.parse(xmlname)
    xml_root = xml.getroot()
    xml_namespace = xml_root.nsmap
    xml_prefix_root = xml_root.prefix
    xml_namespace_uri = xml_namespace[xml_prefix_root]
    if xml_prefix_root is None:
        xml_prefix_root_string = ''
    else:
        xml_prefix_root_string = xml_prefix_root + ':'

    csvfile = open(csvname, 'w')

    csvwriter = csv.writer(csvfile, delimiter=';', lineterminator='\n')

    csv_head = ["time"]
    for courbe in xml_root.findall('.//' + xml_prefix_root_string + 'courbe', xml_namespace):
        nom = courbe.get('nom')
        csv_head.append(nom)

    csvwriter.writerow(csv_head)

    times = []
    for time in xml_root.xpath("//*[local-name() = 'courbe'][1]/*[local-name() = 'point']"):
        times.append(time.attrib['t'])

    data = [times]
    for courbe in xml_root.xpath("//*[local-name() = 'courbe']"):
        points = []
        for point in courbe:
            points.append(point.attrib['val'])
        data.append(points)

    for row in zip(*data):
        csvwriter.writerow(row)

    csvfile.close()

def main():
    if len(sys.argv) > 2:
        xmlname = sys.argv[1]
        csvname = sys.argv[2]
        create_curves(xmlname, csvname)
    else:
        help()

def help():
    print("You need to give two arguments:")
    print("  First the path to the donneesModelesSortie xml file")
    print("  Second the csv path where you want the curves to be written")

    sys.exit(1)

if __name__ == '__main__':
    main()
