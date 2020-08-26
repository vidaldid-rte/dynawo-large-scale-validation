
HOWTO Configure events in Dynawo and Astre
==========================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------



CONFIGURING EVENTS IN ASTRE
===========================

Astre is much simpler than Dynawo. Here's a summary of the information
we got so far from RTE.

The general way to simulate a disconnection (or any other event) is to add an
"evtouvrtopo" element to the "scenario" element, which appears typically near
the end of the input xml file (donneesModelesEntree.xml).  Example:

```
 <scenario nom="scenario" duree="1200">
       <evtouvrtopo instant="300" ouvrage="54" type="2" typeevt="1" cote="0"/>
 </scenario>
```

The "ouvrage" attribute points to the affected element ID (but beware
that Astre XML files use "nom" instead of "id").  The "type" is the
type of equipment that is being disconnected. Here is a summary of the
syntax:

```
<scenario nom="scenario" duree="{SimulationLengthInSeconds}">
   <evtouvrtopo instant="{DisconnectionTimeInSeconds}"
                ouvrage="{'num' attribute of the network component to be disconnected}"
                type="{2 if generator (declared as groupe element in the xml)
                       3 if load (declared as conso element in the xml)
                       4 if shunt (declared as shunt element in the xml)
                       5 if switch/breaker (declared as couplage in the xml)???
                       9 if line (declared as quadripole element in the xml)}"
                typeevt="{1 for disconnection}"
                cote="{0 if generator, load, or shunt, or to disconnect a line on both sides
                       1 to disconnect a line's origin
                       2 to disconnect a line's end}"
                />
</scenario>
```

**A note about the entreesAstre element and its atbus attribute**: The
`evtouvrtopo` element is wrapped in a `entreesAstre`element, having an
`atbus`attribute.  That bus is not related to the event; it is an
indication of the slack bus used in the powerflow calculation
(i.e. the bus with a zero phase angle). As Astre doesn't have a proper
frequency modelling (in contrast to Dynawo), the active power is
adjusted instantaneously and it is necessary to set a certain angle
phase to zero even during the dynamic simulation. For convenience
purposes and for easing the convergence at initialization time,
`atbus` provides Astre with the powerflow slack node.



Available example cases:
------------------------

  * 2020-07-08/donneesEntreeIEEE14.xml  (disconnection of group "GEN2")

  * 2020-07-09/donneesModelesEntreeLille20190410_1200.xml (disconnection of
    group "GRAV57GRAV5T6")

  * 2020-07-09/PtFige-Lyon.zip (disconnection of busbar "ALBERP7_1B")

  * 2020-07-09/PtFige-Marseille.zip (a topology change, disconnecting line
    "TAVELL74TRI.P" and its associated breakers)

  * 2020-07-10/donneesEntree_ExampleLineDisconnection.xml (disconnection of line
    ".CAM5L61.CAMP" at its origin side)
  

-------------------------------------------------------------------------------




CONFIGURING EVENTS IN DYNAWO
============================

Configuring events in Dynawo is more complex than in Astre, because
there are more files involved. Moreover, the current documentation
does not contain neither a practical tutorial nor a detailed
specification on how to perform events on network equipment.

For now, it is best to start from some already-configured example and
use it as a "base-case" from which to configure other similar events
and disconnections.

But the key idea to understand first is that Dynawo's actions are also
implemented via models. For instance, to disconnect a given piece of
equipment in the network, one instantiates _a model that represents a
disconnection_; and then wires up that model with the equipment that
is to be affected.

In general, for _disconnections_, RTE uses mainly the following three
models:

   * `EventSetPointBoolean`: disconnects devices that are given a
     modelica dynamic model in the DYD file (loads, generators, etc.)
   
   * `EventConnectedStatus`: disconnects devices that are given a default cpp
     model (and are therefore part of the NETWORK model), such as shunts. There
     is one exception: lines (see next model).

   * `EventQuadripoleDisconnection`: lines are also given a default
     cpp model, but require EventQuadripoleDisconnection in order to
     specify which side(s) will be disconnected.

_[Note: there's many other event models under the `ddb`
directory. Here's the list of all currently available:]_

```
EventConnectedStatus.desc.xml
EventQuadripoleConnection.desc.xml
EventQuadripoleDisconnection.desc.xml
EventSetPointBoolean.desc.xml
EventSetPointDoubleReal.desc.xml
EventSetPointGenerator.desc.xml
EventSetPointLoad.desc.xml
EventSetPointReal.desc.xml
```

Every component that has a dynamic Modelica representation in the DYD
should be disconnected via that dynamic model, not the static one in
the IIDM.  For example, loads may be represented both in the IIDM and
in the DYD file, but trying to disconnect them using their IIDM model
(as you would do with shunts) will not work.

Typically only shunts and lines are given default cpp models and
therefore have to be disconnected by means of `EventConnectedStatus`
or `EventQuadripoleDisconnection` acting on the identifyers found in
the IIDM file.

To get started, it is instructive to inspect a given example case in
which a disconnection has already been configured. Proceed as follows:

  * Look first in the DYD file. Search for any of the three event
    models shown above being instantiated as a `<blackBoxModel>`
    element. Take their id's and you will find the way they are wired
    up via `<connect>` elements. This will give you the blackBoxModel
    id of the network device that is being affected.
	
  * The `<blackBoxModel>` of the disconnecting action also contains
    the parFile and parId.  With those you can look in the PAR file
    and see how the disconnection is configured (i.e. things such as
    the time of the event, which side of a line is opened, etc.)


For example, a load disconnection would read like:

```
  DYD FILE:
  <blackBoxModel id="LoadDisconnection" lib="EventSetPointBoolean" parFile="tFin/fic_PAR.xml" parId="99999"/>
  <connect id1="LoadDisconnection" var1="event_state1_value" id2="DM_SOISS3Y311" var2="load_switchOffSignal2_value"/>

  PAR FILE:
  <set id="99999">
      <par type="DOUBLE" name="event_tEvent" value="4200"/>
      <par type="BOOL" name="event_stateEvent1" value="true"/>
  </set>
```

Whereas a shunt disconnection would read like:

```
  DYD FILE:
  <blackBoxModel id="Disconnect_BIANC1REAC.1_TFin" lib="EventConnectedStatus" parFile="fic_PAR.xml" parId="982"/>
  <connect id1="Disconnect_BIANC1REAC.1_TFin" var1="event_state1_value" id2="NETWORK" var2="BIANC1REAC.1_state_value"/>

  PAR FILE:
  <set id="982">
      <par type="DOUBLE" name="event_tEvent" value="1250"/>
      <par type="BOOL" name="event_open" value="true"/>
  </set>
```

The `<connect>` line also shows which variables are used to connect
the event model with the equipment model. For dynamic models, you will
typically connect the event to the corresponding
`*_switchOffSignal2_value` boolean variable of the component.  The
different `switchOffSignal` variables correspond to the different ways
in which a component can be disconnected:

  1. as a consequence of the disconnection of the node it is connected
     to (`switchOffSignal1`),

  2. following a signal sent by the user (`switchOffSignal2`, that is
     thus used to perform an event),

  3. or acting under an order given by an automaton (`switchOffSignal3`
     for generators equipped with an under-voltage protection, for
     example).

That's why you can see in the DYD that every `load_switchOffSignal1`
is linked to its corresponding static `_switchOff` variable. You can
find quick descriptions of the switchOff variables' meaning of every
device in the modelica switchOff model itself:
`Dynawo.Electrical.Controls.Basics.SwitchOffLoad`.

To get the exact names of the variables that should be used, always
check the corresponding "desc" file under the ddb directory.




Detailed steps for tripping loads:
----------------------------------

### In Dynawo:

  * Find the id of the load in the DYD file: among elements with tag
    "BlackBoxModel" and attribute "lib" == "Load*", find the desired
    load name using the attribute `staticId`.  Then keep the id, which
    is usually the same but prefixed with "DM_" (and starting "."
    converted to "_") Example:	
	```
	<blackBoxModel id="DM__ANDU7TR751" lib="LoadPQ" parFile="tFin/fic_PAR.xml" parId="1000" staticId=".ANDU7TR751">
	```

  * In the DYD file, declare a model `EventSetPointBoolean` with the
    corrresponding section in the PAR file:
    ```
      <blackBoxModel id="Disconnect my load" lib="EventSetPointBoolean" parFile="fic_PAR.xml" parId="99991234"/>
    ```

  * And (also in the DYD file) connect this with the corresponding id
    of the load model in the same DYD file.  Look in the ddb desc file
    of the Event model for the variable you need to connect as var1.
    Look in the ddb desc file of the Load* model for the variable you
    need to connect as var2.
	```
      <connect id1="Disconnect my load" var1="event_state1_value" id2="DM__ANDU7TR751" var2="load_switchOffSignal2_value"/>
    ```

  * In the PAR file, add a section with the parameters for the
    disconnection (the time and the action itself).  You can look in
    the ddb desc file of the `EventSetPointBoolean` model if you want
    to check the exact names of these parameters:
	
	```
      <set id="99991234">
        <par type="DOUBLE" name="event_tEvent" value="4300"/>
        <par type="BOOL" name="event_stateEvent1" value="true"/>
      </set>
    ```


### In Astre:

  * Find the corresponding load in Astre: among elements with tag
    "conso", find nom == ".ANDU7TR751".  Keep its "num" attribute,
    which is the load id.

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the load id using the `ouvrage`
    attribute.  Example:
  
    ```
      <scenario nom="scenario" duree="1200">
        <evtouvrtopo instant="300" ouvrage="3" type="3" typeevt="1" cote="0"/>
      </scenario>
    ```

Reminder of event types:

    ```
                type="{2 if generator (declared as groupe element in the xml)
                       3 if load (declared as conso element in the xml)
                       4 if shunt (declared as shunt element in the xml)
                       5 if switch/breaker (declared as couplage in the xml)???
                       9 if line (declared as quadripole element in the xml)}"
    ```

And typeevt is always 1 for disconnection.


**A note about load models in Astre:** the different static loads
("conso") on one node are aggregated on one only dynamic object
("dynanoeud"), for which the behavior is defined by both the load and
node elements. Indeed, for example, the dynamic behavior is defined by
the "type" element in dynanoeud (0 being a load behind one
transformer, 1 being a load between two normal transformers, 2 being a
load behind one ideal and one normal transformer, 3 being an
alpha-beta load, and 4 being a PQ load). The only information taken
from the static load element is the p and q reference/set
point/initial values.  Nevertheless, the disconnection event should be
built using the evtouvrtopo="3" syntax, acting on the corresponding
"conso" element. At the time of the event, Astre will modify the p
and q reference values accordingly (pref_new = pref_old -
p_disconnected).








Steps for tripping shunts:
--------------------------

### In Dynawo:

  * Find the id of load in IIDM: among elements with tag "shunt", find
    the desired id (e.g. "TODO")

  * In the DYD file, declare a model `EventConnectedStatus` with the
    corrresponding section in the PAR file:
	
    ```
      <blackBoxModel id="Disconnect my shunt" lib="EventConnectedStatus" parFile="fic_PAR.xml" parId="99991234"/>
    ```

  * And (also in the DYD file) connect this with the corresponding id
    in NETWORK (which you'll have to look for in the IIDM file).  Look
    in the ddb desc file of the Event model for the variable you need
    to connect as var1.  As for var2, for NETWORK models the var2 is
    always composed by appending "_state_value".
	
    ```
      <connect id1="Disconnect my shunt" var1="event_state1_value" id2="NETWORK" var2="TODO_state_value"/>
    ```

  * In the PAR file, add a section with the parameters for the
    disconnection (the time and the action itself).  You can look in
    the ddb desc file of the `EventConnectedStatus` model if you want
    to check the exact names of these parameters:
	
    ```
      <set id="99991234">
        <par type="DOUBLE" name="event_tEvent" value="4300"/>
        <par type="BOOL" name="event_open" value="true"/>
      </set>
    ```


### In Astre:

  * Find the corresponding shunt in Astre: among elements with tag
    "shunt", find nom == "TODO".  Keep its "num" attribute, which is
    the shunt id.

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the load id using the `ouvrage`
    attribute.  Example:
  
    ```
      <scenario nom="scenario" duree="1200">
        <evtouvrtopo instant="300" ouvrage="TODO" type="4" typeevt="1" cote="0"/>
      </scenario>
    ```

Reminder of event types:

    ```
                type="{2 if generator (declared as groupe element in the xml)
                       3 if load (declared as conso element in the xml)
                       4 if shunt (declared as shunt element in the xml)
                       5 if switch/breaker (declared as couplage in the xml)???
                       9 if line (declared as quadripole element in the xml)}"
    ```

And typeevt is always 1 for disconnection.



**END OF DOCUMENT**
