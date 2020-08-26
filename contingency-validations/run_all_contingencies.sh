#!/bin/bash
#
#
# run_all_contingencies.sh: given a base directory containing
# Dynawo+Astre cases, run all that have a given prefix in their name
# (possibly in parallel, using GNU parallel)
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

Usage: $0 [OPTIONS] CASEDIR INPUTPREFIX
  Options:
    -c | --cleanup    Delete input cases (both Astre & Dynawo) after getting the results
    -d | --debug      More debug messages
    -h | --help       This help message
    -o | --output     Specify a directory (no whitespace!) for collecting results (default: RESULTS)
    -v | --verbose    Mode verbose output
    -s | --sequential Run jobs sequentially (defult is parallel)

  Example: $0 PtFige-Lille load
    (will run all cases PtFige-Lille/load* and leave the collected results under RESULTS) 

EOF
}


find_cmd()
{
    find "$baseDir" -type d -name "$casePrefix"'*'
}



# -allow a command to fail with !’s side effect on errexit
# -use return value from ${PIPESTATUS[0]}, because ! hosed $?
! getopt --test > /dev/null 
if [[ ${PIPESTATUS[0]} -ne 4 ]]; then
    echo 'I’m sorry, `getopt --test` failed in this environment.'
    exit 1
fi

OPTIONS=cdho:vs
LONGOPTS=cleanup,debug,help,output:,verbose,sequential

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

c=n d=n h=n outDir="RESULTS" v=n s=n
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
if [[ $# -ne 2 ]]; then
    echo -e "\n$0: please specify the base directory containing cases and a case prefix"
    usage
    exit 4
fi

if [ $d = "y" ]; then
    set -o xtrace
fi



#######################################
# The real meat starts here
########################################
baseDir=$1
casePrefix=$2
if [ ! -d "$baseDir" ]; then
   echo "Base directory $baseDir not found."
   exit 1
fi

dirList=$(find_cmd)
if [ -z "$dirList" ]; then
   echo -e "No cases with pattern $casePrefix* found under $baseDir"
   exit 1
fi

# Create the output dir if it doesn't exist
mkdir -p "$outDir"

# Run each case, using GNU parallel if available
if [ $c = "y" ]; then   # TODO: do this properly with an array
    OPTS="-c -o $outDir"
else
    OPTS="-o $outDir"
fi
run_case=$(dirname "$0")/run_one_contingency.sh
if [ $s = "y" -o -z $(which parallel) ]; then
    echo "*** Running sequentially"
    set +e   # allow to continue if some fail
    find_cmd | while read CASE; do
	echo "   $CASE"
	$run_case $OPTS "$CASE"
    done
else
    echo "*** Running in parallel"
    find_cmd | parallel -j+0 --eta $run_case $OPTS {}
fi

