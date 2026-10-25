"""MPL Indonesia dataset pipeline.

Collects the public data published on https://id-mpl.com into a set of
CSV files suitable for esports analytics.

Modules
-------
fetch       HTTP download with on-disk cache (obscura fallback)
parse       shared text/number/date helpers
schedule    /schedule           -> matches (regular season + playoffs)
standings   /home               -> official standings tables
teams       /teams, /team/<id>  -> teams, rosters, players
statistics  /statistics         -> hero, player, team, MVP aggregates
matchdetail /match-detail/<id>  -> per-game drafts and player stats
analytics   derived tables (synergy, matchups, team hero pools)
pipeline    orchestration + CSV upsert
quality     dataset validation report
"""

__version__ = "2.0.0"
