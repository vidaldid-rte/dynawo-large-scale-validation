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
MATCH_TO_EXTRACT_FROM="starting simulation"


usage()
{
    cat <<EOF

Usage: $0 LOG__DIR

  where LOGDIR contains the compressed Dynawo log files for the contingency runs.

  Example: $0 20190410_1200.RESULTS/branchBs/log
    (will process all logs named *-Dynawo.log.xz found under that directory) 

EOF
}

xztrim()
{
    xzcat "$1" | awk  "/$MATCH_TO_EXTRACT_FROM/ {print_line=1} print_line"
}




if [[ $# -ne 1 ]]; then
    usage
    exit 4
fi
LOG_DIR="$1"

rm -rf $OUTPUT_FILE
echo "Cases containing ERRORS:"
echo "========================"
find "$LOG_DIR" -maxdepth 1 -name '*-Dynawo.log.xz' | while read -r LOG_FILE; do
    if xztrim "$LOG_FILE" | grep -F -q "ERROR"; then
        echo "$LOG_FILE"
        {
            echo "$LOG_FILE"
            echo "==============================================================="
            xztrim "$LOG_FILE"
            echo -e "[***END OF LOG***]\\n\\n"
        } >> $OUTPUT_FILE
    fi
done

