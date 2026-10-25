"""Schedule page: both stages, de-duplication, upcoming vs completed."""

from __future__ import annotations

from mplid.schedule import parse_schedule


def test_row_count_and_stages(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    assert len(rows) == 80
    assert {r.stage for r in rows} == {"Regular Season", "Playoffs"}
    assert sum(1 for r in rows if r.stage == "Regular Season") == 72
    assert sum(1 for r in rows if r.stage == "Playoffs") == 8


def test_rows_are_deduplicated(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    ids = [r.match_id for r in rows if r.match_id]
    assert len(ids) == len(set(ids))
    # Two playoff slots can share a date with both teams still TBD, so the
    # round label is part of the identity.
    keys = [(r.stage, r.match_date, r.team1_name, r.team2_name, r.round) for r in rows]
    assert len(keys) == len(set(keys))


def test_completed_and_scheduled_split(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    completed = [r for r in rows if r.match_status == "completed"]
    scheduled = [r for r in rows if r.match_status == "scheduled"]
    assert len(completed) == 72
    assert len(scheduled) == 8
    for row in completed:
        assert row.team1_score != "" and row.team2_score != ""
        assert row.detail_url.endswith(row.match_id)
    for row in scheduled:
        assert row.team1_score == "" and row.team2_score == ""
        assert row.detail_url == ""


def test_week_and_round_labels(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    regular = [r for r in rows if r.stage == "Regular Season"]
    assert {r.week for r in regular} == {str(i) for i in range(1, 10)}
    assert all(r.round == f"Week {r.week}" for r in regular)
    playoffs = [r for r in rows if r.stage == "Playoffs"]
    assert any("Grand Finals" in r.round for r in playoffs)


def test_first_match_fields(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    first = next(r for r in rows if r.match_id == "1036")
    assert first.match_date == "2026-08-14"
    assert first.match_time == "15:00"
    assert (first.team1_name, first.team2_name) == ("EVOS", "RRQ")
    assert (first.team1_score, first.team2_score) == ("2", "0")
    assert first.replay_url.startswith("https://")


def test_dates_are_sorted_and_iso(schedule_html):
    rows = parse_schedule(schedule_html, 18, "test")
    dates = [r.match_date for r in rows]
    assert dates == sorted(dates)
    assert all(len(d) == 10 and d[4] == "-" for d in dates)
