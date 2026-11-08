AI Trade Index Paper — Compile Instructions
============================================

This archive contains everything needed to compile the paper to PDF.

Contents
--------
  ai-trade.tex            Main LaTeX source
  us-tariff-bibtex.bib    Bibliography database
  ai-trade.bbl            Pre-built bibliography (fallback, optional)
  figures/                All figures referenced by the paper (.png)
  tables/                 All tables \input by the paper (.tex)

Requirements
------------
  A standard LaTeX distribution (TeX Live, MiKTeX, or MacTeX). The
  document uses common packages (graphicx, natbib, booktabs, tcolorbox,
  pdflscape, threeparttable, palatino, etc.) and the "chicago"
  bibliography style, all included in a full TeX distribution.

How to compile
--------------
From this folder, run:

    pdflatex ai-trade
    bibtex   ai-trade
    pdflatex ai-trade
    pdflatex ai-trade

This produces ai-trade.pdf.

(If you cannot run bibtex, the included ai-trade.bbl lets a single
pdflatex pass resolve citations from the pre-built bibliography.)
