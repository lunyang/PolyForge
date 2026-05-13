# PolyForge v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `@superpowers:test-driven-development` for each task and `@superpowers:verification-before-completion` before claiming a task done. Use `@superpowers:executing-plans` if you want to batch tasks in this session.

**Goal:** Build a compiler-first, CLI-first PolyForge v0.1 package that validates `.pdsl` programs, canonicalizes them into stable JSON IR, exports multiple views, and trains simple baseline models from local feature tables.

**Architecture:** Keep a single canonical IR at the center. Parser, checker, canonicalizer, exporters, and ML code should all depend on that IR, not on parser internals. The CLI should stay thin and only orchestrate the pipeline.

**Tech Stack:** Python 3.11+, `uv`, `lark`, pinned `rdkit`, `pandas`, `numpy`, `scikit-learn`, `pytest`, `dataclasses`.

---

## File map

- `pyproject.toml`: project metadata, dependencies, console script, test config.
- `polyforge/grammar/polyforge.lark`: language grammar.
- `polyforge/__main__.py`: `python -m polyforge` entry point.
- `polyforge/ir/nodes.py`: typed AST and canonical IR dataclasses.
- `polyforge/parser/parse.py`: parse source into parse tree and diagnostics.
- `polyforge/parser/ast_builder.py`: parse tree to AST conversion.
- `polyforge/check/diagnostics.py`: structured diagnostics types and helpers.
- `polyforge/check/symbols.py`: name resolution and reserved-name checks.
- `polyforge/check/chemistry.py`: RDKit validation and chemistry warnings/errors.
- `polyforge/check/semantics.py`: polymer semantic rules.
- `polyforge/canonicalize/normalize.py`: normalization and unit conversion.
- `polyforge/canonicalize/hash.py`: canonical ID and structure hash generation.
- `polyforge/canonicalize/json_ir.py`: canonical JSON serialization/deserialization.
- `polyforge/emit/json.py`: canonical JSON exporter.
- `polyforge/emit/tokens.py`: token-sequence exporter.
- `polyforge/emit/descriptors.py`: descriptor builder used by both export and featurize.
- `polyforge/emit/bigsmiles.py`: limited BigSMILES exporter.
- `polyforge/ml/featurize.py`: feature-table builder for local inputs.
- `polyforge/ml/models.py`: baseline model factory and split helpers.
- `polyforge/ml/train.py`: baseline training/evaluation workflow.
- `polyforge/cli/main.py`: CLI entry point and subcommand dispatch.
- `examples/*.pdsl`: valid example programs.
- `examples/invalid/*.pdsl`: invalid example programs.
- `tests/*.py`: layer-specific tests and CLI smoke tests.

---

### Task 1: Package skeleton and CLI smoke test

**Files:**
- Create: `pyproject.toml`
- Create: `polyforge/__init__.py`
- Create: `polyforge/__main__.py`
- Create: `polyforge/cli/__init__.py`
- Create: `polyforge/cli/main.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
import subprocess
import sys

def test_import_and_help():
    result = subprocess.run(
        [sys.executable, "-m", "polyforge", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "validate" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_smoke.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'polyforge'` or an equivalent missing-entry-point error.

- [ ] **Step 3: Write minimal implementation**

Create the package skeleton, add `project.scripts.polyforge = "polyforge.cli.main:main"` in `pyproject.toml`, add `polyforge/__main__.py` that forwards to `main()`, and implement a CLI stub that prints help for `validate`, `export`, `featurize`, and `train`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml polyforge tests/test_cli_smoke.py
git commit -m "feat: bootstrap PolyForge package and CLI"
```

### Task 2: Grammar, parser, and AST

**Files:**
- Create: `polyforge/grammar/polyforge.lark`
- Create: `polyforge/parser/parse.py`
- Create: `polyforge/parser/ast_builder.py`
- Create: `polyforge/ir/nodes.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

Add one valid PMMA fixture and one invalid fixture. Assert that parsing yields a `PolymerProgram` AST for the valid file and a syntax diagnostic for the invalid file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py -v`
Expected: fail because grammar, AST, or parser functions are missing.

- [ ] **Step 3: Write minimal implementation**

Implement the grammar for `polymer`, `monomer`, `architecture`, `sequence`, `molecular_weight`, `stereochemistry`, and `predict` blocks. Add typed dataclasses for `PolymerProgram`, `MonomerDef`, `SequenceExpr`, `MolecularWeight`, `Tacticity`, and `PropertyTarget`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/grammar/polyforge.lark polyforge/parser polyforge/ir tests/test_parser.py
git commit -m "feat: add PolyForge grammar and AST parsing"
```

### Task 3: Diagnostics, symbols, and semantic checker

**Files:**
- Create: `polyforge/check/diagnostics.py`
- Create: `polyforge/check/symbols.py`
- Create: `polyforge/check/semantics.py`
- Create: `tests/test_checker.py`

- [ ] **Step 1: Write the failing test**

Cover duplicate polymer names, duplicate monomer names, undefined monomer references, unsupported architecture, composition sums outside the 1e-6 tolerance, missing block DP, and reserved-keyword rejection.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_checker.py -v`
Expected: fail because checker functions and diagnostics types are missing.

- [ ] **Step 3: Write minimal implementation**

Implement structured diagnostics with `code`, `severity`, `message`, `file`, `line`, `column`, `path`, and `stage`. Add symbol resolution and semantic checks that enforce v0.1 rules only.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_checker.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/check tests/test_checker.py
git commit -m "feat: add PolyForge symbol and semantic checks"
```

### Task 4: RDKit chemistry validation

**Files:**
- Create: `polyforge/check/chemistry.py`
- Modify: `pyproject.toml`
- Create: `tests/test_chemistry.py`

- [ ] **Step 1: Write the failing test**

Test that valid monomer SMILES passes, invalid SMILES fails, and inferred attachment points produce a warning when inference is used.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chemistry.py -v`
Expected: fail because chemistry helpers are missing.

- [ ] **Step 3: Write minimal implementation**

Add RDKit parsing and sanitization, a conservative attachment plausibility check, and version recording for the RDKit minor version used during canonicalization.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chemistry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml polyforge/check/chemistry.py tests/test_chemistry.py
git commit -m "feat: add RDKit chemistry validation"
```

### Task 5: Canonicalization and canonical JSON

**Files:**
- Create: `polyforge/canonicalize/normalize.py`
- Create: `polyforge/canonicalize/hash.py`
- Create: `polyforge/canonicalize/json_ir.py`
- Create: `tests/test_canonicalize.py`

- [ ] **Step 1: Write the failing test**

Add tests for canonical ID format, stable hashing, unit normalization, explicit unknown preservation, provenance retention, sequence canonical forms, and idempotent round-trip canonicalization.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_canonicalize.py -v`
Expected: fail because canonicalization functions are missing.

- [ ] **Step 3: Write minimal implementation**

Implement canonical JSON output with `PolyForge:{schema_version}:sha256:{hex}` IDs, `structure_hash`, unit-suffixed numeric keys, and a dedicated provenance subobject.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_canonicalize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/canonicalize tests/test_canonicalize.py
git commit -m "feat: add canonical IR and hashing"
```

### Task 6: Exporters

**Files:**
- Create: `polyforge/emit/json.py`
- Create: `polyforge/emit/tokens.py`
- Create: `polyforge/emit/descriptors.py`
- Create: `polyforge/emit/bigsmiles.py`
- Create: `tests/test_exporters.py`

- [ ] **Step 1: Write the failing test**

Assert that JSON export matches the canonical IR, token export is deterministic, descriptor export is stable, and BigSMILES export obeys the support matrix.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exporters.py -v`
Expected: fail because emitter modules are missing.

- [ ] **Step 3: Write minimal implementation**

Make exporters consume only canonical IR. Reuse the same descriptor builder for `export --to descriptors` and `featurize`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exporters.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/emit tests/test_exporters.py
git commit -m "feat: add canonical exporters"
```

### Task 7: CLI command wiring

**Files:**
- Modify: `polyforge/cli/main.py`
- Create: `tests/test_cli_commands.py`

- [ ] **Step 1: Write the failing test**

Exercise `validate`, `export`, `featurize`, and `train` against example inputs and assert the expected exit codes and output files.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_commands.py -v`
Expected: fail because command dispatch is incomplete.

- [ ] **Step 3: Write minimal implementation**

Wire CLI subcommands to the parser, canonicalizer, exporters, featurizer, and trainer. Support `.pdsl` and canonical JSON inputs where the spec allows it.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_commands.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/cli tests/test_cli_commands.py
git commit -m "feat: wire PolyForge CLI commands"
```

### Task 8: Featurize pipeline

**Files:**
- Create: `polyforge/ml/featurize.py`
- Create: `tests/test_featurize.py`

- [ ] **Step 1: Write the failing test**

Verify that local `.pdsl` or canonical JSON inputs produce a CSV with the fixed prefix columns, deterministic descriptor order, and a target column when requested.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_featurize.py -v`
Expected: fail because the feature pipeline is missing.

- [ ] **Step 3: Write minimal implementation**

Build `featurize` on top of canonical IR and the shared descriptor builder. Support repeated `--input` and `--inputs-dir`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_featurize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/ml tests/test_featurize.py
git commit -m "feat: add PolyForge featurization pipeline"
```

### Task 9: Baseline training workflow

**Files:**
- Create: `polyforge/ml/models.py`
- Create: `polyforge/ml/train.py`
- Create: `tests/test_train.py`

- [ ] **Step 1: Write the failing test**

Verify the `mean`, `linear_regression`, and `random_forest` models, grouped 5-fold splitting by `structure_hash`, artifact creation, and failure on missing target columns.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_train.py -v`
Expected: fail because the training workflow is missing.

- [ ] **Step 3: Write minimal implementation**

Implement deterministic grouped cross-validation by default, optional `--split random`, and artifact outputs such as `metrics.json`, `model.joblib`, and `predictions.csv`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_train.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add polyforge/ml tests/test_train.py
git commit -m "feat: add PolyForge baseline training workflow"
```

### Task 10: Example corpus and README quickstart

**Files:**
- Create: `examples/pmma.pdsl`
- Create: `examples/random_copolymer.pdsl`
- Create: `examples/block_copolymer.pdsl`
- Create: `examples/invalid/duplicate_name.pdsl`
- Create: `examples/invalid/bad_composition.pdsl`
- Create: `examples/invalid/invalid_smiles.pdsl`
- Create: `tests/test_examples.py`
- Modify: `readme.md`

- [ ] **Step 1: Write the failing test**

Add a fixture test that verifies the example corpus matches the spec and that the invalid examples fail for the expected reasons.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_examples.py -v`
Expected: fail because the example corpus does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create the example programs and update the README with the CLI quickstart and links to the language spec and implementation plan.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_examples.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add examples readme.md tests/test_examples.py
git commit -m "docs: add PolyForge examples and quickstart"
```

## Non-goals for v0.1 implementation

- BigSMILES import
- graph export
- transformer/GNN training
- automatic dataset cleaning
- remote fetching or scraping
- inverse design generation
- benchmark claims beyond pipeline correctness

## Completion criteria

PolyForge v0.1 is ready to ship when:

- `polyforge validate` works on the example `.pdsl` corpus and canonical JSON
- `polyforge export` emits deterministic JSON, tokens, descriptors, and limited BigSMILES
- `polyforge featurize` produces a stable CSV contract from local files only
- `polyforge train` runs the three baseline models with grouped CV by default
- tests cover parser, checker, canonicalization, exporters, CLI, featurization, and training
