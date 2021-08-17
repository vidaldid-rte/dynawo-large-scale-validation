
DynaFlow validation
====================

This section of the repo contains scripts and utilities used for the
validation of **DynaFlow**, i.e. Dynawo used for steady-state power flow
calculations.

These validation studies are done mostly by means of comparing
contingency case results between DynaFlow and Hades 2. But the system
also contemplates comparing DynaFlow vs. DynaFlow cases (for instance
for comparing different versions of DynaFlow, or for comparing
executions configured with different simulation parameters).

***(c) 2021 Grupo AIA***

**marinjl@aia.es**


-------------------------------------------------------------------------------


## Main subdirectories

  * `doc`: documents about the validation procedures, how to perform
    disconnections in Dynawo & Hades, how to match network components
    in the two, etc.
    
  * `notebooks`: Python notebooks to explore the data, graph results,
    and generally help in quantifying comparisons.

  * `pipeline`: scripts to automatically generate test cases, then run
    those cases with Dynawo and Hades, then extract the relevant
    results, and finally compute comparison metrics in a format that
    is amenable for analysis with furter tools (mainly Python
    Notebooks).  The test cases are all derived from a given BASECASE,
    and they are typically N-1 contingency cases of all kinds of
    elements (loads, gens, lines, etc.).

