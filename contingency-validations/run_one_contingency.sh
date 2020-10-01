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
set -o nounset -o noclobber
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 [OPTIONS] INPUTDIR
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
    echo 'I’m sorry, `getopt --test` failed in this environment.'
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
    echo "PARAMS: $@"
fi

if [ $h = "y" ]; then
    usage
    exit 0
fi

# handle non-option arguments
if [[ $# -ne 1 ]]; then
    echo -e "\n$0: A single directory name is required."
    usage
    exit 4
fi

if [ $d = "y" ]; then
    set -o xtrace
fi



#######################################
# The real meat starts here
########################################
inDir=$1   # it could contain whitespace, so remember to quote it!
prefix=$(basename "$inDir")
if [ ! -d "$inDir" ]; then
   echo "Directory $inDir not found."
   exit 1
fi

# Create the output dir if it doesn't exist
mkdir -p "$outDir"

# Save the PWD to avoid having to deal with absolute/relative paths in outDir vs inDir
OLD_PWD=$(pwd)


########################################
# Run Astre
########################################
if [ ! -d "$inDir"/Astre ]; then
   echo "Directory $inDir/Astre not found."
   exit 1
fi
cd "$inDir"/Astre
rm -f log.txt
astre donneesModelesEntree.xml > log.txt 2>&1
if [ ! -f donneesModelesSortie.csv ]; then
   echo "Astre run failed. Check the log: $inDir/Astre/log.txt"
   exit 1
fi
cd $OLD_PWD
mv -f "$inDir"/Astre/donneesModelesSortie.csv "$outDir/$prefix"-Astre.csv

LOG="$outDir/$prefix"-Astre.log
mv -f "$inDir"/Astre/log.txt "$LOG"
ASTRE_LOG="$inDir"/Astre/donneesModelesLog.xml
if fgrep -q 'level="ERROR"' "$ASTRE_LOG"; then
    echo -e "\n\n\nSOME ERRORS WERE FOUND -- CONTENT OF donneesModelesLog.xml:" >> "$LOG"
    cat "$ASTRE_LOG" >> "$LOG"
fi


########################################
# Run Dynawo
########################################
if [ ! -f "$inDir"/fic_JOB.xml ] || [ ! -d "$inDir"/tFin ]; then
   echo "Dynawo input files not found under $inDir/."
   exit 1
fi
cd "$inDir"
rm -f log.txt
dynawo-RTE jobs fic_JOB.xml > log.txt 2>&1 || true  # allow it to fail while using errexit
if [ ! -f ./tFin/outputs/curves/curves.csv ]; then
   echo "Dynawo run failed. Check the logs: $inDir/log.txt, $inDir/tFin/outputs/curves/curves.csv"
   exit 1
fi
cd $OLD_PWD
mv -f "$inDir"/tFin/outputs/curves/curves.csv "$outDir/$prefix"-Dynawo.csv
mv -f "$inDir"/tFin/outputs/constraints/constraints.xml "$outDir/$prefix"-Dynawo.constraints.xml
mv -f "$inDir"/tFin/outputs/timeLine/timeline.xml "$outDir/$prefix"-Dynawo.timeLine.xml

LOG="$outDir/$prefix"-Dynawo.log
mv -f "$inDir"/log.txt "$LOG"
DYNAWO_LOG="$inDir"/tFin/outputs/logs/dynamo.log
if fgrep -q 'ERROR' "$DYNAWO_LOG"; then
    echo -e "\n\n\nSOME ERRORS WERE FOUND -- CONTENT OF dynawo.log:" >> "$LOG"
    cat "$DYNAWO_LOG" >> "$LOG"
fi



# Delete input dir if cleanup
if [ $c = "y" ]; then
    rm -rf "$inDir"
fi

