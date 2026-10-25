# Methodology and discovery notes

How the site was reverse engineered, what each page actually contains, and the
decisions behind the pipeline. Kept in the repo so a future maintainer does not
have to rediscover it.

## 1. Stack discovery

The site was originally approached with a headless browser (Obscura, Rust +
V8) because the task brief described `id-mpl.com` as a JavaScript SPA.

Checking the raw HTTP response disproved that:

```powershell
(Invoke-WebRequest "https://id-mpl.com/statistics" -UseBasicParsing).Content.Length
# 1878405 bytes — the full table markup is already there
```

Confirmed by inspecting the payload: `/statistics` contains
`#table-team-statistics`, `#table-heroes-statistics`, `#table-hero-pools`,
`#table-player-pools` and `.mvp-card` in the initial HTML. `/schedule` contains
all 224 match blocks. Only jQuery, DataTables and slider libraries are loaded as
scripts.

**Decision:** plain `requests` + BeautifulSoup. The browser is kept as a
fallback (`fetch.py:_fetch_obscura`) for the case where the CDN returns a
challenge page, but a normal run never uses it. This dropped a full refresh from
minutes to seconds and removed a native dependency.

## 2. Route inventory

`href` values on the home page, filtered to same-origin links:

```
/home  /schedule  /teams  /team/<slug>  /statistics  /mpljourney
/theawards  /news  /ticket  /codeofconduct  /en/<page>
```

Probed for season variants:

| URL | Result |
| --- | --- |
| `/statistics?season=17` | 200, but identical to `/statistics` (query ignored) |
| `/statistics/17` | 404 |
| `/schedule?season=17` | 200, identical content |
| `/season/17` | 404 |
| `/statistics/s17` | 404 |

**Decision:** the site serves exactly one season. `season` is auto-detected from
the `ROSTER SEASON <n>` heading on a team page, with a CLI override. Multi-season
data must be accumulated by running the pipeline once per season.

## 3. Schedule structure

`/schedule` has two `.tab-content` panes: `#regular-season` and `#playoffs`.

Inside `#regular-season` there are nine `#t-week-<n>` panes, plus two hidden
filter copies of every match (`#filter-<nnn>`). A single match therefore appears
**three times** in the DOM:

```
1036 [(['t-week-1'], ['filter-all']), ([], ['filter-164']), ([], ['filter-165'])]
```

Naively counting `.match` elements gives 257 rows for 80 matches.

**Decision:** de-duplicate on the detail id parsed from
`onclick="openMatchDetail(1036)"`. Playoff rows have no detail handler, so their
identity is `(date, team1, team2, round)` — two playoff slots can share a date
with both teams still `TBD`, so the round label is required.

Fields per row:

- date: a preceding `.match.date` sibling, Indonesian format
  (`Rabu, 4 November 2026`)
- time: `.time` cell, `HH:MM` WIB (UTC+7)
- round: `.time` cell text matching `Round|Bracket|Final|Semi`, or `Week <n>`
  from the enclosing `#t-week-<n>`
- scores: two `.score.font-primary` cells; **empty for upcoming matches**
- replay: `a.replay[href]` (YouTube)
- status: derived — `completed` iff both score cells are non-empty

## 4. Match detail endpoint

Match detail is not a page and not a JSON API. The schedule page opens a
magnific-popup and calls:

```js
$.ajax({ url: "https://id-mpl.com/match-detail/" + matchId, type: 'GET' })
$("#match-detail-content").html(response);
```

`GET /match-detail/1036` returns an **HTML fragment** (242 KB) containing:

1. Series header — two team logos and the series score.
2. One `.tab-content.match-detail` per game (`GAME 1`, `GAME 2`, ...).
3. Per game, two `div.victory` / `div.defeat` blocks with team name, team kills
   and a clock icon carrying `MM:SS`.
4. Per game, two `.col-6` columns with five `div.my-3` player blocks each.

Per player block: hero icon + name, IGN, emblem, three runes, five items, KDA
(`.kda-content`, `k/d/a`), and a hidden `#data-content<n>` with four figures
whose meaning follows the icon:

| Icon | Meaning |
| --- | --- |
| `sword-64.png` / `sword-r-64.png` | damage dealt |
| `shield-64-v2.png` | damage taken |
| `tower-64.png` | tower damage |
| `money-64-v2.png` | gold |

Numbers use Indonesian formatting: `38.859` = 38,859 (dot as thousands
separator). All four figures are converted with the same rule.

### Two traps in the markup

**Trap 1 — column order does not imply side.** In game 2 of match 1036 the
defeat block is rendered *first*:

```
TAB info-1851
  block: defeat  | 9 | RRQ
  block: victory | 9 | EVOS
  col 0 ['Joshua', 'Demonkite', 'Hajirin', 'Said', 'Arthur']   # RRQ
  col 1 ['Rendyyy', 'Alberttt', 'DrianW', 'Muezza', 'Erlan']   # EVOS
```

Hard-coding "column 1 = winner" silently mislabels half the dataset. The parser
reads the `victory`/`defeat` blocks in document order and pairs them with the
columns positionally, then labels each player from the block class.

**Trap 2 — winner and loser blocks are mirrored.** In a winner block the hero
icon comes before the name; in a loser block the KDA and items come first. So
`imgs[0]` is not always the hero. The parser locates the name via
`div[style*='font-weight: 700']` and the hero via `div[style*='font-size: 0.9rem']`,
which is stable in both layouts.

Both traps are covered by `tests/test_matchdetail.py::test_side_follows_team_not_column`
and the kills-vs-scoreboard cross-check.

### What is absent

There are **no ban elements** in the fragment. Searching the payload for
`ban` returns only `Bang` (the game name) and `Bane` (a hero). Ban totals exist
only in the `/statistics` hero table, so `mpl-drafts.csv` has picks only.

## 5. Statistics page

One document, six tab panes, all server rendered:

| Pane | Structure |
| --- | --- |
| `#teams` | `#table-team-statistics`: 9 rows × 9 numeric columns |
| `#players` | `#player-team-all` + one `.player-statistics-card` per team |
| `#heroes` | three `.top-hero-stats-outer` blocks + `#table-heroes-statistics` |
| `#hero-pools` | `#table-hero-pools`: player rows with a hero strip |
| `#player-pools` | `#table-player-pools`: hero rows with a player strip |
| `#mvp-standings` | `.mvp-card` blocks |

Number formats encountered:

- `2,54` — comma decimal (avg kills, avg KDA)
- `2,044,010` — comma thousands (team gold)
- `63%` — percentage
- `81%` — kill participation

`parse.py` handles all four and converts percentages to fractions.

Hero pools encode a nested list inside one table cell: each hero is a
`.hero-pool-outer > div` with `.hero-pool-image` (hero name in the URL),
`.hero-pool-pick` (count) and `.hero-pool-count` (win rate). Player pools use
the mirror structure with `.player-pool-card`.

Cross-check that the parser is not dropping or double counting:
`sum(hero_stats.picks) == sum(hero_pools.picks) == sum(player_pools.picks) == 1740`.
This is asserted in the test suite.

## 6. Teams and rosters

`/teams` renders nine `.team-card-outer` blocks. Each card links to
`/team/<slug>` and carries a logo and a short name.

`/team/<slug>` adds the full name in `#content h4`, social links, and a
`ROSTER SEASON <n>` block. Each person is a `.player-image` inside a column with
`.player-name` and `.player-role`.

Role labels are **not consistent** across the site:

| Source | Vocabulary |
| --- | --- |
| Roster page | `EXP Lane`, `Gold Lane`, `Mid Lane`, `Midlane`, `Jungle`, `Roam`, `Roamer`, `Coach`, `Asst. Coach`, `Analyst` |
| Statistics page | `EXP`, `GOLD`, `MID`, `JUNGLE`, `ROAM` |

**Decision:** store both verbatim in their own columns (`mpl-rosters.role`,
`mpl-player-stats.lane`) and do not invent a normalisation. A consumer who wants
a common vocabulary can map it explicitly.

Only the *current* roster is published. Players who left mid-season still appear
in game logs, so `mpl-players.csv` is the union of roster entries and game-log
appearances. The four players that exist only in game logs have an empty `role`.

## 7. Player identity

The same person is spelled differently across pages:

| Roster page | Statistics page | Match detail |
| --- | --- | --- |
| `KENNZYYSKIE` | `KennzySkie` | `KennzySkie` |
| `KEVIN` (TLID jungle) | `KEVIN` | `Kevinn` |
| `SANZ` (ONIC) | `Sanz` | `S-A-N-Z` |
| `ALBERTTT` | `ALBERTTT` | `Alberttt` |

`player_id` is `<team_id>:<slug>` and would otherwise fork. The pipeline builds
a per-team alias index from the roster and statistics pages, resolves each game
log name by exact slug match, then by `difflib` similarity ≥ 0.85, and stores the
roster spelling as `player_name`. Unresolved names fall back to a new id rather
than being dropped, so nothing disappears silently.

Result: 91 players, 1,740 game rows, zero dangling ids
(`tests/test_dataset.py::test_players_cover_every_game_row`).

## 8. Cache and audit trail

- `cache/<slug>-<sha1>.html` — one file per URL, 6-hour freshness window,
  `--refresh` bypasses it.
- `raw/<YYYY-MM-DD>/<page>.html` — timestamped snapshot of every page actually
  fetched, so a past run can be re-parsed without touching the network.
- `manifest.json` — row counts, added/updated counts, fetch counters, timing.
- `data-quality.json` / `.md` — per-column blank counts plus the known gaps.

`legacy/` receives any file whose header no longer matches the current schema,
so an upgrade never silently corrupts a downstream join.

## 9. Ethics and politeness

- Only public pages, no login, no token, no bypass of any access control.
- One request at a time, 0.4 s default delay, exponential backoff on 403/429/503
  with three attempts.
- Full refresh ≈ 90 requests; most are served from cache on a rerun.
- `robots.txt` allows the crawled paths.
- The dataset is published with attribution and a CC BY 4.0 data licence.

## 10. Things deliberately not done

| Idea | Why not |
| --- | --- |
| Scrape historical seasons | Not served; no archive route exists |
| Infer per-game bans | Not published; guessing would fabricate data |
| Compute `matches_played` from the schedule instead of W-L | Would disagree with the official table when a match is rescheduled |
| Normalise `Roamer` → `ROAM` | The two vocabularies are separate source fields; merging them would lose information |
| Derive `nationality` from player names | Unreliable, and not published |
| Parse the playoff bracket image | Would require OCR and produce unverifiable numbers |
