# Research Positioning and Feasibility

PolyForge is strongest when it is framed as a polymer representation system, not as a new polymer SMILES. BigSMILES, SELFIES, CRIPT-style data models, and polymer language-model work already cover important pieces of the space. The opportunity is to combine typing, validation, canonicalization, and compiler targets in one polymer-specific DSL.

The central hypothesis is simple: a typed polymer language can preserve information that repeat-unit-only representations often discard. That includes architecture, stochastic composition, molecular-weight metadata, tacticity, and measurement context. If that information is exposed to downstream models in a stable way, property prediction and inverse design should improve or at least become easier to evaluate fairly.

The novelty should therefore be claimed in three layers:

1. Formal semantics for supported polymer classes.
2. A compiler that emits multiple machine-readable representations.
3. Validation and canonicalization that make polymer data easier to compare, deduplicate, and featurize.

The main risk is scope creep. A universal polymer language is not a realistic v0.1 target. The right first paper is a narrow compiler prototype for linear polymers with good validation and clean interoperability. That keeps the project defensible and implementable.

Recommended positioning for the first version:

- Support linear homopolymers, random copolymers, alternating copolymers, and block copolymers.
- Treat BigSMILES as an export target, not a replacement target.
- Keep inverse design and network polymers out of scope until the representation layer is stable.

Bottom line: PolyForge can be a good research project if it is presented as a typed, compiler-based polymer representation layer with clear boundaries, not as a total replacement for existing notation systems.
