# MPL ID data quality report

- Generated: 2026-10-25T09:29:27+07:00
- Season: 18
- Source: https://id-mpl.com

| table | rows | fields with blanks |
| --- | --- | --- |
| mpl-drafts.csv | 1740 | - |
| mpl-game-players.csv | 1740 | `hero_id`=752 |
| mpl-games.csv | 174 | - |
| mpl-head-to-head.csv | 36 | - |
| mpl-hero-matchups.csv | 2880 | - |
| mpl-hero-pools.csv | 621 | - |
| mpl-hero-stats.csv | 133 | - |
| mpl-hero-synergy.csv | 1228 | - |
| mpl-match-details.csv | 72 | - |
| mpl-mvp.csv | 8 | - |
| mpl-player-hero-stats.csv | 623 | - |
| mpl-player-pools.csv | 621 | - |
| mpl-player-stats.csv | 66 | - |
| mpl-players.csv | 91 | `role`=4, `nationality`=91, `profile_url`=91 |
| mpl-rosters.csv | 84 | `valid_from`=84, `valid_until`=84 |
| mpl-schedule.csv | 80 | `team1_id`=4, `team2_id`=6, `team1_score`=8, `team2_score`=8, `winner_team_id`=8, `match_url`=8 |
| mpl-seasons.csv | 1 | - |
| mpl-standings.csv | 9 | - |
| mpl-team-form.csv | 80 | - |
| mpl-team-stats.csv | 9 | - |
| mpl-teams.csv | 9 | - |

## Known gaps in the public source

- Per-game bans are not published on match detail pages. Only season-level ban totals exist (`mpl-hero-stats.csv`).
- Player nationality, profile URLs and contract dates are not published; those columns stay empty.
- Player statistics are season aggregates; per-game values exist only in `mpl-game-players.csv`.
- Only the current season is served. The site has no season selector or archive route.
- Playoff standings are published as an image only; the URL is kept in `mpl-seasons.csv`.
- `matches_played` and `win_rate` in `mpl-standings.csv` are derived from the official W-L record.
