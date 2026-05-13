# BigSMILES Import and Inverse Design

BigSMILES should be treated as an interoperability target, not as the whole language. A PolyForge importer can recover some structural information from BigSMILES, but it should never pretend to recover fields that are not encoded.

## Import scope

Supported in the first version:

- Linear homopolymers
- Simple random copolymers
- Simple alternating copolymers
- Simple block copolymers when the structure is obvious

Not supported in v0.1:

- Branched polymers
- Network polymers
- Ambiguous stochastic objects
- Morphology
- Processing history
- Full synthesis routes

## Import behavior

The importer should have three modes:

- `strict`: reject anything that does not map cleanly
- `best_effort`: import the structural part and mark missing fields as `unknown`
- `annotated`: allow the user to add missing metadata manually

The key rule is that missing information must stay missing. If BigSMILES does not encode molecular weight distribution, tacticity, or processing context, PolyForge should not invent them.

## Inverse design

PolyForge can support inverse design if it is treated as a constrained design language:

`target -> generate -> validate -> featurize -> predict -> rank -> filter`

The validation stack should separate:

1. Syntax validity
2. Type validity
3. Chemical plausibility
4. Polymer semantic validity
5. Synthesizability filtering
6. Property prediction with uncertainty

That layered approach is better than claiming a single all-or-nothing notion of validity.

## Validity claim

Safe claim:

> PolyForge enables grammar-constrained and type-checked generation of polymer candidates, ensuring syntactic validity and enforcing supported semantic constraints.

Avoid claiming:

> PolyForge guarantees full real-world molecular or synthetic validity.

## Practical recommendation

For v0.1, implement limited BigSMILES import only after the parser, canonical IR, and export path are stable. Inverse design should come later, after the representation layer has been exercised on real examples.
