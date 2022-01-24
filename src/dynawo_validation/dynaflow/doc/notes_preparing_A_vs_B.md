
CHECKLIST: actions performed to prepare a DynaFlow + Hades BASECASE
===================================================================

Assuming we start with two prepared basecases

  1. First of all run the script convert_dflow2dwoAdwoB.sh BASECASE_A BASECASE_B to generate a new directory with the files. 
  
  2. Run both cases before proceeding.
  
  3. Execute the script add_contg_job.py JOB_A.xml "BASECASE directory relative to the site where the contingencies will be created"
     Execute the script add_contg_job.py JOB_B.xml "BASECASE directory relative to the site where the contingencies will be created"
     
  4. Create new dummy contingency files for directory A and directory B named contingency.par and contingency.dyd with text like the following:
     
     <?xml version="1.0" encoding="UTF-8" standalone="no"?>
     <dyn:dynamicModelsArchitecture xmlns:dyn="http://www.rte-france.com/dynawo">
       <dyn:blackBoxModel id="Disconnect my branch" lib="EventQuadripoleDisconnection" parFile="A/contingency.par" parId="99991234"/>
       <dyn:connect id1="Disconnect my branch" var1="event_state1_value" id2="NETWORK" var2="AGNEAL41VLEDI_state_value"/>
     </dyn:dynamicModelsArchitecture>
     
     <?xml version="1.0" encoding="UTF-8" standalone="no"?>
     <parametersSet xmlns="http://www.rte-france.com/dynawo">
       <set id="99991234">
         <par name="event_tEvent" type="DOUBLE" value="100"/>
         <par name="event_disconnectOrigin" type="BOOL" value="true"/>
         <par name="event_disconnectExtremity" type="BOOL" value="true"/>
       </set>
     </parametersSet>
     

