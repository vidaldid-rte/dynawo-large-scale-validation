
ARTICLE=dynawo_validation


default:
	pdflatex $(ARTICLE)

complete: default
	bibtex $(ARTICLE)
	pdflatex $(ARTICLE)
	pdflatex $(ARTICLE)

pretty:
	latexindent -s -y="defaultIndent:'  '" -w $(ARTICLE).tex

clean:
	rm -f *.toc *.aux *.log *.out *.bbl *.blg *.bak*

mrproper: clean
	rm -f *~ $(ARTICLE).pdf

