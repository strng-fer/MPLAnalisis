"""CSV upsert semantics: refresh values, never erase with blanks, archive on schema change."""

from __future__ import annotations

import csv

from mplid.pipeline import upsert_csv

COLUMNS = ["season", "match_id", "score", "status"]
KEY = ("season", "match_id")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_insert_then_update(tmp_path):
    path = tmp_path / "table.csv"
    first = [{"season": 18, "match_id": "1", "score": "", "status": "scheduled"}]
    assert upsert_csv(path, first, COLUMNS, KEY)["added"] == 1

    second = [{"season": 18, "match_id": "1", "score": "2", "status": "completed"}]
    result = upsert_csv(path, second, COLUMNS, KEY)
    assert result == {"rows": 1, "added": 0, "updated": 1}

    row = read(path)[0]
    assert row["score"] == "2"
    assert row["status"] == "completed"


def test_blank_never_overwrites(tmp_path):
    path = tmp_path / "table.csv"
    upsert_csv(path, [{"season": 18, "match_id": "1", "score": "2", "status": "completed"}], COLUMNS, KEY)
    upsert_csv(path, [{"season": 18, "match_id": "1", "score": "", "status": ""}], COLUMNS, KEY)
    row = read(path)[0]
    assert row["score"] == "2"
    assert row["status"] == "completed"


def test_new_rows_are_appended_in_order(tmp_path):
    path = tmp_path / "table.csv"
    rows = [
        {"season": 18, "match_id": str(i), "score": "", "status": "scheduled"} for i in range(3)
    ]
    upsert_csv(path, rows, COLUMNS, KEY)
    assert [r["match_id"] for r in read(path)] == ["0", "1", "2"]


def test_schema_change_archives_old_file(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("old_column\nvalue\n", encoding="utf-8")
    upsert_csv(path, [{"season": 18, "match_id": "1", "score": "1", "status": "completed"}], COLUMNS, KEY)
    archived = list((tmp_path / "legacy").glob("table-*.csv"))
    assert len(archived) == 1
    assert "old_column" in archived[0].read_text(encoding="utf-8")
    assert read(path)[0]["match_id"] == "1"


def test_roundtrip_is_stable(tmp_path):
    path = tmp_path / "table.csv"
    rows = [{"season": 18, "match_id": "1", "score": "2", "status": "completed"}]
    upsert_csv(path, rows, COLUMNS, KEY)
    before = path.read_bytes()
    upsert_csv(path, rows, COLUMNS, KEY)
    assert path.read_bytes() == before
