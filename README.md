
Dynawo validation
=================

A repository of scripts and utilities built during the
projects carried out in 2020--2021 for the purpose of validating
*DynaWaltz* and *DynaFlow*.

***(c) 2020--2021 Grupo AIA***  
**marinjl@aia.es**  
**omsg@aia.es**     
**rte-dynawo@rte-france.com**

-------------------------------------------------------------------------------

## Get involved!

Dyna&omega;o-large-scale-validation is an open-source project and as such, questions, discussions, feedbacks and more generally any form of contribution are very welcome and greatly appreciated!

For further informations about contributing guidelines, please refers to the [contributing documentation](https://github.com/dynawo/.github/blob/master/CONTRIBUTING.md).

## Overview

The methodology for validation is based on running extensive sets of
(single-element) contingency cases, and then compare the results
between Dynawo and another well-established legacy simulator (in our
case, Astre vs. DynaWaltz and Hades vs. DynaFlow).  Additionally, the
validation pipeline allows comparison of Dynawo vs. Dynawo, which can
be used for ongoing validation of future Dynawo versions, or for
analyzing the effects of different simulation parameters, different
model parameterizations, etc.

In essence the system consists of a "processing pipeline" and a
Jupyter Notebook for the analysys of results. The pipeline
orchestrates all Python and shell scripts for the creation of
contingency cases, running them, collecting results, calculating
metrics, etc. The Notebook presents results in the form of tables and
graphs, also computing a few further analyses.


## Repository structure

At a high-level, this repo is structured as follows:

```
src
└── dynawo_validation
    ├── attic
    │   └── launchers
    ├── commons
    │   ├── log_utils
    │   └── xml_utils
    ├── doc
    │   ├── conf_paper
    │   ├── Github installation
    │   └── journal_paper
    ├── dynaflow
    │   ├── doc
    │   ├── notebooks
    │   └── pipeline
    └── dynawaltz
        ├── doc
        ├── notebooks
        └── pipeline
```

[comment]: <> (tree view obtained with: tree -d -L 3 -I '*.egg-info' src)

The repository contains two main parts: DynaWaltz validation and
DynaFlow validation. In addition, it has a set of common utilities
that are used for both parts.



## How to use it

Although it is possible to just clone this repo and start using the
pipeline by running the scripts directly off of their folder (e.g., by
adding the pipeline directory to your PATH), please note that the
software has been packaged as a proper **Python package** that can be
installed via **pip**. This is the recommended way to use it and the
most convenient, in order to have all dependencies automatically
installed.  For more information, please consult the
[README_INSTALLATION.md](src/dynawo_validation/doc/README_INSTALLATION.MD)
under the general doc folder.



## Documentation

At the root of the source, the general [doc](/src/dynawo_validation/doc)
folder contains:
  * the installation instructions for users
  * notes for developers setting up their environment
  * publications related to the project

Then there are two additional folders with information specific to each sub-project:
  * DynaWaltz pipeline [dynawaltz/doc](src/dynawo_validation/dynawaltz/doc)
  * DynaFlow pipeline [dynaflow/doc](src/dynawo_validation/dynaflow/doc)

