# Data dictionary

Every column of every table, with type, provenance and caveats.

**Provenance key**

| Tag | Meaning |
| --- | --- |
| `official` | Printed by id-mpl.com, stored unchanged |
| `parsed` | Read from the page but converted (date, number, duration, fraction) |
| `derived` | Computed by this pipeline from other columns |
| `empty` | Column exists for completeness; the source publishes nothing |
| `id` | Identifier assigned by this pipeline or by the site |

**Conventions**

- Encoding: UTF-8 with BOM. Delimiter `,`. Header on the first line.
- `season` is an integer (`18`).
- `*_id` values are stable strings. Empty means "not resolvable", never `NULL`.
- All `*_rate` columns are fractions in `[0, 1]`, not percentages.
- `scraped_at` is ISO 8601 with the local UTC+7 offset, e.g. `2026-10-25T09:29:27+07:00`.
- `source_url` is the exact page a row came from.

---

## `mpl-schedule.csv` — 80 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `stage` | str | parsed | `Regular Season` or `Playoffs`. |
| `match_id` | str | id | Site detail id (`1036`). Playoff slots without a detail id get `<season>-pl-<nn>`. |
| `match_date` | date | parsed | `YYYY-MM-DD`, from the Indonesian date header (`Rabu, 4 November 2026`). |
| `match_time` | str | parsed | `HH:MM` local (WIB, UTC+7). |
| `round` | str | parsed | `Week <n>` for the regular season; the bracket label (`Upper Bracket Finals`) for playoffs. |
| `match_status` | str | derived | `completed` when both score cells are filled, else `scheduled`. |
| `team1_id` | str | id | Team slug, empty for `TBD`. |
| `team1_name` | str | official | Short name as printed (`EVOS`, `TBD`). |
| `team2_id` | str | id | Team slug, empty for `TBD`. |
| `team2_name` | str | official | Short name as printed. |
| `team1_score` | int | official | Series games won; empty for scheduled matches. |
| `team2_score` | int | official | Series games won; empty for scheduled matches. |
| `winner_team_id` | str | derived | Slug of the series winner, empty when unknown. |
| `match_url` | str | official | `https://id-mpl.com/match-detail/<id>`; empty for scheduled playoff slots. |
| `scraped_at` | datetime | derived | When the row was collected. |

## `mpl-teams.csv` — 9 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `team_id` | str | id | Profile slug (`btr`, `tlid`). Join key everywhere. |
| `team_name` | str | official | Full name from the profile heading (`BIGETRON BY VIT`). |
| `team_short_name` | str | official | Card label (`BTR`). |
| `team_logo_url` | str | official | Logo URL (imagekit CDN, wrapped by wsrv.nl). |
| `team_profile_url` | str | official | `https://id-mpl.com/team/<slug>`. |
| `roster_reference` | str | official | Literal roster heading, e.g. `ROSTER SEASON 18`. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-standings.csv` — 9 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `stage` | str | parsed | Always `Regular Season`; playoff standings are an image. |
| `team_id` | str | id | Team slug. |
| `team_name` | str | official | Full team name. |
| `rank` | int | official | Table position. |
| `matches_played` | int | **derived** | `wins + losses`. Not printed by the site. |
| `wins` | int | official | Match W-L, left side. |
| `losses` | int | official | Match W-L, right side. |
| `game_wins` | int | official | Game W-L, left side. |
| `game_losses` | int | official | Game W-L, right side. |
| `game_difference` | int | official | Net Game Win column. |
| `points` | int | official | Match Point column. |
| `win_rate` | float | **derived** | `wins / matches_played`, 4 decimals. |
| `source_url` | str | official | `https://id-mpl.com/home`. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-players.csv` — 91 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `player_id` | str | id | `<team_id>:<slug(ign)>`, e.g. `evos:rendyyy`. Join key. |
| `player_name` | str | official | Canonical IGN (roster spelling when available). |
| `in_game_name` | str | official | Same as `player_name`; no separate legal name is published. |
| `current_team_id` | str | id | Team slug at collection time. |
| `role` | str | official | Role label verbatim (`Jungle`, `Mid Lane`, `Coach`); empty for players who only appear in game logs. |
| `nationality` | str | **empty** | Not published anywhere on the site. |
| `profile_url` | str | **empty** | No player profile pages exist. |
| `season` | int | official | Season number. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-rosters.csv` — 84 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season from the `ROSTER SEASON <n>` heading. |
| `team_id` | str | id | Team slug. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `role` | str | official | Verbatim label: `EXP Lane`, `Gold Lane`, `Mid Lane`, `Midlane`, `Jungle`, `Roam`, `Roamer`, `Coach`, `Asst. Coach`, `Analyst`. |
| `roster_status` | str | derived | `active` for the published roster. |
| `valid_from` | date | **empty** | No contract or signing dates are published. |
| `valid_until` | date | **empty** | Same. |
| `source_url` | str | official | Team profile URL. |

## `mpl-match-details.csv` — 72 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `match_id` | str | id | Site detail id. |
| `season` | int | official | Season number. |
| `stage` | str | parsed | `Regular Season` or `Playoffs`. |
| `match_date` | date | parsed | From the schedule. |
| `match_time` | str | parsed | From the schedule. |
| `round` | str | parsed | `Week <n>` or bracket label. |
| `team1_id` | str | id | Slug of the left-hand team in the detail header. |
| `team1_name` | str | official | Short name. |
| `team1_score` | int | official | Series games won. |
| `team2_id` | str | id | Slug of the right-hand team. |
| `team2_name` | str | official | Short name. |
| `team2_score` | int | official | Series games won. |
| `winner_team_id` | str | derived | Series winner slug. |
| `games_played` | int | derived | Number of game tabs. |
| `total_duration_seconds` | int | derived | Sum of game durations. |
| `avg_game_duration_seconds` | int | derived | Mean game duration, rounded. |
| `source_url` | str | official | Match detail URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-games.csv` — 174 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `match_id` | str | id | Parent match. |
| `season` | int | official | Season number. |
| `stage` | str | parsed | `Regular Season` or `Playoffs`. |
| `match_date` | date | parsed | From the schedule. |
| `game_no` | int | parsed | 1-based order of the game tabs. |
| `game_uid` | str | official | Site game tab id (`1850`). |
| `duration_seconds` | int | parsed | From `MM:SS`. |
| `winner_team_id` | str | derived | Slug of the winning side. |
| `winner_team_name` | str | official | Short name. |
| `winner_kills` | int | official | Team kills, winner. |
| `loser_team_id` | str | derived | Slug of the losing side. |
| `loser_team_name` | str | official | Short name. |
| `loser_kills` | int | official | Team kills, loser. |
| `source_url` | str | official | Match detail URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-game-players.csv` — 1,740 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `match_id` | str | id | Parent match. |
| `game_no` | int | parsed | Parent game. |
| `season` | int | official | Season number. |
| `stage` | str | parsed | `Regular Season` or `Playoffs`. |
| `side` | str | derived | `winner` or `loser` for this game. |
| `team_id` | str | id | Team slug (authoritative, not column position). |
| `team_name` | str | official | Short name. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `player_name` | str | official | Canonical IGN. |
| `hero_name` | str | official | Hero picked. |
| `hero_id` | str | official | Scoregg hero number from the icon URL; empty when the icon uses a path form. |
| `kills` | int | official | From the KDA cell. |
| `deaths` | int | official | From the KDA cell. |
| `assists` | int | official | From the KDA cell. |
| `damage_dealt` | int | parsed | Sword icon figure. Indonesian decimal separator removed (`38.859` → `38859`). |
| `damage_taken` | int | parsed | Shield icon figure. |
| `tower_damage` | int | parsed | Tower icon figure. |
| `gold` | int | parsed | Money icon figure. |
| `emblem_id` | str | official | Emblem number (`20003`). |
| `rune_ids` | str | official | Three rune numbers joined by `\|`. |
| `item_ids` | str | official | Item numbers joined by `\|`; fewer than five when the build slot was empty. |
| `source_url` | str | official | Match detail URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-drafts.csv` — 1,740 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `match_id` | str | id | Parent match. |
| `game_no` | int | parsed | Parent game. |
| `season` | int | official | Season number. |
| `stage` | str | parsed | `Regular Season` or `Playoffs`. |
| `side` | str | derived | `winner` or `loser`. |
| `team_id` | str | id | Team slug. |
| `player_name` | str | official | Canonical IGN. |
| `hero_name` | str | official | Hero picked. |
| `pick_slot` | int | derived | Display order inside the side (1-5). **Not** the official draft order. |
| `source_url` | str | official | Match detail URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

> Bans are not in this table because the source does not publish per-game bans.
> Season-level ban counts live in `mpl-hero-stats.csv`.

## `mpl-team-stats.csv` — 9 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `team_id` | str | id | Team slug. |
| `team_name` | str | official | Short name. |
| `kills` | int | official | Season total. |
| `deaths` | int | official | Season total. |
| `assists` | int | official | Season total. |
| `gold` | int | parsed | Season total, thousands separators removed. |
| `damage` | int | parsed | Season total. |
| `lord` | int | official | Lord (objective) count. |
| `tortoise` | int | official | Turtle count. |
| `tower` | int | official | Towers destroyed. |
| `source_url` | str | official | `https://id-mpl.com/statistics`. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-player-stats.csv` — 66 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `team_id` | str | id | Team slug. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `player_name` | str | official | Canonical IGN. |
| `lane` | str | official | Site vocabulary: `EXP`, `GOLD`, `MID`, `JUNGLE`, `ROAM`. |
| `games` | int | official | Games played. |
| `kills` | int | official | Season total. |
| `avg_kills` | float | parsed | Indonesian decimal (`2,54`). |
| `deaths` | int | official | Season total. |
| `avg_deaths` | float | parsed | |
| `assists` | int | official | Season total. |
| `avg_assists` | float | parsed | |
| `avg_kda` | float | official | As printed by the site. |
| `kill_participation` | float | parsed | `81%` → `0.81`. |
| `source_url` | str | official | Statistics URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-hero-stats.csv` — 133 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `hero_name` | str | official | Hero name. |
| `picks` | int | official | Season picks. |
| `bans` | int | official | Season bans (the only ban data available). |
| `wins` | int | official | Games won when picked. |
| `win_rate` | float | parsed | `63%` → `0.63`. |
| `source_url` | str | official | Statistics URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

Rows with `picks = 0` and `bans = 0` are heroes that were never used; they are
kept so the hero dimension is complete.

## `mpl-hero-pools.csv` — 621 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `team_id` | str | id | Team slug. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `player_name` | str | official | Canonical IGN. |
| `lane` | str | official | Lane label from the pool table. |
| `distinct_heroes` | int | official | Site `Total` column: number of **different heroes** the player used, not games. |
| `hero_name` | str | official | Hero. |
| `picks` | int | official | Times this player picked this hero. |
| `win_rate` | float | parsed | Win rate for that player on that hero. |
| `source_url` | str | official | Statistics URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-player-pools.csv` — 621 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `hero_name` | str | official | Hero. |
| `total_picks` | int | official | Total picks of that hero in the season. |
| `team_id` | str | id | Team slug. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `player_name` | str | official | Canonical IGN. |
| `picks` | int | official | This player's picks of that hero. |
| `win_rate` | float | parsed | |
| `source_url` | str | official | Statistics URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

Same facts as `mpl-hero-pools.csv`, transposed. Summing `picks` over either
table yields 1,740.

## `mpl-mvp.csv` — 8 rows

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `rank` | int | official | MVP rank. |
| `points` | int | official | MVP points. |
| `player_display` | str | official | Site label (`TLID KEVIN`). |
| `team_id` | str | id | Team slug parsed from the label or logo. |
| `player_id` | str | id | Matches `mpl-players.csv`. |
| `player_name` | str | official | IGN without the team prefix. |
| `source_url` | str | official | Statistics URL. |
| `scraped_at` | datetime | derived | Collection timestamp. |

## `mpl-seasons.csv` — 1 row

| Column | Type | Prov | Description |
| --- | --- | --- | --- |
| `season` | int | official | Season number. |
| `season_label` | str | derived | `MPL ID Season 18`. |
| `playoffs_bracket_url` | str | official | Image URL of the playoff bracket. |
| `source_url` | str | official | `https://id-mpl.com/home`. |
| `scraped_at` | datetime | derived | Collection timestamp. |

---

## Derived analytics tables

These have no `source_url` / `scraped_at` because they are recomputed from the
tables above on every run. `win_rate` is always a fraction.

### `mpl-hero-synergy.csv` — 1,228 rows

| Column | Type | Description |
| --- | --- | --- |
| `season` | int | Season number. |
| `stage` | str | Stage the games belong to. |
| `hero_a` | str | Alphabetically first hero of the pair. |
| `hero_b` | str | Second hero. |
| `games_together` | int | Games both heroes were on the same side. |
| `wins_together` | int | Games that side won. |
| `win_rate` | float | `wins_together / games_together`. |

### `mpl-hero-matchups.csv` — 2,880 rows

| Column | Type | Description |
| --- | --- | --- |
| `season` | int | Season number. |
| `stage` | str | Stage. |
| `hero` | str | Reference hero. |
| `opponent_hero` | str | Hero on the opposing side. |
| `games` | int | Games where both heroes were present on opposite sides. |
| `wins` | int | Games `hero` won. |
| `win_rate` | float | `wins / games` for `hero`. |

Both directions are present, so `(Hirara, Paquito)` and `(Paquito, Hirara)`
describe the same 35 games from opposite perspectives.

### `mpl-player-hero-stats.csv` — 623 rows

| Column | Type | Description |
| --- | --- | --- |
| `season` | int | Season number. |
| `team_name` | str | Short name as printed on the match page. |
| `player_name` | str | Canonical IGN. |
| `hero_name` | str | Hero. |
| `games` | int | Games played on that hero. |
| `wins` | int | Wins on that hero. |
| `win_rate` | float | `wins / games`. |
| `kills`, `deaths`, `assists` | int | Totals. |
| `avg_kills`, `avg_deaths`, `avg_assists` | float | Per game, 2 decimals. |
| `kda` | float | `(kills + assists) / deaths`; zero deaths treated as `kills + assists`. |
| `total_gold` | int | Sum of gold. |
| `total_damage` | int | Sum of damage dealt. |

### `mpl-head-to-head.csv` — 36 rows

| Column | Type | Description |
| --- | --- | --- |
| `season` | int | Season number. |
| `stage` | str | Stage. |
| `team_a`, `team_b` | str | Team short names, alphabetically ordered. |
| `team_a_id`, `team_b_id` | str | Slugs. |
| `matches` | int | Series played. |
| `team_a_match_wins`, `team_b_match_wins` | int | Series wins. |
| `team_a_game_wins`, `team_b_game_wins` | int | Individual games won. |
| `first_match_date`, `last_match_date` | date | Meeting range. |

### `mpl-team-form.csv` — 80 rows

| Column | Type | Description |
| --- | --- | --- |
| `season` | int | Season number. |
| `stage` | str | Stage. |
| `week` | int | Week number (regular season only). |
| `team_name`, `team_id` | str | Team. |
| `matches` | int | Series played that week. |
| `match_wins`, `match_losses` | int | Series record. |
| `game_wins`, `game_losses` | int | Game record. |
| `game_difference` | int | `game_wins - game_losses`. |
| `first_match_date`, `last_match_date` | date | Week range. |

---

## Join recipes

```python
import pandas as pd

d = "data/"

# full draft with player and hero detail
gp = pd.read_csv(d + "mpl-game-players.csv")
schedule = pd.read_csv(d + "mpl-schedule.csv")
players = pd.read_csv(d + "mpl-players.csv")
teams = pd.read_csv(d + "mpl-teams.csv")

df = (
    gp.merge(schedule[["match_id", "match_date", "round"]], on="match_id")
      .merge(players[["player_id", "role"]], on="player_id", how="left")
      .merge(teams[["team_id", "team_name"]].rename(columns={"team_name": "team_full_name"}), on="team_id")
)
```

```sql
-- hero win rate by side, straight from the box score
SELECT hero_name,
       COUNT(*)                                    AS games,
       SUM(CASE WHEN side = 'winner' THEN 1 ELSE 0 END) AS wins,
       ROUND(1.0 * SUM(CASE WHEN side = 'winner' THEN 1 ELSE 0 END) / COUNT(*), 4) AS win_rate
FROM mpl_game_players
GROUP BY hero_name
HAVING COUNT(*) >= 10
ORDER BY win_rate DESC;
```

## Known gaps

1. Per-game bans — not published. Only `mpl-hero-stats.bans` exists.
2. Player nationality, profile URLs, contract dates — not published.
3. Past seasons — the site only serves the live season.
4. Playoff standings as rows — only a bracket image is published.
5. Official draft order — `pick_slot` is display order.
6. `hero_id` — empty for 752 of 1,740 rows where the icon URL has no numeric id.
