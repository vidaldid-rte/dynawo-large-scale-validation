
HOWTO Configure events in Dynawo and Astre
==========================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------



IMPORTANT INFO ABOUT MODEL TOPOLOGIES
=====================================

To understand the context, it is important to know that Dynawo allows
buses to be modeled either in a "node-breaker" topology (full topology
with all switches & breakers), or in a "bus-breaker" topology (a
reduced topology in which there are no switches & breakers--at least,
within the voltage level that hosts that reduced bus). Moreover, these
two can be used at the same time in a given case.

Initially RTE provided 3 sample base cases (Lille, Lyon, Marseille) in
which most of the buses (though not all) where NODE-BREAKER.  Then we
were provided newer files (of the same cases) in which the majority
(but not all) of the buses were modeled as BUS-BREAKER.

Here's the analysis of how many buses are present of each kind in the
old vs. the new cases:


|                |              | OLD TOPO CASES |  NEW TOPO CASES |
| -------------- | ------------ | -------------: | --------------: |
| Lille case     |              |                |                 |
|                | Node-breaker |       448      |        42       |
|                | Bus-breaker  |       590      |       750       |
|                | Total        |    **1038**    |     **792**     |
|                | (Astre)      |     (1114)     |     (1114)      |
|                |              |                |                 |
| Lyon case      |              |                |                 |
|                | Node-breaker |       589      |        24       |
|                | Bus-breaker  |      1080      |      1345       |
|                | Total        |    **1669**    |    **1369**     |
|                | (Astre)      |     (2056)     |     (2056)      |
|                |              |                |                 |
| Marseille case |              |                |                 |
|                | Node-breaker |       464      |        29       |
|                | Bus-breaker  |       644      |       834       |
|                | Total        |    **1108**    |     **863**     |
|                | (Astre)      |     (1353)     |     (1353)      |
|                |              |                |                 |



We have to take all this into account whenever we want to configure a
contingency event that should be the same in Dynawo and Astre. For instance:

  * When configuring load disconnections, 


If the bus topology is BUS-BREAKER, chances are that,
compared to the Astre model, some loads have been merged (not
always). If the corresponding loads in Astre are still disaggregated,
the contngency in Astre will have to consist of all loads attached to
the same bus (and the same thing in Dynawo, in case there's more than
one aggregated load at the same bus).




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

**A note about the entreesAstre element and its `atbus` attribute**: The
`evtouvrtopo` element is wrapped in a `entreesAstre`element, having an
`atbus`attribute.  That bus is not related to the event; it is an
indication of the slack bus used in the powerflow calculation
(i.e. the bus with a zero phase angle). As Astre doesn't have a proper
frequency modelling (in contrast to Dynawo), the active power is
adjusted instantaneously and it is necessary to set a certain angle
phase to zero even during the dynamic simulation. For convenience
purposes and for easing the convergence at initialization time,
`atbus` provides Astre with the powerflow slack node.


Configuring Astre output variables (curves)
-------------------------------------------

Here is the enum that links the different variables with their
`typecourbe` attriibute number, which is to be used when configuring
the output curves:

    ```
    enum TypeCourbe {
      // noeuds
      N_TENSION                   = 0,
      N_PHASE                     = 1,
      N_CONSO_ACT                 = 2,
      N_CONSO_REA                 = 3,
      N_DEMANDE_ACT               = 4,
      N_DEMANDE_REA               = 5,
      N_PUISS_ACT_MCS             = 6,
      N_PUISS_REA_MCS             = 7,
      N_REGLEUR_PRISE             = 8,
      N_REGLEUR_TENS_SURV         = 9,
      N_REGLEUR_LIMSUP_BANDEMORTE = 10,
      N_REGLEUR_LIMINF_BANDEMORTE = 11,
      N_SENSIVITY_DQG_DQL         = 62,
      N_V_MAGNITUDE_PU            = 63,
      N_MOST_DECREASED_V          = 64,
      N_REGLEUR_PRISE_TRANSPORT   = 84,
      N_REGLEUR_TENS_SURV_TRANSPORT = 85,
      N_REGLEUR_LIMSUP_BANDEMORTE_TRANSPORT = 86,
      N_REGLEUR_LIMINF_BANDEMORTE_TRANSPORT = 87,
      // quadripoles
      Q_PUISS_ACT_OR              = 12,
      Q_PUISS_ACT_EX              = 13,
      Q_PUISS_REA_OR              = 14,
      Q_PUISS_REA_EX              = 15,
      Q_INTENS_OR                 = 16,
      Q_INTENS_EX                 = 17,
      Q_REGLEUR_PRISE             = 18,
      Q_REGLEUR_TENS_SURV         = 19,
      Q_REGLEUR_LIMSUP_BANDEMORTE = 20,
      Q_REGLEUR_LIMINF_BANDEMORTE = 21,
      Q_TD_DEPHASAGE              = 22,
      Q_IMPEDANCE_OR              = 23,
      Q_IMPEDANCE_EX              = 24,
      Q_TD_POSITION               = 65,
      // groupes
      G_TENSION_STATOR            = 25,
      G_CONSIGNE_TENSION          = 26,
      G_PUISS_ACT                 = 27,
      G_PUISS_REA                 = 28,
      G_RESERVE_PUISS_REA         = 29,
      G_COURANT_ROTOR             = 30,
      G_PUISS_ACT_STAT            = 46,
      G_PUISS_REA_STAT            = 47,
      G_U_STAT_KV                 = 48,
      G_INTERNAL_ANGLE            = 49,
      G_FIELD_CURRENT             = 50,
      G_STATOR_CURRENT            = 51,
      G_SATURATED_EMFV            = 52,
      G_MECHANICAL_POWER          = 53,
      G_Q_MAX                     = 54,

      // csprs
      CSPR_CONSIGNE_TENSION       = 31,
      CSPR_PUISS_REA              = 32,
      CSPR_RESERVE_PUISS_REA      = 33,
      CSPR_SUSCEPTANCE            = 55,
      CSPR_CONTROLLED_V           = 56,
      // groupes rst
      GRST_CONSIGNE_REAC_APR      = 34,
      GRST_SIGNAL_ERREUR_APR      = 35,
      GRST_LIMSUP_BANDEMORTE_APR  = 36,
      GRST_LIMINF_BANDEMORTE_APR  = 37,
      // regroupements
      REGR_CONSO_ACT              = 38,
      REGR_CONSO_REA              = 39,
      REGR_DEMANDE_ACT            = 40,
      REGR_DEMANDE_REA            = 41,
      REGR_PROD_ACT               = 42,
      REGR_PROD_REA               = 43,
      REGR_RESERVE_REA            = 44,
      REGR_RESERVE_ACT            = 57,
      REGR_AVERAGE_VOLTAGE        = 58,
      ZONERST_NIVEAU              = 45,
      ZONERST_TENSION_PILOTE      = 88,
      ZONERST_TENSION_CONSIGNE    = 89,

      // lccs
      LCC_PUISS_ACT_OR            = 66,
      LCC_PUISS_ACT_EX            = 67,
      LCC_PUISS_REA_OR              = 68,
      LCC_PUISS_REA_EX              = 69,
      LCC_COURANT_DC              = 70,
      LCC_TENSION_DC_OR              = 71,
      LCC_TENSION_DC_EX              = 72,
      LCC_ANGLE_ALLUMAGE          = 73,
      LCC_ANGLE_EXTINCTION          = 74,
      LCC_PRISE_REGLEUR_OR          = 75,
      LCC_PRISE_REGLEUR_EX          = 76,

      // vscs
      VSC_PUISS_ACT_OR            = 77,
      VSC_PUISS_ACT_EX            = 78,
      VSC_PUISS_REA_OR              = 79,
      VSC_PUISS_REA_EX              = 80,
      VSC_COURANT_DC              = 81,
      VSC_TENSION_DC_OR              = 82,
      VSC_TENSION_DC_EX              = 83,
      VSC_TENSION_REF_OR              = 90,
      VSC_TENSION_REF_EX              = 91,

      // valeurs globales
      ALL_LOST_LOAD_LINE_TRIP     = 59,
      ALL_TOTAL_LOST_LOAD         = 60,
      ALL_TOTAL_SHED_LOAD         = 61,
      ALL_LOST_GEN_TRIP     = 92
      // max = 92
    };
	```


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
==================================

In Astre:
---------

  * Find the corresponding load in Astre: among elements with tag
    "conso", find nom == ".ANDU7TR751".  Keep its "num" attribute,
    which is the load id.

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the load id using the `ouvrage`
    attribute.  Use `type="3"` for loads, and `typeevt="1"` for
    disconnection (see table above). Example:
  
    ```
      <scenario nom="scenario" duree="1200">
        <evtouvrtopo instant="300" ouvrage="3" type="3" typeevt="1" cote="0"/>
      </scenario>
    ```

  * For the courves output, you have to add `courbe` elements; they
    are children of element `entreesAstre` and siblings to `scenario`.
    The base case file will already have some courves configured (the
    variables that monitor the behavior of the SVC: pilot point
    voltage, K level, and P,Q of participating generators). We would
    then add at least the voltage of the bus on which the load has
    been disconnected (and perhaps all first-neighbor buses as well).
    To do this,get the id of the bus that the load is attached to
    (attribute `noeud`), and add an element as in the example:
	
	```
	  <courbe nom="BUSLABEL_Upu_value" typecourbe="63" ouvrage="2" type="7"/>
	```

    Here typecourbe="0" means buses (noeud).
    The name of the variable is free.  In order to have names that
    match those in Dynawo, it is useful to construct the name as
    `"BUSLABEL" + "_Upu_value"`, where BUSLABEL is the name of the
    corresponding bus in Dynawo. In the example above, bus ".ANDU771".
	

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



In Dynawo:
----------

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

  * In the CRV file, expand the `curvesInput` section with the names
    of any additional variables that makes sense to have in the
    output. The base case file is already prepared with the variables
    that monitor the behavior of the SVC (pilot point voltage, K
    level, and P,Q of participating generators).  We would then add at
    least the voltage of the bus on which the load has been
    disconnected (and perhaps all first-neighbor buses as well).  To
    do so, first find the static load in the IIDM (using the
    `staticID` of the load model in the DYD file). Now you have to
    take into account that the bus topology may be either
    `BUS_BREAKER` or `NODE_BREAKER`, as you'll do things differently
    in each case:
	
	  - `BUS_BREAKER`: recognizable because the static load has an
        attribute "bus", which is the identifyer of the correspondig
        `bus` element in the IIDM (Note: there's no need to search for
        this bus through the whole XML; you can search it from the
        parent element of the load, the `voltageLevel`). Its voltage
        variable is formed by concatenating the bus id and
        `"_Upu_value"`. The specified model has to be
        "NETWORK". Example, for load ".ANDU7TR751":  
		`<curve model="NETWORK" variable=".ANDU771_Upu_value"/>`
			  
	  - `NODE_BREAKER`: recognizable because the static load has an
        attribute "node" instead of "bus". In the node-breaker
        topology there are no `bus` elements; instead, there are
        `busbarSection` elements, which connect with each other and
        loads, gens, etc. through "nodes". Now, it would be a bit
        contrived to resolve the topology in order to find out which
        of the busbarSections a load is effectively connected to. This
        is not worth it, as we just want a voltage point to monitor
        that is "close enough" to the disconnected load.  Instead, we
        will resort to this **simple heuristic**: just take the first
        busbarSection that happens to have a non-null or non-zero
        voltage value (attribute "v"), and we will assume the load was
        connected to that one. Its voltage variable is formed by
        concatenating the busbarSection id and `"_Upu_value"`. The
        specified model has to be "NETWORK". Example, for load
        "AULNO1LMA1":  
		`<curve model="NETWORK" variable="AULNOP1_1C_Upu_value"/>`
		




Detailed steps for tripping shunts:
===================================

In Astre:
---------

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


In Dynawo:
----------

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




**END OF DOCUMENT**
