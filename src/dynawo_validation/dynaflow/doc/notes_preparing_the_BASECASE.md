
CHECKLIST: actions performed to prepare a DynaFlow + Hades BASECASE
===================================================================

Assuming we start with a "raw" DynaFlow + Hades basecase, as provided
by RTE:

  1. For good measure, start by formatting all XML files with
     xmllint. Use the provided script `xml_format_dir.sh`. It's good
     practice to keep a backup copy the formatted case at this point,
     so that all the edits that come below can be viewed cleanly when
     using diff.

  2. Put all all DynaFlow files under a directory `<casename>.BASECASE/`

  3. Create a subdir Hades and put `donneesEntreeHADES2.xml` in
     it. There's nothing else to do with the Hades file.

  4. JOB file: create a symlink called `JOB.xml`, and:
  
       * edit the simulation stopTime (double it, for the disconnection)
       
       * enable the constraints file (`<dyn:constraints exportMode="XML"/>`)
       
       * enable the timeline file (`<dyn:timeline exportMode="XML"/>`)

       * enable the curves file (`<dyn:curves inputFile="recollement_summer.crv" exportMode="CSV"/>`)
       
       * enable the PF output (`<dyn:finalState exportIIDMFile="true" exportDumpFile="false"/>`)
       
       * set the desired log level ("DEBUG" is too verbose for a full contingency run)


  5. Introduce a dummy disconnection in DynaFlow, which will become
     the reference for the disconnection time (typically, set the
     disconnection event at t=100 and the stopTime at t=200). To do 
     this, we must first modify the JOB file with the script included 
     in the package (add_contg_job.py). This script will add a new 
     dyd file so you don't have to copy the entire old dyd. Also, it 
     will change various paths to run optimizations and save memory 
     on execution. Next, we need to create two new files. One called 
     contingency.par and the other contingency.dyd. In them, we need 
     to copy the following code and place them at the same level as 
     the dyd and par files that already contains our base case.
     
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

