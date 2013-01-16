all: wherigo.pdf

%.dvi: %.tex
	latex $<

%.pdf: %.dvi
	dvipdf $<
	evince $@
