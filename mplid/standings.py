"""Parser for the standings tables on https://id-mpl.com/home.

Two tables are published:

``#standing-regular-season``
    Team, Match Point, Match W-L, Net Game Win, Game W-L. Every column is an
    official value; ``matches_played`` and ``win_rate`` are derived here and
    flagged as such in the README.

``#standing-playoffs``
    Only a bracket image plus a "Regular Season Rank" summary table. The
    bracket carries no machine readable numbers, so it is recorded as an image
    URL in ``mpl-seasons.csv`` instead of being parsed into standings rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .parse import first_int, split_record, squash


@dataclass
class StandingRow:
    season: int
    stage: str
    team_id: str
    team_name: str
    team_short_name: str
    rank: int | None
    matches_played: int | None
    wins: int | None
    losses: int | None
    game_wins: int | None
    game_losses: int | None
    game_difference: int | None
    points: int | None
    win_rate: float | None
    source_url: str
    scraped_at: str


@dataclass
class SeasonInfo:
    season: int
    season_label: str
    playoffs_bracket_url: str
    source_url: str
    scraped_at: str


def _team_cell(tr) -> tuple[str, str, str]:
    """Return (short name, display name, logo url) from a team-info cell."""
    cell = tr.select_one("td.team-info")
    if cell is None:
        return "", "", ""
    logo = cell.select_one("img")
    short = ""
    full = ""
    for span in cell.select(".team-name span"):
        classes = " ".join(span.get("class") or [])
        text = squash(span.get_text(" ", strip=True))
        if "d-lg-none" in classes and not short:
            short = text
        elif "d-lg-block" in classes and not full:
            full = text
    if not short and logo is not None:
        short = (logo.get("alt") or "").strip()
    if not full:
        full = squash(cell.select_one(".team-name").get_text(" ", strip=True)) if cell.select_one(".team-name") else short
    return short, full or short, (logo.get("src") or "") if logo is not None else ""


def parse_standings(
    html: str,
    season: int,
    scraped_at: str,
    team_ids: dict[str, str] | None = None,
    source_url: str = "https://id-mpl.com/home",
) -> tuple[list[StandingRow], SeasonInfo | None]:
    soup = BeautifulSoup(html, "lxml")
    team_ids = team_ids or {}
    rows: list[StandingRow] = []

    table = soup.select_one("#standing-regular-season table")
    if table is not None:
        headers = [squash(th.get_text(" ", strip=True)).lower() for th in table.select("thead th")]
        index = {name: i for i, name in enumerate(headers)}

        def col(cells, name, default=None):
            pos = index.get(name)
            if pos is None or pos >= len(cells):
                return default
            return cells[pos]

        for tr in table.select("tbody tr"):
            cells = tr.find_all("td", recursive=False)
            if not cells:
                continue
            short, full, logo = _team_cell(tr)
            if not short and not full:
                continue
            rank = first_int(squash(cells[0].get_text(" ", strip=True)))
            points = first_int(squash(col(cells, "match point", "").get_text(" ", strip=True)) if col(cells, "match point") else "")
            wins, losses = split_record(
                col(cells, "match w-l").get_text(" ", strip=True) if col(cells, "match w-l") else ""
            )
            game_diff = first_int(
                squash(col(cells, "net game win", "").get_text(" ", strip=True)) if col(cells, "net game win") else ""
            )
            game_wins, game_losses = split_record(
                col(cells, "game w-l").get_text(" ", strip=True) if col(cells, "game w-l") else ""
            )
            played = (wins + losses) if wins is not None and losses is not None else None
            win_rate = round(wins / played, 4) if wins is not None and played else None
            team_id = team_ids.get(short.upper()) or team_ids.get(full.upper()) or ""
            if not team_id:
                match = re.search(r"/teams/([a-z0-9_\-]+?)-\d+\.(?:png|webp)", logo or "")
                team_id = match.group(1) if match else ""
            rows.append(
                StandingRow(
                    season=season,
                    stage="Regular Season",
                    team_id=team_id,
                    team_name=full,
                    team_short_name=short,
                    rank=rank,
                    matches_played=played,
                    wins=wins,
                    losses=losses,
                    game_wins=game_wins,
                    game_losses=game_losses,
                    game_difference=game_diff,
                    points=points,
                    win_rate=win_rate,
                    source_url=source_url,
                    scraped_at=scraped_at,
                )
            )

    info = None
    playoffs = soup.select_one("#standing-playoffs")
    if playoffs is not None:
        img = playoffs.select_one("img")
        info = SeasonInfo(
            season=season,
            season_label=f"MPL ID Season {season}",
            playoffs_bracket_url=(img.get("src") or "") if img is not None else "",
            source_url=source_url,
            scraped_at=scraped_at,
        )

    return rows, info
