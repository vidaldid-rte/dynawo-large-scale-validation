#!/bin/bash
#
#
# create_and_process_all.sh: a simple high-level "driver" script that
# runs the whole process pipeline.  Given a directory containing a
# Dynawo+Astre basecase, and for each type of device (load, shunt,
# gen, etc.):
#
#   (a) creates all contingency cases (it assumes the BASECASE is
#       already prepared--see the script "prepare_basecase.py" to help
#       you do that, before running this script)
#
#   (b) runs them all and collects the results in the given directory
#
# So, for example, instead of running these commands:
#
#    $ cd ~/work/PtFige-Lille
#    $ rm -rf RESULTS gen_*
#    $ gen_contingencies.py 20190410_1200.BASECASE
#    $ run_all_contingencies.sh -v -c -o MyResults/Generators . 20190410_1200.BASECASE gen_
#
# and having to repeat this for loads, branches, etc., invoke this
# script as follows, to obtain the same result:
#
#    $ create_and_process_all.sh 20190410_1200.BASECASE MyResults
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


# Config your particular installation path here:
DWO_VALIDATION_SRC=$HOME/work/dynawo-validation-AIA

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


# Configure what devices to process (using an associative array -- bash version >= 4)
declare -A create_contg
create_contg[shunt]="shunts/shunt_contingencies.py"
create_contg[load]="loads/load_contingencies.py"
create_contg[gen]="generators/gen_contingencies.py"

# Process all devices from the list
for DEVICE in "${!create_contg[@]}"; do
    colormsg "****** PROCESSING: $DEVICE"s
    echo
    
    colormsg "*** CREATING CONTINGENCY CASES:"
    rm -rf "$CASE_DIR"/"$DEVICE"_*
    set -x
    "$CONTG_SRC"/"${create_contg[$DEVICE]}" "$BASECASE"
    set +x
    echo
    
    colormsg "*** RUNNING CONTINGENCY CASES:"
    RESULTS_DIR="$RESULTS_BASEDIR"/"$DEVICE"s
    mkdir -p "$RESULTS_DIR"
    set -x
    "$CONTG_SRC"/run_all_contingencies.sh "${RUN_OPTS[@]}" -o "$RESULTS_DIR" "$CASE_DIR" "$BASECASE" "$DEVICE"_
    set +x
    echo

    colormsg "*** COMPUTING CURVE METRICS:"
    "$METRICS_SRC"/calc_curve_diffmetrics.py "$RESULTS_DIR"/crv "$DEVICE"_
    echo
    
    colormsg "*** COMPUTING AUTOMATA EVENT METRICS:"
    "$METRICS_SRC"/calc_automata_diffmetrics.py "$RESULTS_DIR"/aut "$DEVICE"_ "$BASECASE"
    echo

done

