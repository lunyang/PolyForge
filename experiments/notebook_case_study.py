from __future__ import annotations

import hashlib
import json
from pathlib import Path
from textwrap import dedent
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from rdkit import Chem
from rdkit import RDLogger
from rdkit.Chem import Draw

from experiments.inverse_design.rank import rank_candidates
from experiments.llm_generation.evaluate import evaluate_saved_llm_outputs
from experiments.llm_generation.repair import make_repair_prompt
from experiments.tg_benchmark.benchmark import run_tg_benchmark
from experiments.tg_benchmark.dataset import audit_dataset, load_bigsmiles_tg_csv
from experiments.tg_benchmark.features import make_bigsmiles_char_features
from polyforge.emit.bigsmiles import export_bigsmiles
from polyforge.emit.descriptors import descriptor_row
from polyforge.emit.json import export_json
from polyforge.emit.tokens import token_sequence
from polyforge.ml.models import make_estimator
from polyforge.pipeline import format_diagnostic, load_source

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "runs" / "notebook_case_study"
DATASET_PATH = ROOT / "bigsmiles-Tg.csv"
RDLogger.DisableLog("rdApp.error")

ACS_COLORS = {
    "blue": "#2f6f9f",
    "teal": "#2f8f83",
    "orange": "#d17a22",
    "red": "#b54a4a",
    "gray": "#4d4d4d",
    "light_gray": "#e6e6e6",
}

SYNTAX_EXAMPLES = {
    "homopolymer": dedent(
        """
        polymer PMMA_demo {
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
        """
    ).strip(),
    "random_copolymer": dedent(
        """
        polymer MMA_BA_random_demo {
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
        }
        """
    ).strip(),
    "block_copolymer": dedent(
        """
        polymer PS_b_PMMA_demo {
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
        }
        """
    ).strip(),
}

INVALID_EXAMPLE = dedent(
    """
    polymer InvalidCompositionDemo {
      monomer MMA {
        smiles: "C=C(C)C(=O)OC"
        polymerization: vinyl
      }
      monomer BA {
        smiles: "C=CC(=O)OCCCC"
        polymerization: vinyl
      }
      architecture: linear
      sequence: random_copolymer {
        units: [MMA, BA]
        composition: {MMA: 0.70, BA: 0.20}
      }
    }
    """
).strip()

INVERSE_DESIGN_SOURCES = {
    "BA_low_Tg_candidate": dedent(
        """
        polymer BA_low_Tg_candidate {
          monomer BA {
            smiles: "C=CC(=O)OCCCC"
            polymerization: vinyl
            attach: inferred
          }
          architecture: linear
          sequence: homopolymer(BA)
        }
        """
    ).strip(),
    "MMA_BA_mid_Tg_candidate": dedent(
        """
        polymer MMA_BA_mid_Tg_candidate {
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
            composition: {MMA: 0.60, BA: 0.40}
          }
        }
        """
    ).strip(),
    "PS_PMMA_high_Tg_candidate": dedent(
        """
        polymer PS_PMMA_high_Tg_candidate {
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
              block(Styrene, DP=120),
              block(MMA, DP=60)
            ]
          }
        }
        """
    ).strip(),
}


def prepare_output_dirs(run_dir: str | Path = DEFAULT_RUN_DIR) -> dict[str, Path]:
    run_path = Path(run_dir)
    paths = {
        "run": run_path,
        "figures": run_path / "figures",
        "tables": run_path / "tables",
        "pdsl": run_path / "pdsl",
        "benchmark": run_path / "benchmark",
        "llm": run_path / "llm_generation",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def set_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.2,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def compile_pdsl(name: str, source: str, pdsl_dir: str | Path) -> dict[str, Any]:
    pdsl_path = Path(pdsl_dir) / f"{name}.pdsl"
    pdsl_path.write_text(source, encoding="utf-8")
    artifact = load_source(pdsl_path)
    return {
        "path": pdsl_path,
        "artifact": artifact,
        "diagnostics": [format_diagnostic(diagnostic) for diagnostic in artifact.diagnostics],
        "canonical_ir": artifact.canonical_ir,
    }


def compile_syntax_examples(pdsl_dir: str | Path) -> dict[str, dict[str, Any]]:
    return {name: compile_pdsl(name, source, pdsl_dir) for name, source in SYNTAX_EXAMPLES.items()}


def canonical_summary(canonical_ir: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"field": "schema", "value": canonical_ir["schema"]},
            {"field": "name", "value": canonical_ir["name"]},
            {"field": "canonical_id", "value": canonical_ir["canonical_id"]},
            {"field": "structure_hash", "value": canonical_ir["structure_hash"]},
            {"field": "architecture", "value": canonical_ir["architecture"]},
            {"field": "sequence_type", "value": canonical_ir["sequence"]["type"]},
            {"field": "rdkit_version", "value": canonical_ir["rdkit_version"]},
        ]
    )


def export_summary(canonical_ir: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"export": "canonical_json", "preview": export_json(canonical_ir)[:160] + "..."},
            {"export": "tokens", "preview": " ".join(token_sequence(canonical_ir)[:18]) + " ..."},
            {"export": "descriptors", "preview": json.dumps(descriptor_row(canonical_ir), sort_keys=True)[:160] + "..."},
            {"export": "limited_bigsmiles", "preview": export_bigsmiles(canonical_ir)},
        ]
    )


def run_dataset_and_benchmark(paths: dict[str, Path]) -> dict[str, Any]:
    dataset = load_bigsmiles_tg_csv(DATASET_PATH)
    audit = audit_dataset(dataset.frame)
    benchmark = run_tg_benchmark(
        dataset_path=DATASET_PATH,
        output_dir=paths["benchmark"],
        representations=["bigsmiles_char", "smiles_rdkit"],
        models=["mean", "linear_regression", "random_forest"],
        n_splits=5,
        seed=13,
    )
    pd.DataFrame([audit]).to_csv(paths["tables"] / "dataset_audit.csv", index=False)
    pd.DataFrame(benchmark["runs"]).to_csv(paths["tables"] / "benchmark_metrics.csv", index=False)
    return {"dataset": dataset, "audit": audit, "benchmark": benchmark}


def evaluate_llm_fixtures(paths: dict[str, Path]) -> dict[str, Any]:
    metrics = evaluate_saved_llm_outputs(ROOT / "experiments" / "fixtures" / "llm_outputs", paths["llm"])
    pd.DataFrame([metrics]).to_csv(paths["tables"] / "llm_generation_metrics.csv", index=False)
    return metrics


def score_inverse_design_candidates(paths: dict[str, Path], target_low: float = 320.0, target_high: float = 400.0) -> pd.DataFrame:
    dataset = load_bigsmiles_tg_csv(DATASET_PATH)
    training_features = make_bigsmiles_char_features(dataset.frame)
    estimator = make_estimator("random_forest", random_state=13)
    estimator.fit(training_features.frame[training_features.feature_columns], training_features.frame["tg_k"])

    candidate_rows: list[dict[str, Any]] = []
    for name, source in INVERSE_DESIGN_SOURCES.items():
        compiled = compile_pdsl(name, source, paths["pdsl"])
        canonical_ir = compiled["canonical_ir"]
        if canonical_ir is None:
            continue
        bigsmiles = export_bigsmiles(canonical_ir)
        smiles = ";".join(monomer["canonical_smiles"] for monomer in canonical_ir["monomers"].values())
        candidate_rows.append(
            {
                "row_index": len(candidate_rows),
                "polymer_name": name,
                "smiles": smiles,
                "bigsmiles": bigsmiles,
                "tg_k": np.nan,
                "structure_key": _structure_key(smiles, bigsmiles),
                "canonical_id": canonical_ir["canonical_id"],
                "sequence_type": canonical_ir["sequence"]["type"],
            }
        )

    candidate_frame = pd.DataFrame(candidate_rows)
    candidate_features = make_bigsmiles_char_features(candidate_frame)
    predictions = estimator.predict(candidate_features.frame[training_features.feature_columns])
    candidate_frame["predicted_tg_k"] = predictions
    ranked = rank_candidates(
        candidate_frame.to_dict(orient="records"),
        target_low=target_low,
        target_high=target_high,
        training_structure_keys=set(dataset.frame["structure_key"]),
    )
    ranked_frame = pd.DataFrame(ranked)
    ranked_frame.to_csv(paths["tables"] / "inverse_design_top_candidates.csv", index=False)
    return ranked_frame


def make_repair_demo(paths: dict[str, Path]) -> dict[str, Any]:
    compiled = compile_pdsl("invalid_composition_demo", INVALID_EXAMPLE, paths["pdsl"])
    prompt = make_repair_prompt(INVALID_EXAMPLE, compiled["diagnostics"])
    repair_path = paths["run"] / "repair_prompt.txt"
    repair_path.write_text(prompt, encoding="utf-8")
    return {"diagnostics": compiled["diagnostics"], "repair_prompt": prompt, "path": repair_path}


def render_all_figures(paths: dict[str, Path], dataset_result: dict[str, Any], llm_metrics: dict[str, Any], inverse_ranked: pd.DataFrame) -> list[Path]:
    set_publication_style()
    figures = [
        _figure_workflow_and_structures(paths),
        _figure_dataset(paths, dataset_result),
        _figure_prediction(paths, paths["benchmark"]),
        _figure_llm_and_inverse_design(paths, llm_metrics, inverse_ranked),
    ]
    return figures


def run_case_study(run_dir: str | Path = DEFAULT_RUN_DIR) -> dict[str, Any]:
    paths = prepare_output_dirs(run_dir)
    examples = compile_syntax_examples(paths["pdsl"])
    dataset_result = run_dataset_and_benchmark(paths)
    llm_metrics = evaluate_llm_fixtures(paths)
    inverse_ranked = score_inverse_design_candidates(paths)
    repair_demo = make_repair_demo(paths)
    figures = render_all_figures(paths, dataset_result, llm_metrics, inverse_ranked)
    manifest = {
        "run_dir": str(paths["run"]),
        "figures": [str(path) for path in figures],
        "tables": sorted(str(path) for path in paths["tables"].glob("*")),
        "benchmark_artifacts": sorted(str(path) for path in paths["benchmark"].glob("*")),
        "example_canonical_ids": {
            name: result["canonical_ir"]["canonical_id"]
            for name, result in examples.items()
            if result["canonical_ir"] is not None
        },
        "repair_prompt": str(repair_demo["path"]),
    }
    (paths["run"] / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def _figure_workflow_and_structures(paths: dict[str, Path]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [0.95, 1.35]})
    ax = axes[0]
    ax.axis("off")
    steps = [
        "Natural-language intent",
        "LLM-generated .pdsl",
        "PolyForge compiler",
        "Canonical IR and exports",
        "Tg model and ranking",
    ]
    y_positions = np.linspace(0.82, 0.18, len(steps))
    for index, (y, label) in enumerate(zip(y_positions, steps, strict=True)):
        box = FancyBboxPatch(
            (0.12, y - 0.055),
            0.76,
            0.11,
            boxstyle="round,pad=0.015,rounding_size=0.012",
            fc="#f7f7f7",
            ec=ACS_COLORS["gray"],
            lw=0.8,
            transform=ax.transAxes,
        )
        ax.add_patch(box)
        ax.text(0.50, y, label, ha="center", va="center", fontsize=7.2, transform=ax.transAxes)
        if index < len(steps) - 1:
            ax.annotate(
                "",
                xy=(0.50, y_positions[index + 1] + 0.07),
                xytext=(0.50, y - 0.07),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops={"arrowstyle": "->", "lw": 0.8, "color": ACS_COLORS["gray"]},
            )
    ax.text(0.0, 0.98, "a", transform=ax.transAxes, fontweight="bold", fontsize=10, va="top")
    ax.set_title("Compiler-mediated LLM polymer design")

    ax = axes[1]
    ax.axis("off")
    structure_data = [
        ("PMMA repeat unit", "[*]CC(C)(C(=O)OC)[*]"),
        ("PBA repeat unit", "[*]CC(C(=O)OCCCC)[*]"),
        ("PS repeat unit", "[*]CC(C1=CC=CC=C1)[*]"),
    ]
    for idx, (name, smiles) in enumerate(structure_data):
        mol = Chem.MolFromSmiles(smiles)
        image = Draw.MolToImage(mol, size=(520, 210))
        inset = ax.inset_axes([0.00, 0.66 - idx * 0.30, 0.58, 0.25])
        inset.imshow(image)
        inset.axis("off")
        ax.text(0.62, 0.79 - idx * 0.30, name, transform=ax.transAxes, va="center", fontsize=8)
    ax.text(0.0, 0.98, "b", transform=ax.transAxes, fontweight="bold", fontsize=10, va="top")
    ax.set_title("Representative polymer repeat-unit structures")
    return _save_figure(fig, paths["figures"], "figure_1_workflow_structures")


def _figure_dataset(paths: dict[str, Path], dataset_result: dict[str, Any]) -> Path:
    dataset = dataset_result["dataset"]
    audit = dataset_result["audit"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axes[0]
    ax.hist(dataset.frame["tg_k"], bins=24, color=ACS_COLORS["blue"], edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Experimental Tg (K)")
    ax.set_ylabel("Count")
    ax.set_title("Tg distribution")
    ax.text(-0.14, 1.05, "a", transform=ax.transAxes, fontweight="bold", fontsize=10)

    ax = axes[1]
    labels = ["Rows", "Unique\nnames", "Dup.\nSMILES", "Dup.\nBigSMILES"]
    values = [audit["rows"], audit["unique_polymer_names"], audit["duplicate_smiles"], audit["duplicate_bigsmiles"]]
    colors = [ACS_COLORS["teal"], ACS_COLORS["teal"], ACS_COLORS["orange"], ACS_COLORS["orange"]]
    ax.bar(labels, values, color=colors)
    ax.set_ylabel("Count")
    ax.set_title("Dataset audit")
    ax.text(-0.14, 1.05, "b", transform=ax.transAxes, fontweight="bold", fontsize=10)
    return _save_figure(fig, paths["figures"], "figure_2_dataset_audit")


def _figure_prediction(paths: dict[str, Path], benchmark_dir: Path) -> Path:
    metrics = pd.DataFrame(json.loads((benchmark_dir / "metrics.json").read_text(encoding="utf-8"))["runs"])
    predictions = pd.read_csv(benchmark_dir / "predictions.csv")
    selected = predictions[(predictions["representation"] == "bigsmiles_char") & (predictions["model"] == "random_forest")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    ax = axes[0]
    ax.scatter(selected["tg_k"], selected["prediction"], s=16, alpha=0.72, color=ACS_COLORS["blue"], edgecolor="white", linewidth=0.2)
    limits = [min(selected["tg_k"].min(), selected["prediction"].min()), max(selected["tg_k"].max(), selected["prediction"].max())]
    ax.plot(limits, limits, color=ACS_COLORS["gray"], lw=0.8, ls="--")
    ax.set_xlabel("Experimental Tg (K)")
    ax.set_ylabel("Predicted Tg (K)")
    ax.set_title("Random forest parity")
    ax.text(-0.14, 1.05, "a", transform=ax.transAxes, fontweight="bold", fontsize=10)

    ax = axes[1]
    metrics["label"] = metrics["representation"].str.replace("_", " ") + "\n" + metrics["model"].str.replace("_", " ")
    metrics_sorted = metrics.sort_values("mae")
    ax.barh(metrics_sorted["label"], metrics_sorted["mae"], color=ACS_COLORS["teal"])
    ax.set_xlabel("MAE (K)")
    ax.set_title("Benchmark comparison")
    ax.invert_yaxis()
    ax.text(-0.14, 1.05, "b", transform=ax.transAxes, fontweight="bold", fontsize=10)
    return _save_figure(fig, paths["figures"], "figure_3_tg_prediction")


def _figure_llm_and_inverse_design(paths: dict[str, Path], llm_metrics: dict[str, Any], inverse_ranked: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    ax = axes[0]
    stages = ["Generated", "Parsed", "Semantic", "Chemistry", "Canonical"]
    total = llm_metrics["total_candidates"]
    values = [
        total,
        total * llm_metrics["parse_pass_rate"],
        total * llm_metrics["semantic_pass_rate"],
        total * llm_metrics["chemistry_pass_rate"],
        total * llm_metrics["canonicalization_pass_rate"],
    ]
    ax.bar(stages, values, color=[ACS_COLORS["blue"], ACS_COLORS["blue"], ACS_COLORS["teal"], ACS_COLORS["teal"], ACS_COLORS["orange"]])
    ax.set_ylabel("Candidate count")
    ax.set_title("LLM validity funnel")
    ax.tick_params(axis="x", rotation=25)
    ax.text(-0.14, 1.05, "a", transform=ax.transAxes, fontweight="bold", fontsize=10)

    ax = axes[1]
    plot_data = inverse_ranked.sort_values("rank_score")
    colors = [ACS_COLORS["teal"] if hit else ACS_COLORS["orange"] for hit in plot_data["target_hit"]]
    ax.barh(plot_data["polymer_name"], plot_data["predicted_tg_k"], color=colors)
    ax.axvspan(320, 400, color=ACS_COLORS["light_gray"], zorder=0)
    ax.set_xlabel("Predicted Tg (K)")
    ax.set_title("Constrained inverse-design ranking")
    ax.invert_yaxis()
    ax.text(-0.14, 1.05, "b", transform=ax.transAxes, fontweight="bold", fontsize=10)
    return _save_figure(fig, paths["figures"], "figure_4_llm_inverse_design")


def _save_figure(fig: plt.Figure, figure_dir: Path, stem: str) -> Path:
    figure_dir.mkdir(parents=True, exist_ok=True)
    png_path = figure_dir / f"{stem}.png"
    pdf_path = figure_dir / f"{stem}.pdf"
    svg_path = figure_dir / f"{stem}.svg"
    fig.tight_layout()
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    fig.savefig(svg_path)
    plt.close(fig)
    return png_path


def _structure_key(smiles: str, bigsmiles: str) -> str:
    return f"sha256:{hashlib.sha256(f'{smiles}\\n{bigsmiles}'.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    print(json.dumps(run_case_study(), indent=2))
