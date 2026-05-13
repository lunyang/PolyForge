from __future__ import annotations

import argparse
from collections.abc import Sequence

from experiments.tg_benchmark.benchmark import SUPPORTED_REPRESENTATIONS, run_tg_benchmark
from polyforge.ml.models import SUPPORTED_MODELS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m experiments.tg_benchmark.cli")
    parser.add_argument("--dataset", required=True, help="Path to bigsmiles-Tg.csv")
    parser.add_argument("--out", required=True, help="Output directory for benchmark artifacts")
    parser.add_argument(
        "--representation",
        action="append",
        choices=SUPPORTED_REPRESENTATIONS,
        dest="representations",
        help="Representation to evaluate; may be provided more than once",
    )
    parser.add_argument(
        "--model",
        action="append",
        choices=SUPPORTED_MODELS,
        dest="models",
        help="Model to evaluate; may be provided more than once",
    )
    parser.add_argument("--splits", type=int, default=5, help="Number of grouped folds")
    parser.add_argument("--seed", type=int, default=13, help="Deterministic seed")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_tg_benchmark(
        dataset_path=args.dataset,
        output_dir=args.out,
        representations=args.representations or ("bigsmiles_char",),
        models=args.models or ("mean", "random_forest"),
        n_splits=args.splits,
        seed=args.seed,
    )
    print(f"{args.out} ({len(result['runs'])} run(s))")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
