# PolyForge Paper Experiments Design

Date: 2026-05-13
Status: approved design draft
Primary dataset: `bigsmiles-Tg.csv`
Implementation baseline: PolyForge v0.1 on `main`

## 1. Goal

Design the next research phase for PolyForge as a paper-grade experimental program.

The paper should not claim that PolyForge is a universal polymer language or a complete inverse-design engine. The defensible claim is narrower:

> PolyForge provides a typed, compiler-checked polymer programming layer that allows LLMs to generate, repair, validate, canonicalize, and rank polymer candidates under explicit structural and property constraints.

The first paper should frame PolyForge as a representation and compiler system for LLM-driven polymer design, then validate the system on Tg prediction and constrained inverse-design tasks.

## 2. Core hypothesis

LLMs are strong at code generation but weak at guaranteeing chemical, semantic, and data-contract validity. PolyForge is designed to make polymer design look like programming:

```text
natural-language design intent
-> LLM-generated .pdsl candidate programs
-> PolyForge parse/check/canonicalize
-> descriptor/token generation
-> Tg prediction
-> rank/filter/repair
```

The key hypothesis is that a typed polymer DSL improves LLM-driven polymer workflows by turning hallucinated or underspecified outputs into compiler-diagnosable programs.

## 3. Confirmed scope

This phase includes:

- Tg prediction using `bigsmiles-Tg.csv`
- LLM generation of PolyForge `.pdsl` programs
- compiler-feedback repair of invalid `.pdsl` programs
- constrained inverse design with Tg as the soft target and PolyForge validity as hard constraints
- evaluation of validity, repair success, target-hit rate, novelty, and diversity

This phase excludes:

- claims of guaranteed real-world synthesizability
- full BigSMILES import
- network, branched, or gradient polymers
- morphology-aware property prediction
- transformer or GNN benchmark claims unless separately implemented and validated
- closed-loop wet-lab validation

## 4. Dataset facts

Initial scan of `bigsmiles-Tg.csv`:

- encoding: Latin-1, not UTF-8
- rows: 304
- columns: unnamed index, `Polymer`, `SMILES`, `BigSMILES`, `Tg (K) exp`
- target completeness: 304 / 304 numeric Tg values
- Tg range: 130 K to 685 K
- mean Tg: 360.566 K
- median Tg: 359 K
- population standard deviation: 114.546 K
- unique polymer names: 276
- exact duplicate full rows: 0
- duplicate `(SMILES, BigSMILES)` structure pairs: 0
- duplicate SMILES strings: 2
- duplicate BigSMILES strings: 2

Important implication: `Polymer` name must not be used as the primary structure group key. Some repeated names correspond to different structures and different Tg values.

## 5. Paper narrative

The paper should have three linked contributions:

1. **Language and compiler contribution**
   - A typed polymer DSL with explicit syntax, semantic checks, canonical IR, unit normalization, provenance, and schema validation.

2. **LLM-programming contribution**
   - A workflow where an LLM generates polymer programs, while PolyForge provides diagnostics, repair targets, and canonical candidate contracts.

3. **Property and inverse-design contribution**
   - A Tg prediction and constrained inverse-design benchmark showing that compiler-checked generation is measurable and reproducible.

The paper should avoid claiming that PolyForge replaces BigSMILES. BigSMILES is an interoperability representation; PolyForge is the compiler-facing programming layer.

## 6. System design

The experimental system has five components:

1. **Dataset adapter**
   - Reads `bigsmiles-Tg.csv` with Latin-1 encoding.
   - Normalizes column names.
   - Produces train/eval tables with `polymer_name`, `smiles`, `bigsmiles`, and `tg_k`.
   - Computes stable dataset row IDs and structure keys.

2. **Prediction baselines**
   - Mean predictor.
   - SMILES-derived RDKit descriptor baseline where chemically valid.
   - BigSMILES string-token baseline.
   - PolyForge-derived descriptor/token baseline for candidates expressible in v0.1.

3. **LLM candidate generator**
   - Accepts target Tg range and hard constraints.
   - Emits `.pdsl` candidate programs.
   - Stores prompts, raw outputs, extracted `.pdsl`, and model metadata.

4. **PolyForge validation and repair loop**
   - Runs `parse -> resolve -> chemistry -> semantics -> canonicalize`.
   - Converts diagnostics into repair prompts.
   - Runs a bounded repair loop, e.g. max 3 attempts per candidate.

5. **Inverse-design ranker**
   - Featurizes valid candidates.
   - Predicts Tg.
   - Filters hard constraints.
   - Ranks by target fit, novelty, diversity, and validation confidence.

## 7. Experiment 1: Tg prediction benchmark

Purpose: establish a reproducible property-prediction baseline on the provided dataset.

Inputs:

- `bigsmiles-Tg.csv`

Representations:

- raw SMILES descriptors
- BigSMILES character or token features
- PolyForge descriptors for generated or successfully adapted candidates

Important boundary: `bigsmiles-Tg.csv` should not be treated as if every row already has a lossless PolyForge representation. v0.1 does not include full BigSMILES import. The main dataset benchmark can compare SMILES and BigSMILES baselines; PolyForge descriptors enter when a candidate is generated as `.pdsl` or when a row is manually or programmatically adapted with explicit missing-field provenance.

Models:

- mean baseline
- linear regression
- random forest
- optional later: gradient boosting if added as a dependency

Splits:

- deterministic 5-fold split
- grouped split by stable structure key, not by polymer name
- random split may be reported only as a secondary optimistic baseline

Metrics:

- MAE
- RMSE
- R2
- fold mean and standard deviation

Required artifact outputs:

- `metrics.json`
- `predictions.csv`
- `splits.json`
- `dataset_audit.json`

## 8. Experiment 2: LLM program-generation validity

Purpose: measure whether LLMs can generate usable PolyForge programs and how much the compiler helps.

Prompt conditions:

1. plain natural-language prompt
2. schema-guided prompt with a compact PolyForge grammar summary
3. example-guided prompt with 2-3 valid `.pdsl` examples
4. compiler-feedback repair prompt

All repair must be automated and bounded. Do not manually fix LLM outputs inside the reported evaluation set.

Tasks:

- generate linear homopolymers
- generate random copolymers with valid composition
- generate block copolymers with positive DP
- generate candidates targeting a Tg window

Metrics:

- parse pass rate
- semantic pass rate
- chemistry pass rate
- canonicalization pass rate
- valid candidate yield per prompt
- average repair attempts
- repair success rate
- diagnostic category distribution

The LLM is not treated as a validator. PolyForge is the validator.

## 9. Experiment 3: Constrained inverse design

Purpose: evaluate the full LLM-driven inverse-design loop under hard constraints.

Input:

```text
Target: Tg in a specified window
Hard constraints:
- linear architecture
- supported v0.1 sequence type
- valid monomer definitions
- valid composition sum when random copolymer
- positive block DP when block copolymer
- RDKit-parseable monomer chemistry
- canonical IR schema validation
```

Pipeline:

```text
target + constraints
-> LLM candidate generation
-> PolyForge validation
-> compiler-feedback repair
-> canonicalization
-> Tg prediction
-> rank/filter
```

Target windows:

- low Tg: 180-250 K
- medium Tg: 320-400 K
- high Tg: 500-620 K

Target windows should be fixed before running inverse-design experiments and reported as protocol choices, not tuned after seeing candidate performance.

Metrics:

- valid candidate rate
- repaired valid candidate rate
- top-k target hit rate
- predicted Tg error to window center
- novelty against `bigsmiles-Tg.csv`
- candidate diversity by structure hash, token distance, or descriptor distance
- constraint violation distribution

Claim boundary:

PolyForge can enforce grammar, type, semantic, and basic chemical constraints. It does not guarantee synthesizability or experimental Tg correctness.

## 10. LLM evaluation protocol

All LLM experiments must be reproducible at the artifact level:

- save system prompt
- save user prompt
- save raw LLM output
- save extracted `.pdsl`
- save compiler diagnostics
- save repair prompts
- save final canonical IR
- save model/provider/version if available
- save timestamp and random seed where applicable

If external LLM APIs are used, the paper should report enough prompt and output artifacts for reproduction without requiring access to the exact same model endpoint.

Tests should not depend on live LLM calls. Implementation should support a fixture mode that replays saved LLM outputs.

## 11. Data leakage controls

Avoid these leakage paths:

- splitting duplicate or near-duplicate structures across train/test
- using `Polymer` name as a leakage-prone group key
- tuning prompts on the test target windows without reporting it
- reporting random split as the main result
- allowing generated candidates copied from the training table to count as novel inverse-design hits

Recommended structure key hierarchy:

1. canonicalized SMILES when available
2. normalized BigSMILES string
3. raw `(SMILES, BigSMILES)` pair

Novelty should be computed against the training dataset by structure key, not by polymer name.

## 12. Figures and tables

Recommended figures:

- PolyForge compiler pipeline for LLM-driven polymer design
- canonical IR example for a valid candidate
- repair-loop diagram from invalid `.pdsl` to valid canonical IR
- Tg prediction parity plot
- inverse-design funnel: generated -> parsed -> semantically valid -> chemically valid -> ranked

Recommended tables:

- dataset audit summary
- prediction benchmark results
- LLM generation validity by prompt condition
- repair success by diagnostic category
- top-k inverse-design candidates by target window

## 13. Required implementation additions

The current v0.1 compiler is sufficient as the foundation, but the paper experiments need additional code:

- dataset audit command or script for `bigsmiles-Tg.csv`
- dataset-specific baseline featurizers
- grouped split writer
- benchmark runner
- LLM prompt/output artifact schema
- candidate extraction from LLM text
- repair-loop driver
- inverse-design ranking report
- plotting utilities

These should be added under a clear experimental namespace, such as:

```text
experiments/
  tg_benchmark/
  llm_generation/
  inverse_design/
```

The core `polyforge/` package should remain focused on the compiler. Experiment-specific code should not pollute the language implementation.

## 14. Acceptance criteria

The phase is ready for paper writing when:

- dataset audit is generated from `bigsmiles-Tg.csv`
- Tg benchmark can be reproduced from one command
- LLM generation artifacts are stored for all prompt conditions
- repair-loop metrics are computed automatically
- inverse-design reports include target hit rate, novelty, and diversity
- all claims are supported by saved artifacts
- tests cover dataset loading, split generation, and metric computation

## 15. Open risks

- BigSMILES strings in the dataset may not map cleanly into PolyForge v0.1.
- RDKit descriptor coverage may be uneven for wildcard polymer repeat units.
- LLM output quality may vary across providers and dates.
- Tg prediction on 304 samples may have high variance.
- Inverse-design candidates are model-ranked, not experimentally validated.

These risks are acceptable if they are surfaced explicitly and the paper frames PolyForge as a compiler-mediated LLM design layer rather than a finished autonomous materials-discovery system.
