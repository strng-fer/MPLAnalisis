"""Derived analytics tables.

Everything in this module is computed from the scraped facts; none of it is
published by id-mpl.com. Each table is reproducible from the CSVs in the same
output directory:

``mpl-hero-synergy.csv``      hero pairs played on the same team in one game
``mpl-hero-matchups.csv``     hero A versus hero B in one game (A's win rate)
``mpl-player-hero-stats.csv`` per player per hero game totals
``mpl-head-to-head.csv``      team pair series results
``mpl-team-form.csv``         team results per week (season progression)
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations, product

from .matchdetail import MatchDetail
from .schedule import MatchRow


def _ratio(part: int, total: int) -> float | None:
    return round(part / total, 4) if total else None


def hero_synergy(details: list[MatchDetail], meta: dict[str, dict]) -> list[dict]:
    """Hero pairs that appeared together on the same side of a game."""
    stats: dict[tuple, dict] = defaultdict(lambda: {"games": 0, "wins": 0})
    for detail in details:
        info = meta.get(detail.match_id, {})
        for game in detail.games:
            for side in ("winner", "loser"):
                heroes = sorted({p.hero_name for p in game.players if p.side == side and p.hero_name})
                won = side == "winner"
                for a, b in combinations(heroes, 2):
                    key = (info.get("season"), info.get("stage"), a, b)
                    stats[key]["games"] += 1
                    stats[key]["wins"] += 1 if won else 0

    rows = []
    for (season, stage, a, b), value in stats.items():
        rows.append(
            {
                "season": season,
                "stage": stage,
                "hero_a": a,
                "hero_b": b,
                "games_together": value["games"],
                "wins_together": value["wins"],
                "win_rate": _ratio(value["wins"], value["games"]),
            }
        )
    rows.sort(key=lambda r: (-(r["games_together"] or 0), r["hero_a"], r["hero_b"]))
    return rows


def hero_matchups(details: list[MatchDetail], meta: dict[str, dict]) -> list[dict]:
    """Head-to-head record between two heroes across opposing sides.

    Both directions are recorded, so ``hero`` is the reference hero and
    ``win_rate`` is that hero's win rate when facing ``opponent_hero``.
    """
    stats: dict[tuple, dict] = defaultdict(lambda: {"games": 0, "wins": 0})
    for detail in details:
        info = meta.get(detail.match_id, {})
        for game in detail.games:
            winners = sorted({p.hero_name for p in game.players if p.side == "winner" and p.hero_name})
            losers = sorted({p.hero_name for p in game.players if p.side == "loser" and p.hero_name})
            for a, b in product(winners, losers):
                forward = (info.get("season"), info.get("stage"), a, b)
                stats[forward]["games"] += 1
                stats[forward]["wins"] += 1
                reverse = (info.get("season"), info.get("stage"), b, a)
                stats[reverse]["games"] += 1

    rows = []
    for (season, stage, a, b), value in stats.items():
        rows.append(
            {
                "season": season,
                "stage": stage,
                "hero": a,
                "opponent_hero": b,
                "games": value["games"],
                "wins": value["wins"],
                "win_rate": _ratio(value["wins"], value["games"]),
            }
        )
    rows.sort(key=lambda r: (-(r["games"] or 0), r["hero"], r["opponent_hero"]))
    return rows


def player_hero_stats(details: list[MatchDetail], meta: dict[str, dict]) -> list[dict]:
    stats: dict[tuple, dict] = defaultdict(
        lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0, "gold": 0, "damage": 0}
    )
    for detail in details:
        info = meta.get(detail.match_id, {})
        for game in detail.games:
            for player in game.players:
                key = (info.get("season"), player.team_name, player.player_name, player.hero_name)
                bucket = stats[key]
                bucket["games"] += 1
                bucket["wins"] += 1 if player.side == "winner" else 0
                bucket["kills"] += player.kills or 0
                bucket["deaths"] += player.deaths or 0
                bucket["assists"] += player.assists or 0
                bucket["gold"] += player.gold or 0
                bucket["damage"] += player.damage_dealt or 0

    rows = []
    for (season, team, player, hero), value in stats.items():
        games = value["games"]
        kda = (value["kills"] + value["assists"]) / value["deaths"] if value["deaths"] else float(value["kills"] + value["assists"])
        rows.append(
            {
                "season": season,
                "team_name": team,
                "player_name": player,
                "hero_name": hero,
                "games": games,
                "wins": value["wins"],
                "win_rate": _ratio(value["wins"], games),
                "kills": value["kills"],
                "deaths": value["deaths"],
                "assists": value["assists"],
                "avg_kills": round(value["kills"] / games, 2) if games else None,
                "avg_deaths": round(value["deaths"] / games, 2) if games else None,
                "avg_assists": round(value["assists"] / games, 2) if games else None,
                "kda": round(kda, 2),
                "total_gold": value["gold"],
                "total_damage": value["damage"],
            }
        )
    rows.sort(key=lambda r: (-(r["games"] or 0), r["player_name"], r["hero_name"]))
    return rows


def head_to_head(matches: list[MatchRow], team_ids: dict[str, str]) -> list[dict]:
    stats: dict[tuple, dict] = defaultdict(
        lambda: {"matches": 0, "a_wins": 0, "b_wins": 0, "a_games": 0, "b_games": 0, "dates": []}
    )
    for match in matches:
        if match.match_status != "completed":
            continue
        a, b = sorted([match.team1_name, match.team2_name])
        if not a or not b:
            continue
        key = (match.season, match.stage, a, b)
        bucket = stats[key]
        bucket["matches"] += 1
        bucket["dates"].append(match.match_date)
        score_a = int(match.team1_score or 0) if match.team1_name == a else int(match.team2_score or 0)
        score_b = int(match.team2_score or 0) if match.team1_name == a else int(match.team1_score or 0)
        bucket["a_games"] += score_a
        bucket["b_games"] += score_b
        if score_a > score_b:
            bucket["a_wins"] += 1
        elif score_b > score_a:
            bucket["b_wins"] += 1

    rows = []
    for (season, stage, a, b), value in stats.items():
        rows.append(
            {
                "season": season,
                "stage": stage,
                "team_a": a,
                "team_a_id": team_ids.get(a, ""),
                "team_b": b,
                "team_b_id": team_ids.get(b, ""),
                "matches": value["matches"],
                "team_a_match_wins": value["a_wins"],
                "team_b_match_wins": value["b_wins"],
                "team_a_game_wins": value["a_games"],
                "team_b_game_wins": value["b_games"],
                "first_match_date": min(value["dates"]) if value["dates"] else "",
                "last_match_date": max(value["dates"]) if value["dates"] else "",
            }
        )
    rows.sort(key=lambda r: (r["season"], r["team_a"], r["team_b"]))
    return rows


def team_form(matches: list[MatchRow], team_ids: dict[str, str]) -> list[dict]:
    """Per team per week: match wins, game wins and running record."""
    buckets: dict[tuple, dict] = defaultdict(
        lambda: {"matches": 0, "wins": 0, "losses": 0, "game_wins": 0, "game_losses": 0, "dates": []}
    )
    for match in matches:
        if match.match_status != "completed" or not match.week:
            continue
        for name, own, other in (
            (match.team1_name, match.team1_score, match.team2_score),
            (match.team2_name, match.team2_score, match.team1_score),
        ):
            if not name:
                continue
            key = (match.season, match.stage, match.week, name)
            bucket = buckets[key]
            bucket["matches"] += 1
            bucket["dates"].append(match.match_date)
            own_score, other_score = int(own or 0), int(other or 0)
            bucket["game_wins"] += own_score
            bucket["game_losses"] += other_score
            if own_score > other_score:
                bucket["wins"] += 1
            else:
                bucket["losses"] += 1

    rows = []
    for (season, stage, week, name), value in buckets.items():
        rows.append(
            {
                "season": season,
                "stage": stage,
                "week": week,
                "team_name": name,
                "team_id": team_ids.get(name, ""),
                "matches": value["matches"],
                "match_wins": value["wins"],
                "match_losses": value["losses"],
                "game_wins": value["game_wins"],
                "game_losses": value["game_losses"],
                "game_difference": value["game_wins"] - value["game_losses"],
                "first_match_date": min(value["dates"]) if value["dates"] else "",
                "last_match_date": max(value["dates"]) if value["dates"] else "",
            }
        )
    rows.sort(key=lambda r: (r["season"], int(r["week"] or 0), r["team_name"]))
    return rows
