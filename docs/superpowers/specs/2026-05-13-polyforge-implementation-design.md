# PolyForge v0.1 Implementation Design

Date: 2026-05-13
Status: approved design draft
Source of truth: `docs/language_spec_v0.1.md`

## 1. Goal

Implement PolyForge v0.1 as a compiler-first, CLI-first Python package that:

- parses `.pdsl` files
- validates linear polymer programs
- canonicalizes accepted programs into stable JSON IR
- exports JSON, token, descriptor, and limited BigSMILES views
- featurizes local `.pdsl` or canonical JSON inputs
- trains simple baseline ML models on the exported features

The implementation must stay aligned with the language specification. The spec defines syntax and semantics; the code implements them.

## 2. Confirmed scope

v0.1 includes:

- linear homopolymers
- linear random copolymers
- linear alternating copolymers
- linear block copolymers
- molecular-weight metadata
- tacticity metadata
- property-target metadata
- canonical JSON export
- token export
- descriptor export
- limited BigSMILES export
- `validate`, `export`, `featurize`, and `train` CLI commands
- baseline models: `mean`, `linear_regression`, `random_forest`

v0.1 does not include:

- BigSMILES import
- graph export
- network or branched polymers
- gradient copolymers
- automatic data cleaning
- remote dataset download
- transformer or GNN training
- inverse-design generation

## 3. Design principles

- Keep the IR stable and central.
- Make each layer depend only on the layer below it.
- Keep parser logic separate from chemistry logic.
- Keep emitters pure and deterministic.
- Keep ML code thin and downstream of canonicalization.
- Fail loudly on unsupported features rather than guessing.

## 4. Package layout

```text
polyforge/
  __init__.py
  cli/
    __init__.py
    main.py
  grammar/
    polyforge.lark
  parser/
    __init__.py
    parse.py
    ast_builder.py
  ir/
    __init__.py
    nodes.py
  check/
    __init__.py
    diagnostics.py
    symbols.py
    chemistry.py
    semantics.py
  canonicalize/
    __init__.py
    normalize.py
    hash.py
    json_ir.py
  emit/
    __init__.py
    json.py
    tokens.py
    descriptors.py
    bigsmiles.py
  ml/
    __init__.py
    featurize.py
    train.py
    models.py
examples/
tests/
docs/
```

The package name is lowercase `polyforge`. The CLI entry point is `polyforge`.

## 5. Dependencies

Use `pyproject.toml` and `uv`.

Core dependencies:

- `lark`
- `rdkit` pinned to a specific minor version in `pyproject.toml`
- `pandas`
- `numpy`
- `scikit-learn`
- `dataclasses` for core AST/IR objects
- `pydantic` only if CLI/config validation needs it
- `pytest` for tests

The implementation should avoid optional dependencies unless they are needed for a specific module.

## 6. Core data model

The code should expose typed internal objects for:

- `PolymerProgram`
- `MonomerDef`
- `Architecture`
- `SequenceExpr`
- `MolecularWeight`
- `Tacticity`
- `PropertyTarget`
- `CanonicalPolymer`
- `Diagnostic`

AST and IR may use `dataclasses` with explicit type hints. The canonical IR is the contract for exporters and ML features.

### 6.1 Canonical IR

Canonical JSON should include:

- `schema`
- `name`
- `monomers`
- `architecture`
- `sequence`
- `molecular_weight`
- `stereochemistry`
- `targets`
- `metadata`
- `canonical_id`
- `rdkit_version`
- `structure_hash`

Normalization rules:

- stable monomer IDs replace user-facing names
- ordered constructs preserve order
- unordered maps are sorted
- numeric units are normalized where unambiguous
- missing optional values become `null`
- explicitly unknown values remain explicit
- `canonical_id` is `PolyForge:{schema}:sha256:{hex}`
- the hash input is the canonical JSON serialization with UTF-8 encoding, sorted keys, no trailing newline, and without the `canonical_id` field itself
- `structure_hash` is a stable hash over the structural part of the canonical IR, excluding measurement-only metadata
- `rdkit_version` records the pinned RDKit minor version used for canonical chemistry normalization

### 6.2 Units and values

Canonical numeric fields should use explicit unit-suffixed keys.

Mandatory canonical unit mappings for v0.1:

- `Mn` -> `Mn_g_mol`
- `Mw` -> `Mw_g_mol`
- `DPn` -> `DPn`
- `heating_rate` -> `heating_rate_K_per_min`
- `pressure` -> `pressure_Pa`
- `temperature` -> `temperature_K`

Rules:

- canonical numeric fields use `{name}_{unit_snake}` when units are applicable
- strings such as `10 K/min` are only allowed in source syntax, not in canonical IR
- `predict` metadata should canonicalize into numeric values with unit-suffixed keys whenever a unit is known

### 6.3 Explicit unknowns and provenance

PolyForge must distinguish:

- omitted value
- explicit `unknown`
- inferred value

Suggested canonical representation:

- omitted value -> `null`
- explicit unknown -> `{"value": null, "explicit_unknown": true}`
- inferred value -> regular field plus provenance metadata

Provenance should be stored in a dedicated subobject, not encoded ad hoc per field.

Example:

```json
{
  "monomers": {
    "M0": {
      "attach": ["inferred"],
      "provenance": {
        "attach": "inferred"
      }
    }
  }
}
```

## 7. Pipeline

The main pipeline is:

```text
.pdsl source
  -> parse
  -> AST
  -> symbol resolution
  -> chemistry validation
  -> semantic validation
  -> canonicalization
  -> canonical IR

canonical JSON input
  -> schema load
  -> consistency check
  -> canonical IR

canonical IR
  -> export / featurize / train
```

### 7.1 Parser

Input: raw `.pdsl` text

Output: parse tree and syntax diagnostics

Responsibilities:

- load grammar
- produce line/column-aware syntax errors
- reject unknown top-level syntax
- do not perform chemistry checks

### 7.2 AST builder

Input: parse tree

Output: typed AST

Responsibilities:

- convert parse tree into dataclasses
- preserve source order
- keep raw field values available for later diagnostics

### 7.3 Symbol resolution

Input: AST

Output: diagnostics + resolved AST

Responsibilities:

- detect duplicate polymer or monomer names
- detect undefined monomer references in sequences and blocks
- protect reserved names and keywords

### 7.4 Chemistry validation

Input: resolved AST

Output: diagnostics

Responsibilities:

- parse monomer SMILES with RDKit
- reject invalid SMILES
- check attachment plausibility
- warn on inferred attachment points when inference is used
- keep chemistry checks limited to the supported v0.1 polymer classes

### 7.5 Semantic validation

Input: resolved AST

Output: diagnostics

Responsibilities:

- enforce linear architecture only
- enforce sequence rules
- enforce composition sum constraints
- enforce positive molecular-weight values
- enforce dispersity >= 1.0
- enforce positive block DPs
- accept optional metadata as `unknown` or missing

### 7.6 Canonicalization

Input: validated AST

Output: canonical IR

Responsibilities:

- canonicalize units
- normalize numeric fields
- assign stable internal IDs
- sort unordered maps
- preserve ordered constructs
- compute canonical hash

## 8. CLI contract

### 8.1 `validate`

Example:

```bash
polyforge validate examples/pmma.pdsl
```

Behavior:

- accept `.pdsl` or canonical JSON
- parse `.pdsl` files or load canonical JSON
- run all checks
- print diagnostics
- print canonical ID when validation succeeds
- reject canonical JSON whose `schema` version is unsupported
- exit 0 on success, nonzero on error

Warnings do not fail the command by default.

### 8.2 `export`

Example:

```bash
polyforge export examples/pmma.pdsl --to json
polyforge export examples/pmma.pdsl --to tokens
polyforge export examples/pmma.pdsl --to descriptors
polyforge export examples/pmma.pdsl --to bigsmiles
```

Behavior:

- accept `.pdsl` or canonical JSON
- canonicalize input first
- dispatch to a single exporter
- write to stdout or a target file
- fail loudly on unsupported input features

Supported `--to` values:

- `json`
- `tokens`
- `descriptors`
- `bigsmiles`

### 8.3 `featurize`

Example:

```bash
polyforge featurize dataset/*.pdsl --target Tg --out tg_features.csv
```

Behavior:

- accept only local `.pdsl` or canonical JSON inputs
- do not perform automatic scraping or cleaning
- canonicalize every input before feature generation
- emit one row per polymer
- include `canonical_id` and source metadata
- include target columns when present
- write a CSV with stable column names and deterministic column order
- support either repeated `--input` arguments or `--inputs-dir`; do not rely on shell glob expansion alone

Fixed CSV prefix columns:

- `canonical_id`
- `source_file`
- `source_format`
- `structure_hash`
- `target_property`
- `target_value`
- `target_units`

Descriptor columns must appear after the fixed prefix, sorted alphabetically.

### 8.4 `train`

Example:

```bash
polyforge train tg_features.csv --model random_forest
```

Behavior:

- read a local feature CSV only
- do not read `.pdsl` directly
- do not clean raw data automatically
- train a baseline model only
- use a deterministic grouped 5-fold cross-validation protocol by default
- group rows by `structure_hash`
- require `--split random` for plain random splits
- refit the chosen model on the full feature table after evaluation
- save metrics and model artifacts to a run directory

Supported models:

- `mean`
- `linear_regression`
- `random_forest`

Recommended metrics:

- MAE
- RMSE
- R2

Recommended artifacts:

- `metrics.json`
- `model.joblib`
- `predictions.csv`

Training should be deterministic where the model permits it.

## 9. Export behavior

### 9.1 JSON exporter

Outputs the canonical JSON IR.

Requirements:

- deterministic key ordering
- stable hash
- round-trippable from canonical IR

### 9.2 Token exporter

Outputs a stable token sequence derived from canonical IR.

Requirements:

- deterministic
- no hidden randomness
- stable ordering for equivalent polymers

### 9.3 Descriptor exporter

Outputs a flat numeric feature map.

Requirements:

- include chemical descriptors derived from monomer structures
- include polymer descriptors from the IR
- include measurement or target metadata where available
- avoid implicit imputation
- share the same feature builder as `featurize`

### 9.4 Limited BigSMILES exporter

Outputs a best-effort BigSMILES string for supported linear cases only.

Requirements:

- support only the v0.1 structural subset
- fail explicitly on unsupported cases
- do not pretend to be lossless
- use the following support matrix:

| sequence type | support | note |
| --- | --- | --- |
| homopolymer | yes | emit a single stochastic object |
| alternating copolymer | yes | emit a deterministic alternating structure |
| block copolymer | yes | emit ordered stochastic segments |
| random copolymer | conditional | emit only when composition is explicit; otherwise fail |

## 10. Diagnostics and errors

Diagnostics should be structured, not free-form text.

Recommended fields:

- `code`
- `severity`
- `message`
- `file`
- `line`
- `column`
- `path`
- `stage`

Severity levels:

- `error`
- `warning`
- `info`

Error classes:

- syntax errors
- semantic errors
- chemistry errors
- export errors
- ML input errors

Command behavior:

- parsing failures stop the pipeline
- validation should accumulate as many diagnostics as possible before failing
- warnings should not break normal validation

## 11. Testing strategy

Tests should follow the compiler layers.

### 11.1 Parser tests

- 10+ valid `.pdsl` fixtures
- 10+ invalid `.pdsl` fixtures
- line/column assertions for syntax failures

### 11.2 Checker tests

- one minimal failing case per rule
- duplicate name detection
- undefined reference detection
- composition sum failures
- invalid SMILES failures
- invalid architecture failures

### 11.3 Canonicalization tests

- identical logical inputs produce identical canonical JSON
- equivalent unit spellings normalize to the same canonical value
- hash stability across runs

### 11.4 Export tests

- JSON export matches canonical IR
- token export is stable
- descriptor export includes expected keys
- limited BigSMILES export fails on unsupported cases
- canonicalization is idempotent after JSON round-trip

### 11.5 CLI smoke tests

- `validate` on valid and invalid examples
- `export` for each backend
- `featurize` on local inputs
- `train` on a prepared feature CSV

### 11.6 ML tests

- baseline model selection
- metric calculation
- deterministic output with fixed random seed
- failure on missing target column or non-numeric target
- grouped split keeps identical `structure_hash` rows in the same fold

## 12. Repository inputs

The code should work against local files only.

Allowed inputs:

- `.pdsl`
- canonical JSON
- feature CSV produced by `featurize`

Not allowed in v0.1:

- automatic data cleaning
- remote downloads
- scraping
- networked dataset fetching

## 13. Milestones

### Milestone 1: Package skeleton

Deliverables:

- `pyproject.toml`
- `polyforge/` package skeleton
- CLI entry point
- basic test harness

### Milestone 2: Parser and AST

Deliverables:

- grammar file
- parser
- AST builder
- syntax tests

### Milestone 3: Symbol, chemistry, and semantic checks

Deliverables:

- symbol resolution
- RDKit validation
- semantic checker
- diagnostics model

### Milestone 4: Canonical IR

Deliverables:

- canonicalization
- hash generation
- canonical JSON export
- provenance tracking
- explicit unknown handling

### Milestone 5: Exporters

Deliverables:

- token exporter
- descriptor exporter
- limited BigSMILES exporter

### Milestone 6: Featurize and train

Deliverables:

- feature CSV generation
- baseline model training
- metrics and artifact outputs
- grouped cross-validation

## 14. Acceptance criteria

The implementation is acceptable when:

- the CLI can validate example `.pdsl` files
- the CLI can also validate canonical JSON inputs
- the canonical JSON output is deterministic
- the export backends are deterministic for the same canonical IR
- invalid programs fail with useful diagnostics
- the exporters consume canonical IR, not parser internals
- `featurize` and `train` work on local files without cleaning pipelines
- baseline training runs with the three supported models

## 15. Non-goals

v0.1 explicitly does not attempt to:

- replace BigSMILES
- import BigSMILES
- solve all polymer chemistry
- support all polymer architectures
- predict every property
- run inverse design
- build a general-purpose modeling platform

The first implementation should be small enough to finish and strict enough to trust.
