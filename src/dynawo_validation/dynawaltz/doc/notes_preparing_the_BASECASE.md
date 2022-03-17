
CHECKLIST: actions performed to prepare a DynaFlow + Astre BASECASE
===================================================================

Assuming we start with a "raw" DynaWaltz + Astre basecase, as provided
by RTE:

  1. For good measure, start by formatting all XML files with
     xmllint. Use the provided script `xml_format_dir.sh`. It's good
     practice to keep a backup copy the formatted case at this point,
     so that all the edits that come below can be viewed cleanly when
     using diff.

  2. Put all all DynaWaltz files under a directory
     `<casename>.BASECASE/`. It is assumed that they are already
     structured in two stages, with subdirectories `t0` and `tfin` as
     usual. The JOB file should be at the top level inside the
     directory.

  3. Create a subdir Astre and put `donneesModelesEntree.xml` in
     it. There's nothing else to do with the Astre file.

  4. Introduce a disconnection event in both DynaWaltz and Astre. It
     doesn't matter much what disconnection it is, since the results
     of running the BASECASE will not be used.  But the scripts will
     *edit* this disconnection when constructing the contingency
     cases, so it needs to be present. Also, the event time will
     become the reference for the disconnection time (typically we set
     the disconnection event at t=300 to t=600, and the stopTime at
     t=1200 to t=2000).
          
       * in the DYD file, introduce a disconnection model. Example:
         ```
         <blackBoxModel id="Disconnect_AVELIL71GAVRE_TFin" lib="EventQuadripoleDisconnection" parFile="tFin/fic_PAR.xml" parId="99991234"/>
         <connect id1="Disconnect_AVELIL71GAVRE_TFin" var1="event_state1_value" id2="NETWORK" var2="AVELIL71GAVRE_state_value"/>

         ```

        * in the PAR file, introduce the corresponding parameters. Example:
          ```
          <set id="99991234">
            <par type="DOUBLE" name="event_tEvent" value="1800"/>
            <par type="BOOL" name="event_disconnectOrigin" value="true"/>
            <par type="BOOL" name="event_disconnectExtremity" value="true"/>
          </set>
           ```
           
        * in the Astre file, introduce the analogous event. Example:
          ```
          <scenario nom="scenario" duree="2000">
            <evtouvrtopo instant="600" ouvrage="1563" type="9" typeevt="1" cote="0"/>
          </scenario>
           ```

  5. Create or complete the curves file, for both Astre and DynaWaltz
     Use the helper script `prepare_pipeline_basecase.py`, which creates a
     set of standardized, RTE-specific curves.

  6. Now **run** the Dynawo case, because we need to keep the `t0`
     output (it will be re-used for all contingency runs). Erase the
     `tFin` output.

  7. Prepare the JOB file:
  
       * comment out the `t0` job altogether. 
       
       * in the `tFin` job, edit the path to the `t0` results, so that
         all contingency cases will pick up these results when running
         them. Example:
         ```
         <       <initialState file="t0/outputs/finalState/outputState.dmp"/>
         ---
         >       <initialState file="../20210211-0930.BASECASE/t0/outputs/finalState/outputState.dmp"/>
         ```

        * disable the final IIDM dump (finalState), to save space
        
        * set the desired log level ("DEBUG" is too verbose for a full contingency run)


ABOUT FUTURE CHANGES IN DYNAWO: the scripts that generate the contingency cases
from the BASECASE (i.e. `create_gen_contg.py`, etc.) only copy those files that
we know about *today*: `job_file, solver_parFile, network_parFile, iidmFile,
dydFile, parFile, curves_inputFile`.  If, in the future, there appear **new**
files that should also be copied, this would have to be modified in
`dwo_jobinfo.py` and `common_funcs.py`.  _However_, for files that are
referenced in the JOB file, there's a trick to avoid having to update the code:
just reference the new file to the one in the BASECASE, just as in the case of
the final state in `"t0/outputs"`.

