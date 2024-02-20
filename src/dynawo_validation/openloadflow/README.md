OpenLoadFlow validation
=======================

Scripts anr utilities to compare OpenLoadFlow with Hades2.

# Usage

## Prerequisite
You need 
   * a binary of hades2 
   * a binary of itools using openloadflow as loadflow solver. For more information to build or configure itools to use oenlaodflow see [package-itools](./package-itools)
## Intalling the environment
   * checkout this project
   * run build_and_install.sh (compiles the code and installs it in a virtual python environment)
   * activate the environment with this command 'source dwo_env/bin/activate'

## Preparing the data
   * Create a directory (for example inputFiles)
   * In this directory add the same network situation n two different formats
      * A file with ADN format named 'entreeHades.xml'
      * A file with XIIDM format namde 'entreeHades.xml'
      * A parameter file for OpenLoadFlow named 'OLFParams.json' ([example](./samples/OLFParams.json))

## Running the simulation
 
   * Run the simulation with this command 
     * olf_run_validation -H ~/tools/hades/hades2-V6.9.0.2/hades2.sh -O ~/tools/powsybl-distribution-2024.0.0-SNAPSHOT/bin/itools -c inputDir resultDir
   * See the result ith this command 
     * jupyter-notebook  
       * Notebooks available (basecase and for load, gen, branch and shunt contingencies)
         * myResult/basecase/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
         * myResult/shunt/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
         * myResult/load/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
         * myResult/gen/notebooks/Hades_vs_OpenLoadFlow_final.ipynb
         * myResult/branchB/notebooks/Hades_vs_OpenLoadFlow_final.ipynb

