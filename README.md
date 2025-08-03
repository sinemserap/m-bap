\# M‑BAP — Modular BIDS‑Aware EEG Artefact‑Removal Pipeline



\[!\[CI](https://github.com/<org-or-user>/m-bap/actions/workflows/ci.yml/badge.svg)](https://github.com/<org-or-user>/m-bap/actions/workflows/ci.yml)

\[!\[PyPI](https://img.shields.io/pypi/v/m-bap.svg)](https://pypi.org/project/m-bap/)

\[!\[License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)



> \*\*Reproducible EEG cleaning in one command, audit‑ready for clinical trials.\*\*



M‑BAP ingests raw scalp EEG organised according to the \*\*EEG‑BIDS\*\* standard  

and outputs fully cleaned FIF files, power‑spectral‑density plots and JSON

provenance logs into the BIDS \*\*`derivatives/`\*\* folder. It combines:



\* \*\*Robust bad‑channel detection\*\* (RANSAC, \*Autoreject\*)  

\* \*\*Average re‑referencing\*\* on interpolated channels  

\* \*\*Artifact Subspace Reconstruction (ASR)\*\* to suppress high‑amplitude bursts  

\* \*\*ICA with ICLabel\*\* to auto‑remove ocular, muscle, cardiac and line components  

\* \*\*Optional epoch‑level repair\*\* (Autoreject‑local)  

\* \*\*Config‑driven YAML parameters\*\* + per‑subject QC artefacts



The entire workflow is headless (CLI), container‑friendly and free of

proprietary dependencies.



---



\## Repository layout





Work in progres...

