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

# Config your particular options to pass to run_all_contingencies.sh
declare -a RUN_OPTS
RUN_OPTS=("-v" "-c")


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
    -a | --allcontg   Run all the contingencies
    -l | --regexlist  Run all the contingencies of a .txt file
    -r | --random     Run a different random sample of contingencies
    -h | --help       This help message
EOF
}

colormsg()
{
    echo -e "${GREEN}$1${NC}"
}


#######################################
# getopt-like input option processing
#######################################

# -allow a command to fail with !’s side effect on errexit
# -use return value from ${PIPESTATUS[0]}, because ! hosed $?
! getopt --test > /dev/null 
if [[ ${PIPESTATUS[0]} -ne 4 ]]; then
    echo "I’m sorry, 'getopt --test' failed in this environment."
    exit 1
fi


OPTIONS=A:B:hal:rsdc
LONGOPTS=launcherB:,launcherA:,help,allcontg,regexlist:,random,sequential,debug,cleanup

# -regarding ! and PIPESTATUS see above
# -temporarily store output to be able to check for errors
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
! PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
    # e.g. return value is 1
    #  then getopt has complained about wrong arguments to stdout
    usage
    exit 2
fi
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

A="dynawo.sh" B="dynawo.sh" h=n allcontg=n regexlist="None" random=n sequential=n debug=n cleanup=n
# now enjoy the options in order and nicely split until we see --
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

runallopts=""
space=" "

if [ "$allcontg" == "y" ]; then
    if [ "$regexlist" != "None" ]; then
        echo "ERROR: Option --allcontg and --regexlist aren't supported together"
        exit 1
    fi    
fi

if [ "$regexlist" != "None" ]; then
    if [ "$random" == "y" ]; then
        echo "ERROR: Option --regexlist and --random aren't supported together"
        exit 1
    fi    
fi

if [ "$allcontg" == "y" ]; then
    if [ "$random" == "y" ]; then
        echo "ERROR: Option --allcontg and --random aren't supported together"
        exit 1
    fi    
fi


if [ $h = "y" ]; then
    usage
    exit 0
fi


if [ $sequential = "y" ]; then
    runallopts+=-s
    runallopts+=$space
fi

if [ $debug = "y" ]; then
    runallopts+=-d
    runallopts+=$space
fi

if [ $cleanup = "y" ]; then
    runallopts+=-c 
    runallopts+=$space
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
    rm -rf "$CASE_DIR"/"$DEVICE"_*
    if [ "$allcontg" = "n" ]; then
       if [ "$regexlist" = "None" ]; then
          if [ "$random" = "n" ]; then
             set -x
             python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "$BASECASE"
             set +x
          else
             set -x
             python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "-r" "$BASECASE"
             set +x   
          fi   
       else
          set -x
          python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "-t" "$regexlist" "$BASECASE"
          set +x
       fi
    else
       if [ "$regexlist" = "None" ]; then
          set -x
          python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "-a" "$BASECASE"
          set +x
       else
          set -x
          python3 "$CONTG_SRC"/"${create_contg[$DEVICE]}" "-t" "$regexlist" "-a" "$BASECASE"
          set +x
       fi
    fi
    echo
    
    dirList=$(find_cmd "$DEVICE"_)
    if [ -z "$dirList" ]; then
       echo -e "No cases with pattern $DEVICE""_* found under $CASE_DIR"
    else
       colormsg "*** RUNNING CONTINGENCY CASES:"
       RESULTS_DIR="$RESULTS_BASEDIR"/"$DEVICE"
       mkdir -p "$RESULTS_DIR"
       set -x
       "$CONTG_SRC"/run_all_contg.sh "${RUN_OPTS[@]}" $runallopts -o "$RESULTS_DIR" -A "$A" -B "$B" "$CASE_DIR" "$BASECASE" "$DEVICE"_
       set +x
       echo

       colormsg "*** COMPUTING CURVE METRICS:"
       python3 "$CONTG_SRC"/calc_curve_diffmetrics.py "$RESULTS_DIR"/crv "$DEVICE"_ "$BASECASE"
       echo
       
       colormsg "*** COMPUTING TOP 10 DIFFS:"
       python3 "$DWO_VALIDATION_SRC"/pipeline/top_10_diffs_dwaltz.py "$RESULTS_DIR"/metrics/crv_reducedparams.csv > "$RESULTS_DIR"/../top_10_diffs_"$DEVICE".txt
       echo
    
       colormsg "*** COMPUTING AUTOMATA EVENT METRICS:"
       python3 "$CONTG_SRC"/calc_automata_diffmetrics.py "$RESULTS_DIR"/aut "$DEVICE"_ "$BASECASE"
       echo

       colormsg "*** CREATING NOTEBOOK:"
       python3 "$DWO_VALIDATION_SRC"/notebooks/generate_notebooks.py "$(cd "$(dirname "$RESULTS_DIR")"; pwd)/$DEVICE" "$BASECASE" "$DEVICE"_
       mkdir -p "$RESULTS_DIR"/notebooks
       cp "$DWO_VALIDATION_SRC""/notebooks/simulator_A_vs_simulator_B_final.ipynb" "$RESULTS_DIR"/notebooks
       rm "$DWO_VALIDATION_SRC""/notebooks/simulator_A_vs_simulator_B_final.ipynb"
       echo
    fi

done

