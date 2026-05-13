from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from polyforge.canonicalize.json_ir import dumps_canonical_json
from polyforge.canonicalize.schema import load_canonical_ir_schema
from polyforge.emit.bigsmiles import export_bigsmiles
from polyforge.emit.descriptors import descriptor_row
from polyforge.emit.json import export_json
from polyforge.emit.tokens import token_sequence
from polyforge.ml.featurize import build_feature_table, resolve_input_paths, write_feature_table
from polyforge.ml.train import train_feature_csv
from polyforge.pipeline import format_diagnostic, load_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="polyforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a PolyForge program")
    validate.add_argument("inputs", nargs="+", help="Local .pdsl or canonical JSON files")
    validate.set_defaults(handler=_handle_validate)

    export = subparsers.add_parser("export", help="Export a canonical PolyForge view")
    export.add_argument("input", help="Local .pdsl or canonical JSON file")
    export.add_argument("--to", choices=["json", "tokens", "descriptors", "bigsmiles"], required=True)
    export.set_defaults(handler=_handle_export)

    featurize = subparsers.add_parser("featurize", help="Build a feature table from local inputs")
    featurize.add_argument("--input", action="append", dest="inputs", help="Input file to include")
    featurize.add_argument("--inputs-dir", dest="inputs_dir", help="Directory containing local inputs")
    featurize.add_argument("--target", dest="target", help="Target property to extract")
    featurize.add_argument("--out", required=True, help="Output CSV path")
    featurize.set_defaults(handler=_handle_featurize)

    train = subparsers.add_parser("train", help="Train a baseline model from features")
    train.add_argument("feature_csv", help="Feature CSV produced by featurize")
    train.add_argument("--model", choices=["mean", "linear_regression", "random_forest"], default="random_forest")
    train.add_argument("--run-dir", required=True, help="Directory for training artifacts")
    train.add_argument("--split", choices=["grouped", "random"], default="grouped")
    train.set_defaults(handler=_handle_train)

    schema = subparsers.add_parser("schema", help="Inspect PolyForge schemas")
    schema_subparsers = schema.add_subparsers(dest="schema_command", required=True)
    schema_show = schema_subparsers.add_parser("show", help="Show a packaged schema")
    schema_show.add_argument("version", choices=["v0.1"], help="Schema version to show")
    schema_show.set_defaults(handler=_handle_schema_show)

    return parser


def _emit_diagnostics(diagnostics) -> None:
    for diagnostic in diagnostics:
        print(format_diagnostic(diagnostic), file=sys.stderr)


def _handle_validate(args) -> int:
    exit_code = 0
    for input_path in args.inputs:
        artifact = load_source(input_path)
        if artifact.warnings:
            _emit_diagnostics(artifact.warnings)
        if artifact.errors:
            _emit_diagnostics(artifact.errors)
            exit_code = 1
            continue
        print(f"{artifact.source_file}: OK")
    return exit_code


def _handle_export(args) -> int:
    artifact = load_source(args.input)
    if artifact.errors:
        _emit_diagnostics(artifact.errors)
        return 1

    canonical_ir = artifact.canonical_ir
    if canonical_ir is None:
        _emit_diagnostics(artifact.errors)
        return 1

    if args.to == "json":
        output = export_json(canonical_ir)
    elif args.to == "tokens":
        output = "\n".join(token_sequence(canonical_ir))
    elif args.to == "descriptors":
        output = json.dumps(descriptor_row(canonical_ir), ensure_ascii=False, sort_keys=True)
    elif args.to == "bigsmiles":
        output = export_bigsmiles(canonical_ir)
    else:  # pragma: no cover - argparse constrains choices
        raise ValueError(f"unsupported export mode: {args.to}")

    print(output)
    return 0


def _handle_featurize(args) -> int:
    input_paths = resolve_input_paths(args.inputs, args.inputs_dir)
    result = build_feature_table(input_paths, target_property=args.target)

    if result.warnings:
        _emit_diagnostics(result.warnings)
    if result.errors:
        _emit_diagnostics(result.errors)
        return 1
    if result.dataframe is None:
        print("no feature rows were produced", file=sys.stderr)
        return 1

    write_feature_table(result.dataframe, args.out)
    print(str(Path(args.out)))
    return 0


def _handle_train(args) -> int:
    try:
        result = train_feature_csv(
            args.feature_csv,
            model_name=args.model,
            run_dir=args.run_dir,
            split=args.split,
        )
    except ValueError as exc:
        print(f"polyforge.ml.error: {exc}", file=sys.stderr)
        return 1

    print(str(result.run_dir))
    return 0


def _handle_schema_show(args) -> int:
    if args.version != "v0.1":  # pragma: no cover - argparse constrains choices
        print(f"unsupported schema version: {args.version}", file=sys.stderr)
        return 1
    print(dumps_canonical_json(load_canonical_ir_schema()))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
