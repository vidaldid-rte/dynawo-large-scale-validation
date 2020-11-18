
Standardizing the selection of curves to appear in the output
=============================================================

We have standardized the selections of curves to be output, for each base case.
Essentially, we first include the variables of interest of the
relevant area CSCsi: pilot voltage, K-level of the zone SVCs, and (P,Q) of
participating generators:

In Astre:
```
          <courbe nom="RST_XXXXXXX_U_IMPIN_value" typecourbe="63" ouvrage="???" type="7"/>
          <courbe nom="RST_XXXXXXX_levelK_value" typecourbe="45" ouvrage="???" type="11"/>
          <courbe nom="DM_YYYYYYYY_tfo_generator_PGen" typecourbe="46" ouvrage="???" type="2"/>
          <courbe nom="DM_YYYYYYYY_tfo_generator_QGen" typecourbe="47" ouvrage="???" type="2"/>
```

In Dinawo's CRV:
```
       <curve model="RST_XXXXXXX" variable="U_IMPIN_value"/>
       <curve model="RST_XXXXXXX" variable="levelK_value"/>
       <curve model="DM_YYYYYY" variable="generator_PGen"/>
       <curve model="DM_YYYYYY" variable="generator_QGen"/>
```

Note that we use the same variable names in Astre and Dynawo, so that
the resulting curve data files can be compared directly. This can be
done because the `nom` attribute in Astre curves is a just a label
that the user can choose freely.

We later added the K-level of all SVCs present in the base case,
regardless of the zone.  Then we add additional curves specific to the
particular contingency being processed.

For now, the creation of these curves is done manually, as it is not
clear whether or not it pays trying to automate this step. These are
the steps involved:

  1. First find out which SVC zones (a.k.a. RST zones) belong to the
     Area (look in the documentation)

  2. In Astre:

        (a)  Look for elements `zonerst`, they provide how many SVCs are present in the file and
             their zonerst ID (use this ID for the K-level).  **IMPORTANT NOTE**: these IDs vary from case to case!

        (b)  The zonerst elements contain the pilot buses (use these IDs for the RST_xxxxxxx_U_IMPMIN" curve)
             and the participating generators (use these IDs for the PGen/QGen curves).

  3. In Dinawo:

        (a)  Look in the DYD file for blackbox models with IDs that begin with `RST_`, these provide you with
             all the SVCs present in the file. The name of the RST is all you need for the two first curves, the
             pilot bus voltage and the K-level (see the template above).

        (b)  Then look for their connections (`macroConnect`) to find which
             generators comprise the participants. Use their dynamic model IDs as in the template above.



Automating this selectiom
=========================

We noticed that neither the example LaTeX reports nor the curves
present inside the provided case files provided an exhaustive list of all the
RST zones per Area, or the number of participating generators per RST
zone. It seems it is better to infer this info from each particular
case file.

We now have the complete list of all RST controls and the RST Areas
they belong to. [TODO: EXTRACT FROM THE MAP PROVIDED BT RTE]

With this information, the creation of the curve lists is automated as
follows:

   1. Looking inside the particular case, and knowing which Area
      (Lille, Marseille etc) the case belongs to, we enumerate all RST
      controls that are found inside, and we check them against the
      table above to find out which belong to the Area and which do
      not.
	  
   2. For the participating generators, we just extract them from the
      case, because their online/offline status depends on the case.

