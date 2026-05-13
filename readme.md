# PolyForge

PolyForge is a typed polymer DSL and compiler for property prediction and inverse design.

## Docs

- [Language spec v0.1](docs/language_spec_v0.1.md)
- [Implementation plan](docs/superpowers/plans/2026-05-13-polyforge-v0.1-implementation-plan.md)
- [Research positioning](docs/research_positioning.md)
- [Compiler architecture](docs/compiler_architecture.md)
- [BigSMILES import and inverse design](docs/bigsmiles_inverse_design.md)

## v0.1 scope

- Linear homopolymers
- Linear random copolymers
- Linear alternating copolymers
- Linear block copolymers
- Basic molecular-weight metadata
- Basic tacticity metadata
- Property-target metadata
- Canonical JSON, token, descriptor, and limited BigSMILES export

## Quickstart

Validate a program:

```bash
python -m polyforge validate examples/pmma.pdsl
```

Export a canonical view:

```bash
python -m polyforge export examples/pmma.pdsl --to json
python -m polyforge export examples/pmma.pdsl --to tokens
python -m polyforge export examples/pmma.pdsl --to descriptors
python -m polyforge export examples/pmma.pdsl --to bigsmiles
```

Show the canonical IR schema:

```bash
python -m polyforge schema show v0.1
```

Build a feature table:

```bash
python -m polyforge featurize --input examples/pmma.pdsl --target Tg --out tg_features.csv
```

Train a baseline model:

```bash
python -m polyforge train tg_features.csv --model random_forest --run-dir runs/random_forest
```

## Out of scope for v0.1

- Branched and network polymers
- Gradient copolymers
- Morphology and crystallinity
- Full synthesis-route modeling
- Lossless BigSMILES import
- General inverse-design generation

The language spec is the source of truth for syntax and validation rules.
