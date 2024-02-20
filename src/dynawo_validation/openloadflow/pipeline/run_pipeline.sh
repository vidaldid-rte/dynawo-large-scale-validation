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
declare -a RUNBASE_OPTS


# Nothing else to configure below this point
CONTG_SRC=$OLF_VALIDATION_SRC/pipeline
GREEN="\\033[1;32m"
NC="\\033[0m"

find_cmd()
{
    find "$CASE_DIR" -maxdepth 1 -type d -name "$1"'*'
}
# TODO: add -a --allcontg for run all contingencies
# TODO: add -l / --regextlist egain
# TODO: add -r --random to run a random sample of contingencies et aussi --prandom/-p
usage()
{
    cat <<EOF
Usage: olf_run_validation [OPTIONS] BASECASE RESULTS_DIR
  Options:
    -H | --launcherH  Defines the launcher for Hades
    -O | --launcherO  Defines the launcher for OpenLoadFlow
    -c | --cleanup    Delete input cases after getting the results
    -d | --debug      More debug messages
    -s | --sequential Run jobs sequentially (defult is parallel)
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

OPTIONS=H:O:hdcsw:
LONGOPTS=launcherO:,launcherH:,help,debug,cleanup,weights,sequential:
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# now enjoy the options in order and nicely split until we see --
H="hades2.sh" O="itools" h=n sequential='n'
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
        -s|--sequential)
            sequential=y
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

# No cleanup for base case because files are referenced by symbolic links
RUNBASE_OPTS=("${RUNALL_OPTS[@]}")

# Continue to add options that are specific to contingencies
if [ $cleanup = "y" ]; then
    RUNALL_OPTS=("${RUNALL_OPTS[@]}" "-c")
fi

if [ $sequential = "y" ]; then
    RUNALL_OPTS=("${RUNALL_OPTS[@]}" "-s")
fi

# handle non-option arguments
if [[ $# -ne 2 ]]; then
    echo
    echo "olf_run_validation: Two arguments are required."
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

###################################################
# Create the itools config directory
###################################################

ITOOLS_DIR=${REAL_RESULTS_BASEDIR}/.itools
if [ ! -d  "${ITOOLS_DIR}" ]; then
    mkdir "${ITOOLS_DIR}"

    cat <<EOF > "${ITOOLS_DIR}"/config.yml
load-flow:
  default: "OpenLoadFlow"
EOF

    cat <<EOF > "${ITOOLS_DIR}"/itools.conf
powsybl_config_name=config
java_xmx=8G
EOF

    cat <<EOF > "${ITOOLS_DIR}"/logback-itools.xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <Pattern>%d{yyyy-MM-dd_HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</Pattern>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="STDOUT" />
    </root>
</configuration>
EOF

fi

# Set the config directory variable for itools
export powsybl_config_dirs="${ITOOLS_DIR}"


#######################################
# Run the base case
#######################################

  RESULTS_DIR="$RESULTS_BASEDIR"/basecase
  mkdir -p "$RESULTS_DIR"
  "$CONTG_SRC"/run_one_case.sh "${RUNBASE_OPTS[@]}" --launcherInfo -o "$RESULTS_DIR" -H "$H" -O "$O" \
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


#######################################
# Process all types of contingency
#######################################

# TODO Contingenes spécifiques Transfo / HVDC / Groupe  (lié au controle de tension ? -- A voir)
declare -A create_contg
create_contg[shunt]="create_shunt_contg.py"
create_contg[load]="create_load_contg.py"
create_contg[gen]="create_gen_contg.py"
create_contg[branchB]="create_branchB_contg.py"

CASE_DIR=${RESULTS_BASEDIR}
for DEVICE in "${!create_contg[@]}"; do
    echo
    colormsg "****** PROCESSING CONTINGENCIES OF TYPE: $DEVICE"
    echo

    ####################################
    # Creation of the contingency cases
    ####################################
    CASE_SOURCE_DIR=${RESULTS_BASEDIR}/$(basename "${BASECASE}")
    colormsg "*** CREATING CONTINGENCY CASES:"
    python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "${CREATE_OPTS[@]}" "$CASE_SOURCE_DIR" "$RESULTS_BASEDIR"
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
    "$CONTG_SRC"/run_all_contg.sh "${RUNALL_OPTS[@]}" -o "$RESULTS_DIR" -H "$H" -O "$O" \
                "$CASE_DIR" "$CASE_SOURCE_DIR" "$DEVICE"#
    echo

    ###############################
    # Calculate Power Flow metrics
    ###############################
    colormsg "*** COMPUTING DIFF METRICS:"
    python3 "$CONTG_SRC"/calc_global_pf_diffmetrics.py "$RESULTS_DIR"/pf_sol "$DEVICE#"
    echo

    #####################################
    # Calculate the "Top 10" mini-report
    #####################################
    colormsg "*** COMPUTING TOP 10 DIFFS:"
    python3 "$OLF_VALIDATION_SRC"/pipeline/top_10_diffs_dflow.py "$RESULTS_DIR"/pf_sol/ \
            "$RESULTS_DIR"/pf_metrics/ >| "$RESULTS_DIR"/../top_10_diffs_"$DEVICE".txt
    echo


    ##########################################################
    # Prepare the Notebook (sets paths, weights & thresholds)
    ##########################################################
    colormsg "*** CREATING THE NOTEBOOK:"
    python3 "$OLF_VALIDATION_SRC"/notebooks/generate_notebooks.py \
            "$(cd "$(dirname "$RESULTS_DIR")"; pwd)" "$BASECASE" "$DEVICE" "$RESULTS_BASEDIR"/score_weights.csv

    mkdir -p "$RESULTS_DIR"/notebooks
    cp "$OLF_VALIDATION_SRC"/notebooks/Hades_vs_OpenLoadFlow_final.ipynb "$RESULTS_DIR"/notebooks
    rm "$OLF_VALIDATION_SRC"/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
    echo

done

