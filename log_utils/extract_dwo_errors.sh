#!/bin/bash
#
# A simple script to extract errors from the Dynawo logs of multiple contingency runs.
# (c) 2021 Grupo AIA
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

OUTPUT_FILE="error_summary.txt"
EXTRACT_FROM="INFO |     4299.000 |"


usage()
{
    cat <<EOF

Usage: $0 LOG__DIR

  where LOGDIR contains the compressed Dynawo log files for the contingency runs.

  Example: $0 20190410_1200.RESULTS/branchBs/log
    (will process all logs named *-Dynawo.log.xz found under that directory) 

EOF
}


if [[ $# -ne 1 ]]; then
    usage
    exit 4
fi
LOG_DIR="$1"

rm -rf $OUTPUT_FILE
echo "Cases containing ERRORS:"
echo "========================"
for FI in "$LOG_DIR"/*-Dynawo.log.xz; do
    if xzgrep -q "ERROR" "$FI"; then
	echo "$FI"
	echo "$FI" >> $OUTPUT_FILE
	# shunts, gens, branches: "state of X change"
	# loads: "change for model"
	xzgrep --max-count=1 -B2 -A5000 "$EXTRACT_FROM" "$FI" >> $OUTPUT_FILE
	echo >> $OUTPUT_FILE
    fi
done


