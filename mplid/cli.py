"""Command line entry point: ``python -m mplid --out <dir>``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .pipeline import Pipeline


def default_out() -> Path:
    env = os.environ.get("MPL_OUT")
    if env:
        return Path(env)
    return Path(os.environ.get("TEMP", ".")) / "mpl-out"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mplid", description="Collect the MPL Indonesia dataset.")
    parser.add_argument("--out", default=str(default_out()), help="output directory (default: %%TEMP%%\\mpl-out)")
    parser.add_argument("--season", type=int, default=None, help="season number; auto-detected when omitted")
    parser.add_argument("--refresh", action="store_true", help="ignore the HTML cache and refetch every page")
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between HTTP requests")
    parser.add_argument("--max-matches", type=int, default=None, help="limit match detail pages (debugging)")
    parser.add_argument("--quiet", action="store_true", help="only print the final manifest")
    args = parser.parse_args(argv)

    log = (lambda *a, **k: None) if args.quiet else print
    pipeline = Pipeline(
        Path(args.out),
        season=args.season,
        refresh=args.refresh,
        delay=args.delay,
        max_matches=args.max_matches,
        log=log,
    )
    manifest = pipeline.run()
    print(json.dumps({k: manifest[k] for k in ("season", "duration_seconds", "tables", "warnings")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
