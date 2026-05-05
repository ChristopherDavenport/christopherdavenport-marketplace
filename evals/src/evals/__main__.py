"""CLI entry point: `python -m evals <plugin> [--cases id ...] [--workers N]`."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

from .runner import run_plugin


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
    args = parser.parse_args(argv)

    console = Console()
    try:
        run_plugin(args.plugin, args.cases, args.workers, console)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        console.print("[red]interrupted[/red]")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
