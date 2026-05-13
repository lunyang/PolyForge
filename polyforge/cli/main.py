from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="polyforge")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("validate", help="Validate a PolyForge program")
    subparsers.add_parser("export", help="Export a canonical PolyForge view")
    subparsers.add_parser("featurize", help="Build a feature table from local inputs")
    subparsers.add_parser("train", help="Train a baseline model from features")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0

