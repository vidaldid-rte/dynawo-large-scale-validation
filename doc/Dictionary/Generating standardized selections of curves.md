
Standardizing the selection of curves to appear in the output
=============================================================

We have standardized the selection of curves to be output, for each
base case. This document describes what the selection is, and how we
have automated it.

Essentially, we first include the variables of interest of
the relevant zone's SVCs: pilot voltage, K-levels of the SVCs, and
(P,Q) of participating generators:

Template for Astre:
```
          <courbe nom="RST_XXXXXXX_U_IMPIN_value" typecourbe="63" ouvrage="???" type="7"/>
          <courbe nom="RST_XXXXXXX_levelK_value" typecourbe="45" ouvrage="???" type="11"/>
          <courbe nom="DM_YYYYYYYY_tfo_generator_PGen" typecourbe="46" ouvrage="???" type="2"/>
          <courbe nom="DM_YYYYYYYY_tfo_generator_QGen" typecourbe="47" ouvrage="???" type="2"/>
```

Template for Dynawo's CRV:
```
       <curve model="RST_XXXXXXX" variable="U_IMPIN_value"/>
       <curve model="RST_XXXXXXX" variable="levelK_value"/>
       <curve model="DM_YYYYYY" variable="generator_PGen"/>
       <curve model="DM_YYYYYY" variable="generator_QGen"/>
```

In addition, we are also including the K-levels of **all** other SVCs
present in the base case, regardless of the zone.  And finally, we
then add additional curves specific to the particular contingency
being processed.

Note that we use the same variable names in Astre and Dynawo, so that
the resulting curve data files can be compared directly. This can be
done because the `nom` attribute in Astre curves is a just a label
that the user can choose freely.

Initially, the preparation of these curves was done manually for each
new basecase. But this is a laborious and error-prone task, so it
became clear that it would not scale in the long run.  We therefore
automated the whole procedure.



Automating this selection
=========================

The creation of the curve lists is automated as follows: we first
looking inside the particular case and, knowing which Zone the case
belongs to (Lille, Marseille etc), we first enumerate all RST controls
that are found inside, checking them against the master table below in
order to find out which ones belong to the Zone and which do not. For
the ones that do belong to the Zone, we will be including V, K, P,
Q. For the rest, we will include only K-levels.
	  
As for P, Q: to find out which generators participate in each RST
control, we just extract this info from the case, not from any master
table--because their online/offline status depends on the case.

These are the steps in detail:

  1. First find out which SVC zones (a.k.a. RST zones) belong to the
     Zone. We obtaind this master data from a map provided by RTE:
     "RST-NA-CNES-DGP-03-00071-ind13-PDF.pdf". This data is tabulated
     below.

  2. In Astre:

        - We look for elements `zonerst`, they provide how many SVCs
		  are actually present in the file and their zonerst ID (use
		  this ID for the K-level).  **IMPORTANT NOTE**: these IDs vary
		  from case to case!

        - The child elements of each zonerst contain the pilot buses
		  (use these IDs for the RST_xxxxxxx_U_IMPMIN" curve) and the
		  participating generators (use these IDs for the PGen/QGen
		  curves).

  3. In Dynawo:

        - We look in the DYD file for blackbox models with
		  lib="DYNModelRST" (their IDs typically begin with `RST_`).
		  These provide you with all the SVCs present in the file. The
		  name of the RST is all you need for the two first curves,
		  that is, the pilot bus voltage and the K-level (see the
		  template above).

        - Then look for their connections (`macroConnect`) to find
		  which generators comprise the participants. Use their dynamic
		  model IDs as in the template above.




Master list of RST zones
=========================

At the beginning of the project we obtained a reference list of RST
zones per Zone (and their participating generators) from some example
LaTeX reports provided by RTE, but this information was not very
complete.  Then we obtained a full list, from the reference map
_"RST-NA-CNES-DGP-03-00071-ind13-PDF.pdf"_.


```
{ "Lille": ["LONNYP7", "MASTAP7", "WARANP7"],
  "Lyon": ["ALBERP7", "CHAFFP7", "GEN_PP6", "LAVEYP6"],
  "Marseille": ["TRI_PP7", "BOLL5P6", "LAVERP6", "PALUNP6", "SISTEP6"],
  "Nancy": ["M_SEIP7", "MUHLBP7", "VIGY_P7", "BAYETP6", "J_VILP6", "VOGELP6"],
  "Nantes": ["AVOI5P7", "AVOI5P7_", "COR_PP7", "GAUGLP7", "TABARP7",
             "VALDIP7", "VERGEP7", "BRENNP6", "JUSTIP6", "MARTYP6"],
  "Paris": [ "BARNAP7", "CERGYP7", "MENUEP7", "ARRIGP6", "CHESNP6",
             "HAVRE5P6", "VLEVAP6"],
  "Toulouse": ["BAIXAP7", "BRAUDP7", "DONZAP7", "RUEYRP7", "BREUIP6",
               "LANNEP6", "SSVICP6", "TARASP6"]
}
```

Note that "AVOI5P7 " is an anomalous case: it seems that, in the
Dynawo cases, this SVC happens to be split into two devices: "AVOI5P7"
and "AVOI5P7_" (while in the Astre cases this is only one single SVC
control device). As we understood from RTE, this is because the
associated busbarSections could be (in principle) topologically split,
so Dynawo allows for such split in this way.

For the **Nation-wide** case, we initially considered including only the
SVCs controlling 400 kV buses:
```
"Recollement": ["LONNYP7", "MASTAP7", "WARANP7", "ALBERP7",
                "CHAFFP7", "TRI_PP7", "M_SEIP7", "MUHLBP7", "VIGY_P7",
                "AVOI5P7", "COR_PP7", "GAUGLP7", "TABARP7", "VALDIP7",
                "VERGEP7", "BARNAP7", "CERGYP7", "MENUEP7", "BAIXAP7",
                "BRAUDP7", "DONZAP7", "RUEYRP7"]
```

But this still generates a quite large amount of variables (159!) in
the curve files.  RTE provided us with a shorter list of the most
interesting points to monitor:
```
"Recollement": ["LONNYP7", "WARANP7",
                "CHAFFP7", "TRI.PP7", "M.SEIP7", "VIGY P7",
                "COR.PP7", "TABARP7",
                "BARNAP7", "MENUEP7",
                "BRAUDP7", "DONZAP7"]			
```

With these 12, the number of variables in the curve files goes down to
a more manageable 94 (still, we verified that the processing pipeline
and the Notebooks did cope with those 159 variables just fine).

