#!/bin/bash

# We source ~/.bashrc in order to make the user's aliases visible
# here. This could also be done by running as "bash -i", but GNU
# parallel chokes if the shell is interactive.
if [ -f "$HOME/.bashrc" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.bashrc"
fi

# For saner programming:
set -o nounset  # don't set noclobber because we do need to overwrite files with ">"
set -o errexit -o pipefail

# This line below is needed if we want Ctrl-C to stop the pipeline
# when running interactively on the command line. For a full
# explanation of what's going on here, you'll need to read this:
# https://www.cons.org/cracauer/sigint.html
#
# Short explanation: Hades2 seems to trap and ignore SIGINT completely
# (and Dynawo may take a bit long to interrupt because it can only be
# interrupted at certain points in its execution). So if we hit Ctrl-C
# when the script is executing Hades then the shell waits for the
# child Hades process to exit to checks whether it exited because of
# the SIGINT. But, since Hades completely ignores this signal, the
# process exits as usual and therefore the shell will also ignore it
# and continue as if nothing happened (because Bash default behavior
# is "Wait and Cooperative Exit", see
# https://www.cons.org/cracauer/sigint.html).  So here we change its
# behavior to be IUE ("Immediate Unconditional Exit").  With this, a
# Ctrl-C will stop the script right away, regardless of how the child
# process handles the SIGINT signal. And at the same time, it will
# properly propagate the message to any caller, saying "I exited
# because I was SIGINTed".  The hades child process will continue
# running as usual until it ends, but at least the pipeline will have
# stopped, as the user expects.
trap 'trap - SIGINT ; kill -s SIGINT "$BASHPID"' SIGINT

usage()
{
    cat <<EOF

Usage: $0 [OPTIONS] CASEDIR
  runs entreeHades.xml with Hades (as adn format) and entreeOLF.xiidm with OpenLoadFLow
  Options:
    -c | --cleanup  Delete the contingency case after getting the results
    -d | --debug    More debug messages
    -h | --help     This help message
    -i | --launcherInfo Extract launcher info
    -o | --output   Specify a directory for collecting results (default: RESULTS)
    -v | --verbose  More verbose output
    -H | --launcherH  Defines the launcher for Hades (default hades2.sh)
    -O | --launcherO  Defines the launcher for OpenLoadFlow (default itools)

EOF
}

set_launcher() {
    COMMAND_TYPE=$(type -t "$1" || true)  # OR trick to avoid non-zero exit status (because of errexit)
    case "$COMMAND_TYPE" in
        "file")
            # standard executable file
            LAUNCHER=$1
            ;;
        "alias")
            # aliases cannot be directly invoked from a variable
            LAUNCHER=${BASH_ALIASES[$1]}
            ;;
        "function")
            # functions can be invoked just as regular executable files
            LAUNCHER=$1
            ;;
        *)
            echo "*** ERROR: launcher $1 not found"
            exit 2
            ;;
    esac
}

run_hades(){
    HADES_DIR=`dirname $HADES_FILE`
    echo $HADES_DIR
    if [ ! -d "$HADES_DIR" ]; then
        echo "Directory $HADES_DIR not found."
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$HADES_DIR"
    RUNLOG=Hades.RunStdout.txt
    echo "Running Hades for file: $HADES_FILE"
    set_launcher "$1"
    HADES_FILE_SHORT=$(basename "$HADES_FILE")
    $LAUNCHER "$HADES_FILE_SHORT" out.xml log.xml > "$RUNLOG" 2>&1
    if [ ! -f out.xml ]; then
        echo "Hades run failed. Check the run log: $HADES_DIR/$RUNLOG"
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    xz -c9 "$HADES_DIR"/out.xml > "$outDir"/xml/"$prefix"-Hades.Out.xml.xz
    xz -c9 "$HADES_DIR"/log.xml > "$outDir"/log/"$prefix"-Hades.Log.xml.xz
    xz -c9 "$HADES_DIR/$RUNLOG" > "$outDir"/log/"$prefix"-"$RUNLOG".xz
}

run_olf(){
    OLF_DIR=`dirname $OLF_FILE`
    echo $OLF_DIR
    if [ ! -d "$OLF_DIR" ]; then
        echo "Directory $OLF_DIR not found."
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$OLF_DIR"
    RUNLOG=OLF.RunStdout.txt
    echo "Running OpenLoadFlow for file: $OLF_FILE"
    set_launcher "$1"
    rm -f olf.xiidm
    OLF_FILE_SHORT=$(basename "$OLF_FILE")
    PARAM_SHORT=$(basename "$OLF_PARAM")
    $LAUNCHER loadflow --case-file "$OLF_FILE_SHORT" --parameters-file "$PARAM_SHORT" --output-case-file olf.xiidm --output-case-format XIIDM  > "$RUNLOG" 2>&1
    if [ ! -f olf.xiidm ]; then
        echo "OpenLoadFlow run failed. Check the run log: $OLF_DIR/$RUNLOG"
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    xz -c9 "$OLF_DIR"/olf.xiidm > "$outDir"/xml/"$prefix"-OLF.xiidm.xz
    xz -c9 "$OLF_DIR/$RUNLOG" > "$outDir"/log/"$prefix"-"$RUNLOG".xz
}

######################################
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

OPTIONS=cdhio:vH:O:
LONGOPTS=cleanup,debug,help,launcherInfo,output:,verbose,launcherH:,launcherO:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# TODO Ajouter l'option pour récuperer les infos de param et de version et le coder

# now enjoy the options in order and nicely split until we see --
c=n d=n h=n outDir="RESULTS" v=n H="hades2.sh" O="itools"
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
        -i|--launcherInfo )
        #TODO utiliser ce parametre pour l'extraction
            i=y
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
        -H|--launcherH)
            H="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -O|--launcherO)
            O="$2"   # it could contain whitespace, so remember to quote it!
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
    echo "$0: Called with OPTIONS: cleanup: $c, debug: $d, help: $h, outDir: $outDir, verbose: $v, launcherH: $H, launcherO: $O"
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
if [[ $# -ne 1 ]]; then
    echo
    echo "$0: A file basename is required"
    usage
    exit 4
fi

#######################################
# The real meat starts here
########################################
BASEDIR=$1
HADES_FILE=${BASEDIR}/entreeHades.xml
if [ ! -f "$HADES_FILE" ]; then
   echo "ERROR: Hades input file $HADES_FILE not found."
   exit 1
fi

# TODO - mettre en XML pour supporter directement du arcade ?
OLF_FILE=${BASEDIR}/entreeOLF.xiidm
if [ ! -f "$OLF_FILE" ]; then
   echo "ERROR: OLF input file $OLF_FILE not found."
   exit 1
fi

OLF_PARAM=${BASEDIR}/OLFParams.json
if [ ! -f "$OLF_PARAM" ]; then
   echo "ERROR: OLF parameter file $OLF_PARAM not found."
   exit 1
fi


#if [ ! -d "$CONTG_CASE" ]; then
#   echo "ERROR: Contingency case $CONTG_CASE not found."
#   exit 1
#fi

prefix=$(basename "$BASEDIR")

# Create the output dirs if they don't exist
mkdir -p "$outDir"/pf_sol
mkdir -p "$outDir"/aut
mkdir -p "$outDir"/xml
mkdir -p "$outDir"/log
mkdir -p "$outDir"/casediffs

# TODO diff from base case not done

#####################################################################
# Detect whether it's dwohds / dwodwo, and run the cases accordingly
#####################################################################
H_basename=$(basename "$H")
O_basename=$(basename "$O")
set_launcher "$H"
"$LAUNCHER" --version > "$BASEDIR""/LAUNCHER_HADES" 2>&1 || true
set_launcher "$O"
"$LAUNCHER" version > "$BASEDIR""/LAUNCHER_OLF" 2>&1 || true
#basecase_name=$(basename "BASEDIR")
scripts_basedir=$(dirname "$0")


run_hades $H
run_olf $O

########################################
# Extract the PF solution
########################################
# Extracts the PF solution vaules from the xml output to CSV,
# using a standardized format to allow comparisons
scripts_basedir=$(dirname "$0")
echo "Extracting the powerflow solutions for case: $BASEDIR"
python3 "$scripts_basedir"/extract_powerflow_values.py -i -v "$BASEDIR"

# Collect and compress all results
xz -c9 "$BASEDIR"/pfsolution_HO.csv > "$outDir"/pf_sol/"$prefix"_pfsolutionHO.csv.xz
for error_file in elements_not_in_case*.csv ; do
    if [ -f "$BASEDIR"/"$error_file" ]; then
        xz -c9 "$BASEDIR"/"$error_file" > "$outDir"/pf_sol/"$prefix"-"$error_file".xz
    fi
done

########################################
# Clean up
########################################
# Delete input dir if cleanup was requested
if [ $c = "y" ]; then
    rm -rf "$BASEDIR"
fi