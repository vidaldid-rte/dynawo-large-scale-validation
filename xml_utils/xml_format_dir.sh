#!/bin/bash
#
#
# xml_format_dir.sh: given a base directory containing Dynawo+Astre
# cases, format all of them using xmllint. This is useful so that we
# can later parse with lxml ignoring whitespace and always obtaining
# the same indentation (for the benefit of seeing clean diffs).
#
# (c) Grupo AIA
# marinjl@aia.es
#
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 XMLCASEDIR

  Example: $0 PtFige-Lille/20190410_1200
    (will format all xml files and leave them under PtFige-Lille/20190410_1200.FORMATTED) 

  NOTE: you can control the indentation with the environment variable XMLLINT_INDENT.
  Example: XMLLINT_INDENT="   " $0 PtFige-Lille/20190410_1200
     (will indent using three spaces)

EOF
}



if [ $# -ne 1 ]; then
    usage
    exit -1
fi


DEST="$1.FORMATTED"
rm -rf $DEST
cp -a "$1" "$DEST"

find "$DEST" -type f -iname '*.xml' |  while read XMLFILE; do
    xmllint --format "$XMLFILE" > "$XMLFILE.FMT"
    mv "$XMLFILE.FMT" "$XMLFILE"
done

