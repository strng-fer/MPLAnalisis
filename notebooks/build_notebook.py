"""Generate notebooks/01_explore.ipynb.

Keeping the notebook generated from source makes it reviewable in a diff and
lets the cell code be smoke tested as plain Python.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "notebooks" / "01_explore.ipynb"


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.strip("\n").splitlines(keepends=True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    }


CELLS = [
    md(
        """
# MPL Indonesia Season 18 — exploratory analysis

Starter notebook for the dataset. It runs unchanged on Kaggle (input mounted at
`/kaggle/input/mpl-indonesia-s18`) or locally from a clone of the repository
(`../data`).

**What it covers**

1. Loading and inventory
2. Hero meta: pick rate, ban rate, win rate
3. Draft synergy: hero pairs that win together
4. Player leaderboards
5. Team form across the season
6. Head-to-head matchups
"""
    ),
    code(
        """
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 40)
plt.rcParams["figure.figsize"] = (10, 5)
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25


def find_data() -> Path:
    candidates = [
        Path("/kaggle/input/mpl-indonesia-s18"),
        Path("../data"),
        Path("data"),
    ]
    for candidate in candidates:
        if (candidate / "mpl-game-players.csv").exists():
            return candidate
    raise FileNotFoundError("dataset not found; run `python -m mplid --out ./data` first")


DATA = find_data()
print("data directory:", DATA.resolve())


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")
"""
    ),
    md(
        """
## 1. Inventory

Every table, its row count and its grain. The counts are the ones the pipeline
asserts in its test suite, so a mismatch here means a stale checkout.
"""
    ),
    code(
        """
tables = sorted(p.stem for p in DATA.glob("mpl-*.csv"))
inventory = pd.DataFrame(
    {"table": tables, "rows": [len(load(t)) for t in tables]}
).sort_values("rows", ascending=False)
inventory["rows"] = inventory["rows"].map("{:,}".format)
inventory.reset_index(drop=True)
"""
    ),
    code(
        """
schedule = load("mpl-schedule")
games = load("mpl-games")
gp = load("mpl-game-players")
drafts = load("mpl-drafts")
standings = load("mpl-standings")
hero_stats = load("mpl-hero-stats")

completed = schedule[schedule.match_status == "completed"]
print(f"matches: {len(schedule)} scheduled/completed, {len(completed)} completed")
print(f"games: {len(games)}, average length {games.duration_seconds.mean() / 60:.1f} min")
print(f"player-game rows: {len(gp):,}")
print(f"date range: {completed.match_date.min()} -> {completed.match_date.max()}")
"""
    ),
    md(
        """
## 2. Hero meta

`mpl-hero-stats` carries the official season totals: picks, bans, wins and win
rate. Pick rate and ban rate are derived by dividing by the number of games
(174), because each game has exactly 10 picks and 10 bans would be needed for a
true ban rate — and per-game bans are not published. Ban share is therefore
expressed against total picks, which is a safe denominator.
"""
    ),
    code(
        """
total_games = len(games)
total_picks = hero_stats.picks.sum()

meta = hero_stats[hero_stats.picks > 0].copy()
meta["pick_rate"] = (meta.picks / total_games / 2).round(4)   # 2 teams per game
meta["ban_share"] = (meta.bans / total_picks).round(4)
meta = meta.sort_values("picks", ascending=False)

meta.head(15)[["hero_name", "picks", "bans", "wins", "win_rate", "pick_rate", "ban_share"]]
"""
    ),
    code(
        """
top = meta.head(12).iloc[::-1]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
axes[0].barh(top.hero_name, top.picks, color="#3b6ea5")
axes[0].set_title("Most picked heroes")
axes[0].set_xlabel("picks")

banned = meta.sort_values("bans", ascending=False).head(12).iloc[::-1]
axes[1].barh(banned.hero_name, banned.bans, color="#a5453b")
axes[1].set_title("Most banned heroes")
axes[1].set_xlabel("bans")

plt.tight_layout()
plt.show()
"""
    ),
    code(
        """
# heroes with a real sample size, ranked by win rate
sample = meta[meta.picks >= 15].sort_values("win_rate", ascending=False)
sample[["hero_name", "picks", "bans", "wins", "win_rate"]].head(12)
"""
    ),
    md(
        """
## 3. Draft synergy

`mpl-hero-synergy` counts how often two heroes shared a side and how often that
side won. With only 174 games, most pairs are thin, so filter before drawing
conclusions. The `lift` column compares the pair's win rate with the hero's own
baseline win rate.
"""
    ),
    code(
        """
synergy = load("mpl-hero-synergy")
baseline = hero_stats.set_index("hero_name").win_rate

strong = synergy[synergy.games_together >= 12].copy()
strong["baseline"] = strong[["hero_a", "hero_b"]].apply(
    lambda r: np.mean([baseline.get(r.hero_a, np.nan), baseline.get(r.hero_b, np.nan)]), axis=1
)
strong["lift"] = (strong.win_rate - strong.baseline).round(4)
strong = strong.sort_values(["win_rate", "games_together"], ascending=False)

strong.head(15)[["hero_a", "hero_b", "games_together", "wins_together", "win_rate", "lift"]]
"""
    ),
    md(
        """
## 4. Player leaderboards

Season aggregates live in `mpl-player-stats`. Per-hero splits come from the game
log, which is also where the gold and damage totals live.
"""
    ),
    code(
        """
player_stats = load("mpl-player-stats")
teams = load("mpl-teams")[["team_id", "team_name"]].rename(columns={"team_name": "team_full"})

board = player_stats.merge(teams, on="team_id", how="left")
board = board[board.games >= 20].sort_values("avg_kda", ascending=False)

board.head(15)[["player_name", "team_id", "lane", "games", "avg_kills", "avg_deaths",
                "avg_assists", "avg_kda", "kill_participation"]]
"""
    ),
    code(
        """
per_hero = load("mpl-player-hero-stats")
signature = (
    per_hero.sort_values(["player_name", "games"], ascending=[True, False])
    .groupby("player_name")
    .head(1)
    .sort_values("games", ascending=False)
)
signature.head(15)[["player_name", "team_name", "hero_name", "games", "win_rate", "kda"]]
"""
    ),
    md(
        """
## 5. Team form

`mpl-team-form` gives the weekly record, which is the natural series for a
progression chart. Cumulative game difference is a decent proxy for how a team
trended through the regular season.
"""
    ),
    code(
        """
form = load("mpl-team-form")
form["week"] = form.week.astype(int)
form = form.sort_values(["team_name", "week"])
form["cum_game_diff"] = form.groupby("team_name").game_difference.cumsum()

pivot = form.pivot_table(index="week", columns="team_name", values="cum_game_diff")
pivot = pivot.reindex(range(1, pivot.index.max() + 1)).ffill()

ax = pivot.plot(figsize=(11, 6), linewidth=2)
ax.set_title("Cumulative game difference by week")
ax.set_xlabel("week")
ax.set_ylabel("cumulative game wins - losses")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False)
plt.tight_layout()
plt.show()
"""
    ),
    code(
        """
season_totals = (
    form.groupby("team_name")
    .agg(
        matches=("matches", "sum"),
        match_wins=("match_wins", "sum"),
        match_losses=("match_losses", "sum"),
        game_wins=("game_wins", "sum"),
        game_losses=("game_losses", "sum"),
        game_difference=("game_difference", "sum"),
    )
    .sort_values("game_difference", ascending=False)
)

official = standings.sort_values("rank")[["rank", "team_name", "points", "wins", "losses",
                                          "game_wins", "game_losses", "game_difference"]]
print("Official standings")
display(official)
print("Reconstructed from the schedule, summed over the nine weeks")
display(season_totals)
"""
    ),
    md(
        """
## 6. Head-to-head and matchups

`mpl-head-to-head` is ordered alphabetically (`team_a` < `team_b`), so always
check which side a team is on before reading a record.
"""
    ),
    code(
        """
h2h = load("mpl-head-to-head")
h2h["margin"] = (h2h.team_a_match_wins - h2h.team_b_match_wins).abs()
h2h.sort_values(["matches", "margin"], ascending=False).head(12)[
    ["team_a", "team_b", "matches", "team_a_match_wins", "team_b_match_wins",
     "team_a_game_wins", "team_b_game_wins"]
]
"""
    ),
    code(
        """
matchups = load("mpl-hero-matchups")
top_heroes = meta.head(8).hero_name.tolist()

matrix = (
    matchups[matchups.hero.isin(top_heroes) & matchups.opponent_hero.isin(top_heroes)]
    .pivot_table(index="hero", columns="opponent_hero", values="win_rate")
    .reindex(index=top_heroes, columns=top_heroes)
)

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(matrix.values, cmap="RdYlGn", vmin=0.25, vmax=0.75)
ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
ax.set_yticks(range(len(matrix.index)), matrix.index)
ax.set_title("Win rate of row hero against column hero")
fig.colorbar(im, ax=ax, label="win rate")
plt.tight_layout()
plt.show()
"""
    ),
    md(
        """
## 7. Where to go next

- **Draft modelling**: `mpl-drafts` plus `mpl-hero-synergy` is enough to train a
  pick-win model; treat each game as 10 binary decisions and use team strength as
  a control.
- **Player valuation**: combine `mpl-game-players.gold` share with
  `damage_dealt` and kill participation to get a per-game impact metric.
- **Multi-season trends**: the source serves one season at a time. Run
  `python -m mplid --out ./data` each season and concatenate on `season`.
- **Known gaps**: no per-game bans, no player nationality, no contract dates.
  Do not infer them.

Full column documentation is in `docs/DATA_DICTIONARY.md`.
"""
    ),
]


def main() -> None:
    notebook = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
