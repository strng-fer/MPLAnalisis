"""Cross-table integrity checks on the published dataset.

These run against ``data/*.csv``, so they validate exactly what a consumer of
the repository (or the Kaggle copy) downloads.
"""

from __future__ import annotations

import csv

import pytest

TABLES = [
    "mpl-schedule",
    "mpl-teams",
    "mpl-standings",
    "mpl-players",
    "mpl-rosters",
    "mpl-match-details",
    "mpl-games",
    "mpl-game-players",
    "mpl-drafts",
    "mpl-team-stats",
    "mpl-player-stats",
    "mpl-hero-stats",
    "mpl-hero-pools",
    "mpl-player-pools",
    "mpl-mvp",
    "mpl-seasons",
    "mpl-hero-synergy",
    "mpl-hero-matchups",
    "mpl-player-hero-stats",
    "mpl-head-to-head",
    "mpl-team-form",
]


def load(data_dir, name):
    with (data_dir / f"{name}.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("name", TABLES)
def test_table_exists_and_has_rows(data_dir, name):
    rows = load(data_dir, name)
    assert rows, f"{name}.csv is empty"
    assert all(key.strip() for key in rows[0]), f"{name}.csv has a blank header"


def test_players_cover_every_game_row(data_dir):
    players = {r["player_id"] for r in load(data_dir, "mpl-players")}
    game_rows = load(data_dir, "mpl-game-players")
    missing = {r["player_id"] for r in game_rows if r["player_id"] not in players}
    assert not missing, f"unknown player ids: {sorted(missing)[:5]}"


def test_rosters_reference_known_players(data_dir):
    players = {r["player_id"] for r in load(data_dir, "mpl-players")}
    teams = {r["team_id"] for r in load(data_dir, "mpl-teams")}
    for row in load(data_dir, "mpl-rosters"):
        assert row["player_id"] in players
        assert row["team_id"] in teams


def test_every_completed_match_has_details(data_dir):
    completed = {r["match_id"] for r in load(data_dir, "mpl-schedule") if r["match_status"] == "completed"}
    detailed = {r["match_id"] for r in load(data_dir, "mpl-match-details")}
    assert completed == detailed


def test_game_counts_match_schedule_scores(data_dir):
    games: dict[str, int] = {}
    for row in load(data_dir, "mpl-games"):
        games[row["match_id"]] = games.get(row["match_id"], 0) + 1
    for row in load(data_dir, "mpl-match-details"):
        expected = int(row["team1_score"]) + int(row["team2_score"])
        assert games[row["match_id"]] == expected, row["match_id"]


def test_ten_players_per_game(data_dir):
    counts: dict[tuple, int] = {}
    for row in load(data_dir, "mpl-game-players"):
        key = (row["match_id"], row["game_no"])
        counts[key] = counts.get(key, 0) + 1
    assert all(value == 10 for value in counts.values())


def test_pick_totals_agree(data_dir):
    heroes = sum(int(r["picks"]) for r in load(data_dir, "mpl-hero-stats"))
    pools = sum(int(r["picks"]) for r in load(data_dir, "mpl-hero-pools"))
    player_pools = sum(int(r["picks"]) for r in load(data_dir, "mpl-player-pools"))
    game_rows = len(load(data_dir, "mpl-game-players"))
    assert heroes == pools == player_pools == game_rows


def test_standings_balance(data_dir):
    rows = load(data_dir, "mpl-standings")
    assert sum(int(r["wins"]) for r in rows) == sum(int(r["losses"]) for r in rows)
    assert sum(int(r["game_difference"]) for r in rows) == 0


def test_standings_match_schedule_reconstruction(data_dir):
    """Recomputing the table from match results must reproduce the official one."""
    totals: dict[str, dict[str, int]] = {}
    for row in load(data_dir, "mpl-schedule"):
        if row["match_status"] != "completed":
            continue
        s1, s2 = int(row["team1_score"]), int(row["team2_score"])
        for name, own, other in (
            (row["team1_name"], s1, s2),
            (row["team2_name"], s2, s1),
        ):
            bucket = totals.setdefault(name, {"wins": 0, "losses": 0, "games": 0, "diff": 0})
            bucket["wins" if own > other else "losses"] += 1
            bucket["games"] += own
            bucket["diff"] += own - other

    for row in load(data_dir, "mpl-standings"):
        short = row["team_id"].upper()
        actual = totals.get(short)
        assert actual is not None, f"no schedule rows for {short}"
        assert actual["wins"] == int(row["wins"]), short
        assert actual["losses"] == int(row["losses"]), short
        assert actual["games"] == int(row["game_wins"]), short
        assert actual["diff"] == int(row["game_difference"]), short


def test_no_duplicate_natural_keys(data_dir):
    checks = {
        "mpl-schedule": ("season", "stage", "match_id"),
        "mpl-games": ("match_id", "game_no"),
        "mpl-game-players": ("match_id", "game_no", "team_id", "player_id"),
        "mpl-standings": ("season", "stage", "team_id"),
        "mpl-hero-stats": ("season", "hero_name"),
    }
    for name, key in checks.items():
        rows = load(data_dir, name)
        seen = [tuple(r[k] for k in key) for r in rows]
        assert len(seen) == len(set(seen)), f"{name} has duplicate {key}"


def test_percentages_are_fractions(data_dir):
    for name, column in (
        ("mpl-hero-stats", "win_rate"),
        ("mpl-standings", "win_rate"),
        ("mpl-player-stats", "kill_participation"),
    ):
        for row in load(data_dir, name):
            if row[column]:
                assert 0.0 <= float(row[column]) <= 1.0, f"{name}.{column}={row[column]}"
