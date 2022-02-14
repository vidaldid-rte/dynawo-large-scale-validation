#!/bin/bash
#
#
# run_pipeline.sh:
#
# A simple high-level "driver" script that runs the whole processing
# pipeline.  Given a directory containing either an Hades vs. Dynawo
# OR a Dynawo vs. Dynawo BASECASE, and for each type of device (load,
# shunt, gen, branchB, etc.):
#
#   (a) creates all contingency cases (IMPORTANT: it assumes that the
#       BASECASE is already prepared--see the script
#       "prepare_pipeline_basecase.py" to help you do that, before
#       running this script)
#
#   (b) runs them all (which also processes and collects the results in
#       the provided Results directory)
#
#   (c) calculates metrics, summary reports, etc., and finally
#       prepares the Notebook for analysis.
#
# So, for example, instead of running these commands:
#
#    $ cd ~/work/DynaFlow/
#    $ rm -rf gen#* MyResults/gens/
#    $ gen_contg.py 20190410_1350.BASECASE
#    $ run_all_contg.sh -v -c -o MyResults/gens . 20190410_1350.BASECASE gen#
#    $ calc_global_pf_diffmetrics.py MyResults/gens/pf_sol gen#
#    $ [etc. etc.]
#
# and then having to repeat this for loads, branches, etc.; invoke
# this script instead, to obtain the same result:
#
#    $ run_pipeline.sh [options] 20190410_1350.BASECASE MyResults
#
# You may use either relative or absolute paths.
#
#
# (c) Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


# Configure what devices to process (using an associative array -- bash version >= 4)
declare -A create_contg
create_contg[shunt]="create_shunt_contg.py"
create_contg[load]="create_load_contg.py"
create_contg[gen]="create_gen_contg.py"
create_contg[branchB]="create_branchB_contg.py"
#create_contg[branchF]="branchF_contg.py"
#create_contg[branchT]="branchT_contg.py"
#create_contg[bus]="bus_contg.py"

# Note this assumes all scripts are under the Github src dir structure
# (otherwise, you'll have to edit the correct paths below)
DWO_VALIDATION_SRC=$(dirname "$0")/..
DWO_VALIDATION_SRC=$(realpath "$DWO_VALIDATION_SRC")

# Config options to pass to run_all_contingencies.sh (using a Bash array as a
# safe way to pass parameters when invoking it)
declare -a RUNALL_OPTS
RUNALL_OPTS=("-v" "-c")


# Nothing else to configure below this point
CONTG_SRC=$DWO_VALIDATION_SRC/pipeline
GREEN="\\033[1;32m"
NC="\\033[0m"

find_cmd()
{
    find "$CASE_DIR" -maxdepth 1 -type d -name "$1"'*'
}

usage()
{
    cat <<EOF
Usage: $0 [OPTIONS] BASECASE RESULTS_DIR
  Options:
    -A | --launcherA  Defines the launcher of simulator A
    -B | --launcherB  Defines the launcher of simulator B
    -c | --cleanup    Delete input cases after getting the results
    -d | --debug      More debug messages    
    -s | --sequential Run jobs sequentially (defult is parallel)
    -a | --allcontg   Run all the contingencies
    -l | --regexlist  Run all the contingencies of a .txt file
    -w | --weights    Calculate scores with weights
    -r | --random     Run a different random sample of contingencies
    -p | --prandom    Run a different random sample of contingencies with defined seed
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

OPTIONS=A:B:hal:rsdcp:w:
LONGOPTS=launcherB:,launcherA:,help,allcontg,regexlist:,random,sequential,debug,cleanup,prandom:,weights:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
A="dynawo.sh" B="dynawo.sh" h=n allcontg=n regexlist="None" random=n sequential=n
debug=n cleanup=n prandom="None" weightslist="None"
while true; do
    case "$1" in
        -A|--launcherA)
            A="$2"   # it could contain whitespace, so remember to quote it!
            echo "Launcher A defined as $A"
            shift 2
            ;;
        -B|--launcherB)
            B="$2"   # it could contain whitespace, so remember to quote it!
            echo "Launcher B defined as $B"
            shift 2
            ;;
        -h|--help)
            h=y
            shift
            ;;
        -a|--allcontg)
            allcontg=y
            shift
            ;;
        -l|--regexlist)
            regexlist="$2"
            echo "Read regex from $2 file"
            shift 2
            ;;
        -w|--weights)
            weightslist="$2"
            echo "Read weights from $2 file"
            shift 2
            ;;   
        -r|--random)
            random=y
            shift
            ;;
        -s|--sequential)
            sequential=y
            shift
            ;;
        -d|--debug)
            debug=y
            shift
            ;;
        -c|--cleanup)
            cleanup=y
            shift
            ;;
        -p|--prandom)
            prandom="$2"
            echo "Defined seed $2"
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

if [ $h = "y" ]; then
    usage
    exit 0
fi

# handle options for create_contg.py
if [ "$allcontg" == "y" ] && [ "$regexlist" != "None" ]; then
    echo "ERROR: Option --allcontg and --regexlist aren't supported together"
    exit 1
fi

if [ "$regexlist" != "None" ] && [ "$random" == "y" ]; then
    echo "ERROR: Option --regexlist and --random aren't supported together"
    exit 1
fi

if [ "$allcontg" == "y" ] && [ "$random" == "y" ]; then
    echo "ERROR: Option --allcontg and --random aren't supported together"
    exit 1
fi

if [ "$regexlist" != "None" ] && [ "$prandom" != "None" ]; then
    echo "ERROR: Option --regexlist and --prandom aren't supported together"
    exit 1
fi

if [ "$allcontg" == "y" ] && [ "$prandom" != "None" ]; then
    echo "ERROR: Option --allcontg and --prandom aren't supported together"
    exit 1
fi

if [ "$random" == "y" ] && [ "$prandom" != "None" ]; then
    echo "ERROR: Option --random and --prandom aren't supported together"
    exit 1
fi

if [ "$allcontg" = "y" ]; then
    CREATE_OPTS=("-a")
fi

if [ "$regexlist" != "None" ]; then
    CREATE_OPTS=("-t" "$regexlist")
fi

if [ "$random" = "y" ]; then
    CREATE_OPTS=("-r")
fi

if [ "$prandom" != "None" ]; then
    CREATE_OPTS=("-p" "$prandom")
fi

# handle options for run_all.sh
if [ $sequential = "y" ]; then
    RUNALL_OPTS=("${RUNALL_OPTS[@]}" "-s")
fi

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
if [ "$REAL_BASECASE" != "$REAL_RESULTS_BASEDIR" ]; then
   cp -a "$BASECASE" "$RESULTS_BASEDIR"
   # TODO: Run the basecase now here, to save the user that step
fi
basecase_name=$(basename "$BASECASE")
CP_BASECASE="$RESULTS_BASEDIR"/"$basecase_name"

# Process automata changes for the BASECASE run
DWO_JOBINFO_SCRIPT="$CONTG_SRC"/dwo_jobinfo.py
CASE_TYPE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CP_BASECASE" | grep -F "CASE_TYPE" | cut -d'=' -f2)
if [ "$CASE_TYPE" = "dwohds" ]; then
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CP_BASECASE" | grep -F "outputs_directory" | cut -d'=' -f2)
    set -x
    python3 "$CONTG_SRC"/extract_dynawo_automata_changes_basecase.py \
        "$CP_BASECASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml "$CP_BASECASE"
    python3 "$CONTG_SRC"/extract_hades_automata_changes_basecase.py \
        "$CP_BASECASE"/Hades/out.xml "$CP_BASECASE" "$CP_BASECASE"/Hades/donneesEntreeHADES2.xml
    set +x
else
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CP_BASECASE" | grep -F "outputs_directoryA" | cut -d'=' -f2)
    set -x
    python3 "$CONTG_SRC"/extract_dynawo_automata_changes_basecase.py \
        "$CP_BASECASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml "$CP_BASECASE"/A/
    set +x
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CP_BASECASE" | grep -F "outputs_directoryB" | cut -d'=' -f2)
    set -x
    python3 "$CONTG_SRC"/extract_dynawo_automata_changes_basecase.py \
        "$CP_BASECASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml "$CP_BASECASE"/B/
    set +x
fi


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
    python3 "$DWO_VALIDATION_SRC"/pipeline/top_10_diffs_dflow.py "$RESULTS_DIR"/pf_sol/ \
            "$RESULTS_DIR"/pf_metrics/ > "$RESULTS_DIR"/../top_10_diffs_"$DEVICE".txt
    set +x
    echo

    ##############################################################################
    # Collect all automata changes into a single file & erase the individual ones
    ##############################################################################
    colormsg "*** COLLECTING AUT DIFFS:"
    set -x
    python3 "$DWO_VALIDATION_SRC"/pipeline/collect_aut_diffs.py "$RESULTS_DIR"/aut/ "$RESULTS_DIR"/../ "$BASECASE"
    set +x
    echo

    ##########################################################
    # Prepare the Notebook (sets paths, weights & thresholds)
    ##########################################################
    colormsg "*** CREATING THE NOTEBOOK:"
    set -x
    python3 "$DWO_VALIDATION_SRC"/notebooks/generate_notebooks.py \
            "$(cd "$(dirname "$RESULTS_DIR")"; pwd)" "$BASECASE" "$DEVICE" "$RESULTS_BASEDIR"/score_weights.csv
    set +x
    mkdir -p "$RESULTS_DIR"/notebooks
    cp "$DWO_VALIDATION_SRC"/notebooks/simulator_A_vs_simulator_B_final.ipynb "$RESULTS_DIR"/notebooks
    rm "$DWO_VALIDATION_SRC"/notebooks/simulator_A_vs_simulator_B_final.ipynb
    echo

done

