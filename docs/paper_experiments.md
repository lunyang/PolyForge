# Paper Experiments

This document describes the reproducible experiment layer for the PolyForge paper track.

The core `polyforge/` package remains a compiler. Paper-specific tooling lives under `experiments/` so benchmark and LLM evaluation code does not leak into the language implementation.

## Dataset

The initial Tg benchmark uses:

```text
bigsmiles-Tg.csv
```

Important details:

- The file is Latin-1 encoded, not UTF-8.
- Columns are normalized to `row_index`, `polymer_name`, `smiles`, `bigsmiles`, `tg_k`, and `structure_key`.
- `structure_key` is a SHA-256 hash over the raw SMILES and BigSMILES pair.
- `Polymer` names are not used as split groups because repeated names may refer to different structures.

## Tg Benchmark

Run:

```bash
conda run -n LLM python -m experiments.tg_benchmark.cli --dataset bigsmiles-Tg.csv --out runs/tg_benchmark
```

Artifacts:

- `dataset_audit.json`
- `splits.json`
- `metrics.json`
- `predictions.csv`

Default behavior:

- representation: `bigsmiles_char`
- models: `mean`, `random_forest`
- split: deterministic 5-fold grouped by `structure_key`
- seed: `13`

Additional representations and models can be requested with repeated flags:

```bash
conda run -n LLM python -m experiments.tg_benchmark.cli \
  --dataset bigsmiles-Tg.csv \
  --out runs/tg_benchmark \
  --representation bigsmiles_char \
  --representation smiles_rdkit \
  --model mean \
  --model linear_regression \
  --model random_forest
```

## LLM Fixture Mode

Tests and default evaluation do not depend on live LLM calls.

Saved LLM outputs live under:

```text
experiments/fixtures/llm_outputs/
```

The fixture evaluator extracts PolyForge `.pdsl` blocks, runs the existing compiler pipeline, and reports:

- parse pass rate
- semantic pass rate
- chemistry pass rate
- canonicalization pass rate
- valid candidate count

This supports the paper claim that PolyForge is a compiler-mediated layer for LLM-generated polymer programs.

## Inverse Design

The inverse-design helpers rank already validated candidate records by:

- target Tg window hit
- error to the target-window center
- novelty against training structure keys

The current ranking layer does not claim experimental synthesizability or true measured Tg. It ranks candidates according to model predictions and compiler-enforced hard constraints.

## Claim Boundaries

Safe claims:

- PolyForge can validate LLM-generated polymer programs against v0.1 syntax and semantic rules.
- PolyForge can produce auditable artifacts for Tg benchmark and inverse-design workflows.
- The experiment workflow can run without live LLM dependencies by replaying saved outputs.

Unsafe claims:

- PolyForge guarantees real-world synthesizability.
- The Tg predictor is benchmark-grade against modern polymer foundation models.
- BigSMILES rows are losslessly imported into PolyForge v0.1.

## Verification

Run focused experiment tests:

```bash
conda run -n LLM python -m pytest tests/experiments -v
```

Run the full project test suite:

```bash
conda run -n LLM python -m pytest -v
```
