import streamlit as st
import pandas as pd
from pathlib import Path
import auth

auth.require_login()

st.set_page_config(
    page_title="LTP Stats",
    page_icon="",
    layout="wide",
)

st.title("LTP Basic Stats")
st.caption("Season-to-date team and player batting stats")

LOG_PATH = Path("gameday_log.csv")
SEASON_HISTORY_PATH = Path("season_history.csv")


@st.cache_data
def load_current_season_log() -> pd.DataFrame:
    """Only include plate appearances tied to games in season history."""
    if not LOG_PATH.exists():
        return pd.DataFrame()

    log_df = pd.read_csv(LOG_PATH)
    if log_df.empty:
        return pd.DataFrame()

    required_log_cols = {
        "game_date",
        "opponent",
        "first_name",
        "last_name",
        "jersey_number",
        "outcome",
        "rbis",
    }
    if not required_log_cols.issubset(set(log_df.columns)):
        return pd.DataFrame()

    if not SEASON_HISTORY_PATH.exists():
        return pd.DataFrame()

    hist_df = pd.read_csv(SEASON_HISTORY_PATH)
    if hist_df.empty or not {"date", "opponent"}.issubset(hist_df.columns):
        return pd.DataFrame()

    log_df["game_date"] = pd.to_datetime(log_df["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    hist_df["date"] = pd.to_datetime(hist_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    log_df["opponent"] = log_df["opponent"].fillna("").astype(str).str.strip()
    hist_df["opponent"] = hist_df["opponent"].fillna("").astype(str).str.strip()

    valid_games = hist_df[["date", "opponent"]].dropna().drop_duplicates()
    merged = log_df.merge(
        valid_games,
        left_on=["game_date", "opponent"],
        right_on=["date", "opponent"],
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame()

    merged["first_name"] = merged["first_name"].fillna("").astype(str).str.strip()
    merged["last_name"] = merged["last_name"].fillna("").astype(str).str.strip()
    merged["player_name"] = (merged["first_name"] + " " + merged["last_name"]).str.strip()
    merged["outcome"] = merged["outcome"].fillna("").astype(str).str.strip()
    merged["rbis"] = pd.to_numeric(merged["rbis"], errors="coerce").fillna(0).astype(int)
    merged["jersey_number"] = pd.to_numeric(merged["jersey_number"], errors="coerce").fillna(0).astype(int)

    return merged


def build_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Player",
                "Jersey",
                "G",
                "PA",
                "AB",
                "R",
                "H",
                "1B",
                "2B",
                "3B",
                "HR",
                "RBI",
                "BB",
                "K",
                "AVG",
                "OBP",
                "SLG",
                "OPS",
            ]
        )

    walk_events = {"Walk"}
    strikeout_events = {"Strikeout", "Strikeout Looking"}

    rows = []

    for player, group in df.groupby("player_name"):
        outcomes = group["outcome"]

        singles = (outcomes == "Single").sum()
        doubles = (outcomes == "Double").sum()
        triples = (outcomes == "Triple").sum()
        homers = (outcomes == "Home Run").sum()
        hits = singles + doubles + triples + homers

        walks = outcomes.isin(walk_events).sum()
        strikeouts = outcomes.isin(strikeout_events).sum()

        pa = len(group)
        ab = pa - walks
        games = group[["game_date", "opponent"]].drop_duplicates().shape[0]

        avg = hits / ab if ab > 0 else 0
        obp = (hits + walks) / pa if pa > 0 else 0
        total_bases = singles + (2 * doubles) + (3 * triples) + (4 * homers)
        slg = total_bases / ab if ab > 0 else 0
        ops = obp + slg

        jersey_number = int(group["jersey_number"].iloc[0])

        rows.append(
            {
                "Player": player,
                "Jersey": jersey_number,
                "G": games,
                "PA": pa,
                "AB": ab,
                "R": 0,
                "H": hits,
                "1B": singles,
                "2B": doubles,
                "3B": triples,
                "HR": homers,
                "RBI": int(group["rbis"].sum()),
                "BB": walks,
                "K": strikeouts,
                "AVG": round(avg, 3),
                "OBP": round(obp, 3),
                "SLG": round(slg, 3),
                "OPS": round(ops, 3),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["OPS", "AVG", "H"],
        ascending=False,
    ).reset_index(drop=True)


log_df = load_current_season_log()
stats_df = build_stats(log_df)

st.markdown("### Stats Pipeline")
st.markdown(
    """
1. **Captain manages lineup** on the *Add / Remove Players* page.
2. **Gameday box score is recorded** on the *Gameday* page.
3. **Season History + Stats update** from those recorded game events.
"""
)

if stats_df.empty:
    st.info("No season games recorded yet. Stats will populate after the first completed game.")

metric1, metric2, metric3, metric4 = st.columns(4)
with metric1:
    st.metric("Games", int(log_df[["game_date", "opponent"]].drop_duplicates().shape[0]) if not log_df.empty else 0)
with metric2:
    st.metric("Plate Appearances", int(stats_df["PA"].sum()) if not stats_df.empty else 0)
with metric3:
    st.metric("Hits", int(stats_df["H"].sum()) if not stats_df.empty else 0)
with metric4:
    st.metric("Home Runs", int(stats_df["HR"].sum()) if not stats_df.empty else 0)

st.markdown("---")
search = st.text_input("Search player name").strip().lower()

display_df = stats_df.copy()
if search and not display_df.empty:
    display_df = display_df[
        display_df["Player"].str.lower().str.contains(search, na=False)
    ]

st.subheader("Player Batting Stats")
st.dataframe(display_df, use_container_width=True, hide_index=True)