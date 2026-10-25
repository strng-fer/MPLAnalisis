"""Team index and team profile pages."""

from __future__ import annotations

from mplid.teams import parse_team_index, parse_team_page

SLUGS = {"ae", "btr", "dewa", "evos", "geek", "navi", "onic", "rrq", "tlid"}


def test_team_index(teams_html):
    teams = parse_team_index(teams_html)
    assert len(teams) == 9
    assert {t["team_id"] for t in teams} == SLUGS
    for team in teams:
        assert team["team_profile_url"] == f"https://id-mpl.com/team/{team['team_id']}"
        assert team["team_logo_url"].startswith("https://")
        assert team["team_short_name"]


def test_team_page_header(team_btr_html):
    team, roster = parse_team_page(team_btr_html, "btr", 18, "test")
    assert team.team_name == "BIGETRON BY VIT"
    assert team.roster_reference == "ROSTER SEASON 18"
    assert team.team_profile_url == "https://id-mpl.com/team/btr"
    assert team.team_logo_url.startswith("https://")


def test_roster_roles_are_verbatim(team_btr_html):
    _, roster = parse_team_page(team_btr_html, "btr", 18, "test")
    assert len(roster) == 9
    by_name = {r.player_name: r.role for r in roster}
    assert by_name["K DOT"] == "Coach"
    assert by_name["RUBENHOOD"] == "Asst. Coach"
    assert by_name["HER"] == "Analyst"
    assert by_name["MORENOOO"] == "Mid Lane"
    assert by_name["SHOGUN"] == "EXP Lane"
    assert all(r.roster_status == "active" for r in roster)
    assert all(r.valid_from == "" and r.valid_until == "" for r in roster)


def test_roster_player_ids_are_team_scoped(team_btr_html):
    _, roster = parse_team_page(team_btr_html, "btr", 18, "test")
    ids = [r.player_id for r in roster]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("btr:") for i in ids)
    assert "btr:morenooo" in ids
