
ARTICLE=Dynawo_validation_final_report


default:
	pdflatex $(ARTICLE)

complete: default
	bibtex $(ARTICLE)
	pdflatex $(ARTICLE)
	pdflatex $(ARTICLE)

clean:
	rm -f *.toc *.aux *.log *.out *.bbl *.blg

mrproper: clean
	rm -f *~ $(ARTICLE).pdf
