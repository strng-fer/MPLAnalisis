"""Shared fixtures: gzipped HTML snapshots captured from id-mpl.com.

The snapshots keep the tests offline and stable. They are the exact bytes the
pipeline receives, so a parser regression shows up here before a live run.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
DATA = Path(__file__).resolve().parents[1] / "data"


def load(name: str) -> str:
    path = FIXTURES / f"{name}.html.gz"
    if not path.exists():
        pytest.skip(f"missing fixture {path.name}")
    return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")


@pytest.fixture(scope="session")
def schedule_html() -> str:
    return load("schedule")


@pytest.fixture(scope="session")
def home_html() -> str:
    return load("home")


@pytest.fixture(scope="session")
def statistics_html() -> str:
    return load("statistics")


@pytest.fixture(scope="session")
def teams_html() -> str:
    return load("teams")


@pytest.fixture(scope="session")
def team_btr_html() -> str:
    return load("team-btr")


@pytest.fixture(scope="session")
def match_detail_html() -> str:
    return load("match-detail-1036")


@pytest.fixture(scope="session")
def data_dir() -> Path:
    if not DATA.exists():
        pytest.skip("data directory not found")
    return DATA
