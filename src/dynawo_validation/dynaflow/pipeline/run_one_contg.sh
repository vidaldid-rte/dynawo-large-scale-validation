#!/bin/bash
#
# run_one_contg.sh:
#
# given a specific contingency case (which can be of EITHER type,
# i.e. Hades vs. Dynawo OR Dynawo vs. Dynawo), plus the BASECASE it
# was derived from, this script runs the case and collects all results
# in a (configurable) output directory designed to store the results
# from this and many other contingencies. Optionally, delete the case
# to save space.
#
# (c) Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#

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

Usage: $0 [OPTIONS] BASECASE CONTINGENCY_CASE
  Options:
    -c | --cleanup  Delete the contingency case after getting the results
    -d | --debug    More debug messages
    -h | --help     This help message
    -o | --output   Specify a directory for collecting results (default: RESULTS)
    -v | --verbose  More verbose output
    -A | --launcherA  Defines the launcher of simulator A
    -B | --launcherB  Defines the launcher of simulator B

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
    HADES_DIR="$CONTG_CASE"/Hades
    if [ ! -d "$HADES_DIR" ]; then
        echo "Directory $HADES_DIR not found."
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$HADES_DIR"
    RUNLOG=Hades.RunStdout.txt
    echo "Running Hades for case: $CONTG_CASE"
    set_launcher "$1"
    $LAUNCHER donneesEntreeHADES2.xml out.xml log.xml > "$RUNLOG" 2>&1
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


run_dynawo(){
    if [ ! -f "$CONTG_CASE"/"$DWO_JOBFILE" ]; then
        echo "Dynawo JOB file not found under $CONTG_CASE/"
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$CONTG_CASE"
    RUNLOG=Dynawo"$1".runStdout
    echo "Running Dynawo for case: $CONTG_CASE"
    set_launcher "$2"
    $LAUNCHER jobs "$DWO_JOBFILE" > "$RUNLOG" 2>&1 || true  # allow it to fail while using errexit flag
    if [ ! -f ./"$DWO_OUTPUT_DIR"/curves/curves.csv ]; then
        if [ -f ./"$DWO_OUTPUT_DIR"/curves/curves.xml ]; then
            echo "Dynawo$1 run: output curves file found in XML format; required format is CSV"
        else
            echo "Dynawo$1 run: no curves output found. Check Dynawo's log and the run-log: $CONTG_CASE/$RUNLOG"
        fi
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    if [ -f "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml ]; then
        xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml > "$outDir"/xml/"$prefix"-Dynawo.IIDM"$1".xml.xz
    fi
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/curves/curves.csv           > "$outDir"/crv/"$prefix"-DynawoCurves"$1".csv.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/constraints/constraints.xml > "$outDir"/xml/"$prefix"-DynawoConstraints"$1".xml.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/timeLine/timeline.xml       > "$outDir"/xml/"$prefix"-DynawoTimeLine"$1".xml.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/logs/dynawo.log             > "$outDir"/log/"$prefix"-Dynawo"$1".log.xz
    xz -c9 "$CONTG_CASE"/"$RUNLOG"                                     > "$outDir"/log/"$prefix"-"$RUNLOG".xz
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

OPTIONS=cdho:vA:B:
LONGOPTS=cleanup,debug,help,output:,verbose,launcherA:,launcherB:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
c=n d=n h=n outDir="RESULTS" v=n A="dynawo.sh" B="dynawo.sh"
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
    echo "$0: Called with OPTIONS: cleanup: $c, debug: $d, help: $h, outDir: $outDir, verbose: $v, launcherA: $A, launcherB: $B"
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
if [[ $# -ne 2 ]]; then
    echo
    echo "$0: Two directory names are required."
    usage
    exit 4
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
mkdir -p "$outDir"/pf_sol
mkdir -p "$outDir"/crv
mkdir -p "$outDir"/aut
mkdir -p "$outDir"/xml
mkdir -p "$outDir"/log
mkdir -p "$outDir"/casediffs


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


#####################################################################
# Detect whether it's dwohds / dwodwo, and run the cases accordingly
#####################################################################
A_basename=$(basename "$A")
B_basename=$(basename "$B")
set_launcher "$A"
"$LAUNCHER" version > "$outDir"/../.LAUNCHER_A_WAS_"$A_basename" 2>&1 || true
set_launcher "$B"
"$LAUNCHER" version > "$outDir"/../.LAUNCHER_B_WAS_"$B_basename" 2>&1 || true
basecase_name=$(basename "$BASECASE")
scripts_basedir=$(dirname "$0")
DWO_JOBINFO_SCRIPT=$scripts_basedir/dwo_jobinfo.py
CASE_TYPE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "CASE_TYPE" | cut -d'=' -f2)

if [ "$CASE_TYPE" = "dwohds" ]; then
    DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_file" | cut -d'=' -f2)
    DWO_JOBFILE=$(basename "$DWO_JOBFILE")
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directory" | cut -d'=' -f2)
    if [ "${A_basename:0:5}" == "hades" ]; then
        run_hades "$A"
        run_dynawo "" "$B"
    else
        run_dynawo "" "$A"
        run_hades "$B"
    fi
    python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Dynawo-aut-diff.csv \
            "$outDir"/xml/"$prefix"-Dynawo.IIDM.xml.xz "$outDir"/../"$basecase_name"/

    python3 "$scripts_basedir"/extract_hades_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Hades-aut-diff.csv \
            "$outDir"/xml/"$prefix"-Hades.Out.xml.xz "$outDir"/../"$basecase_name"/ "$outDir"/../"$basecase_name"/Hades/donneesEntreeHADES2.xml
else
    DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_fileA" | cut -d'=' -f2)
    DWO_JOBFILE=$(basename "$DWO_JOBFILE")
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directoryA" | cut -d'=' -f2)
    run_dynawo "A" "$A"
    DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_fileB" | cut -d'=' -f2)
    DWO_JOBFILE=$(basename "$DWO_JOBFILE")
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directoryB" | cut -d'=' -f2)
    run_dynawo "B" "$B"
    python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-DynawoA-aut-diff.csv \
            "$outDir"/xml/"$prefix"-Dynawo.IIDMA.xml.xz "$outDir"/../"$basecase_name"/A/
    python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-DynawoB-aut-diff.csv \
            "$outDir"/xml/"$prefix"-Dynawo.IIDMB.xml.xz "$outDir"/../"$basecase_name"/B/
fi



########################################
# Extract the PF solution
########################################
# Extracts the PF solution vaules from the xml output to CSV,
# using a standardized format to allow comparisons
scripts_basedir=$(dirname "$0")
echo "Extracting the powerflow solutions for case: $CONTG_CASE"
python3 "$scripts_basedir"/extract_powerflow_values.py "$CONTG_CASE" "$outDir"/..

# Collect and compress all results
xz -c9 "$CONTG_CASE"/pfsolution_AB.csv > "$outDir"/pf_sol/"$prefix"_pfsolutionAB.csv.xz
for error_file in "elements_not_in_caseA.csv" "elements_not_in_caseB.csv"; do 
    if [ -f "$CONTG_CASE"/"$error_file" ]; then
        xz -c9 "$CONTG_CASE"/"$error_file" > "$outDir"/pf_sol/"$prefix"-"$error_file".xz
    fi
done


########################################
# Extract automata changes
########################################
# Extracts EVENTS from the xml output to CSV, using standardized
# labels to allow comparison
scripts_basedir=$(dirname "$0")/../../commons
python3 "$scripts_basedir"/extract_automata_changes.py "$CONTG_CASE" "$outDir"/../

scripts_basedir=$(dirname "$0")
# Collect and compress all results
if [ "$CASE_TYPE" = "dwohds" ]; then
    xz -c9 "$CONTG_CASE"/Dynawo_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomata.csv.xz
    python3 "$scripts_basedir"/group_dwo_events.py "$outDir"/aut/"$prefix"-DynawoAutomata.csv.xz \
            "$outDir"/../"$basecase_name"/ "$outDir"/aut/"$prefix"-aut-groups.csv 0
else
    xz -c9 "$CONTG_CASE"/DynawoA_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomataA.csv.xz
    xz -c9 "$CONTG_CASE"/DynawoB_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomataB.csv.xz
    python3 "$scripts_basedir"/group_dwo_events.py "$outDir"/aut/"$prefix"-DynawoAutomataA.csv.xz \
            "$outDir"/../"$basecase_name"/ "$outDir"/aut/"$prefix"-autA-groups.csv 1
    python3 "$scripts_basedir"/group_dwo_events.py "$outDir"/aut/"$prefix"-DynawoAutomataB.csv.xz \
            "$outDir"/../"$basecase_name"/ "$outDir"/aut/"$prefix"-autB-groups.csv 2
fi



########################################
# Clean up
########################################
# Delete input dir if cleanup was requested
if [ $c = "y" ]; then
    rm -rf "$CONTG_CASE"
fi

