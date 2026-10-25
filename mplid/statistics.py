"""Parser for https://id-mpl.com/statistics.

The page is one HTML document with six tabs. Every tab is rendered server side,
so nothing has to be clicked to read the numbers.

Tab                | Table / block                 | Granularity
-------------------+-------------------------------+------------------------------
Teams              | #table-team-statistics        | season totals per team
Players            | #player-team-all and one card | season totals per player
                   | per team                      |
Heroes             | #table-heroes-statistics      | season totals per hero
                   | .top-hero-stats-outer x3      | top 5 pick / ban / win rate
Hero Pools         | #table-hero-pools             | player x hero picks
Player Pools       | #table-player-pools           | hero x player picks
MVP Standings      | .mvp-card                     | MVP points per player

All percentages are converted to 0-1 fractions. ``Total`` in the hero pool
table is the number of distinct heroes a player used, not the number of games.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .parse import first_int, squash, to_float, to_int, to_ratio


@dataclass
class TeamStat:
    season: int
    team_id: str
    team_name: str
    kills: int | None
    deaths: int | None
    assists: int | None
    gold: int | None
    damage: int | None
    lord: int | None
    tortoise: int | None
    tower: int | None
    source_url: str
    scraped_at: str


@dataclass
class PlayerStat:
    season: int
    team_id: str
    player_name: str
    lane: str
    games: int | None
    kills: int | None
    avg_kills: float | None
    deaths: int | None
    avg_deaths: float | None
    assists: int | None
    avg_assists: float | None
    avg_kda: float | None
    kill_participation: float | None
    source_url: str
    scraped_at: str


@dataclass
class HeroStat:
    season: int
    hero_name: str
    picks: int | None
    bans: int | None
    wins: int | None
    win_rate: float | None
    source_url: str
    scraped_at: str


@dataclass
class HeroPoolRow:
    season: int
    team_id: str
    player_name: str
    lane: str
    distinct_heroes: int | None
    hero_name: str
    picks: int | None
    win_rate: float | None
    source_url: str
    scraped_at: str


@dataclass
class PlayerPoolRow:
    season: int
    hero_name: str
    total_picks: int | None
    team_id: str
    player_name: str
    picks: int | None
    win_rate: float | None
    source_url: str
    scraped_at: str


@dataclass
class MvpRow:
    season: int
    rank: int | None
    points: int | None
    player_display: str
    team_id: str
    player_name: str
    source_url: str
    scraped_at: str


@dataclass
class StatisticsBundle:
    team_stats: list[TeamStat] = field(default_factory=list)
    player_stats: list[PlayerStat] = field(default_factory=list)
    hero_stats: list[HeroStat] = field(default_factory=list)
    hero_pools: list[HeroPoolRow] = field(default_factory=list)
    player_pools: list[PlayerPoolRow] = field(default_factory=list)
    mvp: list[MvpRow] = field(default_factory=list)
    top_heroes: list[dict] = field(default_factory=list)


def _team_from_logo(src: str) -> str:
    import re

    match = re.search(r"/teams/([a-z0-9_\-]+?)-\d+\.(?:png|webp)", src or "")
    return match.group(1) if match else ""


def parse_statistics(html: str, season: int, scraped_at: str, source_url: str) -> StatisticsBundle:
    soup = BeautifulSoup(html, "lxml")
    bundle = StatisticsBundle()

    # -- team totals ----------------------------------------------------
    table = soup.select_one("#table-team-statistics")
    if table is not None:
        for tr in table.select("tbody tr"):
            cells = [squash(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(cells) < 9:
                continue
            logo = tr.select_one("img")
            short = ""
            name_node = tr.select_one(".team-name")
            if name_node is not None:
                spans = name_node.select("span")
                short = squash(spans[0].get_text(" ", strip=True)) if spans else squash(name_node.get_text(" ", strip=True))
            bundle.team_stats.append(
                TeamStat(
                    season=season,
                    team_id=_team_from_logo(logo.get("src") if logo is not None else ""),
                    team_name=short,
                    kills=to_int(cells[1]),
                    deaths=to_int(cells[2]),
                    assists=to_int(cells[3]),
                    gold=to_int(cells[4]),
                    damage=to_int(cells[5]),
                    lord=to_int(cells[6]),
                    tortoise=to_int(cells[7]),
                    tower=to_int(cells[8]),
                    source_url=source_url,
                    scraped_at=scraped_at,
                )
            )

    # -- player totals --------------------------------------------------
    for card in soup.select(".player-statistics-card"):
        card_id = card.get("id") or ""
        if not card_id.startswith("player-team-"):
            continue
        team_id = card_id.replace("player-team-", "")
        if team_id == "all":
            continue
        for tr in card.select("tbody tr"):
            cells = tr.find_all("td")
            if len(cells) < 11:
                continue
            name_node = cells[0].select_one(".player-name")
            logo = cells[0].select_one("img")
            player_name = squash(name_node.get_text(" ", strip=True)) if name_node is not None else squash(cells[0].get_text(" ", strip=True))
            values = [squash(td.get_text(" ", strip=True)) for td in cells]
            bundle.player_stats.append(
                PlayerStat(
                    season=season,
                    team_id=team_id or _team_from_logo(logo.get("src") if logo is not None else ""),
                    player_name=player_name,
                    lane=values[1],
                    games=to_int(values[2]),
                    kills=to_int(values[3]),
                    avg_kills=to_float(values[4]),
                    deaths=to_int(values[5]),
                    avg_deaths=to_float(values[6]),
                    assists=to_int(values[7]),
                    avg_assists=to_float(values[8]),
                    avg_kda=to_float(values[9]),
                    kill_participation=to_ratio(values[10]),
                    source_url=source_url,
                    scraped_at=scraped_at,
                )
            )

    # -- hero totals ----------------------------------------------------
    table = soup.select_one("#table-heroes-statistics")
    if table is not None:
        for tr in table.select("tbody tr"):
            cells = [squash(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue
            hero = cells[0]
            if not hero:
                continue
            bundle.hero_stats.append(
                HeroStat(
                    season=season,
                    hero_name=hero,
                    picks=to_int(cells[1]),
                    bans=to_int(cells[2]),
                    wins=to_int(cells[3]),
                    win_rate=to_ratio(cells[4]),
                    source_url=source_url,
                    scraped_at=scraped_at,
                )
            )

    # -- top 5 leaderboards --------------------------------------------
    for outer in soup.select(".top-hero-stats-outer"):
        title_node = outer.select_one("h5")
        title = squash(title_node.get_text(" ", strip=True)) if title_node is not None else ""
        for pos, item in enumerate(outer.select(".hero-info"), start=1):
            name_node = item.select_one(".hero-name")
            value_node = item.select_one(".value")
            bundle.top_heroes.append(
                {
                    "season": season,
                    "leaderboard": title,
                    "rank": pos,
                    "hero_name": squash(name_node.get_text(" ", strip=True)) if name_node is not None else "",
                    "value_raw": squash(value_node.get_text(" ", strip=True)) if value_node is not None else "",
                    "source_url": source_url,
                    "scraped_at": scraped_at,
                }
            )

    # -- hero pools (player x hero) ------------------------------------
    table = soup.select_one("#table-hero-pools")
    if table is not None:
        for tr in table.select("tbody tr"):
            classes = tr.get("class") or []
            team_id = ""
            for cls in classes:
                if cls.startswith("col-team-"):
                    team_id = cls.replace("col-team-", "")
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue
            name_node = cells[0].select_one(".player-name")
            player_name = squash(name_node.get_text(" ", strip=True)) if name_node is not None else squash(cells[0].get_text(" ", strip=True))
            lane = squash(cells[1].get_text(" ", strip=True))
            distinct = to_int(squash(cells[2].get_text(" ", strip=True)))
            for holder in cells[3].select(".hero-pool-outer > div"):
                img = holder.select_one("img.hero-pool-image")
                hero = ""
                if img is not None:
                    src = (img.get("src") or "").split("/heroes/")
                    if len(src) == 2:
                        hero = src[1].rsplit(".", 1)[0].replace("%20", " ")
                pick_node = holder.select_one(".hero-pool-pick")
                count_node = holder.select_one(".hero-pool-count")
                bundle.hero_pools.append(
                    HeroPoolRow(
                        season=season,
                        team_id=team_id,
                        player_name=player_name,
                        lane=lane,
                        distinct_heroes=distinct,
                        hero_name=hero,
                        picks=to_int(squash(pick_node.get_text(" ", strip=True))) if pick_node is not None else None,
                        win_rate=to_ratio(squash(count_node.get_text(" ", strip=True))) if count_node is not None else None,
                        source_url=source_url,
                        scraped_at=scraped_at,
                    )
                )

    # -- player pools (hero x player) ----------------------------------
    table = soup.select_one("#table-player-pools")
    if table is not None:
        for tr in table.select("tbody tr"):
            cells = tr.find_all("td")
            if len(cells) < 3:
                continue
            hero_node = cells[0].select_one(".hero-name")
            hero = squash(hero_node.get_text(" ", strip=True)) if hero_node is not None else squash(cells[0].get_text(" ", strip=True))
            total = to_int(squash(cells[1].get_text(" ", strip=True)))
            for card in cells[2].select(".player-pool-card"):
                info = card.select_one(".player-pool-info")
                label = squash(info.get_text(" ", strip=True)) if info is not None else ""
                team_id, _, player_name = label.partition(" - ")
                pick_node = card.select_one(".player-pool-pick")
                count_node = card.select_one(".player-pool-count")
                bundle.player_pools.append(
                    PlayerPoolRow(
                        season=season,
                        hero_name=hero,
                        total_picks=total,
                        team_id=team_id.strip().lower(),
                        player_name=player_name.strip(),
                        picks=to_int(squash(pick_node.get_text(" ", strip=True))) if pick_node is not None else None,
                        win_rate=to_ratio(squash(count_node.get_text(" ", strip=True))) if count_node is not None else None,
                        source_url=source_url,
                        scraped_at=scraped_at,
                    )
                )

    # -- MVP standings --------------------------------------------------
    for card in soup.select(".mvp-card"):
        rank_node = card.select_one(".rank")
        point_node = card.select_one(".point")
        ign_node = card.select_one(".mvp-ign")
        logo = card.select_one(".mvp-image .team-logo img")
        display = squash(ign_node.get_text(" ", strip=True)) if ign_node is not None else ""
        team_id = _team_from_logo(logo.get("src") if logo is not None else "")
        player_name = display
        if team_id and display.upper().startswith(team_id.upper() + " "):
            player_name = display[len(team_id) + 1 :].strip()
        elif " " in display:
            head, _, tail = display.partition(" ")
            if head.isupper() and len(head) <= 5:
                team_id = team_id or head.lower()
                player_name = tail.strip()
        bundle.mvp.append(
            MvpRow(
                season=season,
                rank=first_int(squash(rank_node.get_text(" ", strip=True))) if rank_node is not None else None,
                points=first_int(squash(point_node.get_text(" ", strip=True))) if point_node is not None else None,
                player_display=display,
                team_id=team_id,
                player_name=player_name,
                source_url=source_url,
                scraped_at=scraped_at,
            )
        )

    return bundle
