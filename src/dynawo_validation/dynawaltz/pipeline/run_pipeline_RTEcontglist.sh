#!/bin/bash
#
#
# run_pipeline.sh:
#
# A simple high-level "driver" script that runs the whole processing
# pipeline.  Given a directory containing either an Astre vs. Dynawo
# OR a Dynawo vs. Dynawo BASECASE, and for each type of device (load,
# shunt, gen, branchB, etc.):
#
#   (a) creates all contingency cases (IMPORTANT: it assumes that the
#       BASECASE is already prepared--see the script
#       "prepare_pipeline_basecase.py" to help you do that, before
#       running this script)
#
#   (b) runs them all, and collects the results in the given directory
#
# So, for example, instead of running these commands:
#
#    $ cd ~/work/PtFige-Lille
#    $ rm -rf gen_* MyResults/gens/
#    $ gen_contg.py 20190410_1350.BASECASE
#    $ run_all_contg.sh -v -c -o MyResults/gens . 20190410_1350.BASECASE gen_
#
# and having to repeat this for loads, branches, etc.; invoke this
# script instead, to obtain the same result:
#
#    $ run_pipeline.sh 20190410_1350.BASECASE MyResults
#
# You may use either relative or absolute paths.
#
#
# (c) Grupo AIA
# marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


# Configure what devices to process (using an associative array -- bash version >= 4)
declare -A create_contg
#create_contg[shunt]="shunt_contg.py"
#create_contg[load]="load_contg.py"
create_contg[gen]="gen_contg.py"
#create_contg[branchB]="branchB_contg.py"
#create_contg[branchF]="branchF_contg.py"
#create_contg[branchT]="branchT_contg.py"
#create_contg[bus]="bus_contg.py"

# Note this assumes all scripts are under the Github src dir structure
# (otherwise, you'll have to edit the correct paths below)
DWO_VALIDATION_SRC=$(dirname "$0")/..
DWO_VALIDATION_SRC=$(realpath "$DWO_VALIDATION_SRC")

# Config your particular options to pass to run_all_contingencies.sh
declare -a RUN_OPTS
RUN_OPTS=("-v" "-c")


# Nothing else to configure below this point
CONTG_SRC=$DWO_VALIDATION_SRC/contingency-validations
METRICS_SRC=$DWO_VALIDATION_SRC/metrics
GREEN="\\033[1;32m"
NC="\\033[0m"


usage()
{
    cat <<EOF

Usage: $0 BASECASE RESULTS_DIR

EOF
}


colormsg()
{
    echo -e "${GREEN}$1${NC}"
}


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
CASE_DIR=$(dirname "$BASECASE")


if [ -f "$RESULTS_BASEDIR" ]; then
   echo "ERROR: Results directory $RESULTS_BASEDIR is an existing file!!!"
   exit 1
fi
echo "Generating results under directory: $RESULTS_BASEDIR"
mkdir -p "$RESULTS_BASEDIR"


# Process all devices from the list
for DEVICE in "${!create_contg[@]}"; do
    colormsg "****** PROCESSING: $DEVICE"s
    echo
    
    colormsg "*** CREATING CONTINGENCY CASES:"
    declare -a CONTG_LIST
    CONTG_LIST=("FLAMA.*" "PALUE.*" "PENLY.*" "HAVRE6HAVRET4"
                "CORD5.CORD5." "G.RIV.TG1" "CHIN.7CHIN2." "D.BU.7D.BUR."
                "CIVAU7CIVAU." "GRAV57GRAV5T." "CHOO.7GROUP.*")    
    rm -rf "$CASE_DIR"/"$DEVICE"_*
    set -x
    python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "$BASECASE" "${CONTG_LIST[@]}"
    set +x
    echo
    
    colormsg "*** RUNNING CONTINGENCY CASES:"
    RESULTS_DIR="$RESULTS_BASEDIR"/"$DEVICE"s
    mkdir -p "$RESULTS_DIR"
    set -x
    "$CONTG_SRC"/run_all_contg.sh "${RUN_OPTS[@]}" -o "$RESULTS_DIR" "$CASE_DIR" "$BASECASE" "$DEVICE"_
    set +x
    echo

    colormsg "*** COMPUTING CURVE METRICS:"
    python3 "$METRICS_SRC"/calc_curve_diffmetrics.py "$RESULTS_DIR"/crv "$DEVICE"_ "$BASECASE"
    echo
    
    colormsg "*** COMPUTING AUTOMATA EVENT METRICS:"
    python3 "$METRICS_SRC"/calc_automata_diffmetrics.py "$RESULTS_DIR"/aut "$DEVICE"_ "$BASECASE"
    echo

done

