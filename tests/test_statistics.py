"""Statistics page: six tabs, one consistent pick total across three tables."""

from __future__ import annotations

import pytest

from mplid.statistics import parse_statistics

SOURCE = "https://id-mpl.com/statistics"


@pytest.fixture(scope="module")
def bundle(statistics_html):
    return parse_statistics(statistics_html, 18, "test", SOURCE)


def test_team_totals(bundle):
    assert len(bundle.team_stats) == 9
    btr = next(t for t in bundle.team_stats if t.team_name == "BTR")
    assert btr.kills == 502
    assert btr.deaths == 439
    assert btr.gold == 2044010
    assert btr.tower == 231


def test_player_totals(bundle):
    assert len(bundle.player_stats) == 66
    moreno = next(p for p in bundle.player_stats if p.player_name == "MORENOOO")
    assert moreno.team_id == "btr"
    assert moreno.lane == "MID"
    assert moreno.games == 39
    assert moreno.avg_kills == pytest.approx(2.54)
    assert moreno.kill_participation == pytest.approx(0.81)


def test_hero_totals(bundle):
    assert len(bundle.hero_stats) == 133
    hirara = next(h for h in bundle.hero_stats if h.hero_name == "Hirara")
    assert hirara.picks == 84
    assert hirara.bans == 80
    assert hirara.wins == 45
    assert hirara.win_rate == pytest.approx(0.54)
    assert any(h.picks == 0 and h.bans == 0 for h in bundle.hero_stats)


def test_pick_totals_agree_across_tables(bundle):
    hero_picks = sum(h.picks or 0 for h in bundle.hero_stats)
    pool_picks = sum(r.picks or 0 for r in bundle.hero_pools)
    player_pool_picks = sum(r.picks or 0 for r in bundle.player_pools)
    assert hero_picks == pool_picks == player_pool_picks == 1740


def test_hero_pool_rows(bundle):
    assert len(bundle.hero_pools) == 621
    row = next(r for r in bundle.hero_pools if r.player_name == "MORENOOO" and r.hero_name == "Selena")
    assert row.team_id == "btr"
    assert row.lane == "MID"
    assert row.distinct_heroes == 10
    assert row.picks == 13
    assert row.win_rate == pytest.approx(0.31)


def test_player_pool_rows(bundle):
    assert len(bundle.player_pools) == 621
    row = next(r for r in bundle.player_pools if r.hero_name == "Miya" and r.player_name == "Zeonn")
    assert row.team_id == "navi"
    assert row.total_picks == 10
    assert row.picks == 7
    assert row.win_rate == pytest.approx(0.71)


def test_mvp_and_leaderboards(bundle):
    assert len(bundle.mvp) == 8
    top = next(m for m in bundle.mvp if m.rank == 1)
    assert top.player_display == "TLID KEVIN"
    assert top.team_id == "tlid"
    assert top.player_name == "KEVIN"
    assert top.points == 151

    assert len(bundle.top_heroes) == 15
    picks = [t for t in bundle.top_heroes if t["leaderboard"] == "Top 5 Pick"]
    assert len(picks) == 5
    assert picks[0]["hero_name"] == "Paquito"
    assert picks[0]["value_raw"] == "87"
