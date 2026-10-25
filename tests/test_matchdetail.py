"""Match detail fragment: series header, games, box score, side attribution."""

from __future__ import annotations

from mplid.matchdetail import parse_match_detail


def test_series_header(match_detail_html):
    detail = parse_match_detail(match_detail_html, "1036")
    assert detail.team1_name == "EVOS"
    assert detail.team2_name == "RRQ"
    assert (detail.team1_score, detail.team2_score) == (2, 0)
    assert "evos-500.png" in detail.team1_logo_url
    assert "rrq-500.png" in detail.team2_logo_url


def test_game_count_and_duration(match_detail_html):
    detail = parse_match_detail(match_detail_html, "1036")
    assert len(detail.games) == 2
    assert detail.games[0].duration_raw == "16:51"
    assert detail.games[0].duration_seconds == 1011
    assert detail.games[1].duration_seconds == 1480
    assert [g.game_no for g in detail.games] == [1, 2]


def test_ten_players_per_game(match_detail_html):
    detail = parse_match_detail(match_detail_html, "1036")
    for game in detail.games:
        assert len(game.players) == 10
        assert {p.side for p in game.players} == {"winner", "loser"}
        assert sum(1 for p in game.players if p.side == "winner") == 5
        assert all(p.hero_name for p in game.players)
        assert all(p.player_name for p in game.players)


def test_side_follows_team_not_column(match_detail_html):
    """Game 2 lists RRQ first, so column order cannot decide the side."""
    detail = parse_match_detail(match_detail_html, "1036")
    game2 = detail.games[1]
    assert game2.winner_team_name == "EVOS"
    for player in game2.players:
        expected = "winner" if player.team_name == "EVOS" else "loser"
        assert player.side == expected


def test_box_score_values(match_detail_html):
    detail = parse_match_detail(match_detail_html, "1036")
    first = next(p for p in detail.games[0].players if p.player_name == "Rendyyy")
    assert first.hero_name == "Dyrroth"
    assert first.hero_id == "85"
    assert (first.kills, first.deaths, first.assists) == (3, 2, 3)
    assert first.damage_dealt == 38859
    assert first.damage_taken == 126389
    assert first.tower_damage == 1699
    assert first.gold == 9316
    assert first.emblem_id == "20003"
    assert first.rune_ids == "811|721|731"
    assert first.item_ids.split("|")[0] == "3204"


def test_kills_match_scoreboard(match_detail_html):
    detail = parse_match_detail(match_detail_html, "1036")
    for game in detail.games:
        for side, team in (("winner", game.winner_team_name), ("loser", game.loser_team_name)):
            total = sum(p.kills or 0 for p in game.players if p.side == side)
            expected = game.winner_kills if side == "winner" else game.loser_kills
            assert total == expected, f"{team} game {game.game_no}"
