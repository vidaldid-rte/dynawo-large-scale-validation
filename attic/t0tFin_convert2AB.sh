#!/bin/bash
#
#
# t0tFin_convert2AB.sh: given a base directory containing a
# Dynawo-vs-Dynawo case with separate A/B subdirectories (t0_A, t0_B,
# tFin_A, tFin_B) and A/B JOB files, it converts the paths inside the
# JOB and DYD files to point to these directories, instead of the
# original t0 and tFin.
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

Usage: $0 CASEDIR

  Example: $0 PtFige-Lille/20190410_1200
    (will prepare the JOB and DYD files to point to the right t0_A, t0_B, tFin_A, tFin_B directories)

EOF
}



if [ $# -ne 1 ]; then
    usage
    exit -1
fi
CASEDIR="$1"

# Stop if the dir doesn't look like a Dynawo-vs-Dynawo case
if ! [ -d "$CASEDIR" ]; then
    echo "Case directory $CASEDIR not found"
    usage
    exit -1
fi
JOB_A=$(find "$CASEDIR" -maxdepth 1 -iname '*JOB_A*.XML')
JOB_B=$(find "$CASEDIR" -maxdepth 1 -iname '*JOB_B*.XML')
if [ -z "$JOB_A" ] || [ -z "$JOB_B" ]; then
    echo "JOB_A or JOB_B files are missing."
    usage
    exit -1
fi
if [ ! -d "$CASEDIR"/t0_A ] || [ ! -d "$CASEDIR"/tFin_A ] || \
   [ ! -d "$CASEDIR"/t0_B ] || [ ! -d "$CASEDIR"/tFin_B ]; then
    echo "Some directory (t0_A, t0_B, tFin_A, tFin_B) was not found."
    usage
    exit -1
fi

# Perform the string replacements
sed -i.BAK -e 's/t0/t0_A/g' -e 's/tFin/tFin_A/g' "$JOB_A"
sed -i.BAK -e 's/t0/t0_B/g' -e 's/tFin/tFin_B/g' "$JOB_B"
sed -i.BAK -e 's%t0/%t0_A/%g' "$CASEDIR"/t0_A/fic_DYD.xml
sed -i.BAK -e 's%t0/%t0_B/%g' "$CASEDIR"/t0_B/fic_DYD.xml
sed -i.BAK -e 's%tFin/%tFin_A/%g' "$CASEDIR"/tFin_A/fic_DYD.xml
sed -i.BAK -e 's%tFin/%tFin_B/%g' "$CASEDIR"/tFin_B/fic_DYD.xml

