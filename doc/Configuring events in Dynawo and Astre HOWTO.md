
HOWTO Configure events in Dynawo and Astre
==========================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------



IMPORTANT INFO ABOUT MODEL TOPOLOGIES
=====================================

To understand the context, it is important to know that Dynawo allows
buses to be modeled either with a "node-breaker" topology (full
topology with all switches & breakers), or a "bus-breaker" topology (a
reduced topology in which there are no switches & breakers--at least,
within the voltage level that hosts that reduced bus). Moreover, these
two can be used at the same time in a given case.

Initially RTE provided 3 sample base cases (Lille, Lyon, Marseille) in
which most of the buses (though not all) where NODE-BREAKER.  Then we
were provided newer files (of the same cases) in which the majority
(but not all) of the buses were modeled as BUS-BREAKER. This has to be
taken into account when configuring a contingency event that should be
the same in Dynawo and Astre.

Additionally, the new set of files not only has node-breaker busbars
fused into single bus-breaker buses; it also has many **loads** that
have been merged.


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
                type="{2 if generator (tag 'groupe' in the xml)
                       3 if load (tag 'conso' in the xml)
                       4 if shunt (tag 'shunt' in the xml)
                       5 if switch/breaker (tag 'couplage' in the xml???)
					   7 if bus (tag 'noeud' in the xml)
                       9 if line (tag 'quadripole' in the xml)
				      11 if K-level of RST control (tag 'zonerst' in the xml)}"
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


Configuring Astre output variables ("courbes")
----------------------------------------------

The variables are selected to appear in the output by configuring
`courbe` elements in the input XML file. These are children of element
`entreesAstre` and siblings to `scenario`.

We have already configured (by hand) the base case file with some
curves; these correspond to the variables that monitor the behavior of
the area SVC: pilot point voltage, K level, and P,Q of participating
generators. One would then add at least the voltage of the bus on
which the element (load, shunt, gen, whatever) has been disconnected;
and perhaps all first-neighbor buses as well.

To do this, get the id of the bus that the element was attached to
(attribute `noeud`), and add an XML element as in the example:
	
	```
	  <courbe nom="BUSLABEL_Upu_value" typecourbe="63" ouvrage="2" type="7"/>
	```

The name of the variable is free.  In order to have names that match
those in Dynawo, it is useful to construct the name as `"BUSLABEL" +
"_Upu_value"`, where BUSLABEL is the name of the corresponding bus in
Dynawo. In the example above, bus ".ANDU771" (Lille case).

Here typecourbe="63" means bus (noeud) voltage in per-unit, while
ouvrage="2" refers to the id (attribute "num") of the bus. Here is the
enum that links the different variables with their `typecourbe`
attriibute number, which is to be used when configuring the output
curves:

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
      LCC_PUISS_REA_OR            = 68,
      LCC_PUISS_REA_EX            = 69,
      LCC_COURANT_DC              = 70,
      LCC_TENSION_DC_OR           = 71,
      LCC_TENSION_DC_EX           = 72,
      LCC_ANGLE_ALLUMAGE          = 73,
      LCC_ANGLE_EXTINCTION        = 74,
      LCC_PRISE_REGLEUR_OR        = 75,
      LCC_PRISE_REGLEUR_EX        = 76,

      // vscs
      VSC_PUISS_ACT_OR            = 77,
      VSC_PUISS_ACT_EX            = 78,
      VSC_PUISS_REA_OR            = 79,
      VSC_PUISS_REA_EX            = 80,
      VSC_COURANT_DC              = 81,
      VSC_TENSION_DC_OR           = 82,
      VSC_TENSION_DC_EX           = 83,
      VSC_TENSION_REF_OR          = 90,
      VSC_TENSION_REF_EX          = 91,

      // valeurs globales
      ALL_LOST_LOAD_LINE_TRIP     = 59,
      ALL_TOTAL_LOST_LOAD         = 60,
      ALL_TOTAL_SHED_LOAD         = 61,
      ALL_LOST_GEN_TRIP           = 92
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




Configuring Dynawo output variables ("curves")
----------------------------------------------

The variables are selected to appear in the output by configuring
`curve` elements in the CRV file.

We have already configured (by hand) the base case file with some
curves; these correspond to the variables that monitor the behavior of
the area SVC: pilot point voltage, K level, and P,Q of participating
generators. One would then add at least the voltage of the bus at
which the element (load, shunt, gen, whatever) has been disconnected;
and perhaps all first-neighbor buses as well.

To do this, first find the element in the IIDM. Then, to find the bus
it is attached to, you first have to take into account that the
substation topology (actually, the "voltageLevel" topology) may be
either `BUS_BREAKER` or `NODE_BREAKER`, since you'll do things
differently in each case. You will find out the topology type by
finding the element's parent (voltageLevel) and reading its
`topologyKind` attribute.  This is how to proceed in each case:

  - `BUS_BREAKER`: in this case there might be more than one bus in
     the busBreakerTopology. Precisely because of this, the element
     (load, gen, etc.) will contain an attribute "bus", which is the
     identifyer of the correspondig `bus` element. Its voltage
     variable is formed by concatenating the bus id and
     `"_Upu_value"`. The specified model has to be "NETWORK". Example,
     for load ".ANDU7TR751":  
	   `<curve model="NETWORK" variable=".ANDU771_Upu_value"/>`
			  
  - `NODE_BREAKER`: in this case the nodeBreakerTopology contains
    switches and busbarSections. Switches and busBarSections define
    electrical "nodes", where each switch connects two nodes and each
    busbarSection is one end-node.  The element in question (load,
    gen, etc.) will have an attribute "node" instead of "bus".  Now,
    it would be a bit contrived to resolve the topology in order to
    find out which of the busbarSections the element is effectively
    connected to. This is not worth it, as we just want a monitor
    voltage point that is "close enough" to the disconnected element.
    Instead, we will resort to this **simple heuristic**: we will just
    take the first busbarSection that happens to have a non-null or
    non-zero voltage value (attribute "v"), and we will assume that
    the tripped element was connected to that one. Its voltage
    variable is formed by concatenating the busbarSection id and
    `"_Upu_value"`. The specified model has to be "NETWORK". Example,
     for load "AULNO1LMA1":  
		`<curve model="NETWORK" variable="AULNOP1_1C_Upu_value"/>`





Detailed steps for tripping loads:
==================================

Tripping loads in Astre:
------------------------

A step by step example using load ".ANDU7TR751" (Lille case):

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

  * Finally, add suitable output variables ("courbes") as described in
    the Section above, _"Configuring Astre output variables"_.


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



Tripping loads in Dynawo:
-------------------------

  * Find the id of the load in the DYD file: among elements with tag
    "BlackBoxModel" and attribute "lib" == "Load*", find the desired
    load name using the attribute `staticId`.  Then keep the id, which
    is usually the same but prefixed with "DM_" (and dots "."
    converted to undersocres "_").  In this example we will use loas
    ".ANDU7TR751".

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

  * Finally, add suitable output variables ("curves") as described in
    the Section above, _"Configuring Dynawo output variables"_.





Detailed steps for tripping shunts:
===================================

Tripping shunts in Astre:
-------------------------

A step by step example using shunt ".AUBA6REAC.1" (Lille case):

  * Find the shunt in Astre: among elements with tag "shunt", find nom
    == ".AUBA6REAC.1".  Keep its "num" attribute, which is the shunt
    id (in this case, 34).

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the shunt id using the `ouvrage`
    attribute.  Use `type="4"` for shunts, and `typeevt="1"` for
    disconnection (see table above). Example:
  
    ```
      <scenario nom="scenario" duree="1200">
		<evtouvrtopo instant="300" ouvrage="34" type="4" typeevt="1" cote="0"/>
      </scenario>
    ```

  * Finally, add suitable output variables ("courbes") as described in
    the Section above, _"Configuring Astre output variables"_.



Tripping shunts in Dynawo:
--------------------------

In contrast with loads, shunts do not have their own dynamic model in
the DYD file.  To disconnect them, we have to do it through their
static description, using an `EventConnectedStatus` instead of an
`EventSetPointBoolean` (see the Introduction above, about the three
differnent types of disconnections).
  
A step by step example, using shunt ".AUBA6REAC.1" (Lille case):
  
  * Find the shunt in the IIDM file by seaching the "shunt" elements;
    the id attribute is the shunt name. Note that if the "bus"
    attribute does not exist, the shunt is not connected (q=0).

  * Edit the DYD file to add an `EventConnectedStatus` model as follows:
    ```
	  <blackBoxModel id="Disconnect my shunt" lib="EventConnectedStatus" parFile="tFin/fic_PAR.xml" parId="99991234"/>

	```

  * And (also in the DYD file) connect this model with the static id2
    `NETWORK` and a var2 that refers to the shunt id in the IIDM file,
    plus the sufffix `_state_value`:

    ```
      <connect id1="Disconnect my shunt" var1="event_state1_value" id2="NETWORK" var2=".AUBA6REAC.1_state_value"/>

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
  * Finally, add suitable output variables ("curves") as described in
    the Section above, _"Configuring Dynawo output variables"_.
	



Detailed steps for tripping generators:
=======================================

Some quick stats on generators (from Dynawo files):

| GEN TYPE   |  Lille |   Lyon | Marseille |
| --------   | -----: | -----: | --------: |
| HYDRO      |      4 |    404 |       160 |
| NUCLEAR    |     28 |     22 |	    10 |
| OTHER      |     12 |     14 |	    23 |
| SOLAR      |      6 |     77 |	   188 |
| THERMAL    |     27 |      6 |	    17 |
| WIND       |    190 |     44 |	    18 |
| Total      |    267 |    567 |	   416 |
| (inactive) |    (25)|   (135)|       (64)|



Tripping generators in Astre:
-----------------------------

A step by step example using generator "HAUBO4GR1" (Lille case):

  * Find the gen in Astre: among elements with tag "groupe", find nom
    == "HAUBO4GR1".  Keep its "num" attribute, which is the gen id (in
    this case, 55).

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the gen id using the `ouvrage`
    attribute. Use `type="2"` for generators, and `typeevt="1"` for
    disconnection (see table above).  Example:
  
    ```
      <scenario nom="scenario" duree="1200">
		<evtouvrtopo instant="300" ouvrage="55" type="2" typeevt="1" cote="0"/>
      </scenario>
    ```

  * Finally, add suitable output variables ("courbes") as described in
    the Section above, _"Configuring Astre output variables"_.



Tripping generators in Dynawo:
------------------------------

Generators may or may not have a dynamic model.  To disconnect them,
one has to do things differently in one case and the other.

If the generator does *not* have a dynamic model, the disconnection is
performed similar to shunts, using an `EventConnectedStatus` model.
(see the Introduction, about the three differnent types of
disconnections).  Here is a step by step example, using gen "BLOCAIN1"
(Lille case):
 
  * Find the gen in the IIDM file by seaching the "generator"
    elements; the id attribute is the gen name. Note that if the gen
    has attributes p="-0" q="-0" (both with the minus sign), then it
    is already disconnected.

  * Edit the DYD file to add an `EventConnectedStatus` model as follows:
    ```
	  <blackBoxModel id="Disconnect my gen" lib="EventConnectedStatus" parFile="tFin/fic_PAR.xml" parId="99991234"/>

	```

  * And (also in the DYD file) connect this model with the static id2
    `NETWORK` and a var2 that refers to the gen id in the IIDM file,
    plus the sufffix `_state_value`:

    ```
      <connect id1="Disconnect my gen" var1="event_state1_value" id2="NETWORK" var2="BLOCAIN1_state_value"/>

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

If the generator *does* have a dynamic model, the disconnection is
performed similar to loads, using an `EventSetPointBoolean` model.
Here's a step by step example, using gen "HAUBO4GR1" (Lille case):

  * Find the id of the gen in the DYD file: among elements with tag
    "BlackBoxModel" and attribute "lib" == "Gen*", find the desired
    generator name using the attribute `staticId`.  Then keep the id,
    which is usually the same but prefixed with "DM_" (and dots
    converted to underscores).

  * In the DYD file, declare a model `EventSetPointBoolean` with the
    corrresponding section in the PAR file:
    ```
      <blackBoxModel id="Disconnect my gen" lib="EventSetPointBoolean" parFile="fic_PAR.xml" parId="99991234"/>
    ```

  * And (also in the DYD file) connect this with the corresponding id
    of the gen model in the same DYD file.  Look in the ddb desc file
    of the EventSetPointBoolean model for the variable you need to
    connect as var1.  Look in the ddb desc file of the Generator*
    model for the variable you need to connect as var2.
	```
      <connect id1="Disconnect my gen" var1="event_state1_value" id2="DM_HAUBO4GR1" var2="generator_switchOffSignal2_value"/>
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

Finally, add suitable output variables ("curves") as described in the
Section above, _"Configuring Dynawo output variables"_.






Detailed steps for tripping lines and transformers:
==================================================

In Dynawo, lines and transformers are contained in the IIDM file, They
are represented by elements with XML tags "line", and
"twoWindingsTransformer", respectively.  They do not have a
corresponding dynamic model in the DYD file. Phase-shifting
transformers can be identified because they contain a child element
with tag `phaseTapChanger` (standard transformers have a
`ratioTapChanger` instead).

Note: all transformers in all three Dynawo cases (Lille, Lyon,
Marseille) seem to be **two-winding**. There are no three-winding
tranformers (at least, not modeled as such).  Also, the high-voltage
side is almost always the "TO" side (or bus2); there's only two
exceptions in the Lyon case (SIEREY764, SIEREY762) and another two in
the Marseille case (G.ILEY761, G.ILEY762).

In Astre, both lines and transformers are described by elements with
XML tag "quadripole", and they can be told apart by the value of the
`type` attribute: 0--lines; 1--transformers; 2--phase shifting
transformers. The "from" and "to" buses are described in the "nor"
(noeud origine) an "nex" (noeud extreme) attributes, respectively.


Some quick stats:

| Lille case      | Astre  | Dynawo  |
| --------------  | -----: | ------: |
| Lines           |    969 |     969 |
| Transformers    |    257 |     214 |
| Phase Shifters  |      4 |       4 |
| TOTAL           |   1230 |    1187 |


| Lyon case       | Astre  | Dynawo  |
| --------------  | -----: | ------: |
| Lines           |   1562 |    1561 |
| Transformers    |    521 |     391 |
| Phase Shifters  |      5 |       5 |
| TOTAL           |   2088 |    1957 |


| Marseille case  | Astre  | Dynawo  |
| --------------  | -----: | ------: |
| Lines           |    980 |     979 |
| Transformers    |    377 |     269 |
| Phase Shifters  |      5 |       5 |
| TOTAL           |   1362 |    1253 |



Tripping lines and transformers in Astre:
-----------------------------------------

A step by step example using line "CHARPL31CIVRI" (Lyon case):

  * Find the line in Astre: among elements with tag "quadripole", find
    nom == "CHARPL31CIVRI".  Keep its "num" attribute, which is the
    line id (in this case, 711). Apparently [TO BE CONFIRMED], lines
    that are already disconnected can be detected by the values of P,Q
    flows:
	```
	  <variables por="0" pex="0" qor="0" qex="0"/>
	```

  * Edit the event using the `evtouvrtopo` element, wrapped in a
    `scenario` element.  Refer to the line id using the `ouvrage`
    attribute. Use `type="9"` for lines, and `typeevt="1"` for
    disconnection (see table above).  Choose the end of the connection
    using the `cote` attribute (0 = both ends; 1 = "From" end; 2 =
    "To" end). Example:
  
    ```
      <scenario nom="scenario" duree="1200">
		<evtouvrtopo instant="300" ouvrage="711" type="9" typeevt="1" cote="0"/>
      </scenario>
    ```

  * Finally, add suitable output variables ("courbes") as described in
    the Section above, _"Configuring Astre output variables"_.




Tripping lines and transformers in Dynawo:
------------------------------------------

Lines and transformers in RTE's Dynawo cases usually have a static
model only. But in this case the disconnection is not performed using
an `EventConnectedStatus` model, but an `EventQuadripoleDisconnection`
instead, so that one can specify which side(s) will be disconnected
(see the Introduction, about the three differnent types of
disconnections).  Here is a step by step example, using line
"CHARPL31CIVRI" (Lyon case):
 
  * Find the line in the IIDM file by seaching the "line" elements
    (for transformers, search the "twoWindingsTransformer" elements
    instead); the id attribute is the line name. Apparently [TO BE
    CONFIRMED], lines are disconnected if all values are zero,
    possibly with signed zeros (example: p1="0" q1="-0" p2="0"
    q2="-0").

  * Edit the DYD file to add an `EventQuadripoleDisconnection` model as follows:
    ```
	  <blackBoxModel id="Disconnect my BRANCH" lib="EventQuadripoleDisconnection" parFile="tFin/fic_PAR.xml" parId="99991234"/>

	```

  * And (also in the DYD file) connect this model with the static id2
    `NETWORK` and a var2 that refers to the line id in the IIDM file,
    plus the sufffix `_state_value`:

    ```
      <connect id1="Disconnect my BRANCH" var1="event_state1_value" id2="NETWORK" var2="CHARPL31CIVRI_state_value"/>

	```

  * In the PAR file, add a section with the parameters for the
    disconnection (the time and the action itself).  You can look in
    the ddb desc file of the `EventQuadripoleDisconnection` model if
    you want to check the exact names of these parameters:
	
	```
      <set id="99991234">
        <par type="DOUBLE" name="event_tEvent" value="4300"/>
        <par type="BOOL" name="event_disconnectOrigin" value="false"/>
        <par type="BOOL" name="event_disconnectExtremity" value="true"/>
      </set>
    ```

   * Finally, add suitable output variables ("curves") as described in
     the Section above, _"Configuring Dynawo output variables"_.




**END OF DOCUMENT**
