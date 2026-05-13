# Compiler Architecture

PolyForge should be organized as a language-plus-compiler stack:

`source -> parser -> AST -> symbol table -> chemical checker -> semantic checker -> canonicalizer -> IR -> exporters -> ML features`

The most important design choice is the canonical intermediate representation. The surface syntax can change later, but the IR should remain stable and become the contract for exporters, tests, and ML pipelines.

## Core pipeline

1. Parse the source file into a syntax tree.
2. Build typed AST nodes.
3. Resolve names and catch duplicates or undefined references.
4. Validate monomer chemistry with RDKit.
5. Check polymer-level semantics such as composition and block order.
6. Canonicalize units, names, ordering, and numeric forms.
7. Emit a stable JSON IR.
8. Derive token, descriptor, and BigSMILES views from the IR.

## IR contract

The IR should capture:

- Polymer name
- Monomer definitions
- Architecture
- Sequence model
- Molecular-weight metadata
- Tacticity metadata
- Property-target metadata
- Provenance and canonical hash

The IR should also preserve unknown values explicitly rather than inventing defaults.

## Export targets

The practical first exports are:

- Canonical JSON for storage and testing
- Token sequences for transformer-style models
- Descriptor vectors for classical ML
- Limited BigSMILES for supported linear cases

Graph export is useful later, but it does not need to be a v0.1 requirement if it slows the core parser and validator work.

## Suggested repository layout

```text
PolyForge/
  docs/
  PolyForge/
    grammar/
    ir/
    chemistry/
    emitters/
    ml/
    tests/
```

## Milestone order

1. Write example `.pdsl` files.
2. Write the grammar.
3. Parse valid and invalid examples.
4. Build AST nodes.
5. Add symbol resolution.
6. Add chemistry and semantic checks.
7. Add canonical JSON export.
8. Add descriptors and tokens.
9. Add limited BigSMILES export.
10. Add a small ML baseline.

This order keeps the representation stable before any model work starts.
