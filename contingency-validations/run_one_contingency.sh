#!/bin/bash
#
#
# run_one_contingency.sh: given a directory containing a Dynawo+Astre
# case, run it and collect the results somewhere else. Optionally,
# delete the case to save space.
#
# (c) Grupo AIA
# marinjl@aia.es
#

# For saner programming:
set -o nounset  # here we don't set noclobber because we need it
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 [OPTIONS] BASE_CASE CONTINGENCY_CASE
  Options:
    -c | --cleanup  Delete the input case (both Astre & Dynawo) after getting the results
    -d | --debug    More debug messages
    -h | --help     This help message
    -o | --output   Specify a directory for collecting results (default: RESULTS)
    -v | --verbose  Mode verbose output

EOF
}



# -allow a command to fail with !’s side effect on errexit
# -use return value from ${PIPESTATUS[0]}, because ! hosed $?
! getopt --test > /dev/null 
if [[ ${PIPESTATUS[0]} -ne 4 ]]; then
    echo "I’m sorry, 'getopt --test' failed in this environment."
    exit 1
fi

OPTIONS=cdho:v
LONGOPTS=cleanup,debug,help,output:,verbose

# -regarding ! and PIPESTATUS see above
# -temporarily store output to be able to check for errors
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
! PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
    # e.g. return value is 1
    #  then getopt has complained about wrong arguments to stdout
    usage
    exit 2
fi
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

c=n d=n h=n outDir="RESULTS" v=n
# now enjoy the options in order and nicely split until we see --
while true; do
    case "$1" in
        -c|--cleanup)
            c=y
            shift
            ;;
        -d|--debug)
            d=y
            shift
            ;;
        -h|--help )
            h=y
            shift
            ;;
        -o|--output)
            outDir="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -v|--verbose)
            v=y
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            exit 3
            ;;
    esac
done

if [ $v = "y" ]; then
    echo "OPTIONS: cleanup: $c, debug: $d, help: $h, outDir: $outDir, verbose: $v"
    echo "PARAMS: $*"
fi

if [ $h = "y" ]; then
    usage
    exit 0
fi

# handle non-option arguments
if [[ $# -ne 2 ]]; then
    echo
    echo "$0: Two directory names are required."
    usage
    exit 4
fi

if [ $d = "y" ]; then
    set -o xtrace
fi



#######################################
# The real meat starts here
########################################
BASECASE=$1
CONTG_CASE=$2
if [ ! -d "$BASECASE" ]; then
   echo "ERROR: Basecase $BASECASE not found."
   exit 1
fi

if [ ! -d "$CONTG_CASE" ]; then
   echo "ERROR: Contingency case $CONTG_CASE not found."
   exit 1
fi
prefix=$(basename "$CONTG_CASE")

# Create the output dirs if they don't exist
mkdir -p "$outDir"/csv
mkdir -p "$outDir"/xml
mkdir -p "$outDir"/log
mkdir -p "$outDir"/casediffs

# Save the PWD to avoid having to deal with absolute/relative paths in outDir vs CONTG_CASE
OLD_PWD=$(pwd)



#################################################
# Save the case compactly as diffs from BASECASE
#################################################
DIFFS="$outDir"/casediffs/"$prefix"-patch
if diff -ru "$BASECASE" "$CONTG_CASE" > "$DIFFS"; then
    echo "ERROR: $BASECASE and $CONTG_CASE are identical."
    exit 1
fi
xz -9f "$DIFFS"

if [ ! -f "$outDir"/casediffs/README ]; then
    cat <<EOF >"$outDir"/casediffs/README
    To re-create the contingency case from these patch files:

       1.  cp -a BASECASE CONTG_CASE

       2.  cd CONTG_CASE

       3.  xzcat CONTG_CASE-patch.xz | patch -p1

    And then verify the result with:

       diff -r BASECASE CONTG_CASE

EOF
fi



########################################
# Run Astre
########################################
if [ ! -d "$CONTG_CASE"/Astre ]; then
   echo "Directory $CONTG_CASE/Astre not found."
   exit 1
fi
cd "$CONTG_CASE"/Astre
RUNLOG=Astre.runStdout
astre donneesModelesEntree.xml > "$RUNLOG" 2>&1
if [ ! -f donneesModelesSortie.csv ]; then
   echo "Astre run failed. Check the runlog: $CONTG_CASE/Astre/$RUNLOG"
   exit 1
fi

# TODO: launch here the extraction of EVENTS (from the xml to CSV)

# Collect and compress all results
cd "$OLD_PWD"
xz -c9 "$CONTG_CASE"/Astre/donneesModelesSortie.csv > "$outDir"/csv/"$prefix"-AstreSortie.csv.xz
xz -c9 "$CONTG_CASE"/Astre/donneesModelesSortie.xml > "$outDir"/xml/"$prefix"-AstreSortie.xml.xz
xz -c9 "$CONTG_CASE"/Astre/donneesModelesLog.xml    > "$outDir"/log/"$prefix"-AstreLog.xml.xz
xz -c9 "$CONTG_CASE"/Astre/"$RUNLOG"                > "$outDir"/log/"$prefix"-"$RUNLOG".xz



########################################
# Run Dynawo
########################################
if [ ! -f "$CONTG_CASE"/fic_JOB.xml ] || [ ! -d "$CONTG_CASE"/tFin ]; then
   echo "Dynawo input files not found under $CONTG_CASE/."
   exit 1
fi
cd "$CONTG_CASE"
RUNLOG=Dynawo.runStdout
dynawo-RTE jobs fic_JOB.xml > "$RUNLOG" 2>&1 || true  # allow it to fail while using errexit flag
if [ ! -f ./tFin/outputs/curves/curves.csv ]; then
   echo "Dynawo run failed. Check Dynawo's log and the run-log: $CONTG_CASE/$RUNLOG"
   exit 1
fi

# Collect and compress all results
cd "$OLD_PWD"
xz -c9 "$CONTG_CASE"/tFin/outputs/curves/curves.csv           > "$outDir"/csv/"$prefix"-Dynawo.csv.xz
xz -c9 "$CONTG_CASE"/tFin/outputs/constraints/constraints.xml > "$outDir"/xml/"$prefix"-DynawoConstraints.xml.xz
xz -c9 "$CONTG_CASE"/tFin/outputs/finalState/outputIIDM.xml   > "$outDir"/xml/"$prefix"-DynawoOutputIIDM.xml.xz
xz -c9 "$CONTG_CASE"/tFin/outputs/timeLine/timeline.xml       > "$outDir"/xml/"$prefix"-DynawoTimeLine.xml.xz
xz -c9 "$CONTG_CASE"/tFin/outputs/logs/dynamo.log             > "$outDir"/log/"$prefix"-Dynawo.log.xz
xz -c9 "$CONTG_CASE"/"$RUNLOG"                                > "$outDir"/log/"$prefix"-"$RUNLOG".xz

# Delete input dir if cleanup was requested
if [ $c = "y" ]; then
    rm -rf "$CONTG_CASE"
fi

