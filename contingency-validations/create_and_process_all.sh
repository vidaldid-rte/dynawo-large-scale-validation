#!/bin/bash
#
#
# create_and_process_all.sh: a simple high-level "driver" script that,
# given a directory containing a Dynawo+Astre basecase, and for each
# type of device (load, shunt, gen, etc.):
#
#    (a) generates all contingency cases
#
#    (b) runs them all and collects the results in the given directory
#
# So, for example, instead of running these commands:
#
#    $ cd ~/work/PtFige-Lille
#    $ rm -rf RESULTS gen_*
#    $ gen_contingencies.py 20190410_1200.BASECASE
#    $ run_all_contingencies.sh -v -c -s -o MyResults/Generators . 20190410_1200.BASECASE gen_
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
DYNAWO_VALIDATION=/home/marinjl/work/dynawo-validation-AIA

CREATE_ALL_CONTG_CASES=$DYNAWO_VALIDATION/contingency-validations
RUN_ALL_CONTG_CASES=$DYNAWO_VALIDATION/contingency-validations/run_all_contingencies.sh


usage()
{
    cat <<EOF

Usage: $0 [OPTIONS] BASECASE RESULTS_DIR

EOF
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
declare -A device_script
device_script[load]="loads/load_contingencies.py"
device_script[shunt]="shunts/shunt_contingencies.py"
device_script[gen]="generators/gen_contingencies.py"

# Process all devices from the list
for DEVICE in "${!device_script[@]}"; do
    echo "*** PROCESSING: $DEVICE"s
    RESULTS_DIR="$RESULTS_BASEDIR"/"$DEVICE"s
    mkdir -p "$RESULTS_DIR"
    rm -rf "$CASE_DIR"/"$DEVICE"_*
    "$CREATE_ALL_CONTG_CASES"/"${device_script[$DEVICE]}"  "$BASECASE"
    "$RUN_ALL_CONTG_CASES" -v -c -s -o "$RESULTS_DIR" "$CASE_DIR" "$BASECASE" "$DEVICE"_
    echo
    echo
    echo
done

