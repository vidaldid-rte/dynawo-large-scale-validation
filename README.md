
Dynawo validation
=================

A repository of scripts and utilities used for the RTE-AIA project. It can be used in package form or each of the scripts individually.
*"Validation of dynamic simulations made using open source tool"*.

***(c) 2020 Grupo AIA***

**marinjl@aia.es**


-------------------------------------------------------------------------------


## Intro

This repository contains two main parts. Dynawaltz validation and Dynaflow validation. In addition, it has a set of common utilities that serve for both parts.

## How to use it

Before following this process, it is important to read the document located in commons called README_INSTALLATION.md
There are two ways to use it. The first is to add the root directory to the system's PATH and use the scripts individually. You can find the directory by running the script located in commons: dynawo_validation_find_path.

The second way is by installing the package. This package can be downloaded from the PyPi website or created manually from the repository. To do this, we just have to go to the root directory and execute the command: python3 -m build.

A folder called "dist" will be created and inside there will be a .tar.gz file that we can install with: pip install dist/file_name.tar.gz.

It can also be done through the build_and_install.sh script, which by simply executing it will install the package and do all the necessary actions to use the package. 

Once installed, several instructions for the command line will have been added to our system:
- add_contg_job.py
- convert_dflow2dwoAdwoB_all.sh
- convert_dwaltz2dwoAdwoB.sh
- create_graph.py
- dynaflow_run_validation
- dynawaltz_run_validation
- dynawo_validation_extract_bus
- dynawo_validation_find_path
- prepare_pipeline_basecase.py
- top_10_diffs_dflow.py
- top_10_diffs_dwaltz.py
- xml_format_dir.sh
