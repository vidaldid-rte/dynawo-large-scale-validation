
# NOTES ON HOW THE FIGURES WERE PRODUCED

  * pipeline*.pdf: produced with PowerPoint, slides in 4:3 format, exported to
    PDF. Source file: fig_pipeline.pptx

  * transient_characteristics_*.pdf: produced with PowerPoint, slides in 4:3
    format, exported to PDF. Source file: figs_transient_characteristics.pptx

  * Ubus_dSS_GENS_20210211-0930_moreT600.pdf fig: produced with the
    notebook. Plot of dSS for the contingency-local bus voltage, for all GEN
    contingencies. Basecase was Recollement 20210211-0930, simulation time
    extended to 2000 sec (event at t=600).
  
  * Qgen_curve_GENS_20210211-0930_moreT600.pdf: produced with the notebook. Plot
    of the curve of Qgen for a generator in a contingency case where large dSS
    differences were observed. On top, the case-wide event diffs for this
    contingency case. Basecase was the same as above. The contingency case is
    CRUA57TRANCHE2, and the generator plotted here is SSALT7T 2.


To prepare good quality figures from PowerPoint, I exported to PDF, then used
the PDF viewer on macOS to select a tighter box around the figure, copied the
selection, and pasted on a new document (all within the PDF viewer). Then saved
the document choosing PDF as the format.  This preserves the PDF in vector
format and eliminates all extra white space from the margins of the slide.

