"""Parser for https://id-mpl.com/schedule.

The page renders the regular season and the playoff bracket in two tabs. Each
match block is emitted three times in the markup (week tab pane plus two filter
copies), so rows are de-duplicated on their detail id / modal id.

Fields published per match: date (Indonesian), start time (WIB, UTC+7), week
(regular season) or round label (playoffs), both teams, series score, detail id
and VOD link. Upcoming matches carry empty score cells.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .parse import parse_indonesian_date, parse_time, squash

DETAIL_RE = re.compile(r"openMatchDetail\((\d+)\)")
MODAL_RE = re.compile(r'id="modal2?-([\w-]+)"')
WEEK_RE = re.compile(r"^t-week-(\d+)$")


@dataclass
class MatchRow:
    season: int
    stage: str
    match_id: str
    match_key: str
    match_date: str
    match_time: str
    round: str
    week: str
    match_status: str
    team1_name: str
    team2_name: str
    team1_score: str
    team2_score: str
    detail_url: str
    replay_url: str
    source_url: str
    scraped_at: str = ""
    extras: dict = field(default_factory=dict)


def _text(node) -> str:
    return squash(node.get_text(" ", strip=True)) if node else ""


def _week_of(node) -> str:
    for parent in node.parents:
        if getattr(parent, "attrs", None):
            pid = parent.get("id") or ""
            match = WEEK_RE.match(pid)
            if match:
                return match.group(1)
    return ""


def _round_label(node) -> str:
    """Playoff round label sits in the middle cell of the match row."""
    for div in node.select(".time div"):
        text = _text(div)
        if text and re.search(r"(?i)round|bracket|final|semi", text):
            return text
    return ""


def parse_schedule(html: str, season: int, scraped_at: str) -> list[MatchRow]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[MatchRow] = []
    seen: set[str] = set()
    counters: dict[str, int] = {}

    for tab in soup.select(".tab-content"):
        tab_id = tab.get("id") or ""
        if tab_id == "regular-season":
            stage = "Regular Season"
        elif tab_id == "playoffs":
            stage = "Playoffs"
        else:
            continue

        current_date = ""
        for node in tab.descendants:
            if getattr(node, "name", None) != "div":
                continue
            classes = node.get("class") or []
            if "match" not in classes:
                continue
            if "date" in classes:
                current_date = _text(node)
                continue
            teams = node.select(".team")
            if len(teams) < 2:
                continue

            names = [_text(t.select_one(".name")) for t in teams]
            raw = str(node)
            detail = DETAIL_RE.search(raw)
            modal = MODAL_RE.search(raw)
            identity = detail.group(1) if detail else (modal.group(1) if modal else "")
            if not identity:
                identity = f"{current_date}|{names[0]}|{names[1]}|{_round_label(node)}"
            if identity in seen:
                continue
            seen.add(identity)

            scores = [_text(s) for s in node.select(".score.font-primary")]
            replay = node.select_one("a.replay")
            round_label = _round_label(node)
            week = _week_of(node)
            counters[stage] = counters.get(stage, 0) + 1

            match_date = parse_indonesian_date(current_date)
            match_time = parse_time(_text(node.select_one(".time")))
            team1_score = scores[0] if len(scores) > 0 else ""
            team2_score = scores[1] if len(scores) > 1 else ""
            has_result = bool(team1_score and team2_score)
            match_id = detail.group(1) if detail else f"{season}-{stage[:2].lower()}-{counters[stage]:02d}"
            match_key = "|".join(
                [str(season), stage, match_date, names[0] or "TBD", names[1] or "TBD"]
            )

            rows.append(
                MatchRow(
                    season=season,
                    stage=stage,
                    match_id=match_id,
                    match_key=match_key,
                    match_date=match_date,
                    match_time=match_time,
                    round=round_label or (f"Week {week}" if week else ""),
                    week=week,
                    match_status="completed" if has_result else "scheduled",
                    team1_name=names[0],
                    team2_name=names[1],
                    team1_score=team1_score,
                    team2_score=team2_score,
                    detail_url=(
                        f"https://id-mpl.com/match-detail/{detail.group(1)}" if detail else ""
                    ),
                    replay_url=(replay.get("href") or "") if replay else "",
                    source_url="https://id-mpl.com/schedule",
                    scraped_at=scraped_at,
                )
            )

    rows.sort(key=lambda r: (r.match_date, r.match_time, r.stage))
    return rows
