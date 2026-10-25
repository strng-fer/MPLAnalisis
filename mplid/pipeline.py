"""Pipeline orchestration: fetch -> parse -> CSV upsert -> analytics -> report.

Run through ``python -m mplid`` (see ``cli.py``). Every step is idempotent:
existing CSV rows are merged on a natural key, so a rerun refreshes scores and
status without dropping records that are no longer on the site.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import time
from pathlib import Path

from . import __version__, analytics
from .fetch import BASE_URL, Fetcher, default_obscura
from .matchdetail import MatchDetail, parse_match_detail
from .parse import slugify, squash
from .schedule import MatchRow, parse_schedule
from .standings import SeasonInfo, StandingRow, parse_standings
from .statistics import StatisticsBundle, parse_statistics
from .teams import RosterEntry, TeamRow, parse_team_index, parse_team_page

SCHEDULE_COLUMNS = [
    "season",
    "stage",
    "match_id",
    "match_date",
    "match_time",
    "round",
    "match_status",
    "team1_id",
    "team1_name",
    "team2_id",
    "team2_name",
    "team1_score",
    "team2_score",
    "winner_team_id",
    "match_url",
    "scraped_at",
]

TEAM_COLUMNS = [
    "season",
    "team_id",
    "team_name",
    "team_short_name",
    "team_logo_url",
    "team_profile_url",
    "roster_reference",
    "scraped_at",
]

STANDING_COLUMNS = [
    "season",
    "stage",
    "team_id",
    "team_name",
    "rank",
    "matches_played",
    "wins",
    "losses",
    "game_wins",
    "game_losses",
    "game_difference",
    "points",
    "win_rate",
    "source_url",
    "scraped_at",
]

PLAYER_COLUMNS = [
    "player_id",
    "player_name",
    "in_game_name",
    "current_team_id",
    "role",
    "nationality",
    "profile_url",
    "season",
    "scraped_at",
]

ROSTER_COLUMNS = [
    "season",
    "team_id",
    "player_id",
    "role",
    "roster_status",
    "valid_from",
    "valid_until",
    "source_url",
]

MATCH_DETAIL_COLUMNS = [
    "match_id",
    "season",
    "stage",
    "match_date",
    "match_time",
    "round",
    "team1_id",
    "team1_name",
    "team1_score",
    "team2_id",
    "team2_name",
    "team2_score",
    "winner_team_id",
    "games_played",
    "total_duration_seconds",
    "avg_game_duration_seconds",
    "source_url",
    "scraped_at",
]

GAME_COLUMNS = [
    "match_id",
    "season",
    "stage",
    "match_date",
    "game_no",
    "game_uid",
    "duration_seconds",
    "winner_team_id",
    "winner_team_name",
    "winner_kills",
    "loser_team_id",
    "loser_team_name",
    "loser_kills",
    "source_url",
    "scraped_at",
]

GAME_PLAYER_COLUMNS = [
    "match_id",
    "game_no",
    "season",
    "stage",
    "side",
    "team_id",
    "team_name",
    "player_id",
    "player_name",
    "hero_name",
    "hero_id",
    "kills",
    "deaths",
    "assists",
    "damage_dealt",
    "damage_taken",
    "tower_damage",
    "gold",
    "emblem_id",
    "rune_ids",
    "item_ids",
    "source_url",
    "scraped_at",
]

DRAFT_COLUMNS = [
    "match_id",
    "game_no",
    "season",
    "stage",
    "side",
    "team_id",
    "player_name",
    "hero_name",
    "pick_slot",
    "source_url",
    "scraped_at",
]

TEAM_STAT_COLUMNS = [
    "season",
    "team_id",
    "team_name",
    "kills",
    "deaths",
    "assists",
    "gold",
    "damage",
    "lord",
    "tortoise",
    "tower",
    "source_url",
    "scraped_at",
]

PLAYER_STAT_COLUMNS = [
    "season",
    "team_id",
    "player_id",
    "player_name",
    "lane",
    "games",
    "kills",
    "avg_kills",
    "deaths",
    "avg_deaths",
    "assists",
    "avg_assists",
    "avg_kda",
    "kill_participation",
    "source_url",
    "scraped_at",
]

HERO_STAT_COLUMNS = [
    "season",
    "hero_name",
    "picks",
    "bans",
    "wins",
    "win_rate",
    "source_url",
    "scraped_at",
]

HERO_POOL_COLUMNS = [
    "season",
    "team_id",
    "player_id",
    "player_name",
    "lane",
    "distinct_heroes",
    "hero_name",
    "picks",
    "win_rate",
    "source_url",
    "scraped_at",
]

PLAYER_POOL_COLUMNS = [
    "season",
    "hero_name",
    "total_picks",
    "team_id",
    "player_id",
    "player_name",
    "picks",
    "win_rate",
    "source_url",
    "scraped_at",
]

MVP_COLUMNS = [
    "season",
    "rank",
    "points",
    "player_display",
    "team_id",
    "player_id",
    "player_name",
    "source_url",
    "scraped_at",
]

SEASON_COLUMNS = ["season", "season_label", "playoffs_bracket_url", "source_url", "scraped_at"]

SYNERGY_COLUMNS = ["season", "stage", "hero_a", "hero_b", "games_together", "wins_together", "win_rate"]

MATCHUP_COLUMNS = ["season", "stage", "hero", "opponent_hero", "games", "wins", "win_rate"]

PLAYER_HERO_COLUMNS = [
    "season",
    "team_name",
    "player_name",
    "hero_name",
    "games",
    "wins",
    "win_rate",
    "kills",
    "deaths",
    "assists",
    "avg_kills",
    "avg_deaths",
    "avg_assists",
    "kda",
    "total_gold",
    "total_damage",
]

H2H_COLUMNS = [
    "season",
    "stage",
    "team_a",
    "team_a_id",
    "team_b",
    "team_b_id",
    "matches",
    "team_a_match_wins",
    "team_b_match_wins",
    "team_a_game_wins",
    "team_b_game_wins",
    "first_match_date",
    "last_match_date",
]

FORM_COLUMNS = [
    "season",
    "stage",
    "week",
    "team_name",
    "team_id",
    "matches",
    "match_wins",
    "match_losses",
    "game_wins",
    "game_losses",
    "game_difference",
    "first_match_date",
    "last_match_date",
]


# -- CSV helpers ---------------------------------------------------------


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        try:
            return next(csv.reader(handle))
        except StopIteration:
            return []


def _archive_legacy(path: Path) -> None:
    """Move a file with an older schema aside instead of merging into it."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    legacy_dir = path.parent / "legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    path.replace(legacy_dir / f"{path.stem}-{stamp}{path.suffix}")


def upsert_csv(path: Path, rows: list[dict], columns: list[str], key: tuple[str, ...]) -> dict:
    """Merge ``rows`` into ``path`` on ``key``; empty new values never erase old ones."""
    if path.exists() and _headers(path) != columns:
        _archive_legacy(path)
    existing = _read_csv(path)
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in existing:
        ident = tuple(squash(row.get(field, "")) for field in key)
        if ident not in merged:
            order.append(ident)
        merged[ident] = {field: row.get(field, "") for field in columns}

    added = 0
    updated = 0
    for row in rows:
        record = {field: ("" if row.get(field) is None else str(row.get(field))) for field in columns}
        ident = tuple(squash(record.get(field, "")) for field in key)
        if ident in merged:
            changed = False
            for field in columns:
                value = record[field]
                if value != "" and merged[ident].get(field, "") != value:
                    merged[ident][field] = value
                    changed = True
            updated += 1 if changed else 0
        else:
            merged[ident] = record
            order.append(ident)
            added += 1

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for ident in order:
            writer.writerow(merged[ident])
    tmp.replace(path)
    return {"rows": len(order), "added": added, "updated": updated}


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: ("" if row.get(field) is None else row.get(field)) for field in columns})
    return {"rows": len(rows)}


# -- pipeline ------------------------------------------------------------


class Pipeline:
    def __init__(
        self,
        out_dir: Path,
        *,
        season: int | None = None,
        refresh: bool = False,
        delay: float = 0.4,
        max_matches: int | None = None,
        log=print,
    ) -> None:
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.cache = self.out / "cache"
        self.raw = self.out / "raw"
        self.fetcher = Fetcher(
            self.cache,
            delay=delay,
            refresh=refresh,
            obscura=default_obscura(),
        )
        self.season = season
        self.max_matches = max_matches
        self.log = log
        self.started = time.time()
        self.stats: dict[str, dict] = {}
        self.warnings: list[str] = []

    # -- small helpers ---------------------------------------------------
    def _season(self) -> int:
        if self.season is not None:
            return self.season
        html = self.fetcher.get(f"{BASE_URL}/teams", expect="team-card")
        teams = parse_team_index(html)
        if not teams:
            self.season = 18
            return self.season
        page = self.fetcher.get(teams[0]["team_profile_url"], expect="ROSTER SEASON")
        import re

        match = re.search(r"(?i)ROSTER SEASON\s*(\d+)", page)
        self.season = int(match.group(1)) if match else 18
        return self.season

    def _save_raw(self, name: str, payload: str) -> None:
        folder = self.raw / dt.date.today().isoformat()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.html").write_text(payload, encoding="utf-8")

    def _player_id(self, team_id: str, name: str) -> str:
        return f"{team_id}:{slugify(name)}"

    def _build_aliases(self, roster_rows: list[RosterEntry], player_stats: list[dict]) -> None:
        """Map the IGN spellings used across pages onto one player id.

        The roster page, the statistics page and the match detail page do not
        always agree (``KENNZYYSKIE`` / ``KennzySkie``, ``KEVIN`` / ``Kevinn``),
        so each team keeps a fuzzy index over its known names.
        """
        import difflib

        self._alias_cache = {}
        self._alias_index: dict[str, list[tuple[str, str, str]]] = {}
        seen: set[tuple[str, str]] = set()
        for entry in roster_rows:
            key = (entry.team_id, entry.player_id)
            if key in seen:
                continue
            seen.add(key)
            self._alias_index.setdefault(entry.team_id, []).append(
                (slugify(entry.player_name).replace("-", ""), entry.player_id, entry.player_name)
            )
        for stat in player_stats:
            key = (stat["team_id"], stat["player_id"])
            if key in seen:
                continue
            seen.add(key)
            self._alias_index.setdefault(stat["team_id"], []).append(
                (slugify(stat["player_name"]).replace("-", ""), stat["player_id"], stat["player_name"])
            )

    def _resolve_player(self, team_id: str, name: str) -> tuple[str, str]:
        import difflib

        cache = getattr(self, "_alias_cache", None)
        if cache is None:
            cache = self._alias_cache = {}
        cache_key = (team_id, name)
        if cache_key in cache:
            return cache[cache_key]

        norm = slugify(name).replace("-", "")
        candidates = self._alias_index.get(team_id, [])
        for alias, player_id, display in candidates:
            if alias == norm:
                cache[cache_key] = (player_id, display)
                return cache[cache_key]
        best = None
        for alias, player_id, display in candidates:
            score = difflib.SequenceMatcher(None, norm, alias).ratio()
            if best is None or score > best[0]:
                best = (score, player_id, display)
        if best is not None and best[0] >= 0.85:
            cache[cache_key] = (best[1], best[2])
        else:
            cache[cache_key] = (self._player_id(team_id, name), name)
        return cache[cache_key]


    # -- steps -----------------------------------------------------------
    def run(self) -> dict:
        season = self._season()
        now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        self.log(f"season {season}")

        home_html = self.fetcher.get(f"{BASE_URL}/home", expect="standing-regular-season")
        self._save_raw("home", home_html)

        teams_html = self.fetcher.get(f"{BASE_URL}/teams", expect="team-card")
        self._save_raw("teams", teams_html)
        team_index = parse_team_index(teams_html)
        team_ids = {t["team_short_name"].upper(): t["team_id"] for t in team_index}
        self.log(f"teams {len(team_index)}")

        team_rows: list[TeamRow] = []
        roster_rows: list[RosterEntry] = []
        for entry in team_index:
            try:
                page = self.fetcher.get(entry["team_profile_url"], expect="player-image")
            except Exception as exc:  # noqa: BLE001 - keep other teams going
                self.warnings.append(f"team page failed: {entry['team_id']}: {exc}")
                continue
            self._save_raw(f"team-{entry['team_id']}", page)
            team, roster = parse_team_page(page, entry["team_id"], season, now)
            team.team_short_name = entry["team_short_name"] or team.team_short_name
            if not team.team_logo_url:
                team.team_logo_url = entry["team_logo_url"]
            team_rows.append(team)
            roster_rows.extend(roster)
        self.log(f"roster entries {len(roster_rows)}")

        standings_rows, season_info = parse_standings(home_html, season, now, team_ids)
        for row in standings_rows:
            if not row.team_id:
                row.team_id = team_ids.get(row.team_short_name.upper(), "")
        self.log(f"standings {len(standings_rows)}")

        schedule_html = self.fetcher.get(f"{BASE_URL}/schedule", expect="regular-season")
        self._save_raw("schedule", schedule_html)
        matches = parse_schedule(schedule_html, season, now)
        self.log(f"matches {len(matches)}")

        stats_html = self.fetcher.get(f"{BASE_URL}/statistics", expect="table-team-statistics")
        self._save_raw("statistics", stats_html)
        bundle = parse_statistics(stats_html, season, now, f"{BASE_URL}/statistics")
        self.log(
            f"statistics: {len(bundle.team_stats)} teams, {len(bundle.player_stats)} players, "
            f"{len(bundle.hero_stats)} heroes"
        )

        # -- match details ------------------------------------------------
        details: list[MatchDetail] = []
        meta: dict[str, dict] = {}
        targets = [m for m in matches if m.match_status == "completed" and m.detail_url]
        if self.max_matches is not None:
            targets = targets[: self.max_matches]
        failures = 0
        for index, match in enumerate(targets, start=1):
            try:
                html = self.fetcher.get(match.detail_url, expect="match-detail", max_age=30 * 24 * 3600)
            except Exception as exc:  # noqa: BLE001 - a single match must not stop the run
                failures += 1
                self.warnings.append(f"match detail failed: {match.match_id}: {exc}")
                continue
            self._save_raw(f"match-{match.match_id}", html)
            try:
                detail = parse_match_detail(html, match.match_id)
            except Exception as exc:  # noqa: BLE001 - parser guard
                failures += 1
                self.warnings.append(f"match detail parse failed: {match.match_id}: {exc}")
                continue
            details.append(detail)
            meta[match.match_id] = {
                "season": season,
                "stage": match.stage,
                "match_date": match.match_date,
                "match_time": match.match_time,
                "round": match.round,
            }
            if index % 20 == 0:
                self.log(f"  match details {index}/{len(targets)}")
        self.log(f"match details {len(details)} ok, {failures} failed")

        # -- build rows ---------------------------------------------------
        schedule_rows = self._schedule_rows(matches, team_ids)
        team_stat_rows = []
        for stat in bundle.team_stats:
            team_id = team_ids.get(stat.team_name.upper()) or stat.team_id
            team_stat_rows.append(
                {
                    "season": stat.season,
                    "team_id": team_id,
                    "team_name": stat.team_name,
                    "kills": stat.kills,
                    "deaths": stat.deaths,
                    "assists": stat.assists,
                    "gold": stat.gold,
                    "damage": stat.damage,
                    "lord": stat.lord,
                    "tortoise": stat.tortoise,
                    "tower": stat.tower,
                    "source_url": stat.source_url,
                    "scraped_at": stat.scraped_at,
                }
            )
        self._build_aliases(roster_rows, [])
        player_stat_rows = [
            {
                "season": stat.season,
                "team_id": stat.team_id,
                "player_id": self._resolve_player(stat.team_id, stat.player_name)[0],
                "player_name": self._resolve_player(stat.team_id, stat.player_name)[1],
                "lane": stat.lane,
                "games": stat.games,
                "kills": stat.kills,
                "avg_kills": stat.avg_kills,
                "deaths": stat.deaths,
                "avg_deaths": stat.avg_deaths,
                "assists": stat.assists,
                "avg_assists": stat.avg_assists,
                "avg_kda": stat.avg_kda,
                "kill_participation": stat.kill_participation,
                "source_url": stat.source_url,
                "scraped_at": stat.scraped_at,
            }
            for stat in bundle.player_stats
        ]
        self._build_aliases(roster_rows, player_stat_rows)
        detail_rows, game_rows, player_rows, draft_rows = self._game_rows(details, meta, matches, team_ids)
        hero_stat_rows = [
            {
                "season": stat.season,
                "hero_name": stat.hero_name,
                "picks": stat.picks,
                "bans": stat.bans,
                "wins": stat.wins,
                "win_rate": stat.win_rate,
                "source_url": stat.source_url,
                "scraped_at": stat.scraped_at,
            }
            for stat in bundle.hero_stats
        ]
        hero_pool_rows = [
            {
                "season": row.season,
                "team_id": row.team_id,
                "player_id": self._resolve_player(row.team_id, row.player_name)[0],
                "player_name": self._resolve_player(row.team_id, row.player_name)[1],
                "lane": row.lane,
                "distinct_heroes": row.distinct_heroes,
                "hero_name": row.hero_name,
                "picks": row.picks,
                "win_rate": row.win_rate,
                "source_url": row.source_url,
                "scraped_at": row.scraped_at,
            }
            for row in bundle.hero_pools
        ]
        player_pool_rows = [
            {
                "season": row.season,
                "hero_name": row.hero_name,
                "total_picks": row.total_picks,
                "team_id": row.team_id,
                "player_id": self._resolve_player(row.team_id, row.player_name)[0],
                "player_name": self._resolve_player(row.team_id, row.player_name)[1],
                "picks": row.picks,
                "win_rate": row.win_rate,
                "source_url": row.source_url,
                "scraped_at": row.scraped_at,
            }
            for row in bundle.player_pools
        ]
        mvp_rows = [
            {
                "season": row.season,
                "rank": row.rank,
                "points": row.points,
                "player_display": row.player_display,
                "team_id": row.team_id,
                "player_id": self._resolve_player(row.team_id, row.player_name)[0],
                "player_name": self._resolve_player(row.team_id, row.player_name)[1],
                "source_url": row.source_url,
                "scraped_at": row.scraped_at,
            }
            for row in bundle.mvp
        ]

        players = self._players(roster_rows, player_stat_rows, player_rows)
        roster_rows_out = [
            {
                "season": row.season,
                "team_id": row.team_id,
                "player_id": row.player_id,
                "role": row.role,
                "roster_status": row.roster_status,
                "valid_from": row.valid_from,
                "valid_until": row.valid_until,
                "source_url": row.source_url,
            }
            for row in roster_rows
        ]
        team_rows_out = [
            {
                "season": row.season,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "team_short_name": row.team_short_name,
                "team_logo_url": row.team_logo_url,
                "team_profile_url": row.team_profile_url,
                "roster_reference": row.roster_reference,
                "scraped_at": row.scraped_at,
            }
            for row in team_rows
        ]
        standings_out = [
            {
                "season": row.season,
                "stage": row.stage,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "rank": row.rank,
                "matches_played": row.matches_played,
                "wins": row.wins,
                "losses": row.losses,
                "game_wins": row.game_wins,
                "game_losses": row.game_losses,
                "game_difference": row.game_difference,
                "points": row.points,
                "win_rate": row.win_rate,
                "source_url": row.source_url,
                "scraped_at": row.scraped_at,
            }
            for row in standings_rows
        ]

        # -- write --------------------------------------------------------
        self.stats["mpl-schedule.csv"] = upsert_csv(
            self.out / "mpl-schedule.csv", schedule_rows, SCHEDULE_COLUMNS, ("season", "stage", "match_id")
        )
        self.stats["mpl-teams.csv"] = upsert_csv(
            self.out / "mpl-teams.csv", team_rows_out, TEAM_COLUMNS, ("season", "team_id")
        )
        self.stats["mpl-standings.csv"] = upsert_csv(
            self.out / "mpl-standings.csv", standings_out, STANDING_COLUMNS, ("season", "stage", "team_id")
        )
        self.stats["mpl-players.csv"] = upsert_csv(
            self.out / "mpl-players.csv", players, PLAYER_COLUMNS, ("player_id", "season")
        )
        self.stats["mpl-rosters.csv"] = upsert_csv(
            self.out / "mpl-rosters.csv", roster_rows_out, ROSTER_COLUMNS, ("season", "team_id", "player_id")
        )
        self.stats["mpl-match-details.csv"] = upsert_csv(
            self.out / "mpl-match-details.csv", detail_rows, MATCH_DETAIL_COLUMNS, ("match_id",)
        )
        self.stats["mpl-games.csv"] = upsert_csv(
            self.out / "mpl-games.csv", game_rows, GAME_COLUMNS, ("match_id", "game_no")
        )
        self.stats["mpl-game-players.csv"] = upsert_csv(
            self.out / "mpl-game-players.csv",
            player_rows,
            GAME_PLAYER_COLUMNS,
            ("match_id", "game_no", "team_id", "player_id"),
        )
        self.stats["mpl-drafts.csv"] = upsert_csv(
            self.out / "mpl-drafts.csv", draft_rows, DRAFT_COLUMNS, ("match_id", "game_no", "team_id", "hero_name")
        )
        self.stats["mpl-team-stats.csv"] = upsert_csv(
            self.out / "mpl-team-stats.csv", team_stat_rows, TEAM_STAT_COLUMNS, ("season", "team_id")
        )
        self.stats["mpl-player-stats.csv"] = upsert_csv(
            self.out / "mpl-player-stats.csv", player_stat_rows, PLAYER_STAT_COLUMNS, ("season", "team_id", "player_name")
        )
        self.stats["mpl-hero-stats.csv"] = upsert_csv(
            self.out / "mpl-hero-stats.csv", hero_stat_rows, HERO_STAT_COLUMNS, ("season", "hero_name")
        )
        self.stats["mpl-hero-pools.csv"] = upsert_csv(
            self.out / "mpl-hero-pools.csv",
            hero_pool_rows,
            HERO_POOL_COLUMNS,
            ("season", "team_id", "player_name", "hero_name"),
        )
        self.stats["mpl-player-pools.csv"] = upsert_csv(
            self.out / "mpl-player-pools.csv",
            player_pool_rows,
            PLAYER_POOL_COLUMNS,
            ("season", "hero_name", "team_id", "player_name"),
        )
        self.stats["mpl-mvp.csv"] = upsert_csv(
            self.out / "mpl-mvp.csv", mvp_rows, MVP_COLUMNS, ("season", "team_id", "player_name")
        )

        if season_info is not None:
            self.stats["mpl-seasons.csv"] = upsert_csv(
                self.out / "mpl-seasons.csv",
                [
                    {
                        "season": season_info.season,
                        "season_label": season_info.season_label,
                        "playoffs_bracket_url": season_info.playoffs_bracket_url,
                        "source_url": season_info.source_url,
                        "scraped_at": season_info.scraped_at,
                    }
                ],
                SEASON_COLUMNS,
                ("season",),
            )

        # -- analytics ----------------------------------------------------
        self.stats["mpl-hero-synergy.csv"] = write_csv(
            self.out / "mpl-hero-synergy.csv", analytics.hero_synergy(details, meta), SYNERGY_COLUMNS
        )
        self.stats["mpl-hero-matchups.csv"] = write_csv(
            self.out / "mpl-hero-matchups.csv", analytics.hero_matchups(details, meta), MATCHUP_COLUMNS
        )
        self.stats["mpl-player-hero-stats.csv"] = write_csv(
            self.out / "mpl-player-hero-stats.csv", analytics.player_hero_stats(details, meta), PLAYER_HERO_COLUMNS
        )
        self.stats["mpl-head-to-head.csv"] = write_csv(
            self.out / "mpl-head-to-head.csv", analytics.head_to_head(matches, team_ids), H2H_COLUMNS
        )
        self.stats["mpl-team-form.csv"] = write_csv(
            self.out / "mpl-team-form.csv", analytics.team_form(matches, team_ids), FORM_COLUMNS
        )

        manifest = self._manifest(season, now, details)
        (self.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self._quality_report(manifest)
        return manifest

    # -- row builders ----------------------------------------------------
    def _schedule_rows(self, matches: list[MatchRow], team_ids: dict[str, str]) -> list[dict]:
        rows = []
        for match in matches:
            winner = ""
            if match.match_status == "completed":
                s1 = int(match.team1_score or 0)
                s2 = int(match.team2_score or 0)
                if s1 > s2:
                    winner = match.team1_name
                elif s2 > s1:
                    winner = match.team2_name
            rows.append(
                {
                    "season": match.season,
                    "stage": match.stage,
                    "match_id": match.match_id,
                    "match_date": match.match_date,
                    "match_time": match.match_time,
                    "round": match.round,
                    "match_status": match.match_status,
                    "team1_id": team_ids.get(match.team1_name.upper(), ""),
                    "team1_name": match.team1_name,
                    "team2_id": team_ids.get(match.team2_name.upper(), ""),
                    "team2_name": match.team2_name,
                    "team1_score": match.team1_score,
                    "team2_score": match.team2_score,
                    "winner_team_id": team_ids.get(winner.upper(), "") if winner else "",
                    "match_url": match.detail_url,
                    "scraped_at": match.scraped_at,
                }
            )
        return rows

    def _game_rows(
        self,
        details: list[MatchDetail],
        meta: dict[str, dict],
        matches: list[MatchRow],
        team_ids: dict[str, str],
    ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        by_id = {m.match_id: m for m in matches}
        detail_rows: list[dict] = []
        game_rows: list[dict] = []
        player_rows: list[dict] = []
        draft_rows: list[dict] = []

        for detail in details:
            info = meta.get(detail.match_id, {})
            match = by_id.get(detail.match_id)
            durations = [g.duration_seconds for g in detail.games if g.duration_seconds]
            winner_name = detail.games[0].winner_team_name if detail.games else ""
            detail_rows.append(
                {
                    "match_id": detail.match_id,
                    "season": info.get("season"),
                    "stage": info.get("stage"),
                    "match_date": info.get("match_date"),
                    "match_time": info.get("match_time"),
                    "round": info.get("round"),
                    "team1_id": team_ids.get(detail.team1_name.upper(), ""),
                    "team1_name": detail.team1_name,
                    "team1_score": detail.team1_score,
                    "team2_id": team_ids.get(detail.team2_name.upper(), ""),
                    "team2_name": detail.team2_name,
                    "team2_score": detail.team2_score,
                    "winner_team_id": "",
                    "games_played": len(detail.games),
                    "total_duration_seconds": sum(durations) if durations else "",
                    "avg_game_duration_seconds": round(sum(durations) / len(durations)) if durations else "",
                    "source_url": match.detail_url if match else f"{BASE_URL}/match-detail/{detail.match_id}",
                    "scraped_at": match.scraped_at if match else "",
                }
            )
            if match is not None and match.match_status == "completed":
                s1 = int(match.team1_score or 0)
                s2 = int(match.team2_score or 0)
                if s1 != s2:
                    winner_name = match.team1_name if s1 > s2 else match.team2_name
            if detail_rows[-1]["team1_score"] is not None and detail_rows[-1]["team2_score"] is not None:
                if detail_rows[-1]["team1_score"] > detail_rows[-1]["team2_score"]:
                    winner_name = detail.team1_name
                elif detail_rows[-1]["team2_score"] > detail_rows[-1]["team1_score"]:
                    winner_name = detail.team2_name
            detail_rows[-1]["winner_team_id"] = team_ids.get(winner_name.upper(), "") if winner_name else ""

            for game in detail.games:
                game_rows.append(
                    {
                        "match_id": game.match_id,
                        "season": info.get("season"),
                        "stage": info.get("stage"),
                        "match_date": info.get("match_date"),
                        "game_no": game.game_no,
                        "game_uid": game.game_uid,
                        "duration_seconds": game.duration_seconds,
                        "winner_team_id": team_ids.get(game.winner_team_name.upper(), ""),
                        "winner_team_name": game.winner_team_name,
                        "winner_kills": game.winner_kills,
                        "loser_team_id": team_ids.get(game.loser_team_name.upper(), ""),
                        "loser_team_name": game.loser_team_name,
                        "loser_kills": game.loser_kills,
                        "source_url": match.detail_url if match else f"{BASE_URL}/match-detail/{detail.match_id}",
                        "scraped_at": match.scraped_at if match else "",
                    }
                )
                for player in game.players:
                    team_id = team_ids.get(player.team_name.upper(), "")
                    player_id, canonical = self._resolve_player(
                        team_id or slugify(player.team_name), player.player_name
                    )
                    player_rows.append(
                        {
                            "match_id": player.match_id,
                            "game_no": player.game_no,
                            "season": info.get("season"),
                            "stage": info.get("stage"),
                            "side": player.side,
                            "team_id": team_id,
                            "team_name": player.team_name,
                            "player_id": player_id,
                            "player_name": canonical,
                            "hero_name": player.hero_name,
                            "hero_id": player.hero_id,
                            "kills": player.kills,
                            "deaths": player.deaths,
                            "assists": player.assists,
                            "damage_dealt": player.damage_dealt,
                            "damage_taken": player.damage_taken,
                            "tower_damage": player.tower_damage,
                            "gold": player.gold,
                            "emblem_id": player.emblem_id,
                            "rune_ids": player.rune_ids,
                            "item_ids": player.item_ids,
                            "source_url": match.detail_url if match else f"{BASE_URL}/match-detail/{detail.match_id}",
                            "scraped_at": match.scraped_at if match else "",
                        }
                    )
                    if player.hero_name:
                        draft_rows.append(
                            {
                                "match_id": player.match_id,
                                "game_no": player.game_no,
                                "season": info.get("season"),
                                "stage": info.get("stage"),
                                "side": player.side,
                                "team_id": team_id,
                                "player_name": canonical,
                                "hero_name": player.hero_name,
                                "pick_slot": player.player_slot,
                                "source_url": match.detail_url if match else f"{BASE_URL}/match-detail/{detail.match_id}",
                                "scraped_at": match.scraped_at if match else "",
                            }
                        )
        return detail_rows, game_rows, player_rows, draft_rows

    def _players(
        self,
        roster_rows: list[RosterEntry],
        player_stats: list[dict],
        game_player_rows: list[dict] | None = None,
    ) -> list[dict]:
        seen: dict[str, dict] = {}
        for entry in roster_rows:
            seen[entry.player_id] = {
                "player_id": entry.player_id,
                "player_name": entry.player_name,
                "in_game_name": entry.in_game_name,
                "current_team_id": entry.team_id,
                "role": entry.role,
                "nationality": "",
                "profile_url": "",
                "season": entry.season,
                "scraped_at": entry.scraped_at,
            }
        for stat in player_stats:
            player_id = stat["player_id"]
            if player_id in seen:
                continue
            seen[player_id] = {
                "player_id": player_id,
                "player_name": stat["player_name"],
                "in_game_name": stat["player_name"],
                "current_team_id": stat["team_id"],
                "role": stat["lane"],
                "nationality": "",
                "profile_url": "",
                "season": stat["season"],
                "scraped_at": stat["scraped_at"],
            }
        # Players who appear in game logs but not on the current roster page:
        # the site only publishes the active roster, so earlier-season players
        # would otherwise be missing from the player dimension.
        for row in game_player_rows or []:
            player_id = row["player_id"]
            if player_id in seen:
                continue
            seen[player_id] = {
                "player_id": player_id,
                "player_name": row["player_name"],
                "in_game_name": row["player_name"],
                "current_team_id": row["team_id"],
                "role": "",
                "nationality": "",
                "profile_url": "",
                "season": row["season"],
                "scraped_at": row["scraped_at"],
            }
        return sorted(seen.values(), key=lambda r: (r["current_team_id"], r["player_name"].lower()))

    # -- reporting -------------------------------------------------------
    def _manifest(self, season: int, now: str, details: list[MatchDetail]) -> dict:
        return {
            "generated_at": now,
            "generator": f"mplid-dataset {__version__}",
            "source": BASE_URL,
            "season": season,
            "duration_seconds": round(time.time() - self.started, 1),
            "fetch": self.fetcher.stats,
            "match_details_parsed": len(details),
            "games_parsed": sum(len(d.games) for d in details),
            "player_game_rows": sum(len(g.players) for d in details for g in d.games),
            "tables": self.stats,
            "warnings": self.warnings,
        }

    def _quality_report(self, manifest: dict) -> None:
        checks = []
        for name in sorted(self.stats):
            path = self.out / name
            rows = _read_csv(path)
            if not rows:
                checks.append({"table": name, "rows": 0, "status": "empty"})
                continue
            blank = {field: sum(1 for r in rows if not squash(r.get(field, ""))) for field in rows[0]}
            checks.append(
                {
                    "table": name,
                    "rows": len(rows),
                    "columns": list(rows[0].keys()),
                    "blank_fields": {k: v for k, v in blank.items() if v},
                    "status": "ok",
                }
            )

        report = {
            "generated_at": manifest["generated_at"],
            "season": manifest["season"],
            "tables": checks,
            "warnings": self.warnings,
        }
        (self.out / "data-quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        lines = [
            f"# MPL ID data quality report",
            "",
            f"- Generated: {manifest['generated_at']}",
            f"- Season: {manifest['season']}",
            f"- Source: {BASE_URL}",
            "",
            "| table | rows | fields with blanks |",
            "| --- | --- | --- |",
        ]
        for check in checks:
            blanks = ", ".join(f"`{k}`={v}" for k, v in check.get("blank_fields", {}).items()) or "-"
            lines.append(f"| {check['table']} | {check['rows']} | {blanks} |")
        lines += [
            "",
            "## Known gaps in the public source",
            "",
            "- Per-game bans are not published on match detail pages. Only season-level ban totals exist (`mpl-hero-stats.csv`).",
            "- Player nationality, profile URLs and contract dates are not published; those columns stay empty.",
            "- Player statistics are season aggregates; per-game values exist only in `mpl-game-players.csv`.",
            "- Only the current season is served. The site has no season selector or archive route.",
            "- Playoff standings are published as an image only; the URL is kept in `mpl-seasons.csv`.",
            "- `matches_played` and `win_rate` in `mpl-standings.csv` are derived from the official W-L record.",
            "",
        ]
        if self.warnings:
            lines += ["## Warnings", ""] + [f"- {w}" for w in self.warnings] + [""]
        (self.out / "data-quality.md").write_text("\n".join(lines), encoding="utf-8")
