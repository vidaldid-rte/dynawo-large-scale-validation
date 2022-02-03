#!/bin/bash
#
#
# run_all_contg.sh:
#
# given a directory containing contingency cases (which can be of
# EITHER Hades vs. Dynawo OR Dynawo vs. Dynawo type), all of them
# derived from a common BASECASE, this script runs all cases having a
# given prefix in their name. It is essentially a thin wrapper around
# the script run_one_contg.sh, in order to be able to launch the
# simulations either sequentially or in parallel (using GNU parallel).
#
# (c) Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
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



#######################################
# getopt-like input option processing
#######################################

# Test for getopt's version (this needs to temporarily deactivate errexit)
set +e
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "I’m sorry, 'getopt --test' failed in this environment."
    exit 1
fi
set -e

OPTIONS=cdho:vsA:B:
LONGOPTS=cleanup,debug,help,output:,verbose,sequential,launcherA:,launcherB:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
c=n d=n h=n outDir="RESULTS" v=n s=n A="dynawo.sh" B="dynawo.sh"
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
    echo "$0: Called with OPTIONS: cleanup: $c, debug: $d, help: $h, output: $outDir, verbose: $v, sequential: $s, launcherA: $A, launcherB: $B"
    echo "$0: Called with PARAMS: $*"
fi

if [ $h = "y" ]; then
    usage
    exit 0
fi

if [ $d = "y" ]; then
    set -o xtrace
fi

# handle non-option arguments
if [[ $# -ne 3 ]]; then
    echo
    echo "$0: please specify the directory containing the cases, the basecase, and a case prefix"
    usage
    exit 4
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
    set +e    # allow the script to continue if any case fails
    find_cmd | while read -r CONTG_CASE; do
	echo "   $CONTG_CASE"
	$run_case "${OPTS[@]}" "$CONTG_CASE"	
    done
    set -e 
else
    echo "*** Running in parallel (using GNU parallel)"
    set +e    # allow the script to continue if any case fails
    find_cmd | parallel -j 100% --verbose "$run_case" "${OPTS[@]}" {}
    EXIT_VAL=$?
    set -e
    if [ "$EXIT_VAL" -ne 0 ]; then
        if [ "$EXIT_VAL" -ge 1 ] && [ "$EXIT_VAL" -le 100 ]; then
            echo "WARNING: GNU parallel: $EXIT_VAL contingency jobs failed"
        elif [ "$EXIT_VAL" = 101 ]; then
            echo "WARNING: GNU parallel: more than 100 contingency jobs failed"
        else
            echo "WARNING: GNU parallel: unexpected exit value: $EXIT_VAL"
        fi
    fi
fi

