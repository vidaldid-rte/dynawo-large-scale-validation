#!/bin/bash
#
# A simple script to extract errors from the Dynawo logs of multiple contingency runs.
# (c) 2021 Grupo AIA
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
###set -o errexit -o pipefail 

OUTPUT_FILE="error_summary.txt"
MATCH_TO_EXTRACT_FROM="starting simulation"


usage()
{
    cat <<EOF

Usage: $0 LOG__DIR [error_string]

  where LOGDIR contains the compressed Dynawo log files for the contingency runs. You may also
  provide a quoted error string to search for (default: "ERROR").

  Example: $0 20190410_1200.RESULTS/branchBs/log
    (will process all logs named *-Dynawo.log.xz found under that directory) 

EOF
}

xztrim()
{
    xzcat "$1" | awk  "/$MATCH_TO_EXTRACT_FROM/ {print_line=1} print_line"
}



if [[ $# -eq 1 ]]; then
    LOG_DIR="$1"
    ERR_STRING="ERROR"
elif [[ $# -eq 2 ]]; then
    LOG_DIR="$1"
    ERR_STRING="$2"
else
    usage
    exit 4
fi

rm -rf $OUTPUT_FILE
echo "Cases containing ERRORS:"
echo "========================"
find "$LOG_DIR" -maxdepth 1 -name '*-Dynawo.log.xz' | while read -r LOG_FILE; do
    # echo "Searching $LOG_FILE"
    if xztrim "$LOG_FILE" | grep -F -q "$ERR_STRING"; then
        echo "$LOG_FILE"
        {
            echo "$LOG_FILE"
            echo "==============================================================="
            xztrim "$LOG_FILE"
            echo -e "[***END OF LOG***]\\n\\n"
        } >> $OUTPUT_FILE
    fi
done

