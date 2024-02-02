#!/bin/bash
#
#
# run_pipeline.sh:
#
# A simple high-level "driver" script that runs the whole processing
# pipeline.  Given a directory containing Hades vs. OpenLoadFlow
#
#   TODO: create and run contingencies
#
#   (a) runs the two models
#
#   (b) calculates metrics, summary reports, etc., and finally
#       prepares the Notebook for analysis.
#
#
#    $ run_pipeline.sh [options] modelDirectory MyResults
#
# You may use either relative or absolute paths.
#
#
# adapted from ../dynaflow/run_pipeline.sh
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


# TODO: put again the code that creates the contingencies

# Note this assumes all scripts are under the Github src dir structure
# (otherwise, you'll have to edit the correct paths below)
#TODO clean unused variables
OLF_VALIDATION_SRC=$(dirname "$0")/..
#OLF_VALIDATION_SRC=$(realpath "$OLF_VALIDATION_SRC")

# Config options to pass to run_all_contingencies.sh (using a Bash array as a
# safe way to pass parameters when invoking it)
declare -a RUNALL_OPTS


# Nothing else to configure below this point
CONTG_SRC=$OLF_VALIDATION_SRC/pipeline
GREEN="\\033[1;32m"
NC="\\033[0m"

find_cmd()
{
    find "$CASE_DIR" -maxdepth 1 -type d -name "$1"'*'
}
# TODO: add -a --allcontg for run all contingencies
# TODO: add -s/--sequential
# TODO: add -l / --regextlist egain
# TODO: add -r --random to run a random sample of contingencies et aussi --prandom/-p
usage()
{
    cat <<EOF
Usage: $0 [OPTIONS] BASECASE RESULTS_DIR
  Options:
    -H | --launcherH  Defines the launcher for Hades
    -O | --launcherO  Defines the launcher for OpenLoadFlow
    -c | --cleanup    Delete input cases after getting the results
    -d | --debug      More debug messages
    -w | --weights    Calculate scores with weights
    -h | --help       This help message
EOF
}

colormsg()
{
    if [ -t 1 ] ; then
        echo -e "${GREEN}$1${NC}"
    fi
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


OPTIONS=H:O:hdcw:
LONGOPTS=launcherO:,launcherH:,help,debug,cleanup,weights:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
H="hades2.sh" O="itools" h=n
debug=n cleanup=n weightslist="None"
while true; do
    case "$1" in
        -H|--launcherH)
            H="$2"   # it could contain whitespace, so remember to quote it!
            echo "Launcher for Hades defined as $H"
            shift 2
            ;;
        -O|--launcherO)
            O="$2"   # it could contain whitespace, so remember to quote it!
            echo "Launcher for OpenLoadFlow defined as $O"
            shift 2
            ;;
        -h|--help)
            h=y
            shift
            ;;
        -w|--weights)
            weightslist="$2"
            echo "Read weights from $2 file"
            shift 2
            ;;
        -d|--debug)
            debug=y
            shift
            ;;
        -c|--cleanup)
            cleanup=y
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

if [ $h = "y" ]; then
    usage
    exit 0
fi

# TODO handle options for create_contg.py


# handle options for run_all.s
# TODO: update RUNALL_OPTS when sequential is introdeced again

if [ $debug = "y" ]; then
    RUNALL_OPTS=("${RUNALL_OPTS[@]}" "-d")
fi

if [ $cleanup = "y" ]; then
    RUNALL_OPTS=("${RUNALL_OPTS[@]}" "-c")
fi

# handle non-option arguments
if [[ $# -ne 2 ]]; then
    echo
    echo "$0: Two arguments are required."
    usage
    exit 4
fi
BASECASE=$1
RESULTS_BASEDIR=$2

if [ ! -d "$BASECASE" ]; then
   echo "ERROR: Basecase dir $BASECASE not found."
   exit 1
fi

if [ -f "$RESULTS_BASEDIR" ]; then
   echo "ERROR: Results directory $RESULTS_BASEDIR is an existing file!!!"
   exit 1
fi



#######################################
# The real meat starts here
#######################################
echo -e "Generating results under directory: $RESULTS_BASEDIR\n\n"
mkdir -p "$RESULTS_BASEDIR"

##############################################################
# Process the user-provided weights & thresholds for scoring
##############################################################
colormsg "*** CONFIGURING WEIGHTS & THRESHOLDS FOR THE COMPOUND SCORES:"
if [ "$weightslist" != "None" ]; then
    echo "Reading weights & thresholds from the user-provided file"
    set -x
    python3 "$CONTG_SRC"/get_and_define_weights.py "-w" "$weightslist" "$RESULTS_BASEDIR"
    set +x
else
    echo "Using default weights & thresholds"
    set -x
    python3 "$CONTG_SRC"/get_and_define_weights.py "$RESULTS_BASEDIR"
    set +x
fi
echo


###################################################
# Copy and process the BASECASE in the Results dir
###################################################
colormsg "*** COPYING & PROCESSING THE BASECASE:" 
REAL_BASECASE=$(realpath "$BASECASE/..")
REAL_RESULTS_BASEDIR=$(realpath "$RESULTS_BASEDIR")
BASECASE_NAME=$(basename "$BASECASE")
if [ "$REAL_BASECASE" != "$REAL_RESULTS_BASEDIR" ]; then
   cp -a "$BASECASE" "$RESULTS_BASEDIR"
   REAL_BASECASE=${RESULTS_BASEDIR}/${BASECASE_NAME}
fi

CP_BASECASE=$REAL_BASECASE


# TODO: Need to reconnect ? Process automata changes for the BASECASE run

#######################################
# Run the base case
#######################################

  RESULTS_DIR="$RESULTS_BASEDIR"/basecase
  mkdir -p "$RESULTS_DIR"
  "$CONTG_SRC"/run_one_case.sh "${RUNALL_OPTS[@]}" -o "$RESULTS_DIR" -H "$H" -O "$O" \
              "$CP_BASECASE"

###############################
# Calculate Power Flow metrics
###############################
colormsg "*** COMPUTING DIFF METRICS:"
python3 "$CONTG_SRC"/calc_global_pf_diffmetrics.py "$RESULTS_DIR"/pf_sol  "$BASECASE_NAME"
echo


#####################################
# Calculate the "Top 10" mini-report
#####################################
colormsg "*** COMPUTING TOP 10 DIFFS:"
python3 "$OLF_VALIDATION_SRC"/pipeline/top_10_diffs_dflow.py "$RESULTS_DIR"/pf_sol/ \
        "$RESULTS_DIR"/pf_metrics/ >| "$RESULTS_DIR"/../top_10_diffs_"$BASECASE_NAME".txt
echo

##########################################################
# Prepare the Notebook (sets paths, weights & thresholds)
##########################################################
colormsg "*** CREATING THE NOTEBOOK:"
python3 "$OLF_VALIDATION_SRC"/notebooks/generate_notebooks.py \
        "$(cd "$(dirname "$RESULTS_DIR")"; pwd)" "$BASECASE" basecase "$RESULTS_BASEDIR"/score_weights.csv

mkdir -p "$RESULTS_DIR"/notebooks
cp "$OLF_VALIDATION_SRC"/notebooks/Hades_vs_OpenLoadFlow_final.ipynb "$RESULTS_DIR"/notebooks
rm "$OLF_VALIDATION_SRC"/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
echo

echo Fin ici avant de coder les contingences
exit

#######################################
# Process all types of contingency
#######################################
CASE_DIR=$(dirname "$BASECASE")
for DEVICE in "${!create_contg[@]}"; do
    echo
    colormsg "****** PROCESSING CONTINGENCIES OF TYPE: $DEVICE"
    echo
    
    ####################################
    # Creation of the contingency cases
    ####################################
    colormsg "*** CREATING CONTINGENCY CASES:"
    rm -rf "$CASE_DIR"/"$DEVICE"_*
    set -x
    python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "${CREATE_OPTS[@]}" "$BASECASE"
    set +x
    echo

    #############################################################
    # Run all the contingency cases just created
    # (this step also extracts the PF values & automata changes)
    #############################################################
    dirList=$(find_cmd "$DEVICE"#)
    if [ -z "$dirList" ]; then
        echo -e "No cases with pattern $DEVICE""#* found under $CASE_DIR"
        continue
    fi
    colormsg "*** RUNNING CONTINGENCY CASES:"
    RESULTS_DIR="$RESULTS_BASEDIR"/"$DEVICE"
    mkdir -p "$RESULTS_DIR"
    set -x
    "$CONTG_SRC"/run_all_contg.sh "${RUNALL_OPTS[@]}" -o "$RESULTS_DIR" -A "$A" -B "$B" \
                "$CASE_DIR" "$BASECASE" "$DEVICE"#
    set +x
    echo

    ###############################
    # Calculate Power Flow metrics
    ###############################
    colormsg "*** COMPUTING DIFF METRICS:"
    set -x
    python3 "$CONTG_SRC"/calc_global_pf_diffmetrics.py "$RESULTS_DIR"/pf_sol "$DEVICE#"
    set +x
    echo

    #####################################
    # Calculate the "Top 10" mini-report
    #####################################
    colormsg "*** COMPUTING TOP 10 DIFFS:"
    set -x
    python3 "$OLF_VALIDATION_SRC"/pipeline/top_10_diffs_dflow.py "$RESULTS_DIR"/pf_sol/ \
            "$RESULTS_DIR"/pf_metrics/ > "$RESULTS_DIR"/../top_10_diffs_"$DEVICE".txt
    set +x
    echo

    ##############################################################################
    # Collect all automata changes into a single file & erase the individual ones
    ##############################################################################
    colormsg "*** COLLECTING AUT DIFFS:"
    set -x
    python3 "$OLF_VALIDATION_SRC"/pipeline/collect_aut_diffs.py "$RESULTS_DIR"/aut/ "$RESULTS_DIR"/../ "$BASECASE"
    set +x
    echo

    ##########################################################
    # Prepare the Notebook (sets paths, weights & thresholds)
    ##########################################################
    colormsg "*** CREATING THE NOTEBOOK:"
    echo python3 "$OLF_VALIDATION_SRC"/notebooks/generate_notebooks.py \
            "$(cd "$(dirname "$RESULTS_DIR")"; pwd)" "$BASECASE" "$DEVICE" "$RESULTS_BASEDIR"/score_weights.csv

    mkdir -p "$RESULTS_DIR"/notebooks
    cp "$OLF_VALIDATION_SRC"/notebooks/simulator_A_vs_simulator_B_final.ipynb "$RESULTS_DIR"/notebooks
    rm "$OLF_VALIDATION_SRC"/notebooks/simulator_A_vs_simulator_B_final.ipynb
    echo

done

