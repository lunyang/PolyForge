# PolyForge Paper Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `@superpowers:subagent-driven-development` (recommended) or `@superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use `@superpowers:test-driven-development` for each behavior change and `@superpowers:verification-before-completion` before claiming completion.

**Goal:** Build reproducible paper-experiment tooling for Tg benchmarking, LLM-generated PolyForge program validation, compiler-feedback repair, and constrained inverse-design reports.

**Architecture:** Keep experiment code under `experiments/` and leave `polyforge/` focused on the compiler. The experiment layer consumes stable PolyForge APIs and writes auditable artifacts under `runs/` or a user-provided output directory. Live LLM calls are optional; tests and default demos use saved fixture outputs.

**Tech Stack:** Python 3.11+, `pandas`, `numpy`, `scikit-learn`, `rdkit`, `pytest`, existing PolyForge parser/checker/canonicalizer APIs.

---

## File Map

- Create: `experiments/__init__.py`
- Create: `experiments/tg_benchmark/__init__.py`
- Create: `experiments/tg_benchmark/dataset.py`
- Create: `experiments/tg_benchmark/splits.py`
- Create: `experiments/tg_benchmark/features.py`
- Create: `experiments/tg_benchmark/benchmark.py`
- Create: `experiments/tg_benchmark/cli.py`
- Create: `experiments/llm_generation/__init__.py`
- Create: `experiments/llm_generation/artifacts.py`
- Create: `experiments/llm_generation/extract.py`
- Create: `experiments/llm_generation/evaluate.py`
- Create: `experiments/llm_generation/repair.py`
- Create: `experiments/inverse_design/__init__.py`
- Create: `experiments/inverse_design/rank.py`
- Create: `experiments/inverse_design/report.py`
- Create: `experiments/fixtures/llm_outputs/*.txt`
- Create: `tests/experiments/test_tg_dataset.py`
- Create: `tests/experiments/test_tg_splits.py`
- Create: `tests/experiments/test_tg_features.py`
- Create: `tests/experiments/test_tg_benchmark.py`
- Create: `tests/experiments/test_llm_artifacts.py`
- Create: `tests/experiments/test_llm_generation.py`
- Create: `tests/experiments/test_inverse_design.py`
- Modify: `readme.md`

## Task 1: Dataset Loader and Audit

**Files:**
- Create: `experiments/__init__.py`
- Create: `experiments/tg_benchmark/__init__.py`
- Create: `experiments/tg_benchmark/dataset.py`
- Create: `tests/experiments/test_tg_dataset.py`

- [ ] **Step 1: Write the failing test**

Create tests that load `bigsmiles-Tg.csv` using Latin-1 encoding, normalize columns to `row_index`, `polymer_name`, `smiles`, `bigsmiles`, `tg_k`, and compute the audit facts already observed:

```python
def test_load_bigsmiles_tg_dataset_normalizes_columns():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    assert list(dataset.frame.columns) == ["row_index", "polymer_name", "smiles", "bigsmiles", "tg_k", "structure_key"]
    assert len(dataset.frame) == 304
    assert dataset.frame["tg_k"].notna().all()

def test_dataset_audit_reports_expected_counts():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    audit = audit_dataset(dataset.frame)
    assert audit["rows"] == 304
    assert audit["target_missing_or_bad"] == 0
    assert audit["unique_polymer_names"] == 276
    assert audit["exact_duplicate_rows"] == 0
    assert audit["duplicate_structure_pairs"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_dataset.py -v
```

Expected: fail because `experiments.tg_benchmark.dataset` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `BigSmilesTgDataset` dataclass with `frame` and `source_path`
- `load_bigsmiles_tg_csv(path: str | Path) -> BigSmilesTgDataset`
- `audit_dataset(frame: pd.DataFrame) -> dict[str, object]`
- `structure_key` as `sha256(smiles + "\n" + bigsmiles)` for now
- explicit Latin-1 reading
- validation that `Tg (K) exp` is numeric

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_dataset.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments tests/experiments/test_tg_dataset.py
git commit -m "feat: add Tg dataset loader and audit"
```

## Task 2: Deterministic Grouped Splits

**Files:**
- Create: `experiments/tg_benchmark/splits.py`
- Create: `tests/experiments/test_tg_splits.py`

- [ ] **Step 1: Write the failing test**

Test deterministic 5-fold grouped splitting by `structure_key`:

```python
def test_make_grouped_folds_is_deterministic_and_exhaustive():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    folds_a = make_grouped_folds(dataset.frame, n_splits=5, seed=13)
    folds_b = make_grouped_folds(dataset.frame, n_splits=5, seed=13)
    assert folds_a == folds_b
    test_rows = sorted(row for fold in folds_a for row in fold["test_indices"])
    assert test_rows == list(range(len(dataset.frame)))

def test_grouped_folds_do_not_split_structure_keys():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    folds = make_grouped_folds(dataset.frame, n_splits=5, seed=13)
    for fold in folds:
        train_keys = set(dataset.frame.iloc[fold["train_indices"]]["structure_key"])
        test_keys = set(dataset.frame.iloc[fold["test_indices"]]["structure_key"])
        assert train_keys.isdisjoint(test_keys)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_splits.py -v
```

Expected: fail because `make_grouped_folds` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `make_grouped_folds(frame, n_splits=5, seed=13)` with `sklearn.model_selection.GroupKFold`. Sort rows deterministically before split and emit JSON-serializable lists:

```python
[
  {"fold": 0, "train_indices": [...], "test_indices": [...]},
  ...
]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_splits.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/tg_benchmark/splits.py tests/experiments/test_tg_splits.py
git commit -m "feat: add deterministic Tg benchmark splits"
```

## Task 3: SMILES and BigSMILES Baseline Features

**Files:**
- Create: `experiments/tg_benchmark/features.py`
- Create: `tests/experiments/test_tg_features.py`

- [ ] **Step 1: Write the failing test**

Test two feature families:

```python
def test_smiles_features_are_numeric_and_row_aligned():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    features = make_smiles_features(dataset.frame.head(8))
    assert len(features.frame) == 8
    assert features.frame.index.tolist() == list(range(8))
    assert all(name.startswith("smiles.") for name in features.feature_columns)

def test_bigsmiles_char_features_are_numeric_and_stable():
    dataset = load_bigsmiles_tg_csv("bigsmiles-Tg.csv")
    a = make_bigsmiles_char_features(dataset.frame.head(8))
    b = make_bigsmiles_char_features(dataset.frame.head(8))
    assert a.feature_columns == b.feature_columns
    assert a.frame[a.feature_columns].equals(b.frame[b.feature_columns])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_features.py -v
```

Expected: fail because feature builders do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `FeatureTable` dataclass with `frame`, `feature_columns`, and `metadata`
- `make_smiles_features(frame)` using RDKit descriptors on wildcard-stripped SMILES where possible
- `make_bigsmiles_char_features(frame)` using deterministic character counts and length features

For SMILES wildcard handling, replace `*` with `[H]` only inside the experiment feature builder and record failures in metadata. Do not change PolyForge compiler chemistry behavior.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_features.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/tg_benchmark/features.py tests/experiments/test_tg_features.py
git commit -m "feat: add Tg baseline feature builders"
```

## Task 4: Reproducible Tg Benchmark Runner

**Files:**
- Create: `experiments/tg_benchmark/benchmark.py`
- Create: `experiments/tg_benchmark/cli.py`
- Create: `tests/experiments/test_tg_benchmark.py`

- [ ] **Step 1: Write the failing test**

Test a local benchmark run against a temporary output directory:

```python
def test_run_tg_benchmark_writes_required_artifacts(tmp_path):
    result = run_tg_benchmark(
        dataset_path="bigsmiles-Tg.csv",
        output_dir=tmp_path,
        representations=["bigsmiles_char"],
        models=["mean", "random_forest"],
        n_splits=5,
        seed=13,
    )
    assert (tmp_path / "dataset_audit.json").exists()
    assert (tmp_path / "splits.json").exists()
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "predictions.csv").exists()
    assert result["dataset"]["rows"] == 304
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_benchmark.py -v
```

Expected: fail because `run_tg_benchmark` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `run_tg_benchmark(...)`
- grouped fold evaluation
- metrics: MAE, RMSE, R2
- artifact writing: `dataset_audit.json`, `splits.json`, `metrics.json`, `predictions.csv`
- CLI entrypoint module runnable as:

```bash
conda run -n LLM python -m experiments.tg_benchmark.cli --dataset bigsmiles-Tg.csv --out runs/tg_benchmark
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_tg_benchmark.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/tg_benchmark/benchmark.py experiments/tg_benchmark/cli.py tests/experiments/test_tg_benchmark.py
git commit -m "feat: add reproducible Tg benchmark runner"
```

## Task 5: LLM Artifact Schema and Candidate Extraction

**Files:**
- Create: `experiments/llm_generation/__init__.py`
- Create: `experiments/llm_generation/artifacts.py`
- Create: `experiments/llm_generation/extract.py`
- Create: `experiments/fixtures/llm_outputs/valid_homopolymer.txt`
- Create: `experiments/fixtures/llm_outputs/invalid_then_repair.txt`
- Create: `tests/experiments/test_llm_artifacts.py`

- [ ] **Step 1: Write the failing test**

Test saved-output fixture mode:

```python
def test_extract_pdsl_blocks_from_saved_llm_output():
    text = Path("experiments/fixtures/llm_outputs/valid_homopolymer.txt").read_text()
    blocks = extract_pdsl_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].startswith("polymer ")

def test_llm_artifact_round_trip(tmp_path):
    artifact = LlmRunArtifact(
        run_id="fixture-001",
        model="fixture",
        prompt="generate a valid PolyForge program",
        raw_output="polymer PMMA { }",
        extracted_pdsl=["polymer PMMA { }"],
    )
    path = write_llm_artifact(artifact, tmp_path)
    assert read_llm_artifact(path) == artifact
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_llm_artifacts.py -v
```

Expected: fail because LLM artifact helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `LlmRunArtifact` dataclass
- JSON read/write helpers
- `extract_pdsl_blocks(text)` supporting fenced `pdsl`, fenced generic code, and raw `polymer ... { ... }` blocks

Do not add live LLM API integration in this task.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_llm_artifacts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/llm_generation experiments/fixtures tests/experiments/test_llm_artifacts.py
git commit -m "feat: add LLM artifact fixtures and extraction"
```

## Task 6: LLM Generation Evaluation and Repair Loop

**Files:**
- Create: `experiments/llm_generation/evaluate.py`
- Create: `experiments/llm_generation/repair.py`
- Create: `tests/experiments/test_llm_generation.py`

- [ ] **Step 1: Write the failing test**

Test evaluation from fixture outputs without live LLM calls:

```python
def test_evaluate_llm_outputs_reports_validation_stages(tmp_path):
    result = evaluate_saved_llm_outputs(
        fixture_dir="experiments/fixtures/llm_outputs",
        output_dir=tmp_path,
    )
    assert result["total_outputs"] >= 2
    assert "parse_pass_rate" in result
    assert "canonicalization_pass_rate" in result
    assert (tmp_path / "llm_generation_metrics.json").exists()

def test_make_repair_prompt_includes_diagnostics():
    prompt = make_repair_prompt("polymer Bad {", ["syntax error at line 1"])
    assert "syntax error at line 1" in prompt
    assert "Return only corrected PolyForge" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_llm_generation.py -v
```

Expected: fail because evaluation and repair modules do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `evaluate_saved_llm_outputs(fixture_dir, output_dir)`
- validation through existing `polyforge.pipeline.load_source` or parser/checker APIs using temporary `.pdsl` files
- metrics by stage: parse, semantic, chemistry, canonicalization
- `make_repair_prompt(pdsl, diagnostics)`

Bounded live repair execution can be added later; this task only produces repair prompts and fixture evaluation.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_llm_generation.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/llm_generation tests/experiments/test_llm_generation.py
git commit -m "feat: add LLM generation evaluation"
```

## Task 7: Inverse-Design Ranking Report

**Files:**
- Create: `experiments/inverse_design/__init__.py`
- Create: `experiments/inverse_design/rank.py`
- Create: `experiments/inverse_design/report.py`
- Create: `tests/experiments/test_inverse_design.py`

- [ ] **Step 1: Write the failing test**

Test ranking valid candidate records:

```python
def test_rank_candidates_prefers_target_window_hits():
    candidates = [
        {"canonical_id": "a", "predicted_tg_k": 210.0, "structure_key": "s1"},
        {"canonical_id": "b", "predicted_tg_k": 390.0, "structure_key": "s2"},
        {"canonical_id": "c", "predicted_tg_k": 700.0, "structure_key": "s3"},
    ]
    ranked = rank_candidates(candidates, target_low=180.0, target_high=250.0, training_structure_keys=set())
    assert ranked[0]["canonical_id"] == "a"
    assert ranked[0]["target_hit"] is True

def test_inverse_design_report_writes_funnel_metrics(tmp_path):
    report = write_inverse_design_report(
        output_dir=tmp_path,
        generated_count=10,
        parsed_count=8,
        valid_count=5,
        ranked_candidates=[],
    )
    assert report["funnel"]["generated"] == 10
    assert (tmp_path / "inverse_design_report.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_inverse_design.py -v
```

Expected: fail because inverse-design ranking modules do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement:

- `rank_candidates(candidates, target_low, target_high, training_structure_keys)`
- fields: `target_hit`, `target_error_to_center`, `novel`, `rank_score`
- `write_inverse_design_report(...)`

Diversity can start as unique `structure_key` count; descriptor-distance diversity can be added later.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments/test_inverse_design.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add experiments/inverse_design tests/experiments/test_inverse_design.py
git commit -m "feat: add inverse-design ranking report"
```

## Task 8: Documentation and End-to-End Verification

**Files:**
- Modify: `readme.md`
- Create: `docs/paper_experiments.md`
- Modify as needed: tests under `tests/experiments/`

- [ ] **Step 1: Write the failing test or smoke script expectation**

Add a test or documented smoke workflow that runs:

```bash
conda run -n LLM python -m experiments.tg_benchmark.cli --dataset bigsmiles-Tg.csv --out /tmp/polyforge_tg_benchmark
conda run -n LLM python -m pytest tests/experiments -v
```

Expected artifacts:

- `dataset_audit.json`
- `splits.json`
- `metrics.json`
- `predictions.csv`

- [ ] **Step 2: Run focused tests**

Run:

```bash
conda run -n LLM python -m pytest tests/experiments -v
```

Expected: PASS.

- [ ] **Step 3: Run full tests**

Run:

```bash
conda run -n LLM python -m pytest -v
```

Expected: PASS.

- [ ] **Step 4: Write docs**

Document:

- dataset source and encoding
- exact benchmark command
- artifact layout
- live LLM calls are excluded from tests
- claim boundaries for inverse design

- [ ] **Step 5: Commit**

```bash
git add readme.md docs/paper_experiments.md tests/experiments
git commit -m "docs: add paper experiment workflow"
```

## Final Verification

Before calling the phase complete, run:

```bash
conda run -n LLM python -m pytest -v
conda run -n LLM python -m experiments.tg_benchmark.cli --dataset bigsmiles-Tg.csv --out /tmp/polyforge_tg_benchmark
```

Expected:

- all tests pass
- benchmark command exits 0
- `/tmp/polyforge_tg_benchmark/dataset_audit.json` exists
- `/tmp/polyforge_tg_benchmark/metrics.json` exists
- `/tmp/polyforge_tg_benchmark/predictions.csv` exists

Then push `main`:

```bash
git push
```
