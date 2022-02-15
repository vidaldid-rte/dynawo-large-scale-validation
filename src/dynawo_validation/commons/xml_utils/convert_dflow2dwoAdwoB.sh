#!/bin/bash
#
#
# convert_dflow2dwoAdwoB.sh: given a base directory containing a
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

  Example: $0 20210422_0930/ A
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
DWODWO_CASE_A="$CASE_DIR_A".DWODWO
mkdir -p "$DWODWO_CASE_A"/A
echo "Preparing A case under:   $DWODWO_CASE_A/A"

mkdir -p "$DWODWO_CASE_A"/B
echo "Preparing B case under:   $DWODWO_CASE_A/B"


########################################################################
#   1. Copy all case files (except the job file):
#        - the iidm, dyd, par, crv files
#        - the *_Diagram directory
########################################################################
echo -n "Copying iidm, dyd, par, crv, and Diagrams... "
find "$CASE_DIR_A" -type f \
     \( -iname '*.*iidm' -o -iname '*.dyd' -o -iname '*.par' -o -iname '*.crv' \) \
     -exec cp -a '{}' "$DWODWO_CASE_A"/A/ \;
find "$CASE_DIR_A" -type d -iname '*_Diagram' -exec cp -a '{}' "$DWODWO_CASE_A"/A/ \;

echo -n "Copying iidm, dyd, par, crv, and Diagrams... "
find "$CASE_DIR_B" -type f \
     \( -iname '*.*iidm' -o -iname '*.dyd' -o -iname '*.par' -o -iname '*.crv' \) \
     -exec cp -a '{}' "$DWODWO_CASE_A"/B/ \;
find "$CASE_DIR_B" -type d -iname '*_Diagram' -exec cp -a '{}' "$DWODWO_CASE_A"/B/ \;
echo "OK."


########################################################################
#  2. Copy the job file to either JOB_A.xml or JOB_B.xml, while editing
#     the internal paths to the iidm, dyd, par, crv files.
########################################################################
echo -n "Editing the JOB file... "
LABEL=A
ORIG_JOB_FILE=$(find "$CASE_DIR_A" -type f \( -iname '*.jobs' -o -iname 'JOB*.xml' \) | head -n1)
sed -e "s%compileDir=\"%compileDir=\"$LABEL/%" \
    -e "s%iidmFile=\"%iidmFile=\"$LABEL/%" \
    -e "s%parFile=\"%parFile=\"$LABEL/%" \
    -e "s%dydFile=\"%dydFile=\"$LABEL/%" \
    -e "s%directory=\"%directory=\"$LABEL/%" \
    -e "s%inputFile=\"%inputFile=\"$LABEL/%" \
    "$ORIG_JOB_FILE" > "$DWODWO_CASE_A"/JOB_A.xml


LABEL=B
ORIG_JOB_FILE=$(find "$CASE_DIR_B" -type f \( -iname '*.jobs' -o -iname 'JOB*.xml' \) | head -n1)
sed -e "s%compileDir=\"%compileDir=\"$LABEL/%" \
    -e "s%iidmFile=\"%iidmFile=\"$LABEL/%" \
    -e "s%parFile=\"%parFile=\"$LABEL/%" \
    -e "s%dydFile=\"%dydFile=\"$LABEL/%" \
    -e "s%directory=\"%directory=\"$LABEL/%" \
    -e "s%inputFile=\"%inputFile=\"$LABEL/%" \
    "$ORIG_JOB_FILE" > "$DWODWO_CASE_A"/JOB_B.xml
echo "OK."

########################################################################
#  3. In the dyd file, edit the paths to the par file
########################################################################
echo -n "Editing the DYD file... "
LABEL=A
DYD_FILE_A_cont=$(find "$DWODWO_CASE_A/$LABEL" -type f -iname 'contingency.dyd')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE_A_cont"
DYD_FILE_A=$(find "$DWODWO_CASE_A/$LABEL" -type f -iname '*.dyd')
DYD_FILE_A=${DYD_FILE_A#"$DYD_FILE_A_cont"}
DYD_FILE_A=${DYD_FILE_A%"$DYD_FILE_A_cont"}
DYD_FILE_A=${DYD_FILE_A//$'\n'/} 
DYD_FILE_A=${DYD_FILE_A%$'\n'}
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE_A"


LABEL=B
echo -n "Editing the DYD file... "
DYD_FILE_B_cont=$(find "$DWODWO_CASE_A/$LABEL" -type f -iname 'contingency.dyd')
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE_B_cont"
DYD_FILE_B=$(find "$DWODWO_CASE_A/$LABEL" -type f -iname '*.dyd')
DYD_FILE_B=${DYD_FILE_B#"$DYD_FILE_B_cont"}
DYD_FILE_B=${DYD_FILE_B%"$DYD_FILE_B_cont"}
DYD_FILE_B=${DYD_FILE_B//$'\n'/} 
DYD_FILE_B=${DYD_FILE_B%$'\n'}
sed -i -e "s%parFile=\"%parFile=\"$LABEL/%" "$DYD_FILE_B"
echo "OK."


########################################################################
#  4. In the par file, edit the paths to the Diagram subdir
########################################################################
echo -n "Editing the PAR file... "
# there may be several par files; make sure we get only the main one
# we do it by searching the DYD for the first instance of parFile="somefilename.par"
LABEL=A
parFileAttr=$(grep -P -m1 -o 'parFile=\".*?\"' "$DYD_FILE_A")
PAR_FILE=$DWODWO_CASE_A/$(echo "$parFileAttr" | cut -d\" -f2)
DIAGRAM_DIR=$(find "$CASE_DIR_A" -type d -iname '*_Diagram')
DIAGRAM_DIR=$(basename "$DIAGRAM_DIR")
sed -i -e "s%value=\"$DIAGRAM_DIR/%value=\"$LABEL/$DIAGRAM_DIR/%" "$PAR_FILE"


LABEL=B
parFileAttr=$(grep -P -m1 -o 'parFile=\".*?\"' "$DYD_FILE_B")
PAR_FILE=$DWODWO_CASE_A/$(echo "$parFileAttr" | cut -d\" -f2)
DIAGRAM_DIR=$(find "$CASE_DIR_B" -type d -iname '*_Diagram')
DIAGRAM_DIR=$(basename "$DIAGRAM_DIR")
sed -i -e "s%value=\"$DIAGRAM_DIR/%value=\"$LABEL/$DIAGRAM_DIR/%" "$PAR_FILE"
echo "OK."


