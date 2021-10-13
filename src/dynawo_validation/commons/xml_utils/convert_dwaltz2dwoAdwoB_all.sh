#!/bin/bash
#
#
# convert_dwaltz2dwoAdwoB.sh: given a base directory containing a
# DynaFlow case that follows RTE filename conventions, rearrange
# filenames and paths in order to prepare a new case with separate A/B
# subdirectories and A/B JOB files, suitable for the dynawo-vs-dynawo
# pipeline. Note that you will have to run this script twice: once for
# A and another time for B (this is to allow for the usage of
# different cases).
#
# (c) Grupo AIA
#     marinjl@aia.es
#
#
# NOTES:
# The script performs the following steps:
#
#   0. The new case will be created under "<inputcase>.DWODWO"
#
#   1. Copies the case files to the A or B subdir, as chosen:
#        - copies the iidm, dyd, par, crv files there
#        - copies the Diagrams dir there
#
#   2. Copies the job file to either "JOB_A.xml" or "JOB_B.xml", and
#      edits its contents to reflect the new path to the iidm, dyd,
#      par, crv files.
#
#   3. In the dyd file, edits the paths to the par file
#
#   4. In the par file, edits the paths to the Diagram subdir
#


# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 CASE_DIR_A CASE_DIR_B

  Example: $0 20210422_0930 20210422_0930
    (will prepare the case as case A in directory 20210422_0930.DWODWO)

EOF
}



if [ $# -ne 2 ]; then
    usage
    exit -1
fi
CASE_DIR_A="${1%/}"  # remove a possible trailing slash
CASE_DIR_B="${2%/}"
if ! [ -d "$CASE_DIR_A" ]; then
    echo "Case directory $CASE_DIR_A not found"
    usage
    exit -1
fi
if ! [ -d "$CASE_DIR_B" ]; then
    echo "Case directory $CASE_DIR_B not found"
    usage
    exit -1
fi


########################################################################
#  Step 0: The new case will be created under "<inputcase>.DWODWO"
########################################################################
DWODWO_CASE="$CASE_DIR_A".DWODWO
LABEL=A
mkdir -p "$DWODWO_CASE/$LABEL"
echo "Preparing $LABEL case under:   $DWODWO_CASE/$LABEL"
LABEL=B
mkdir -p "$DWODWO_CASE/$LABEL"
echo "Preparing $LABEL case under:   $DWODWO_CASE/$LABEL"


########################################################################
#   1. Copy all case files (except the job file):
#        - the iidm, dyd, par, crv files
#        - the *_Diagram directory
########################################################################
echo -n "Copying elements... "
LABEL=A
find "$CASE_DIR_A" -type d -iname 't0' -exec cp -a '{}' "$DWODWO_CASE/$LABEL"/ \;
find "$CASE_DIR_A" -type d -iname 'tFin' -exec cp -a '{}' "$DWODWO_CASE/$LABEL"/ \;

LABEL=B
find "$CASE_DIR_B" -type d -iname 't0' -exec cp -a '{}' "$DWODWO_CASE/$LABEL"/ \;
find "$CASE_DIR_B" -type d -iname 'tFin' -exec cp -a '{}' "$DWODWO_CASE/$LABEL"/ \;
echo "OK."


########################################################################
#  2. Copy the job file to either JOB_A.xml or JOB_B.xml, while editing
#     the internal paths to the iidm, dyd, par, crv files.
########################################################################
echo -n "Editing the JOB file... "
LABEL=A
ORIG_JOB_FILE=$(find "$CASE_DIR_A" -type f \( -iname '*.jobs' -o -iname '*JOB.xml' \) | head -n1)
sed -e "s%compileDir=\"%compileDir=\"$LABEL/%" \
    -e "s%iidmFile=\"%iidmFile=\"$LABEL/%" \
    -e "s%parFile=\"%parFile=\"$LABEL/%" \
    -e "s%dydFile=\"%dydFile=\"$LABEL/%" \
    -e "s%directory=\"%directory=\"$LABEL/%" \
    -e "s%inputFile=\"%inputFile=\"$LABEL/%" \
    -e "s%initialState file=\"%initialState file=\"$LABEL/%" \
    "$ORIG_JOB_FILE" > "$DWODWO_CASE"/JOB_"$LABEL".xml

LABEL=B    
ORIG_JOB_FILE=$(find "$CASE_DIR_B" -type f \( -iname '*.jobs' -o -iname '*JOB.xml' \) | head -n1)
sed -e "s%compileDir=\"%compileDir=\"$LABEL/%" \
    -e "s%iidmFile=\"%iidmFile=\"$LABEL/%" \
    -e "s%parFile=\"%parFile=\"$LABEL/%" \
    -e "s%dydFile=\"%dydFile=\"$LABEL/%" \
    -e "s%directory=\"%directory=\"$LABEL/%" \
    -e "s%inputFile=\"%inputFile=\"$LABEL/%" \
    -e "s%initialState file=\"%initialState file=\"$LABEL/%" \
    "$ORIG_JOB_FILE" > "$DWODWO_CASE"/JOB_"$LABEL".xml
echo "OK."


########################################################################
#  3. In the dyd file, edit the paths to the par file
########################################################################
echo -n "Editing the DYD files... "
LABEL=A
DYD_FILE=$(find "$DWODWO_CASE/$LABEL/t0/" -type f -iname '*_DYD.xml')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE"

DYD_FILE=$(find "$DWODWO_CASE/$LABEL/tFin/" -type f -iname '*_DYD.xml')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE"

LABEL=B
DYD_FILE=$(find "$DWODWO_CASE/$LABEL/t0/" -type f -iname '*_DYD.xml')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE"

DYD_FILE=$(find "$DWODWO_CASE/$LABEL/tFin/" -type f -iname '*_DYD.xml')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE"

echo "OK."



