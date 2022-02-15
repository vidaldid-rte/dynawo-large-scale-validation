
# Instructions for running the pipeline

## Install the package

  0. Follow the dynawo-validation-AIA/src/dynawo_validation/doc/README_INSTALLATION.md to install the package 

## Prepare the basecase

  1. Start from a case where both Dynawo & Hades run OK
  
  2. Initial directory structure:

        2.1 Put all all DynaFlow files under a directory `<casename>.BASECASE/`, with job filename pattern: *JOB*.xml
        
        2.2 Create a subdir Hades and put `donneesEntreeHADES2.xml` in it. There's nothing else to do with the Hades file.
  
  3. For good measure, start by formatting all XML files with xmllint. Use the provided script `xml_format_dir.sh`. It's good practice to keep a backup copy the formatted case at this point, so that all the edits that come below can be viewed cleanly when using diff.

  4. JOB file: create a symlink called `JOB.xml`, and:
  
       * edit the simulation stopTime (double it, for the disconnection)
       
       * enable the constraints file (`<dyn:constraints exportMode="XML"/>`)
       
       * enable the timeline file (`<dyn:timeline exportMode="XML"/>`)

       * enable the curves file (`<dyn:curves inputFile="recollement_summer.crv" exportMode="CSV"/>`)
       
       * enable the PF output (`<dyn:finalState exportIIDMFile="true" exportDumpFile="false"/>`)
       
       * set the desired log level ("DEBUG" is too verbose for a full contingency run)
  
  5. Introduce a dummy disconnection in DynaFlow, which will become the reference for the disconnection time (typically, set the disconnection event at t=100 and the stopTime at t=200). To do  this, we must first modify the JOB file with the script included in the package (add_contg_job.py). This script will add a new  dyd file so you don't have to copy the entire old dyd. Also, it  will change various paths to run optimizations and save memory on execution. Next, we need to create two new files. One called  contingency.par and the other contingency.dyd. In them, we need  to copy the following code and place them at the same level as the dyd and par files that already contains our base case.

       * in the dyd file, introduce a disconnection model (for an
         element that's already disconnected, so that it doesn't have
         any effect). Example:
         ```
            <?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <dyn:dynamicModelsArchitecture xmlns:dyn="http://www.rte-france.com/dynawo">
              <dyn:blackBoxModel id="Disconnect my branch" lib="EventQuadripoleDisconnection" parFile="contingency.par" parId="99991234"/>
              <dyn:connect id1="Disconnect my branch" var1="event_state1_value" id2="NETWORK" var2="AGNEAL41VLEDI_state_value"/>
            </dyn:dynamicModelsArchitecture>
         ```

        * in the par file, introduce the corresponding parameters:
          ```
             <?xml version="1.0" encoding="UTF-8" standalone="no"?>
             <parametersSet xmlns="http://www.rte-france.com/dynawo">
               <set id="99991234">
                 <par name="event_tEvent" type="DOUBLE" value="100"/>
                 <par name="event_disconnectOrigin" type="BOOL" value="true"/>
                 <par name="event_disconnectExtremity" type="BOOL" value="true"/>
               </set>
             </parametersSet>
           ```
  6. Create a curves file, which is useful for inspecting the
     time-domain response. You don't need to actually configure any
     curves, but you'll need at least an empty file because the
     scripts that generate the contingency cases will *add* curves to
     it. Example:
       ```
       <?xml version='1.0' encoding='UTF-8'?>
       <curvesInput xmlns="http://www.rte-france.com/dynawo">
         <!-- === Pilot bus and gens associated to S.V.C. zone: RST_BARNAP7 === -->
         <curve model="NETWORK" variable="BARNAP71_Upu_value"/>
         <curve model="PALUE7PALUET2" variable="generator_PGenPu"/>
         <curve model="PALUE7PALUET2" variable="generator_QGenPu"/>
         <curve model="PALUE7PALUET4" variable="generator_PGenPu"/>
         <curve model="PALUE7PALUET4" variable="generator_QGenPu"/>
         <!-- === below, the contingency-specific curves === -->
       </curvesInput>
       ```
  7. Example of final directories:
  
	20210422_0930a.BASECASE/
	├── contingency.dyd
	├── contingency.par
	├── Hades
	│   └── donneesEntreeHADES2.xml
	├── JOB.xml
	├── Network.par
	├── recollement_20210422_0930.crv
	├── recollement_20210422_0930_Diagram/
	├── recollement_20210422_0930.dyd
	├── recollement_20210422_0930.par
	├── recollement_20210422_0930.iidm
	└── solver.par

   8. *(This step is only for dynaflow-dynaflow)* Run the script convert_dflow2dwoAdwoB.sh BASECASE_A BASECASE_B to generate a new directory with the files. 
   
	20210422_0930a.BASECASE.DWODWO/
	├── A
	│   ├── contingency.dyd
	│   ├── contingency.par
	│   ├── Network.par
	│   ├── recollement_20210422_0930.crv
	│   ├── recollement_20210422_0930_Diagram
	│   ├── recollement_20210422_0930.dyd
	│   ├── recollement_20210422_0930.par
	│   ├── recollement_20210422_0930.xiidm
	│   └── solver.par
	├── B
	│   ├── contingency.dyd
	│   ├── contingency.par
	│   ├── Network.par
	│   ├── recollement_20210422_0930.crv
	│   ├── recollement_20210422_0930_Diagram
	│   ├── recollement_20210422_0930.dyd
	│   ├── recollement_20210422_0930.par
	│   ├── recollement_20210422_0930.xiidm
	│   └── solver.par
	├── JOB_A.xml
	└── JOB_B.xml

   9. Run Hades and Dynawo or Dynawo and Dynawo before proceeding.
   
## Run the pipeline

   10. Now everything should be ready to run the pipeline with the virtual environment activated through the command line with the command dynaflow_run_validation. This provides us with several options mentioned below: 

	usage: dynaflow_run_validation [-h] [-A LAUNCHERA] [-B LAUNCHERB] [-a] [-s] [-d] [-c] [-l REGEXLIST] [-w WEIGHTS] [-r] [-p RANDOMSEED] base_case results_dir

	positional arguments:
	  base_case
	  results_dir

	optional arguments:
	  -h, --help            show this help message and exit
	  -A LAUNCHERA, --launcherA LAUNCHERA
		                Defines the launcher of simulator A
	  -B LAUNCHERB, --launcherB LAUNCHERB
		                Defines the launcher of simulator B
	  -a, --allcontg        Run all the contingencies
	  -s, --sequential      Run jobs sequentially (defult is parallel)
	  -d, --debug           More debug messages
	  -c, --cleanup         Delete input cases after getting the results
	  -l REGEXLIST, --regexlist REGEXLIST
		                enter regular expressions or contingencies in text (.txt) form, by default, all possible contingencies will be generated (if below MAX_NCASES; otherwise a random sample is generated)
	  -w WEIGHTS, --weights WEIGHTS
		                enter personalized weights to calcule score following the template
	  -r, --random          Run a different random sample of contingencies
	  -p RANDOMSEED, --randomseed RANDOMSEED
		                Run a different random sample of contingencies with a seed

   11. We also have the option with the command line to use other commands such as: 

        * add_contg_job.py 
        * top_10_diffs_dflow.py
        * dynaflow_run_validation
        * convert_dflow2dwoAdwoB.sh
        * xml_format_dir.sh
        * dynawo_validation_find_path
        * create_graph.py
        * dynawo_validation_extract_bus

## Analyze the results 

   12. In the results directory that we have provided when executing, we will find all the comparative files to analyze the simulators and their differences. Also, in the notebook folder, a Jupyter Notebook will be created with all the results accessible, interactive and organized. 


	


