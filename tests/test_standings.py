"""Standings table: official columns only, plus the derived ones."""

from __future__ import annotations

from mplid.standings import parse_standings

TEAM_IDS = {
    "AE": "ae",
    "BTR": "btr",
    "DEWA": "dewa",
    "EVOS": "evos",
    "GEEK": "geek",
    "NAVI": "navi",
    "ONIC": "onic",
    "RRQ": "rrq",
    "TLID": "tlid",
}


def test_nine_rows_with_ids(home_html):
    rows, info = parse_standings(home_html, 18, "test", TEAM_IDS)
    assert len(rows) == 9
    assert all(r.team_id for r in rows)
    assert {r.rank for r in rows} == set(range(1, 10))
    assert info is not None
    assert info.playoffs_bracket_url.startswith("https://")


def test_records_balance(home_html):
    rows, _ = parse_standings(home_html, 18, "test", TEAM_IDS)
    assert sum(r.wins or 0 for r in rows) == sum(r.losses or 0 for r in rows)
    assert sum(r.game_difference or 0 for r in rows) == 0
    assert sum(r.game_wins or 0 for r in rows) == sum(r.game_losses or 0 for r in rows)


def test_derived_fields(home_html):
    rows, _ = parse_standings(home_html, 18, "test", TEAM_IDS)
    for row in rows:
        assert row.matches_played == (row.wins or 0) + (row.losses or 0)
        if row.matches_played:
            assert row.win_rate == round((row.wins or 0) / row.matches_played, 4)


def test_leader_values(home_html):
    rows, _ = parse_standings(home_html, 18, "test", TEAM_IDS)
    leader = next(r for r in rows if r.rank == 1)
    assert leader.team_id == "tlid"
    assert leader.points == 12
    assert (leader.wins, leader.losses) == (12, 4)
    assert (leader.game_wins, leader.game_losses) == (26, 11)
    assert leader.game_difference == 15
