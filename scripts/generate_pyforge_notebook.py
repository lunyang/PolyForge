from __future__ import annotations

import json
from pathlib import Path


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip().splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


NOTEBOOK = {
    "cells": [
        markdown(
            """
            # PolyForge Case Study: Typed Polymer Programs for Prediction and Inverse Design

            This notebook is a complete, English-language case study for PolyForge. It demonstrates the polymer DSL syntax, compiler validation, canonical IR, property-prediction benchmarks, LLM-generated program evaluation, compiler-feedback repair, constrained inverse-design ranking, and publication-quality figure export.

            The figures use an ACS/RSC-style layout and are exported as high-resolution PNG plus vector PDF/SVG files.
            """
        ),
        markdown(
            """
            ## 1. Environment and output paths

            The notebook writes all derived artifacts to `runs/notebook_case_study/`. Live LLM calls are intentionally excluded; the LLM section replays saved outputs from `experiments/fixtures/llm_outputs/`.
            """
        ),
        code(
            """
            from pathlib import Path
            import json
            import pandas as pd
            from IPython.display import Image, display

            from experiments.notebook_case_study import (
                DEFAULT_RUN_DIR,
                INVALID_EXAMPLE,
                INVERSE_DESIGN_SOURCES,
                SYNTAX_EXAMPLES,
                canonical_summary,
                compile_pdsl,
                compile_syntax_examples,
                evaluate_llm_fixtures,
                export_summary,
                make_repair_demo,
                prepare_output_dirs,
                render_all_figures,
                run_dataset_and_benchmark,
                score_inverse_design_candidates,
                set_publication_style,
            )

            paths = prepare_output_dirs(DEFAULT_RUN_DIR)
            set_publication_style()
            paths
            """
        ),
        markdown(
            """
            ## 2. PolyForge syntax walkthrough

            A PolyForge program declares a polymer, one or more monomer definitions, a supported architecture, a sequence model, optional molecular metadata, and optional property targets. The examples below cover a homopolymer, a random copolymer, and a block copolymer.
            """
        ),
        code(
            """
            print(SYNTAX_EXAMPLES["homopolymer"])
            """
        ),
        code(
            """
            print(SYNTAX_EXAMPLES["random_copolymer"])
            """
        ),
        code(
            """
            print(SYNTAX_EXAMPLES["block_copolymer"])
            """
        ),
        markdown(
            """
            ## 3. Compiler pipeline: diagnostics, canonical IR, and provenance

            The compiler pipeline converts source programs into a stable canonical IR. Diagnostics expose syntax, semantic, and chemistry failures instead of letting invalid LLM output silently enter downstream modeling.
            """
        ),
        code(
            """
            compiled = compile_syntax_examples(paths["pdsl"])
            pmma_ir = compiled["homopolymer"]["canonical_ir"]
            canonical_summary(pmma_ir)
            """
        ),
        code(
            """
            invalid = compile_pdsl("invalid_composition_demo", INVALID_EXAMPLE, paths["pdsl"])
            invalid["diagnostics"]
            """
        ),
        markdown(
            """
            ## 4. Export targets

            PolyForge emits several machine-readable views from the same canonical IR. This keeps downstream prediction and inverse-design workflows tied to one stable compiler contract.
            """
        ),
        code(
            """
            export_summary(pmma_ir)
            """
        ),
        markdown(
            """
            ## 5. Dataset audit and Tg prediction benchmark

            The Tg benchmark uses `bigsmiles-Tg.csv`. The file is Latin-1 encoded and contains 304 Tg measurements. Splits are grouped by stable structure keys rather than polymer names.
            """
        ),
        code(
            """
            dataset_result = run_dataset_and_benchmark(paths)
            pd.DataFrame([dataset_result["audit"]])
            """
        ),
        code(
            """
            benchmark_metrics = pd.read_csv(paths["tables"] / "benchmark_metrics.csv")
            benchmark_metrics.sort_values("mae")
            """
        ),
        markdown(
            """
            ## 6. LLM-generated PolyForge programs

            The LLM section uses fixture outputs. The evaluator extracts `.pdsl` blocks, runs PolyForge validation, and reports pass rates across parse, semantic, chemistry, and canonicalization stages.
            """
        ),
        code(
            """
            llm_metrics = evaluate_llm_fixtures(paths)
            pd.DataFrame([llm_metrics])
            """
        ),
        markdown(
            """
            ## 7. Compiler-feedback repair prompt

            Invalid LLM output is not manually edited in the reported workflow. Instead, PolyForge diagnostics are converted into repair prompts that ask the LLM to return corrected PolyForge source.
            """
        ),
        code(
            """
            repair_demo = make_repair_demo(paths)
            print("\\n".join(repair_demo["diagnostics"]))
            print("\\n--- Repair prompt preview ---\\n")
            print(repair_demo["repair_prompt"][:1200])
            """
        ),
        markdown(
            """
            ## 8. Constrained inverse design

            Candidate polymers are generated as `.pdsl`, validated by PolyForge, converted to BigSMILES features, scored by the Tg model, and ranked against a target window. The example target window is 320-400 K.
            """
        ),
        code(
            """
            print("\\n\\n---\\n\\n".join(INVERSE_DESIGN_SOURCES.values()))
            """
        ),
        code(
            """
            inverse_ranked = score_inverse_design_candidates(paths, target_low=320.0, target_high=400.0)
            inverse_ranked[["polymer_name", "sequence_type", "predicted_tg_k", "target_hit", "novel", "rank_score"]]
            """
        ),
        markdown(
            """
            ## 9. Publication figure export

            The following cell exports four ACS/RSC-style figures as PNG, PDF, and SVG files and displays them inline. Figure 1 combines the compiler workflow with RDKit-rendered polymer repeat-unit structures.
            """
        ),
        code(
            """
            figure_paths = render_all_figures(paths, dataset_result, llm_metrics, inverse_ranked)
            for figure_path in figure_paths:
                display(Image(filename=str(figure_path), width=900))
            figure_paths
            """
        ),
        markdown(
            """
            ## 10. Result tables and manifest

            The notebook exports dataset audit, benchmark metrics, LLM metrics, inverse-design rankings, and a manifest file under `runs/notebook_case_study/`.
            """
        ),
        code(
            """
            manifest = {
                "run_dir": str(paths["run"]),
                "figures": sorted(str(path) for path in paths["figures"].glob("*")),
                "tables": sorted(str(path) for path in paths["tables"].glob("*")),
                "benchmark_artifacts": sorted(str(path) for path in paths["benchmark"].glob("*")),
                "repair_prompt": str(paths["run"] / "repair_prompt.txt"),
            }
            (paths["run"] / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            manifest
            """
        ),
        markdown(
            """
            ## 11. Claim boundaries

            PolyForge validates syntax, supported polymer semantics, canonical IR schema contracts, and basic RDKit chemistry. The Tg predictor in this notebook is a demonstration baseline. The inverse-design section ranks model-scored candidates; it does not claim experimental synthesizability or experimentally measured Tg.
            """
        ),
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3 (LLM)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main() -> None:
    Path("PyForge.ipynb").write_text(json.dumps(NOTEBOOK, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
