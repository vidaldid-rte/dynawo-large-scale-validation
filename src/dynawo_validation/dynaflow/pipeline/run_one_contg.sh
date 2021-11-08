#!/bin/bash
#
# run_one_contg.sh:
#
# given a specific contingency case (which can be of EITHER type,
# Astre vs. Dynawo OR Dynawo vs. Dynawo), plus the BASECASE it was
# derived from, this script runs the case and collects all results in
# a (configurable) output directory designed to store the results from
# many other contingencies. Optionally, delete the case to save space.
#
# (c) Grupo AIA
# marinjl@aia.es
#

# We source ~/.bashrc in order to make aliases visible here. This could also be
# done by running as "bash -i", but GNU parallel chokes if the shell is interactive.

if [ -f "$HOME/.bashrc" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.bashrc"
fi

# For saner programming:
set -o nounset  # don't set noclobber because we do need to overwrite files with ">"
set -o errexit -o pipefail 


usage()
{
    cat <<EOF

Usage: $0 [OPTIONS] BASECASE CONTINGENCY_CASE
  Options:
    -c | --cleanup  Delete the contingency case after getting the results
    -d | --debug    More debug messages
    -h | --help     This help message
    -o | --output   Specify a directory for collecting results (default: RESULTS)
    -v | --verbose  More verbose output
    -A | --launcherA  Defines the launcher of simulator A
    -B | --launcherB  Defines the launcher of simulator B

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
    if [ ! -d "$CONTG_CASE"/Astre ]; then
        echo "Directory $CONTG_CASE/Astre not found."
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$CONTG_CASE"/Astre
    RUNLOG=Astre.runStdout
    echo "Running Astre for case: $CONTG_CASE"
    set_launcher "$1"
    $LAUNCHER donneesModelesEntree.xml > "$RUNLOG" 2>&1
    if [ ! -f donneesModelesSortie.csv ]; then
        echo "Astre run failed. Check the runlog: $CONTG_CASE/Astre/$RUNLOG"
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    xz -c9 "$CONTG_CASE"/Astre/donneesModelesSortie.csv > "$outDir"/crv/"$prefix"-AstreCurves.csv.xz
    xz -c9 "$CONTG_CASE"/Astre/donneesModelesSortie.xml > "$outDir"/xml/"$prefix"-AstreSortie.xml.xz
    xz -c9 "$CONTG_CASE"/Astre/donneesModelesLog.xml    > "$outDir"/log/"$prefix"-AstreLog.xml.xz
    xz -c9 "$CONTG_CASE"/Astre/"$RUNLOG"                > "$outDir"/log/"$prefix"-"$RUNLOG".xz
}


run_hades(){
    HADES_DIR="$CONTG_CASE"/Hades
    if [ ! -d "$HADES_DIR" ]; then
        echo "Directory $HADES_DIR not found."
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$HADES_DIR"
    RUNLOG=Hades.RunStdout.txt
    echo "Running Hades for case: $CONTG_CASE"
    set_launcher "$1"
    $LAUNCHER donneesEntreeHADES2.xml out.xml log.xml > "$RUNLOG" 2>&1
    if [ ! -f out.xml ]; then
        echo "Hades run failed. Check the run log: $HADES_DIR/$RUNLOG"
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    xz -c9 "$HADES_DIR"/out.xml > "$outDir"/xml/"$prefix"-Hades.Out.xml.xz
    xz -c9 "$HADES_DIR"/log.xml > "$outDir"/log/"$prefix"-Hades.Log.xml.xz
    xz -c9 "$HADES_DIR/$RUNLOG" > "$outDir"/log/"$prefix"-"$RUNLOG".xz
}


run_dynawo(){
    if [ ! -f "$CONTG_CASE"/"$DWO_JOBFILE" ]; then
        echo "Dynawo JOB file not found under $CONTG_CASE/"
        exit 1
    fi
    OLD_PWD=$(pwd)
    cd "$CONTG_CASE"
    RUNLOG=Dynawo"$1".runStdout
    echo "Running Dynawo for case: $CONTG_CASE"
    set_launcher "$2"
    $LAUNCHER jobs "$DWO_JOBFILE" > "$RUNLOG" 2>&1 || true  # allow it to fail while using errexit flag
    if [ ! -f ./"$DWO_OUTPUT_DIR"/curves/curves.csv ]; then
        if [ -f ./"$DWO_OUTPUT_DIR"/curves/curves.xml ]; then
            echo "Dynawo$1 run: output curves file found in XML format; required format is CSV"
        else
            echo "Dynawo$1 run: no curves output found. Check Dynawo's log and the run-log: $CONTG_CASE/$RUNLOG"
        fi
        exit 1
    fi
    # Collect and compress all results
    cd "$OLD_PWD"
    if [ -f "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml ]; then
        xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/finalState/outputIIDM.xml > "$outDir"/xml/"$prefix"-Dynawo.IIDM"$1".xml.xz
    fi
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/curves/curves.csv           > "$outDir"/crv/"$prefix"-DynawoCurves"$1".csv.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/constraints/constraints.xml > "$outDir"/xml/"$prefix"-DynawoConstraints"$1".xml.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/timeLine/timeline.xml       > "$outDir"/xml/"$prefix"-DynawoTimeLine"$1".xml.xz
    xz -c9 "$CONTG_CASE"/"$DWO_OUTPUT_DIR"/logs/dynawo.log             > "$outDir"/log/"$prefix"-Dynawo"$1".log.xz
    xz -c9 "$CONTG_CASE"/"$RUNLOG"                                     > "$outDir"/log/"$prefix"-"$RUNLOG".xz
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

OPTIONS=cdho:vA:B:
LONGOPTS=cleanup,debug,help,output:,verbose,launcherA:,launcherB:

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

c=n d=n h=n outDir="RESULTS" v=n A="dynawo.sh" B="dynawo.sh"
# now enjoy the options in order and nicely split until we see --
while true; do
    case "$1" in
        -c|--cleanup)
            c=y
            shift
            ;;
        -d|--debug)
            d=y
            shift
            ;;
        -h|--help )
            h=y
            shift
            ;;
        -o|--output)
            outDir="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -v|--verbose)
            v=y
            shift
            ;;
        -A|--launcherA)
            A="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -B|--launcherB)
            B="$2"   # it could contain whitespace, so remember to quote it!
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

if [ $v = "y" ]; then
    echo "OPTIONS: cleanup: $c, debug: $d, help: $h, outDir: $outDir, verbose: $v, launcherA: $A, launcherB: $B"
    echo "PARAMS: $*"
fi

if [ $h = "y" ]; then
    usage
    exit 0
fi

# handle non-option arguments
if [[ $# -ne 2 ]]; then
    echo
    echo "$0: Two directory names are required."
    usage
    exit 4
fi

if [ $d = "y" ]; then
    set -o xtrace
fi


#######################################
# The real meat starts here
########################################
BASECASE=$1
CONTG_CASE=$2
if [ ! -d "$BASECASE" ]; then
   echo "ERROR: Basecase $BASECASE not found."
   exit 1
fi

if [ ! -d "$CONTG_CASE" ]; then
   echo "ERROR: Contingency case $CONTG_CASE not found."
   exit 1
fi
prefix=$(basename "$CONTG_CASE")

# Create the output dirs if they don't exist
mkdir -p "$outDir"/pf_sol
mkdir -p "$outDir"/crv
mkdir -p "$outDir"/aut
mkdir -p "$outDir"/xml
mkdir -p "$outDir"/log
mkdir -p "$outDir"/casediffs


#################################################
# Save the case compactly as diffs from BASECASE
#################################################
DIFFS="$outDir"/casediffs/"$prefix"-patch
if diff -ru "$BASECASE" "$CONTG_CASE" > "$DIFFS"; then
    echo "ERROR: $BASECASE and $CONTG_CASE are identical."
    exit 1
fi
xz -9f "$DIFFS"

if [ ! -f "$outDir"/casediffs/README ]; then
    cat <<EOF >"$outDir"/casediffs/README
    To re-create the contingency case from these patch files:

       1.  cp -a BASECASE CONTG_CASE

       2.  cd CONTG_CASE

       3.  xzcat CONTG_CASE-patch.xz | patch -p1

    And then verify the result with:

       diff -r BASECASE CONTG_CASE

EOF
fi


#####################################################################
# Detect whether it's astdwo / dwodwo, and run the cases accordingly
#####################################################################
DWO_JOBINFO_SCRIPT=$(dirname "$0")/dwo_jobinfo.py
CASE_TYPE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "CASE_TYPE" | cut -d'=' -f2)
hadestring=${A:0:5}
scripts_basedir=$(dirname "$0")
if [ "$CASE_TYPE" = "astdwo" ]; then
    if [ "$hadestring" == "astre" ]; then
        run_astre "$A"
        DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_file" | cut -d'=' -f2)
        DWO_JOBFILE=$(basename "$DWO_JOBFILE")
        DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directory" | cut -d'=' -f2)
        run_dynawo "" "$B"
    else
        DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_file" | cut -d'=' -f2)
        DWO_JOBFILE=$(basename "$DWO_JOBFILE")
        DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directory" | cut -d'=' -f2)
        run_dynawo "" "$A"
        run_astre "$B"  
    fi     
elif [ "$CASE_TYPE" = "dwohds" ]; then
    if [ "$hadestring" == "hades" ]; then
        run_hades "$A"
        DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_file" | cut -d'=' -f2)
        DWO_JOBFILE=$(basename "$DWO_JOBFILE")
        DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directory" | cut -d'=' -f2)
        basecase_name=$(basename "$BASECASE")
        run_dynawo "" "$B" 
        basename "$A" > "$outDir"/../.LAUNCHER_A_WAS_"$A" 2>&1 "$outDir"/../.LAUNCHER_A_WAS_"$A" || true
        basename "$B" version > "$outDir"/../.LAUNCHER_B_WAS_"$B" 2>&1 "$outDir"/../.LAUNCHER_B_WAS_"$B" || true
        python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Dynawo-aut-diff.csv "$outDir"/xml/"$prefix"-Dynawo.IIDM.xml.xz "$outDir"/../"$basecase_name"/
        python3 "$scripts_basedir"/extract_hades_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Hades-aut-diff.csv "$outDir"/xml/"$prefix"-Hades.Out.xml.xz "$outDir"/../"$basecase_name"/
        
    else
        DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_file" | cut -d'=' -f2)
        DWO_JOBFILE=$(basename "$DWO_JOBFILE")
        DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directory" | cut -d'=' -f2)
        run_dynawo "" "$A" 
        run_hades "$B"  
	basename "$A" version > "$outDir"/../.LAUNCHER_A_WAS_"$A" 2>&1 "$outDir"/../.LAUNCHER_A_WAS_"$A" || true 
        basename "$B" > "$outDir"/../.LAUNCHER_B_WAS_"$B" 2>&1 "$outDir"/../.LAUNCHER_B_WAS_"$B" || true
        basecase_name=$(basename "$BASECASE")
        python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Dynawo-aut-diff.csv "$outDir"/xml/"$prefix"-Dynawo.IIDM.xml.xz "$outDir"/../"$basecase_name"/
        python3 "$scripts_basedir"/extract_hades_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-Hades-aut-diff.csv "$outDir"/xml/"$prefix"-Hades.Out.xml.xz "$outDir"/../"$basecase_name"/ 
    fi    
else
    DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_fileA" | cut -d'=' -f2)
    DWO_JOBFILE=$(basename "$DWO_JOBFILE")
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directoryA" | cut -d'=' -f2)
    run_dynawo "A" "$A"
    DWO_JOBFILE=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "job_fileB" | cut -d'=' -f2)
    DWO_JOBFILE=$(basename "$DWO_JOBFILE")
    DWO_OUTPUT_DIR=$(python3 "$DWO_JOBINFO_SCRIPT" "$CONTG_CASE" | grep -F "outputs_directoryB" | cut -d'=' -f2)
    run_dynawo "B" "$B"
    basename "$A" version > "$outDir"/../.LAUNCHER_A_WAS_"$A" 2>&1 "$outDir"/../.LAUNCHER_A_WAS_"$A" || true 
    basename "$B" version > "$outDir"/../.LAUNCHER_B_WAS_"$B" 2>&1 "$outDir"/../.LAUNCHER_B_WAS_"$B" || true
    basecase_name=$(basename "$BASECASE")
    python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-DynawoA-aut-diff.csv "$outDir"/xml/"$prefix"-Dynawo.IIDMA.xml.xz "$outDir"/../"$basecase_name"/A/
    python3 "$scripts_basedir"/extract_dynawo_automata_changes_contgcase.py -s "$outDir"/aut/"$prefix"-DynawoB-aut-diff.csv "$outDir"/xml/"$prefix"-Dynawo.IIDMB.xml.xz "$outDir"/../"$basecase_name"/B/
fi



########################################
# Extract the PF solution
########################################
if  [ "$CASE_TYPE" != "astdwo" ]; then
    # Extracts the PF solution vaules from the xml output to CSV,
    # using a standardized format to allow comparisons
    scripts_basedir=$(dirname "$0")
    echo "Extracting the powerflow solutions for case: $CONTG_CASE"
    python3 "$scripts_basedir"/extract_powerflow_values.py "$CONTG_CASE" "$outDir"/..

    # Collect and compress all results
    xz -c9 "$CONTG_CASE"/pfsolution_AB.csv > "$outDir"/pf_sol/"$prefix"-pfsolution_AB.csv.xz
    for error_file in "elements_not_in_caseA.csv" "elements_not_in_caseB.csv"; do 
        if [ -f "$CONTG_CASE"/"$error_file" ]; then
            xz -c9 "$CONTG_CASE"/"$error_file" > "$outDir"/pf_sol/"$prefix"-"$error_file".xz
        fi
    done
fi


########################################
# Extract automata changes
########################################
# Extracts EVENTS from the xml output to CSV, using standardized
# labels to allow comparison
scripts_basedir=$(dirname "$0")/../../commons
python3 "$scripts_basedir"/extract_automata_changes.py "$CONTG_CASE" "$outDir"/../

# Collect and compress all results
if [ "$CASE_TYPE" = "dwohds" ]; then
    xz -c9 "$CONTG_CASE"/Hades/Hades_automata_changes.csv > "$outDir"/aut/"$prefix"-HadesAutomata.csv.xz
    xz -c9 "$CONTG_CASE"/Dynawo_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomata.csv.xz
else
    xz -c9 "$CONTG_CASE"/DynawoA_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomataA.csv.xz
    xz -c9 "$CONTG_CASE"/DynawoB_automata_changes.csv      > "$outDir"/aut/"$prefix"-DynawoAutomataB.csv.xz
fi



########################################
# Clean up
########################################
# Delete input dir if cleanup was requested
if [ $c = "y" ]; then
    rm -rf "$CONTG_CASE"
fi

