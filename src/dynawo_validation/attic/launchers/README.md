
LAUNCHERS USED FOR ASTRE AND DYNAWO IN THE VALIDATION PIPELINE
==============================================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------


The validation pipeline will use any standard installation of Astre
and Dynawo, with only these particular requirements:

  * The Dynawo version should be RTE's private version, and its
    launcher should be called `dynawo-RTE`, and it should be in
    the $PATH.
  
  * The Astre launcher should be called `astre` and it should be in
    the $PATH. **IMPORTANT:** this launcher should additionally invoke
    the Python script `astreToCSV.py`, right after the execution of
    Astre. (This script, which was provided by RTE, extracts the curve
    data from Astre's output XML into a CSV file, in a format similar
    to Dynawo's.)


Therefore, this directory provides a verbatim copy of the launchers we
used during development at AIA. It also includes a copy of the Python
script `astreToCSV.py` that was provided by RTE.

Some quick notes on the launchers and how to adapt them to your
particular installation of Astre and Dynawo:

   * `astre`, `astre.DEBUG`: these are based on Astre's README and its
     `enable` script, then adding a call to `astreToCSV.py` at the
     end. **You will only need to edit the first variable,
     THIRDPARTY_INSTALL_DIR.**
   
   * `dynawo-RTE`: this one is just `dynawo.sh`.  **You will only need
     to edit the first variable, DYNAWO_INSTALL_DIR.**

