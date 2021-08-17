
Notes about matching matching Dynawo's and Astre's variable names
=================================================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------




ABOUT GENERAL RULES FOR MATCHING VARIABLE NAMES
================================================

RTE does not have general patterns covering all possible cases. But
for the variables of interest (i.e. K levels, SVC pilot voltages, and
the participating groups' Qstator) here is a recap table:

|                       |             Astre              |             Dynawo                     |
| --------------------- | ------------------------------ | -------------------------------------- |
| K level               | ZONERST_NIVEAU_{SVCZoneId}     | RST_{SVCZoneId}_levelK_value           |
| SVC pilot voltage     | NOEUD_TENSION_{PilotVoltageId} | RST_{SVCZoneId}_U_IMPIN_value          |
| Part. group's Qstator | GRP_PUISS_REA_STAT_GroupId     | {GroupDYDId}_generator_QStatorPu_value |


Astre examples:

  * K level: `ZONERST_NIVEAU_CHAFFP7`
  * SVC pilot voltage: `NOEUD_TENSION_CHAFFP7/1A`
  * Participant group's Qstator: `GRP_PUISS_REA_STAT_BUGEY7G4`

Dynawo examples:

  * K level: `RST_CHAFFP7_levelK_value`
  * SVC pilot voltage: `RST_CHAFFP7_U_IMPIN_value`
  * Participant group's Qstator: `DM_BUGEYT 4_tfo_generator_QStatorPu_value`

-------------------------------------------------------------------------------





BUILDING A DICTIONARY
=====================

* An initial step was attempted matching "by hand" the variables used
  in the output curves in Dynawo and Astre, in the provided
  cases. Some of these matches are not correct (see below).

* RTE provided some TeX reports from which we could extract some
  matches that are more certain. Left under `doc/Dictionary/`.
  
* TODO:
    - explore the matching rules of the main identifiers for buses, lines, gens, loads, etc.
	- explore how variable names (the ones in curve files) are formed 
    - ultimately, merge and unify a single dictionary of labels and/or label patterns
 
