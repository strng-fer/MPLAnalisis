# MPL Indonesia Season 18 — Esports Match & Draft Dataset

Data from **MPL Indonesia** (Mobile Legends: Bang Bang Professional League),
season 18, collected from the official league site
[id-mpl.com](https://id-mpl.com).

72 completed matches · 174 games · 1,740 player-game rows · 91 players · 133 heroes

## Files

| File | Rows | What it holds |
| --- | ---: | --- |
| `mpl-schedule.csv` | 80 | Every match: date, time, round, teams, series score, status, VOD link |
| `mpl-match-details.csv` | 72 | One row per match: series score, games played, total and average game length |
| `mpl-games.csv` | 174 | One row per game: duration, winner, team kills |
| `mpl-game-players.csv` | 1,740 | **The box score**: hero, K/D/A, damage dealt, damage taken, tower damage, gold, emblem, runes, items |
| `mpl-drafts.csv` | 1,740 | 10 picks per game with team and side |
| `mpl-teams.csv` | 9 | Team ids, names, logos, profile URLs |
| `mpl-rosters.csv` | 84 | Players per team with verbatim role labels (incl. coaches and analysts) |
| `mpl-players.csv` | 91 | Player dimension, including players only visible in game logs |
| `mpl-standings.csv` | 9 | Official standings: match points, match W-L, net game win, game W-L |
| `mpl-team-stats.csv` | 9 | Season totals: kills, deaths, assists, gold, damage, lord, tortoise, tower |
| `mpl-player-stats.csv` | 66 | Season aggregates per player: lane, games, KDA, kill participation |
| `mpl-hero-stats.csv` | 133 | Picks, bans, wins, win rate per hero |
| `mpl-hero-pools.csv` | 621 | Player × hero picks and win rates |
| `mpl-player-pools.csv` | 621 | The same facts transposed: hero × player |
| `mpl-mvp.csv` | 8 | MVP points standings |
| `mpl-seasons.csv` | 1 | Season label and playoff bracket image URL |
| `mpl-hero-synergy.csv` | 1,228 | Hero pairs played together: games and wins |
| `mpl-hero-matchups.csv` | 2,880 | Hero vs hero, both directions, with win rate |
| `mpl-player-hero-stats.csv` | 623 | Per player per hero: games, wins, K/D/A, KDA, gold, damage |
| `mpl-head-to-head.csv` | 36 | Series and game record between each pair of teams |
| `mpl-team-form.csv` | 80 | Per team per week: match and game record |

`manifest.json` records the run, `data-quality.md` lists per-column blank counts
and the gaps in the source.

## Quick start

```python
import pandas as pd

d = "/kaggle/input/mpl-indonesia-s18/"

gp = pd.read_csv(d + "mpl-game-players.csv")
schedule = pd.read_csv(d + "mpl-schedule.csv")

df = gp.merge(schedule[["match_id", "match_date", "round"]], on="match_id")

# hero win rate, minimum 10 games
hr = (df.assign(win=(df.side == "winner").astype(int))
        .groupby("hero_name")
        .agg(games=("win", "size"), wins=("win", "sum")))
hr["win_rate"] = (hr.wins / hr.games).round(4)
print(hr[hr.games >= 10].sort_values("win_rate", ascending=False).head(10))
```

## Column notes

- `side` is `winner` or `loser` **for that game**; `team_id` is authoritative.
- All `*_rate` columns are fractions (`0.63`), not percentages.
- `damage_dealt`, `damage_taken`, `tower_damage`, `gold` are integers parsed from
  Indonesian formatting (`38.859` → `38859`).
- `pick_slot` is display order inside a side, **not** the official draft order.
- `distinct_heroes` in `mpl-hero-pools.csv` is the number of different heroes a
  player used, not the number of games.
- `hero_id` is empty for 752 of 1,740 rows where the icon URL carries no number.
- `mpl-players.nationality`, `profile_url`, and `mpl-rosters.valid_from/valid_until`
  are empty: the source does not publish them.

## Provenance

Scraped with the open-source pipeline at
[github.com/strng-fer/MPLAnalisis](https://github.com/strng-fer/MPLAnalisis).
Every table is reproducible with `python -m mplid`. Full column documentation is
in `docs/DATA_DICTIONARY.md` in that repository.

## Licence

Data: CC BY 4.0, derived from content published on https://id-mpl.com.
MPL, Mobile Legends: Bang Bang and team logos are trademarks of their respective
owners. This dataset is unofficial and not affiliated with Moonton or MPL.
