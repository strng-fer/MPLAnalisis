"""Text and number parsing rules used by every module."""

from __future__ import annotations

import pytest

from mplid.parse import (
    first_int,
    parse_duration,
    parse_indonesian_date,
    parse_time,
    slugify,
    split_record,
    squash,
    to_float,
    to_int,
    to_ratio,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2,044,010", 2044010),
        ("878", 878),
        (" 12 ", 12),
        ("", None),
        ("-", None),
        ("N/A", None),
    ],
)
def test_to_int(raw, expected):
    assert to_int(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2,54", 2.54),
        ("9.316", 9316.0),
        ("2.044.010", 2044010.0),
        ("6,29", 6.29),
        ("0", 0.0),
        ("", None),
    ],
)
def test_to_float(raw, expected):
    assert to_float(raw) == expected


def test_to_ratio_returns_fraction():
    assert to_ratio("63%") == pytest.approx(0.63)
    assert to_ratio("0%") == pytest.approx(0.0)
    assert to_ratio("100%") == pytest.approx(1.0)
    assert to_ratio("") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Rabu, 4 November 2026", "2026-11-04"),
        ("Minggu, 6 September 2026", "2026-09-06"),
        ("Jumat, 14 Agustus 2026", "2026-08-14"),
        ("", ""),
        ("not a date", ""),
    ],
)
def test_parse_indonesian_date(raw, expected):
    assert parse_indonesian_date(raw) == expected


def test_parse_time_and_duration():
    assert parse_time("13:00") == "13:00"
    assert parse_time("9:05") == "09:05"
    assert parse_time("") == ""
    assert parse_duration("16:51") == 1011
    assert parse_duration("") is None


def test_split_record_and_first_int():
    assert split_record("12 - 4") == (12, 4)
    assert split_record("26\n-\n11") == (26, 11)
    assert first_int("#1") == 1
    assert first_int("") is None


def test_squash_and_slugify():
    assert squash("  BIGETRON \n BY VIT ") == "BIGETRON BY VIT"
    assert squash("a\xa0b") == "a b"
    assert slugify("KENNZYYSKIE") == "kennzyyskie"
    assert slugify("S-A-N-Z") == "s-a-n-z"
