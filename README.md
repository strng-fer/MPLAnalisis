# MPL Indonesia — Scraper & Analytics Dataset

Complete, reproducible data pipeline for **MPL Indonesia** (Mobile Legends: Bang Bang
Professional League), the official league site at <https://id-mpl.com>.

Turns the league's public pages into 21 tidy CSV tables for draft analysis, hero
pools, team and player performance, standings, season progression and
head-to-head records — the same kind of ground truth you would expect from a
basketball analytics dataset, but for MPL ID.

**Season 18 · 72 completed matches · 174 games · 1,740 player-game rows · 91 players · 133 heroes**

---

## Contents

- [What you get](#what-you-get)
- [Quick start](#quick-start)
- [Data model](#data-model)
- [Output tables](#output-tables)
- [Derived analytics](#derived-analytics)
- [How the scraping works](#how-the-scraping-works)
- [What the source does not publish](#what-the-source-does-not-publish)
- [Update semantics](#update-semantics)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Kaggle](#kaggle)
- [Licence and attribution](#licence-and-attribution)

---

## What you get

| | |
| --- | --- |
| **Drafts** | Per game, per side: 10 picks with hero, player, emblem, runes, items |
| **Box scores** | Kills, deaths, assists, damage dealt/taken, tower damage, gold |
| **Hero analytics** | Season pick/ban/win totals, player hero pools, hero-by-hero matchups, hero pair synergy |
| **Team analytics** | Standings, season totals, weekly form, head-to-head series and game records |
| **Player analytics** | Season aggregates, per-hero splits, MVP standings |
| **Season metadata** | Season label, playoff bracket image, match schedule with VOD links |

Everything is keyed consistently (`match_id`, `game_no`, `team_id`, `player_id`,
`hero_name`), so the tables join without cleanup work.

## Quick start

### Use the data only

```bash
git clone https://github.com/<your-user>/MPLAnalisis.git
cd MPLAnalisis
python -c "import pandas as pd; print(pd.read_csv('data/mpl-game-players.csv').head())"
```

### Run the scraper

```bash
pip install -r requirements.txt

python -m mplid                          # full refresh into %TEMP%\mpl-out
python -m mplid --out ./data             # write straight into this repo
python -m mplid --out ./data --refresh   # ignore the HTML cache
python -m mplid --max-matches 5          # smoke test on 5 match pages
```

PowerShell wrapper with the same options:

```powershell
.\scrape-mpl.ps1 -OutDir .\data -Refresh
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--out` | `%TEMP%\mpl-out` | output directory |
| `--season` | auto | season number, detected from the roster heading |
| `--refresh` | off | bypass the on-disk HTML cache |
| `--delay` | `0.4` | seconds between HTTP requests |
| `--max-matches` | all | limit match-detail pages |
| `--quiet` | off | only print the final manifest |

A full run is about 90 requests and finishes in well under a minute once cached.

## Data model

```
mpl-teams ──< mpl-rosters >── mpl-players
    │                             │
    │                             │
mpl-schedule ──< mpl-match-details ──< mpl-games ──< mpl-game-players
    │                                              └──< mpl-drafts
    │
mpl-standings   mpl-team-stats   mpl-player-stats   mpl-hero-stats
mpl-hero-pools  mpl-player-pools mpl-mvp            mpl-seasons
```

All tables carry `season`, and every fact table carries `scraped_at`
(ISO 8601, UTC+7). Percentages are stored as fractions (`0.63`, not `63`).
Files are UTF-8 with BOM so Excel opens them correctly.

## Output tables

Full column-by-column documentation: **[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)**.

| File | Rows | Grain | Notes |
| --- | ---: | --- | --- |
| `mpl-schedule.csv` | 80 | one match | regular season + playoffs, upcoming matches kept with empty scores |
| `mpl-teams.csv` | 9 | one team | slug, full name, short name, logo, profile URL |
| `mpl-standings.csv` | 9 | team, stage | official Match Point / W-L / Net Game Win / Game W-L |
| `mpl-players.csv` | 91 | one player | IGN-keyed; includes players only present in game logs |
| `mpl-rosters.csv` | 84 | player, team, season | roles copied verbatim, coaches and analysts included |
| `mpl-match-details.csv` | 72 | one match | series score, games played, total and average duration |
| `mpl-games.csv` | 174 | one game | duration, winner/loser, team kills |
| `mpl-game-players.csv` | 1,740 | player, game | the box score |
| `mpl-drafts.csv` | 1,740 | pick, game | 10 picks per game, no bans (not published) |
| `mpl-team-stats.csv` | 9 | team, season | kills, deaths, assists, gold, damage, lord, tortoise, tower |
| `mpl-player-stats.csv` | 66 | player, season | lane, games, KDA, kill participation |
| `mpl-hero-stats.csv` | 133 | hero, season | picks, bans, wins, win rate |
| `mpl-hero-pools.csv` | 621 | player, hero | picks and win rate per hero |
| `mpl-player-pools.csv` | 621 | hero, player | the same facts transposed |
| `mpl-mvp.csv` | 8 | player | MVP points standings |
| `mpl-seasons.csv` | 1 | season | label and playoff bracket image URL |
| `mpl-hero-synergy.csv` | 1,228 | hero pair | played together, wins together |
| `mpl-hero-matchups.csv` | 2,880 | hero vs hero | both directions, win rate per reference hero |
| `mpl-player-hero-stats.csv` | 623 | player, hero | per-hero box score totals from game logs |
| `mpl-head-to-head.csv` | 36 | team pair | series and game record |
| `mpl-team-form.csv` | 80 | team, week | weekly record for progression charts |

Sanity checks that hold in the committed dataset (and are enforced by the test
suite): hero picks = hero-pool picks = player-pool picks = player-game rows =
1,740; standings wins = losses; game difference sums to zero; every completed
match has a detail row; every game has exactly 10 players.

## Derived analytics

These tables are **not published by the league**; they are computed from the
scraped facts and are rebuilt on every run.

| File | Definition |
| --- | --- |
| `mpl-hero-synergy.csv` | For each hero pair on the same side of a game: games together and wins together. |
| `mpl-hero-matchups.csv` | Winner hero vs loser hero of the same game, recorded in both directions. `win_rate` is the reference hero's rate against that opponent. |
| `mpl-player-hero-stats.csv` | Per player per hero: games, wins, K/D/A, KDA, gold, damage. `kda = (kills + assists) / deaths`, with zero deaths treated as `kills + assists`. |
| `mpl-head-to-head.csv` | Series and game record between two teams, alphabetically ordered, with first and last meeting date. |
| `mpl-team-form.csv` | Per team per week: matches, match wins/losses, game wins/losses, game difference. |

Also derived, but stored next to the official values:
`mpl-standings.csv` → `matches_played = wins + losses`, `win_rate = wins / matches_played`.

## How the scraping works

Discovery findings that shaped the implementation (details in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md)):

- **The site is server rendered.** Every table is present in the initial HTML;
  no JavaScript execution is required. The pipeline uses plain HTTP. The
  headless browser (Obscura) is kept only as a fallback for a challenge page.
- **Match details are an AJAX HTML fragment**, not JSON:
  `https://id-mpl.com/match-detail/<id>`. The ids come from
  `openMatchDetail(<id>)` handlers on `/schedule`.
- **Each schedule row appears three times** in the markup (week tab plus two
  filter copies). Rows are de-duplicated on the detail id.
- **One page per season.** There is no season selector and no archive route
  (`/statistics/17` returns 404); only the live season is served.
- **IGN spellings differ across pages** (`KENNZYYSKIE` / `KennzySkie`,
  `KEVIN` / `Kevinn`, `SANZ` / `S-A-N-Z`). The pipeline resolves them per team
  by exact match, then fuzzy match at 0.85 similarity, and stores the roster
  spelling as canonical.
- **Responses are cached** in `cache/` keyed by URL hash, with timestamped HTML
  snapshots in `raw/<date>/` for auditing.

Politeness: one request at a time, 0.4 s delay by default, no authentication
bypass, no rate-limit circumvention. The pipeline reads only pages a normal
visitor can open.

## What the source does not publish

These are real gaps in the upstream data, not scraper limitations. Empty columns
stay empty instead of being guessed.

- **Per-game bans.** Only season-level ban totals per hero exist (`mpl-hero-stats.csv`).
- **Player nationality, profile URLs, contract dates.** No player pages exist, so
  `nationality`, `profile_url`, `valid_from` and `valid_until` are empty.
- **Historical seasons.** Only the current season is online. To build a
  multi-season dataset, run the pipeline once per season and merge on `season`.
- **Playoff standings as data.** The bracket is a PNG; its URL is stored in
  `mpl-seasons.csv`.
- **Draft order.** `pick_slot` is the display order inside a side, not the
  official pick sequence.

## Update semantics

- CSVs are **upserted** on a natural key: schedule `(season, stage, match_id)`,
  teams `(season, team_id)`, games `(match_id, game_no)`, and so on.
- A non-empty new value overwrites the stored one; **an empty new value never
  erases data**. That is how a scheduled match later gains its score.
- A file whose header no longer matches the schema is moved to `legacy/`
  before the new table is written.
- Derived tables are rebuilt from scratch each run.
- `data/manifest.json` records row counts, fetch statistics, timings and
  warnings. `data/data-quality.json` and `data/data-quality.md` record
  per-column blank counts and the known gaps.

## Repository layout

```
MPLAnalisis/
├── data/                  the dataset (21 CSVs + manifest + quality report)
├── mplid/                 the scraper package
│   ├── fetch.py           HTTP + disk cache, browser fallback
│   ├── parse.py           Indonesian number/date/duration parsers
│   ├── schedule.py        /schedule
│   ├── standings.py       /home standings
│   ├── teams.py           /teams and /team/<slug>
│   ├── statistics.py      /statistics tabs
│   ├── matchdetail.py     /match-detail/<id>
│   ├── analytics.py       derived tables
│   ├── pipeline.py        orchestration, CSV upsert, quality report
│   └── cli.py             argument parsing
├── tests/                 parser, dataset and upsert tests (83 tests, offline)
├── docs/
│   ├── DATA_DICTIONARY.md every column, type and provenance
│   └── METHODOLOGY.md     discovery notes, HTML structures, ethics
├── kaggle/                dataset card, metadata, publish script
├── notebooks/             starter exploration notebook
├── scrape-mpl.ps1         PowerShell wrapper
└── pyproject.toml
```

## Development

```bash
pip install -e ".[dev]"
pytest                     # 83 tests, fully offline (HTML fixtures are committed)
```

The tests use gzipped HTML snapshots in `tests/fixtures/`, so a parser
regression is caught without touching the network.

## Kaggle

See [kaggle/README.md](kaggle/README.md). In short:

```bash
python kaggle/publish.py --check     # validate metadata and table inventory
python kaggle/publish.py --upload    # create or version the Kaggle dataset
```

Requires `~/.kaggle/kaggle.json` or `KAGGLE_USERNAME` / `KAGGLE_KEY`.

## Licence and attribution

- **Code:** MIT (see [LICENSE](LICENSE)).
- **Data (`data/`):** CC BY 4.0, derived from content published on
  <https://id-mpl.com>.
- MPL, Mobile Legends: Bang Bang and team logos are trademarks of their
  respective owners. This project is unofficial and not affiliated with Moonton
  or MPL Indonesia.

If you use this dataset, cite it as:

```
MPL Indonesia Season 18 Dataset (2026).
https://github.com/<your-user>/MPLAnalisis
```
