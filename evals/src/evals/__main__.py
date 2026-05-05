"""CLI entry point: `python -m evals <plugin> [--cases id ...] [--workers N] [--models …]`."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .inference import MODEL_BASE
from .runner import run_plugin

DEFAULT_MODELS = ["sonnet", "haiku"]


def _parse_models(s: str) -> list[str]:
    aliases = [m.strip() for m in s.split(",") if m.strip()]
    bad = [a for a in aliases if a not in MODEL_BASE]
    if bad:
        raise argparse.ArgumentTypeError(
            f"unknown model alias(es): {bad} (valid: {sorted(MODEL_BASE)})"
        )
    if not aliases:
        raise argparse.ArgumentTypeError("at least one model required")
    return aliases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m evals",
        description="Run the marketplace eval suite for a plugin.",
    )
    parser.add_argument("plugin", help="plugin folder under evals/ (e.g. 'go')")
    parser.add_argument(
        "--cases",
        nargs="+",
        metavar="ID",
        default=None,
        help="run only these case ids (default: all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="cases run in parallel (default: 3)",
    )
    parser.add_argument(
        "--models",
        type=_parse_models,
        default=DEFAULT_MODELS,
        help=(
            "comma-separated list of model aliases to run "
            "(haiku, sonnet, opus). Default: sonnet,haiku — both are "
            "deterministic at temperature=0. Add `opus` for an indicator "
            "of how the largest model behaves (note: opus does not accept "
            "the temperature parameter, so its numbers are noisier)."
        ),
    )
    parser.add_argument(
        "--model",
        type=lambda s: _parse_models(s),
        default=None,
        dest="model_singular",
        help="alias for --models with a single model (e.g. --model sonnet)",
    )
    parser.add_argument(
        "--via-cli",
        action="store_true",
        help=(
            "use the CLI subprocess backend (claude --bare --print --plugin-dir) "
            "instead of the default SDK direct backend. Slower and noisier "
            "(no temperature control) but exercises the real plugin-loading "
            "path end-to-end. Use periodically as an integration check."
        ),
    )
    args = parser.parse_args(argv)

    models = args.model_singular if args.model_singular is not None else args.models

    console = Console()
    try:
        run_plugin(
            args.plugin,
            args.cases,
            args.workers,
            console,
            models=models,
            via_cli=args.via_cli,
        )
    except SystemExit:
        raise
    except KeyboardInterrupt:
        console.print("[red]interrupted[/red]")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
