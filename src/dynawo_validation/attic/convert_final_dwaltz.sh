#!/bin/bash
#
#
# We source ~/.bashrc in order to make aliases visible here. This could also be
# done by running as "bash -i", but GNU parallel chokes if the shell is interactive.

if [ -f "$HOME/.bashrc" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.bashrc"
fi

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 BASECASE_DIR LAUNCH_FILE_1 LAUNCH_FILE_2 IS_DWO_DWO(0 = no, 1 = yes) LAUNCHER_1(ASTRE or DWO) DWO_LAUNCHER(DWO)

  Example: $0 20210422_0930.BASECASE donneesModelesEntree.xml JOB.xml 0 astre dynawo.sh

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


run_astre(){
    if [ ! -d "$BASE_CASE_DIR"/Astre ]; then
        echo "Directory $BASE_CASE_DIR/Astre not found."
        exit 1
    fi
    echo "Running Astre"
    OLD_PWD=$(pwd)
    cd "$BASE_CASE_DIR"/Astre
    set_launcher "$1"
    $LAUNCHER "$2"
    cd "$OLD_PWD"

}


run_dynawo(){
    if [ ! -f "$BASE_CASE_DIR"/"$2" ]; then
        echo "Dynawo JOB file not found under $BASE_CASE_DIR/"
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$BASE_CASE_DIR"
    echo "Running Dynawo"
    set_launcher "$1"
    cd "$OLD_PWD"
    $LAUNCHER jobs "$2"
}



if [ $# -ne 6 ]; then
    usage
    exit -1
fi

BASE_CASE_DIR="${1%/}"  # remove a possible trailing slash
LAUNCH_FILE_1="${2%/}"   # remove a possible trailing slash
LAUNCH_FILE_2="${3%/}"   # remove a possible trailing slash
IS_DWO_DWO="${4%/}"  # remove a possible trailing slash
LAUNCHER_1="${5%/}"  # remove a possible trailing slash
LAUNCHER_2="${6%/}"   # remove a possible trailing slash


if ! [ -d "$BASE_CASE_DIR" ]; then
    echo "Case directory $BASE_CASE_DIR not found"
    usage
    exit -1
fi



########################################################################
#  Step 0: Run both cases
########################################################################
if [ "$IS_DWO_DWO" == "0" ]; then
    run_astre "$LAUNCHER_1" "$LAUNCH_FILE_1"
    run_dynawo "$LAUNCHER_2" "$LAUNCH_FILE_2"
else
    echo -n "Editing the JOB file... "
    LABEL=A
    ORIG_JOB_FILE=$(find "$BASE_CASE_DIR" -type f \( -iname '*.jobs' -o -iname '*JOB_A.xml' \) | head -n1)
    sed -i -e '/A/dynawo.log' '/dynawo.log	'
        "$ORIG_JOB_FILE" >| "$BASE_CASE_DIR"/JOB_"$LABEL".xml

    LABEL=B    
    ORIG_JOB_FILE=$(find "$BASE_CASE_DIR" -type f \( -iname '*.jobs' -o -iname '*JOB_B.xml' \) | head -n1)
    sed -i -e '/B/dynawo.log' '/dynawo.log'
        "$ORIG_JOB_FILE" >| "$BASE_CASE_DIR"/JOB_"$LABEL".xml

    run_dynawo "$LAUNCHER_1" "$LAUNCH_FILE_1"
    run_dynawo "$LAUNCHER_2" "$LAUNCH_FILE_2"
    
fi


########################################################################
#  Step 1: Delete usless files
########################################################################
if [ "$IS_DWO_DWO" == "0" ]; then
# TODO delete astre files
    OLD_PWD=$(pwd)
    cd "$BASE_CASE_DIR"
    rm -rf tFin
    cd "$OLD_PWD"
else
    OLD_PWD=$(pwd)
    cd "$BASE_CASE_DIR"
    rm -rf A/tFin
    rm -rf B/tFin
    cd "$OLD_PWD"
fi



