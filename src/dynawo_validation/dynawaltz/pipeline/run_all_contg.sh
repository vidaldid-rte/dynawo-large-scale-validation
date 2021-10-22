#!/bin/bash
#
#
# run_all_contg.sh:
#
# given a directory containing contingency cases (which can be of
# EITHER Astre vs. Dynawo OR Dynawo vs. Dynawo type), all of them
# derived from a common BASECASE, this script runs all cases having a
# given prefix in their name (possibly in parallel, using GNU
# parallel).
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

Usage: $0 [OPTIONS] CASE_DIR BASECASE CASE_PREFIX
  Options:
    -c | --cleanup    Delete input cases after getting the results
    -d | --debug      More debug messages
    -h | --help       This help message
    -o | --output     Specify a directory (no whitespace!) for collecting results (default: RESULTS)
    -v | --verbose    More verbose output
    -s | --sequential Run jobs sequentially (defult is parallel)
    -A | --launcherA  Defines the launcher of simulator A
    -B | --launcherB  Defines the launcher of simulator B

  Example: $0 PtFige-Lille load
    (will run all cases PtFige-Lille/load* and leave the collected results under RESULTS) 

EOF
}


find_cmd()
{
    find "$CASE_DIR" -maxdepth 1 -type d -name "$CASE_PREFIX"'*'
}



# -allow a command to fail with !’s side effect on errexit
# -use return value from ${PIPESTATUS[0]}, because ! hosed $?
! getopt --test > /dev/null 
if [[ ${PIPESTATUS[0]} -ne 4 ]]; then
    echo "I’m sorry, 'getopt --test' failed in this environment."
    exit 1
fi

OPTIONS=cdho:vsA:B:
LONGOPTS=cleanup,debug,help,output:,verbose,sequential,launcherA:,launcherB:

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

c=n d=n h=n outDir="RESULTS" v=n s=n A="dynawo.sh" B="dynawo.sh"
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
            outDir="$2"
            shift 2
            ;;
        -v|--verbose)
            v=y
            shift
            ;;
        -s|--sequential)
            s=y
            shift
            ;;
        -A|--launcherA)
            A="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -B|--launcherB)
            B="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
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
    echo "OPTIONS: cleanup: $c, debug: $d, help: $h, output: $outDir, verbose: $v, sequential: $s, launcherA: $A, launcherB: $B"
    echo "PARAMS: $*"
fi

if [ $h = "y" ]; then
    usage
    exit 0
fi

# handle non-option arguments
if [[ $# -ne 3 ]]; then
    echo
    echo "$0: please specify the directory containing the cases, the basecase, and a case prefix"
    usage
    exit 4
fi

if [ $d = "y" ]; then
    set -o xtrace
fi



#######################################
# The real meat starts here
########################################
CASE_DIR=$1
BASECASE=$2
CASE_PREFIX=$3
if [ ! -d "$CASE_DIR" ]; then
   echo "Directory $CASE_DIR not found."
   exit 1
fi

if [ ! -d "$BASECASE" ]; then
   echo "Basecase $BASECASE not found."
   exit 1
fi

dirList=$(find_cmd)
if [ -z "$dirList" ]; then
   echo -e "No cases with pattern $CASE_PREFIX* found under $CASE_DIR"
   exit 1
fi

# Create the output dir if it doesn't exist
mkdir -p "$outDir"

# Run each contingency case (using GNU parallel if available)
declare -a OPTS
if [ $c = "y" ]; then
    OPTS=("-c" "-o" "$outDir" "-A" "$A" "-B" "$B" "$BASECASE")
else
    OPTS=("-o" "$outDir" "-A" "$A" "-B" "$B" "$BASECASE")
fi
run_case=$(dirname "$0")/run_one_contg.sh
if [ $s = "y" ] || ! [ -x "$(type -p parallel)" ]; then
    echo "*** Running sequentially"
    # set +e   # allow to continue if any case fails
    set -e 
    find_cmd | while read -r CONTG_CASE; do
	echo "   $CONTG_CASE"
	$run_case "${OPTS[@]}" "$CONTG_CASE"	
    done
    set +e 
else
    echo "*** Running in parallel"
    find_cmd | parallel -j 50% --verbose "$run_case" "${OPTS[@]}" {}
fi

