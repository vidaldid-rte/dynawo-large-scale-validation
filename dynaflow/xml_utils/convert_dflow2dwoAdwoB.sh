#!/bin/bash
#
#
# convert_dflow2dwoAdwoB.sh: given a base directory containing a DynaFlow
# case that follows RTE filename conventions, rearrange filenames and
# paths in order to prepare a case with separate A/B subdirectories
# and A/B JOB files, suitable for the dynawo-vs-dynawo pipeline.
#
# (c) Grupo AIA
# marinjl@aia.es
#
#
# NOTES:
# The script performs the following steps:
#
#   0. The new case will be under "<inputcase>.DWODWO"
#
#   1. Create the A or B subdir, then:
#        - copy the iidm, dyd, par, crv files there
#        - copy the Solver.par there
#        - copy the Diagrams dir there (renamed to "Diagrams")
#
#  2. Copy the job file to file JOB_A.xml or JOB_B.xml.  Then edit
#     the paths to the iidm, dyd, par, crv files.
#
#  3. Copy the content of Network.par to the end of A/*.par or B/*.par
#     file. Then edit the JOB files to reflect that change.
#
#  4. In the dyd file, edit the paths to the par file, as in this example:
#       sed -i.BAK 's%parFile="recollement_20210422_0930.par"%parFile="A/recollement_20210422_0930.par"%' recollement_20210422_0930.dyd
#
#  5. In the par file, edit the paths to the Diagram subdir, as in this example:
#       sed -i.BAK 's%value="recollement_20210422_0930_Diagram/%value="A/Diagrams/%' recollement_20210422_0930.par
#


# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 CASEDIR A|B

  Example: $0 20210422_0930/ A
    (will prepare the case as case A in directory 20210422_0930.DWODWO)

EOF
}



if [ $# -ne 2 ]; then
    usage
    exit -1
fi
CASEDIR="$1"
LABEL="$2"
if ! [ -d "$CASEDIR" ]; then
    echo "Case directory $CASEDIR not found"
    usage
    exit -1
fi
if [ "$LABEL" != "A" ] && [ "$LABEL" != "B" ]; then
    echo "Please specify a label for the case: A or B"
    usage
    exit -1
fi


########################################################################
#  Step 0: The new case will be under "<inputcase>.DWODWO"
########################################################################
DWODWO_CASE="$CASEDIR".DWODWO


########################################################################
#   1. Create the A or B subdir, then:
#        - copy the iidm, dyd, crv files there (par file later below)
#        - copy the solver.par there
#        - copy the _Diagram dir there (renamed to "Diagrams")
########################################################################
mkdir -p "$DWODWO_CASE/$LABEL"
CASENAME=$(basename "$CASEDIR"/*.jobs ".jobs")
cp -a "$CASEDIR/$CASENAME".{xiidm,dyd,crv} "$DWODWO_CASE/$LABEL"/
cp -a "$CASEDIR"/solver.par "$DWODWO_CASE/$LABEL"/
cp -a "$CASEDIR/$CASENAME"_Diagram "$DWODWO_CASE/$LABEL"/Diagrams


########################################################################
#  2. Copy the job file to either JOB_A.xml or JOB_B.xml.  Then edit the
#     paths to the iidm, dyd, par, crv files.
########################################################################
sed -e "s%parFile=\"solver.par\"%parFile=\"$LABEL/solver.par\"%" \
    -e "s%compileDir=\"outputs/compilation\"%compileDir=\"$LABEL/outputs/compilation\"%" \
    -e "s%iidmFile=\"$CASENAME.xiidm\"%iidmFile=\"$LABEL/$CASENAME.xiidm\"%" \
    -e "s%parFile=\"Network.par\"%parFile=\"$LABEL/$CASENAME.par\"%" \
    -e "s%dydFile=\"$CASENAME.dyd\"%dydFile=\"$LABEL/$CASENAME.dyd\"%" \
    -e "s%directory=\"outputs\"%directory=\"$LABEL/outputs\"%" \
    -e "s%inputFile=\"$CASENAME.crv\"%inputFile=\"$LABEL/$CASENAME.crv\"%" \
    "$CASEDIR/$CASENAME".jobs > "$DWODWO_CASE/JOB_$LABEL".xml


########################################################################
#  3. Merge the contents of Network.par and $CASENAME.par into the
#     A/*.par or B/*.par file.
########################################################################
awk '/<\/parametersSet>/ {p=1}; {if(p!=1) print}' "$CASEDIR/$CASENAME".par > "$DWODWO_CASE/$LABEL/$CASENAME".par
awk '/<set / {p=1}; {if(p==1) print}' "$CASEDIR"/Network.par >> "$DWODWO_CASE/$LABEL/$CASENAME".par


########################################################################
#  4. In the dyd file, edit the paths to the par file, as in this example:
########################################################################
sed -i -e "s%parFile=\"$CASENAME.par\"%parFile=\"$LABEL/$CASENAME.par\"%" "$DWODWO_CASE/$LABEL/$CASENAME".dyd

########################################################################
#  5. In the par file, edit the paths to the Diagram subdir, as in this example:
########################################################################
sed -i -e "s%value=\"$CASENAME""_Diagram/%value=\"$LABEL/Diagrams/%" "$DWODWO_CASE/$LABEL/$CASENAME".par

