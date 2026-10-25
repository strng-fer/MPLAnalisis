"""Parsers for https://id-mpl.com/teams and https://id-mpl.com/team/<slug>.

The team index publishes a card per team: slug (from the profile URL), short
name and logo. The profile page adds the full name, social links and the
"ROSTER SEASON <n>" block: display name, role label and portrait per person.

Only what the page states is stored. The role label is copied verbatim
("Mid Lane", "Coach", "Analyst", ...); no lane normalisation is invented here,
because the statistics page uses a different vocabulary (MID, GOLD, ...).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .parse import squash

TEAM_LINK_RE = re.compile(r"/team/([a-z0-9_\-]+)/?$")


@dataclass
class TeamRow:
    season: int
    team_id: str
    team_name: str
    team_short_name: str
    team_logo_url: str
    team_profile_url: str
    roster_reference: str
    scraped_at: str


@dataclass
class RosterEntry:
    season: int
    team_id: str
    player_id: str
    player_name: str
    in_game_name: str
    role: str
    roster_status: str
    valid_from: str
    valid_until: str
    source_url: str
    player_image_url: str
    scraped_at: str


def parse_team_index(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[dict] = []
    for card in soup.select(".team-card-outer"):
        link = card.select_one("a[href]")
        if link is None:
            continue
        match = TEAM_LINK_RE.search((link.get("href") or "").rstrip("/"))
        if not match:
            continue
        slug = match.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        img = card.select_one("img")
        short = squash(card.select_one(".team-name").get_text(" ", strip=True)) if card.select_one(".team-name") else ""
        out.append(
            {
                "team_id": slug,
                "team_short_name": short or (img.get("alt", "").strip() if img else ""),
                "team_logo_url": (img.get("src") or "") if img else "",
                "team_profile_url": f"https://id-mpl.com/team/{slug}",
            }
        )
    return out


def parse_team_page(html: str, slug: str, season: int, scraped_at: str) -> tuple[TeamRow, list[RosterEntry]]:
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one("#content") or soup

    heading = content.select_one("h4")
    team_name = squash(heading.get_text(" ", strip=True)) if heading else slug.upper()
    logo = ""
    if heading is not None and heading.select_one("img") is not None:
        logo = heading.select_one("img").get("src") or ""

    roster_heading = ""
    roster_entries: list[RosterEntry] = []
    roster_season = season
    for h5 in content.select("h5"):
        text = squash(h5.get_text(" ", strip=True))
        match = re.match(r"(?i)roster season\s*(\d+)", text)
        if not match:
            continue
        roster_heading = text
        roster_season = int(match.group(1))
        break

    source_url = f"https://id-mpl.com/team/{slug}"
    for card in content.select(".player-image"):
        holder = card.parent
        name_node = holder.select_one(".player-name") if holder is not None else None
        role_node = holder.select_one(".player-role") if holder is not None else None
        img = card.select_one("img")
        ign = squash(name_node.get_text(" ", strip=True)) if name_node is not None else ""
        if not ign:
            ign = (img.get("alt") or "").strip() if img is not None else ""
        role = squash(role_node.get_text(" ", strip=True)) if role_node is not None else ""
        if not ign:
            continue
        player_id = f"{slug}:{re.sub(r'[^a-z0-9]+', '-', ign.lower()).strip('-')}"
        roster_entries.append(
            RosterEntry(
                season=roster_season,
                team_id=slug,
                player_id=player_id,
                player_name=ign,
                in_game_name=ign,
                role=role,
                roster_status="active",
                valid_from="",
                valid_until="",
                source_url=source_url,
                player_image_url=(img.get("src") or "") if img is not None else "",
                scraped_at=scraped_at,
            )
        )

    team = TeamRow(
        season=season,
        team_id=slug,
        team_name=team_name,
        team_short_name=slug.upper(),
        team_logo_url=logo,
        team_profile_url=source_url,
        roster_reference=roster_heading,
        scraped_at=scraped_at,
    )
    return team, roster_entries
