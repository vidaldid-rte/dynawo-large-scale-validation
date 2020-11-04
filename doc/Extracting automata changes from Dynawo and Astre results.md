Extractinf automata changes from Dynawo and Astre results
=========================================================

***(c) 2020 Grupo AIA***

**marinjl@aia.es**

-------------------------------------------------------------------------------



INTRODUCTION
============

This document puts together several pieces of information provided by
RTE about how to extract and interpret correctly all changes in
automatic control devices, such as tap changers and several others.
The aim is to compare these changes in Astre vs Dynawo simulations.

As suggested by RTE, we will focus on the following types of changes,
which are the ones that affect voltage trajectories the most:

   * tap changers (up/down)
   
   * ACMC and SMACC controls 
   
   * SVC K-levels

Note that the area's SVC K-level is already monitored through the
corresponding curves, but here we are talking about monitoring changes
also in *other* SVC devices besides the area's own.

The ACMC and SMACC controls are automata that monitor one (ACMC) or
two (SMACC) bus voltages and connect or disconnect nearby shunts in
order to keep it or them within given boundaries, thus impacting the
voltage trajectories.




AUTOMATA CHANGES IN ASTRE
=========================

In Astre, events are read in the *chronologie* field in the output
file, like this:
```
    <evtchronologie priorite="3" instant="110" duree="0" type="7" ouvrage="6042"
	                evenement="1" tempo="0" contrainte="0" message="Nouvelle prise :      5"/>
```

As usual in Astre, `ouvrage` is the device ID number, and `type` is the device type:
```
   type="2" if generator (declared as **groupe** element in the xml)
   type="3" if load (declared as **conso** element in the xml)
   type="4" if shunt (declared as **shunt** element in the xml)
   type="5" if switch/breaker (declared as **couplage** in the xml)
   type="7" if ???load-transformer???
   type="9" if line or transformer (declared as **quadripole** element in the xml)
```

Here is the enum to decode the meaning of atributes `priorite`, `evenement`, `contrainte`:
```
class EvtChronologie
    {
      public:

        enum TypePriorite {
          SIMPLE    = 0,
          ENRICHI   = 1,
          DETAILLE  = 2,
          EXPERT    = 3
        };

        enum TypeEvenement {
          SURCHARGE               = 0,
          PRISEPLUS1              = 1,
          PRISEMOINS1             = 2,
          PRISEMAX                = 3,
          PRISEMIN                = 4,
          LIR                     = 5,
          UEL                     = 6,
          QMAX                    = 7,
          QMIN                    = 8,
          PMAX                    = 9,
          PMIN                    = 10,
          RST_UMAX                = 11,
          RST_UMIN                = 12,
          RSCT_CONSIGNE           = 13,
          PROTECTION_SOUS_TENSION = 14,
          CSPR_MISEENMARCHE       = 15,
          RST                     = 16,
          RST_NIVEAU              = 17,
          RST_CONSIGNE            = 18,
          RST_C3R                 = 19,
          RSCT_C3R                = 20,
          ACMC_ENCLENCHEMENT      = 21,
          ACMC_DECLENCHEMENT      = 22,
          ABR                     = 23,
          EVENEMENT_SCENARIO      = 24,
          PERTE_CONNEXITE         = 25,
          DELESTAGE               = 26,
          CRITERE                 = 27,
          AUTOMATE                = 28,
          DECLENCHEMENT_FILTRE    = 29,
          ENCLENCHEMENT_FILTRE    = 30,
          LAI                     = 31,
	      RST_UC_CONSIGNE         = 32,
          SMACC_ENCLENCHEMENT     = 33,
          SMACC_DECLENCHEMENT     = 34
        };

        enum TypeContrainte {
          NO_CONTRAINTE        = 0,
          ARMEMENT             = 1,
          DESARMEMENT          = 2,
          TEMPO_ECOULEE        = 3,
          ENTREE_BUTEE         = 4,
          SORTIE_BUTEE         = 5,
          BLOCAGE_NIVEAU       = 6,
          DEBLOCAGE_NIVEAU     = 7,
          TENSION_BASSE        = 8,
          TENSION_HAUTE        = 9,
          SURINTENSITE         = 10,
          CHARGE_NON_RESTAUREE = 11,
          CHARGE_SS_TENSION    = 12,
          CHARGE_COUPEE        = 13,
          CHARGE_COUPEE_AUTO   = 14,
          PUISS_NON_DISTRIB    = 15,
          PUIS_NON_DISTRIB_TOT = 16,
          HORS_LIM_INIT        = 17,
          PROD_COUPEE        = 18
        };
```

There are many possible messages, but we are interested in the following devices and message keys:

   * Taps: PRISEMOINS1, PRISEPLUS1

   * ACMC: ACMC_ENCLENCHEMENT, ACMC_DECLENCHEMENT
   
   * SMACC: SMACC_ENCLENCHEMENT, SMACC_DECLENCHEMENT
   
   * SVC Klevels: RST_CONSIGNE





AUTOMATA CHANGES IN DYNAWO
==========================

In Dynawo events are read in timeline.xml under this self-explanatory
form:

    <event time="1260" modelName="DM_LAMB5INA" message="Tap -1"/>


Note, however, that the events do not show a message key; they only
show a literal message. To find out the precise message key, one have
to use the following Dynawo dictionaries:

   * `$DYNAWO_INSTALL_DIR/share/DYNTimeline_en_GB.dic`

   * `$DYNAWO_INSTALL_DIR/share/DYNRTETimeline_en_GB.dic`  (additional keys for RTE's private version)
   
RTE's private version contains messages for ACMC, SMACC, and SVC controls.

There are many possible messages, but we are interested in the following devices and message keys:

   * Taps: TapUp, TapDown
	  
   * ACMC: AcmcShuntClosing, AcmcShuntOpening
   
   * SMACC: SmaccClosingDelayPastHV, SmaccOpeningDelayPastHV, SmaccClosingDelayPastLV, SmaccOpeningDelayPastLV
   
   * SVC Klevels: NewRstLevel

Note: for ACMC and SMACC devices, it may actually be easier to catch
the messages directly related to the actual shunt closing /
disconnections (keys ShuntConnected and ShuntDisconnected in the
public dictionary), instead of the orders given by ACMCs and SMACCs.

Summary table:

| EVENT KEY                 |  MESSAGE                                                 |
| ------------------------- | -------------------------------------------------------- |
| TapUp                     | "Tap +1"                                                 |
| TapDown                   | "Tap -1"                                                 |
| ------------------------- | -------------------------------------------------------- |
| ShuntConnected            | "SHUNT : connecting"                                     |
| ShuntDisconnected         | "SHUNT : disconnecting"                                  |
| ------------------------- | -------------------------------------------------------- |
| AcmcShuntClosing          | "VCS : shunt number %1% closing"                         |
| AcmcShuntOpening          | "VCS : shunt number %1% opening"                         |
| ------------------------- | -------------------------------------------------------- |
| SmaccClosingDelayPastHV   | "MVCS : closing shunt number %1% on higher voltage side" |
| SmaccOpeningDelayPastHV   | "MVCS : opening shunt number %1% on higher voltage side" |
| SmaccClosingDelayPastLV   | "MVCS : closing shunt number %1% on lower voltage side"  |
| SmaccOpeningDelayPastLV   | "MVCS : opening shunt number %1% on lower voltage side"  |
| ------------------------- | -------------------------------------------------------- |
| NewRstLevel               | "SVC Area : new level %1%"                               |




ATTEMPTING TO MATCH AUTOMATA CHANGES BETWEEN ASTRE AND DYNAWO
=============================================================

The following table summarizes the best way we have found (so far) to
match events:


| Device / Event            |  Identified in Astre as:               | Identified in Dynawo as:        |
| ------------------------- | -------------------------------------- | ------------------------------- |
| TRANSFORMER / TapUp       | type=9, key=`PRISEPLUS1` (1)           | non-DM, message="Tap +1"        |
| TRANSFORMER / TapDown     | type=9, key=`PRISEMOINS1` (2)          | non-DM, message="Tap -1"        |
| SHUNT / ShuntConnected    | type=4, key=`ACMC_ENCLENCHEMENT` (21)  | message="SHUNT : connecting"    |
| SHUNT / ShuntDisconnected | type=4, key=`ACMC_DECLENCHEMENT` (22)  | message="SHUNT : disconnecting" |
| SHUNT / ShuntConnected    | type=4, key=`SMACC_ENCLENCHEMENT` (33) | message="SHUNT : connecting"    |
| SHUNT / ShuntDisconnected | type=4, key=`SMACC_DECLENCHEMENT` (34) | message="SHUNT : disconnecting" |



Notes:

   * **Transformers:** in Dynawo, timeline events do not identify the
     type of device; they only contain a message (which can be looked
     up in dictionaries). And the same message may come from different
     devices. This is actually what happens with Tap +1/-1 events:
     when they refer to a device with name "DM_*", these are load
     transformers, not transmission transformers. We thus filter these
     out, because they do not show up in Dynawo. _[TODO: maybe they
     do, they're probably type=7, but then merged loads get in the way
     of comparison again.]_

   * **ACMC / SMACC controls:** Dynawo events "AcmcShuntClosing",
     "AcmcShuntOpening", "SmaccClosingDelayPast*",
     "SmaccOpeningDelayPast*", etc. DO NOT seem to have a direct
     counterpart in Astre. Instead, one can observe and match the
     actual actions on each **individual shunt**.
	 
   * **K-levels:** in Astre, event messages related to K-level changes
     (`RST_CONSIGNE`) are associated to each **generator**. By
     contrast, Dynawo only shows messages associated to the RST
     control, and there are no individual messages for each
     participating generator.
	
