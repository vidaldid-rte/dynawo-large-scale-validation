#!/bin/bash
#
# Quick and dirty script to automate all steps for building/installing the package:
#   * it uses a venv named "dwo_venv" right under the top-level of the repo
#   * it also pip-updates all dependencies to their latest version ("eager" strategy)
# Assumes Python 3.4+.
# 
# (c) Grupo AIA / RTE
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail


PKG="dynawo_validation_RTE_AIA"
SCRIPT_PATH=$(realpath "$0")
MY_LOCAL_REPO=$(dirname "$SCRIPT_PATH")
MY_VENV="$MY_LOCAL_REPO"/dwo_venv



GREEN="\\033[1;32m"
NC="\\033[0m"
colormsg()
{
    echo -e "${GREEN}$1${NC}"
}
colormsg_nnl()
{
    echo -n -e "${GREEN}$1${NC}"
}




# Step 0: reminder to refresh your local workspace
echo "You're about to build & reinstall: $PKG  (remember to refresh your local repo if needed)"
read -p "Are you sure? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit
fi


# Step 1: make sure the Python venv exists and activate it
echo
if [ ! -d "$MY_VENV" ]; then
    colormsg_nnl "Virtual env not found, creating it now... "
    python3 -m venv "$MY_VENV"
    colormsg "OK."
fi
colormsg_nnl "Activating venv... "
# shellcheck source=/dev/null
source "$MY_VENV"/bin/activate
colormsg "OK."
colormsg "Installing/upgrading pip, wheel, setuptools, and build... "
pip install --upgrade pip wheel setuptools build
colormsg "OK."


# Step 2: build
echo
colormsg "Building the package... "
cd "$MY_LOCAL_REPO" && python3 -m build
colormsg "OK."


# Step 3: install the package
echo
colormsg "Installing the package... "
pip uninstall "$PKG" 
pip install "$MY_LOCAL_REPO"/dist/*.whl
colormsg "OK."


# Step 4: upgrade all deps
echo
colormsg "Upgrading all dependencies... "
pip install -U --upgrade-strategy eager  "$PKG"
colormsg "OK."


# Step 5: some packages do not automatically register their notebook extensions
colormsg "Registering ipydatagrid as a Jupyter Notebook extension... "
jupyter nbextension enable --py --sys-prefix ipydatagrid
jupyter nbextension enable --py --sys-prefix qgrid
colormsg "OK. (to check all extensions, execute: jupyter nbextension list)"

