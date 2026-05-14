# PyForge Notebook Case Study Design

Date: 2026-05-14
Status: approved implementation design
Target notebook: `PyForge.ipynb`

## Goal

Create a complete English-language PolyForge case-study notebook that demonstrates the language, compiler pipeline, property prediction, LLM-assisted program generation, and constrained inverse design. The notebook must export publication-quality figures and result tables suitable for a materials chemistry paper.

## Style

Use ACS/RSC-style figures:

- restrained palette
- multi-panel layouts
- panel labels `a`, `b`, `c`
- readable axis labels
- 300 dpi PNG export
- vector PDF and SVG export where possible

## Required Sections

The notebook should include:

1. PolyForge purpose and notebook scope.
2. Environment and output paths.
3. PolyForge syntax walkthrough with homopolymer, random copolymer, and block copolymer examples.
4. Compiler pipeline demo: validation, diagnostics, canonical IR, `canonical_id`, and `structure_hash`.
5. Export targets: canonical JSON, token sequence, descriptors, and limited BigSMILES.
6. Dataset audit for `bigsmiles-Tg.csv`.
7. Tg prediction benchmark using `bigsmiles_char` and `smiles_rdkit` representations.
8. LLM-generated program fixture evaluation.
9. Compiler-feedback repair prompt demonstration.
10. Constrained inverse-design candidate ranking.
11. Publication figure export.
12. Result table export.
13. Claim boundaries.

## Required Figures

- Figure 1: PolyForge workflow diagram and representative polymer repeat-unit structures.
- Figure 2: Tg dataset audit and Tg distribution.
- Figure 3: Tg prediction benchmark parity plot and MAE comparison.
- Figure 4: LLM validity funnel and inverse-design ranking.

## Implementation Notes

- Keep reusable plotting and case-study logic in `experiments/notebook_case_study.py`.
- Generate `PyForge.ipynb` from `scripts/generate_pyforge_notebook.py` for reproducibility.
- Do not require live LLM calls. Use saved fixture outputs.
- Do not claim experimental synthesizability or measured inverse-design success.
- Export notebook artifacts under `runs/notebook_case_study/`.
