# PolyForge Language Specification v0.1

Status: draft

This document is the normative specification for the first PolyForge language release. It defines the supported syntax, semantic rules, validation behavior, and canonical IR for v0.1.

## 1. Scope

PolyForge v0.1 supports only linear polymers:

- linear homopolymers
- linear random copolymers
- linear alternating copolymers
- linear block copolymers

The language is designed for compiler use, not as a general-purpose programming language. It should be readable, typed, canonicalizable, and conservative about what it accepts.

## 2. Design principles

- Explicit over implicit
- Typed over free-form
- Canonical over ad hoc
- Interoperable over isolated
- Unknown values must remain unknown

## 3. Lexical conventions

- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`
- Strings: double quoted
- Numbers: decimal integers or floats
- Comments: `#` and `//`
- Whitespace is ignored except inside strings
- Keywords are case-sensitive

The literal `unknown` is reserved for optional metadata fields that are intentionally unset.

## 4. Top-level structure

```text
polymer NAME {
  monomer ...
  architecture: linear
  sequence: ...
  molecular_weight { ... }
  stereochemistry { ... }
  predict Tg { ... }
}
```

Each `polymer` definition must contain exactly one `architecture` statement and one `sequence` statement. Other blocks are optional.

## 5. Monomer definitions

Monomers describe the input chemical building blocks used by the polymer.

```text
monomer MMA {
  smiles: "C=C(C)C(=O)OC"
  polymerization: vinyl
  attach: inferred
}
```

### 5.1 Supported monomer fields

- `smiles`: required, parseable by RDKit
- `polymerization`: required, controlled vocabulary
- `attach`: optional, explicit or inferred attachment points

### 5.2 Supported polymerization kinds

- `vinyl`
- `step_growth`
- `ring_opening`

Other values are rejected in v0.1.

### 5.3 Attachment semantics

- `attach: inferred` is allowed only when the chemistry checker can infer a unique attachment pattern.
- Explicit attachment points are preferred.
- Attachment points must be chemically plausible and valence-consistent.
- If inference is used, the compiler must emit a warning and materialize the inferred sites in canonical IR.

## 6. Architecture

v0.1 supports only:

```text
architecture: linear
```

Any branched, network, or other non-linear architecture is out of scope for v0.1.

## 7. Sequence expressions

### 7.1 Homopolymer

```text
sequence: homopolymer(MMA)
```

Rules:

- references exactly one defined monomer
- monomer must be compatible with the declared polymerization and architecture

### 7.2 Random copolymer

```text
sequence: random_copolymer {
  units: [MMA, BA]
  composition: {MMA: 0.70, BA: 0.30}
}
```

Rules:

- at least two units
- all referenced units must be defined
- composition fractions must sum to 1.0 within a small numeric tolerance
- all fractions must be non-negative

### 7.3 Alternating copolymer

```text
sequence: alternating_copolymer(MMA, BA)
```

Rules:

- exactly two defined monomers
- the order is significant only in the sense of alternation

### 7.4 Block copolymer

```text
sequence: block_copolymer {
  blocks: [
    block(Styrene, DP=100),
    block(MMA, DP=80)
  ]
}
```

Rules:

- block order is significant
- each block must reference a defined monomer
- each block must have a positive `DP`
- the list must contain at least two blocks

## 8. Molecular-weight metadata

```text
molecular_weight {
  Mn: 120000 g/mol
  dispersity: 1.6
  distribution: lognormal
}
```

### 8.1 Supported fields

- `Mn`
- `Mw`
- `DPn`
- `dispersity`
- `distribution`

### 8.2 Semantic rules

- `Mn`, `Mw`, and `DPn` must be positive
- `dispersity` must be greater than or equal to 1.0
- numeric values must be normalized to canonical units
- `distribution` is optional and may be `unknown`

## 9. Stereochemistry metadata

```text
stereochemistry {
  tacticity: atactic
}
```

### 9.1 Supported tacticity values

- `atactic`
- `isotactic`
- `syndiotactic`
- `unknown`

## 10. Property-target block

```text
predict Tg {
  method: DSC
  heating_rate: 10 K/min
  pressure: 1 atm
  sample_state: amorphous
}
```

The `predict` block stores target and measurement context. It is optional and does not affect structural validity.

### 10.1 Recommended keys

- `method`
- `temperature`
- `pressure`
- `heating_rate`
- `sample_state`
- `value`
- `units`

Additional keys are allowed if they are valid key-value pairs.

## 11. Semantic validation rules

The compiler must enforce the following:

| Rule | Severity |
| --- | --- |
| Polymer name must be unique within a file | Error |
| Monomer names must be unique within a polymer | Error |
| Referenced monomers must exist | Error |
| SMILES must parse successfully | Error |
| Architecture must be linear | Error |
| Composition fractions must sum to 1.0 | Error |
| Block DPs must be positive | Error |
| `Mn`, `Mw`, `DPn` must be positive | Error |
| `dispersity` must be >= 1.0 | Error |
| Attachment inference must be unambiguous | Error or warning, depending on the case |
| Missing but optional metadata may be `unknown` | Warning or accepted null |

The checker should distinguish syntax errors, semantic errors, chemistry errors, and warnings.

## 12. Canonical IR

The canonical IR is a normalized JSON object. It is the source of truth for exporters and tests.

```json
{
  "schema": "polyforge.v0.1",
  "name": "PMMA",
  "monomers": {
    "M0": {
      "original_name": "MMA",
      "canonical_smiles": "COC(=O)C(C)=C",
      "polymerization": "vinyl",
      "attach": ["inferred"]
    }
  },
  "architecture": "linear",
  "sequence": {
    "type": "homopolymer",
    "monomer": "M0"
  },
  "molecular_weight": {
    "Mn_g_mol": 120000.0,
    "dispersity": 1.6,
    "distribution": "lognormal"
  },
  "stereochemistry": {
    "tacticity": "atactic"
  },
  "targets": [
    {
      "property": "Tg",
      "method": "DSC",
      "heating_rate": "10 K/min",
      "pressure": "1 atm",
      "sample_state": "amorphous"
    }
  ],
  "metadata": {},
  "canonical_id": "PolyForge:v0.1:sha256:..."
}
```

### 12.1 Canonicalization rules

- Replace user-facing monomer names with stable internal IDs
- Preserve ordered constructs such as block order
- Sort unordered mappings by canonical key
- Normalize numeric units before hashing
- Represent missing optional values as `null` in canonical JSON
- Compute a stable hash over the canonical JSON serialization

### 12.2 Provenance

If a value was inferred, the canonical IR should retain that fact in the relevant field or metadata. Inference must not be silently lost.

## 13. Export contract

The following outputs are valid derivations from the canonical IR:

- Canonical JSON
- Token sequence
- Descriptor vector
- Limited BigSMILES export for supported linear cases

Exports must be deterministic for identical canonical IR input.

## 14. Examples

### 14.1 Homopolymer

```text
polymer PMMA {
  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
    attach: inferred
  }

  architecture: linear
  sequence: homopolymer(MMA)

  molecular_weight {
    Mn: 120000 g/mol
    dispersity: 1.6
    distribution: lognormal
  }

  stereochemistry {
    tacticity: atactic
  }

  predict Tg {
    method: DSC
    heating_rate: 10 K/min
    sample_state: amorphous
  }
}
```

### 14.2 Random copolymer

```text
polymer P_MMA_BA_random {
  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
    attach: inferred
  }

  monomer BA {
    smiles: "C=CC(=O)OCCCC"
    polymerization: vinyl
    attach: inferred
  }

  architecture: linear
  sequence: random_copolymer {
    units: [MMA, BA]
    composition: {MMA: 0.70, BA: 0.30}
  }

  molecular_weight {
    Mn: 80000 g/mol
    dispersity: 2.1
  }
}
```

### 14.3 Block copolymer

```text
polymer PS_b_PMMA {
  monomer Styrene {
    smiles: "C=CC1=CC=CC=C1"
    polymerization: vinyl
    attach: inferred
  }

  monomer MMA {
    smiles: "C=C(C)C(=O)OC"
    polymerization: vinyl
    attach: inferred
  }

  architecture: linear
  sequence: block_copolymer {
    blocks: [
      block(Styrene, DP=100),
      block(MMA, DP=80)
    ]
  }

  molecular_weight {
    Mn: 25000 g/mol
    dispersity: 1.2
  }
}
```

## 15. Unsupported features

Out of scope for v0.1:

- Branched polymers
- Network polymers
- Gradient copolymers
- Supramolecular assemblies
- Morphology and crystallinity
- Full reaction-mechanism modeling
- Full synthesis-route validation
- Lossless BigSMILES decompilation
- Sequence Markov models beyond composition metadata

## 16. Error reporting

Error messages should include:

- file name
- line and column when available
- block or field name
- a concrete fix when possible

Warnings should be explicit and should never be confused with accepted validation.

## 17. Normative summary

v0.1 is intentionally narrow. A valid PolyForge program must be syntactically well-formed, type-correct, chemically plausible for its supported subset, and canonicalizable into a stable JSON IR.
