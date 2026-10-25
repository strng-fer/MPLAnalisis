"""Parser for https://id-mpl.com/match-detail/<id>.

The endpoint returns an HTML fragment (not JSON) with:

* a series header: one logo per team and the series score;
* one tab per game (``GAME 1`` ... ``GAME n``);
* inside a tab, two blocks in winner-then-loser order, each carrying the team
  name and its kill count, plus a clock with the game duration;
* ten player blocks in the same order as those two blocks: hero, IGN, emblem,
  three runes, five items, KDA and four extra figures (damage dealt, damage
  taken, tower damage, gold - the meaning follows the icon next to each one).

Bans are not part of this payload. Ban totals only exist on the statistics
page, so no per-game ban rows can be produced from this source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .parse import parse_duration, squash, to_int

KDA_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*/\s*(\d+)")
HERO_ID_RE = re.compile(r"/hero_h/(\d+)\.png")
HERO_NAME_RE = re.compile(r"/heroes/([^/?]+)\.(?:jpg|png|webp)")


@dataclass
class GamePlayer:
    match_id: str
    game_no: int
    side: str
    team_name: str
    player_name: str
    hero_name: str
    hero_id: str
    kills: int | None
    deaths: int | None
    assists: int | None
    damage_dealt: int | None
    damage_taken: int | None
    tower_damage: int | None
    gold: int | None
    emblem_id: str
    rune_ids: str
    item_ids: str
    hero_icon_url: str
    player_slot: int


@dataclass
class Game:
    match_id: str
    game_no: int
    game_uid: str
    duration_seconds: int | None
    duration_raw: str
    winner_team_name: str
    loser_team_name: str
    winner_kills: int | None
    loser_kills: int | None
    players: list[GamePlayer] = field(default_factory=list)


@dataclass
class MatchDetail:
    match_id: str
    team1_name: str
    team2_name: str
    team1_logo_url: str
    team2_logo_url: str
    team1_score: int | None
    team2_score: int | None
    games: list[Game] = field(default_factory=list)


def _hero_from_img(img) -> tuple[str, str, str]:
    if img is None:
        return "", "", ""
    src = img.get("src") or ""
    alt = (img.get("alt") or "").strip()
    hero_id = ""
    match = HERO_ID_RE.search(src)
    if match:
        hero_id = match.group(1)
    name = alt
    if not name or name.isdigit():
        match = HERO_NAME_RE.search(src)
        if match:
            name = match.group(1).replace("%20", " ")
    return name, hero_id, src


def _side_block(node) -> tuple[str, int | None]:
    """Read one winner/loser block: (team short name, kills)."""
    team = ""
    kills = None
    for div in node.select("div"):
        text = squash(div.get_text(" ", strip=True))
        if not text:
            continue
        if div.select_one("img[src*='swords']") is not None:
            number = to_int(text)
            if number is not None and re.fullmatch(r"\d+", text):
                kills = number
            continue
        style = div.get("style") or ""
        if "font-size: 1rem" in style and not team:
            team = text
    return team, kills


def parse_match_detail(html: str, match_id: str) -> MatchDetail:
    soup = BeautifulSoup(html, "lxml")
    detail = MatchDetail(
        match_id=match_id,
        team1_name="",
        team2_name="",
        team1_logo_url="",
        team2_logo_url="",
        team1_score=None,
        team2_score=None,
    )

    header = soup.select_one("div.d-flex.flex-row.justify-content-center.align-items-center")
    if header is not None:
        logos = [img for img in header.select("img") if "teams/" in (img.get("src") or "")]
        if logos:
            detail.team1_logo_url = logos[0].get("src") or ""
            detail.team1_name = (logos[0].get("alt") or "").strip()
        if len(logos) > 1:
            detail.team2_logo_url = logos[1].get("src") or ""
            detail.team2_name = (logos[1].get("alt") or "").strip()
        scores = []
        for div in header.select("div[style*='font-size: 3rem']"):
            value = to_int(squash(div.get_text(" ", strip=True)))
            if value is not None:
                scores.append(value)
        if len(scores) >= 2:
            detail.team1_score, detail.team2_score = scores[0], scores[1]

    for index, tab in enumerate(soup.select(".tab-content.match-detail"), start=1):
        tab_id = tab.get("id") or ""
        match = re.search(r"info-(\d+)", tab_id)
        game_uid = match.group(1) if match else f"{match_id}-{index}"

        sides = []
        for block in tab.select("div.victory, div.defeat"):
            team, kills = _side_block(block)
            sides.append({"team": team, "kills": kills, "win": "victory" in (block.get("class") or [])})

        duration_raw = ""
        clock = tab.select_one("img[src*='clock']")
        if clock is not None and clock.parent is not None:
            duration_raw = squash(clock.parent.get_text(" ", strip=True))

        winner = next((s for s in sides if s["win"]), sides[0] if sides else {"team": "", "kills": None})
        loser = next((s for s in sides if not s["win"]), sides[1] if len(sides) > 1 else {"team": "", "kills": None})

        game = Game(
            match_id=match_id,
            game_no=index,
            game_uid=game_uid,
            duration_seconds=parse_duration(duration_raw),
            duration_raw=duration_raw,
            winner_team_name=winner["team"],
            loser_team_name=loser["team"],
            winner_kills=winner["kills"],
            loser_kills=loser["kills"],
        )

        ordered = [s["team"] for s in sides]
        for side_index, column in enumerate(tab.select(".row > div.col-6")):
            side = "winner" if side_index < len(sides) and sides[side_index]["win"] else "loser"
            team_name = ordered[side_index] if side_index < len(ordered) else ""
            for slot, block in enumerate(column.select("div.my-3"), start=1):
                # Winner blocks are mirrored compared to loser blocks, so the
                # name and hero are located by their inline typography, not by
                # document position.
                name_node = block.select_one("div[style*='font-weight: 700']")
                hero_node = block.select_one("div[style*='font-size: 0.9rem']:not(.data)")
                player_name = squash(name_node.get_text(" ", strip=True)) if name_node is not None else ""
                hero_name = squash(hero_node.get_text(" ", strip=True)) if hero_node is not None else ""
                hero_img = None
                for img in block.select("img"):
                    src = img.get("src") or ""
                    if "/hero_h/" in src or "/heroes/" in src:
                        hero_img = img
                        break
                img_name, hero_id, hero_icon = _hero_from_img(hero_img)
                hero_name = hero_name or img_name
                kda_node = block.select_one(".kda-content")
                kda_text = squash(kda_node.get_text(" ", strip=True)) if kda_node is not None else ""
                kda = KDA_RE.search(kda_text)
                emblem = ""
                runes = []
                items = []
                for img in block.select("img"):
                    src = img.get("src") or ""
                    alt = (img.get("alt") or "").strip()
                    if "/emblem/" in src:
                        emblem = alt
                    elif "/rune/" in src:
                        runes.append(alt)
                    elif "/equipment/" in src:
                        items.append(alt)

                figures = []
                data = block.select_one("div[id^=data-content]")
                if data is not None:
                    for div in data.find_all("div", recursive=False):
                        figures.append(to_int(squash(div.get_text(" ", strip=True))))
                while len(figures) < 4:
                    figures.append(None)

                game.players.append(
                    GamePlayer(
                        match_id=match_id,
                        game_no=index,
                        side=side,
                        team_name=team_name,
                        player_name=player_name,
                        hero_name=hero_name,
                        hero_id=hero_id,
                        kills=int(kda.group(1)) if kda else None,
                        deaths=int(kda.group(2)) if kda else None,
                        assists=int(kda.group(3)) if kda else None,
                        damage_dealt=figures[0],
                        damage_taken=figures[1],
                        tower_damage=figures[2],
                        gold=figures[3],
                        emblem_id=emblem,
                        rune_ids="|".join(runes),
                        item_ids="|".join(items),
                        hero_icon_url=hero_icon,
                        player_slot=slot,
                    )
                )

        detail.games.append(game)

    return detail
