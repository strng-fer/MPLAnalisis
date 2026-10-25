"""Stage, validate and publish the dataset to Kaggle.

Usage
-----
    python kaggle/publish.py --check
    python kaggle/publish.py --zip
    python kaggle/publish.py --upload            # first upload creates the dataset
    python kaggle/publish.py --upload --version  # later uploads add a version

Credentials: either ``~/.kaggle/kaggle.json`` or the ``KAGGLE_USERNAME`` and
``KAGGLE_KEY`` environment variables.

The staged directory is ``kaggle/_staging`` (gitignored): the 21 CSVs, the
manifest, the quality report, the dataset card as ``README.md``, and a
``dataset-metadata.json`` whose ``id`` is rewritten with the real account slug.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KAGGLE = ROOT / "kaggle"
STAGING = KAGGLE / "_staging"
DIST = ROOT / "dist"

# Rows each table must have for the current season; a mismatch means the data
# directory was not refreshed before publishing.
EXPECTED_ROWS = {
    "mpl-schedule": 80,
    "mpl-teams": 9,
    "mpl-standings": 9,
    "mpl-players": 91,
    "mpl-rosters": 84,
    "mpl-match-details": 72,
    "mpl-games": 174,
    "mpl-game-players": 1740,
    "mpl-drafts": 1740,
    "mpl-team-stats": 9,
    "mpl-player-stats": 66,
    "mpl-hero-stats": 133,
    "mpl-hero-pools": 621,
    "mpl-player-pools": 621,
    "mpl-mvp": 8,
    "mpl-seasons": 1,
    "mpl-hero-synergy": 1228,
    "mpl-hero-matchups": 2880,
    "mpl-player-hero-stats": 623,
    "mpl-head-to-head": 36,
    "mpl-team-form": 80,
}

EXTRA_FILES = ["manifest.json", "data-quality.md", "data-quality.json"]


def read_username() -> str | None:
    user = os.environ.get("KAGGLE_USERNAME")
    if user:
        return user
    cred = Path.home() / ".kaggle" / "kaggle.json"
    if cred.exists():
        try:
            return json.loads(cred.read_text(encoding="utf-8")).get("username")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def validate() -> list[str]:
    problems: list[str] = []

    missing = [name for name in EXPECTED_ROWS if not (DATA / f"{name}.csv").exists()]
    if missing:
        problems.append(f"missing tables: {', '.join(missing)}")

    for name, expected in EXPECTED_ROWS.items():
        path = DATA / f"{name}.csv"
        if not path.exists():
            continue
        actual = count_rows(path)
        if actual != expected:
            problems.append(f"{name}.csv has {actual} rows, expected {expected}")

    for name in EXTRA_FILES:
        if not (DATA / name).exists():
            problems.append(f"missing {name}")

    card = KAGGLE / "README.md"
    if not card.exists():
        problems.append("missing kaggle/README.md")

    meta_path = KAGGLE / "dataset-metadata.json"
    if not meta_path.exists():
        problems.append("missing kaggle/dataset-metadata.json")
    else:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"dataset-metadata.json is not valid JSON: {exc}")
        else:
            for field in ("title", "id", "licenses"):
                if not meta.get(field):
                    problems.append(f"dataset-metadata.json has no {field!r}")
            if "/" not in meta.get("id", ""):
                problems.append("dataset-metadata.json id must be '<username>/<slug>'")

    return problems


def stage(username: str) -> Path:
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    for csv_path in sorted(DATA.glob("mpl-*.csv")):
        shutil.copy2(csv_path, STAGING / csv_path.name)
    for name in EXTRA_FILES:
        source = DATA / name
        if source.exists():
            shutil.copy2(source, STAGING / name)

    shutil.copy2(KAGGLE / "README.md", STAGING / "README.md")

    meta = json.loads((KAGGLE / "dataset-metadata.json").read_text(encoding="utf-8"))
    slug = meta["id"].split("/", 1)[1]
    meta["id"] = f"{username}/{slug}"
    (STAGING / "dataset-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return STAGING


def make_zip() -> Path:
    DIST.mkdir(exist_ok=True)
    target = DIST / "mpl-indonesia-s18.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(STAGING.iterdir()):
            if path.is_file():
                archive.write(path, path.name)
    return target


def upload(version: bool) -> int:
    args = [
        sys.executable,
        "-m",
        "kaggle",
        "datasets",
        "version" if version else "create",
        "-p",
        str(STAGING),
        "--dir-mode",
        "zip",
    ]
    if version:
        args += ["-m", "refresh from id-mpl.com"]
    print("running:", " ".join(args))
    return subprocess.call(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish the MPL ID dataset to Kaggle.")
    parser.add_argument("--check", action="store_true", help="validate tables and metadata only")
    parser.add_argument("--zip", action="store_true", help="build dist/mpl-indonesia-s18.zip")
    parser.add_argument("--upload", action="store_true", help="create or version the Kaggle dataset")
    parser.add_argument("--version", action="store_true", help="add a version instead of creating")
    args = parser.parse_args(argv)

    problems = validate()
    if problems:
        print("validation failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"validation ok: {len(EXPECTED_ROWS)} tables, "
          f"{sum(EXPECTED_ROWS.values()):,} rows total")

    if args.check and not (args.zip or args.upload):
        return 0

    username = read_username() or "YOUR_KAGGLE_USERNAME"
    if username == "YOUR_KAGGLE_USERNAME":
        print("warning: no Kaggle username found; using a placeholder id")
    stage_dir = stage(username)
    files = sorted(p.name for p in stage_dir.iterdir())
    print(f"staged {len(files)} files in {stage_dir}")

    if args.zip:
        archive = make_zip()
        print(f"wrote {archive} ({archive.stat().st_size / 1024:.0f} KB)")

    if args.upload:
        if username == "YOUR_KAGGLE_USERNAME":
            print("cannot upload without credentials; set KAGGLE_USERNAME / KAGGLE_KEY")
            return 1
        return upload(args.version)

    return 0


if __name__ == "__main__":
    sys.exit(main())
