from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from polyforge.check.diagnostics import Diagnostic
from polyforge.emit.descriptors import descriptor_row
from polyforge.pipeline import SourceArtifact, load_source


FIXED_COLUMNS = [
    "canonical_id",
    "source_file",
    "source_format",
    "structure_hash",
    "target_property",
    "target_value",
    "target_units",
]


@dataclass(frozen=True)
class FeatureTableResult:
    dataframe: pd.DataFrame | None
    diagnostics: list[Diagnostic]

    @property
    def errors(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "warning"]


def resolve_input_paths(inputs: list[str] | None = None, inputs_dir: str | None = None) -> list[Path]:
    paths: list[Path] = []

    if inputs:
        paths.extend(Path(item) for item in inputs)

    if inputs_dir:
        directory = Path(inputs_dir)
        discovered = [
            candidate
            for candidate in directory.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in {".pdsl", ".json"}
        ]
        paths.extend(sorted(discovered))

    if not paths:
        raise ValueError("at least one --input or --inputs-dir is required")

    return paths


def _target_payload(canonical_ir: dict[str, Any], target_property: str | None) -> tuple[str | None, Any, str | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    targets = canonical_ir.get("targets") or []

    if target_property is None:
        target = targets[0] if targets else None
    else:
        matches = [entry for entry in targets if entry.get("property") == target_property]
        target = matches[0] if matches else None
        if target is None:
            diagnostics.append(
                Diagnostic(
                    code="polyforge.ml.missing_target",
                    severity="error",
                    message=f"target property {target_property!r} not found",
                    file=None,
                    stage="ml",
                    path="targets",
                )
            )
            return None, None, None, diagnostics

    if target is None:
        return None, None, None, diagnostics

    value = target.get("target_value", target.get("value"))
    units = target.get("target_units", target.get("units"))

    if isinstance(value, dict) and value.get("explicit_unknown"):
        value = None
        units = None
    elif hasattr(value, "value"):
        units = getattr(value, "unit", units)
        value = float(value.value)

    return target.get("property"), value, units, diagnostics


def _row_for_artifact(artifact: SourceArtifact, target_property: str | None) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    diagnostics = list(artifact.diagnostics)
    if artifact.canonical_ir is None:
        return None, diagnostics

    selected_property, target_value, target_units, target_diagnostics = _target_payload(artifact.canonical_ir, target_property)
    diagnostics.extend(target_diagnostics)
    if target_diagnostics and any(diag.severity == "error" for diag in target_diagnostics):
        return None, diagnostics

    descriptors = descriptor_row(artifact.canonical_ir)
    descriptor_columns = sorted(
        key for key in descriptors.keys() if key not in {"canonical_id", "structure_hash"}
    )

    row: dict[str, Any] = {
        "canonical_id": artifact.canonical_ir["canonical_id"],
        "source_file": artifact.source_file,
        "source_format": artifact.source_format,
        "structure_hash": artifact.canonical_ir["structure_hash"],
        "target_property": selected_property,
        "target_value": target_value,
        "target_units": target_units,
    }
    for column in descriptor_columns:
        row[column] = descriptors[column]

    return row, diagnostics


def build_feature_table(paths: list[Path], target_property: str | None = None) -> FeatureTableResult:
    rows: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    descriptor_columns: list[str] | None = None

    for path in paths:
        artifact = load_source(path)
        row, artifact_diagnostics = _row_for_artifact(artifact, target_property)
        diagnostics.extend(artifact_diagnostics)

        if row is None:
            continue

        if descriptor_columns is None:
            descriptor_columns = sorted(
                key for key in row.keys() if key not in FIXED_COLUMNS
            )
        rows.append(row)

    if any(diagnostic.severity == "error" for diagnostic in diagnostics):
        return FeatureTableResult(dataframe=None, diagnostics=diagnostics)

    if not rows:
        return FeatureTableResult(dataframe=pd.DataFrame(columns=FIXED_COLUMNS), diagnostics=diagnostics)

    if descriptor_columns is None:
        descriptor_columns = []

    columns = [*FIXED_COLUMNS, *descriptor_columns]
    dataframe = pd.DataFrame(rows, columns=columns)
    return FeatureTableResult(dataframe=dataframe, diagnostics=diagnostics)


def write_feature_table(dataframe: pd.DataFrame, out_path: str | Path) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(out_path, index=False)
