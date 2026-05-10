import pandas as pd
import streamlit as st

import auth
from stats_utils import (
    build_player_stats,
    completed_game_log,
    load_season_history,
    rebuild_player_stats_export,
)

st.set_page_config(page_title="LTP Stats", page_icon="📈", layout="wide")
auth.require_login()

st.title("LTP Basic Stats")
st.caption("Season-to-date team and player batting stats rebuilt from gameday_log.csv")

st.markdown(
    """
### Stats Pipeline
1. **Roster** is managed from `players.csv`.
2. **Every plate appearance** is logged in `gameday_log.csv`.
3. **Completed games** are saved in `season_history.csv`.
4. This page rebuilds batting stats from the completed-game log, so edits/deletes stay consistent.
"""
)

all_events = completed_game_log()
history_df = load_season_history()

if all_events.empty:
    st.info(
        "No completed games are available yet. Enter plate appearances in Gameday, then click "
        "'End Game & Save Stats' to add them to the season totals."
    )
    stats_df = build_player_stats(all_events)
else:
    all_events["game_date_dt"] = pd.to_datetime(all_events["game_date"], errors="coerce")
    years = sorted(all_events["game_date_dt"].dt.year.dropna().astype(int).unique().tolist())
    year_options = ["All"] + [str(y) for y in years]

    c_filter1, c_filter2 = st.columns([1, 2])
    with c_filter1:
        selected_year = st.selectbox("Filter by year", options=year_options, index=0)
    with c_filter2:
        search = st.text_input("Search player name").strip().lower()

    events_df = all_events.copy()
    if selected_year != "All":
        events_df = events_df[events_df["game_date_dt"].dt.year == int(selected_year)]

    stats_df = build_player_stats(events_df)
    if search and not stats_df.empty:
        stats_df = stats_df[stats_df["Player"].str.lower().str.contains(search, na=False)]

    game_keys = events_df.apply(
        lambda r: str(r.get("game_id") or "").strip()
        or f"{r.get('game_date', '')}|{r.get('opponent', '')}",
        axis=1,
    )

    total_pa = int(stats_df["PA"].sum()) if not stats_df.empty else 0
    total_ab = int(stats_df["AB"].sum()) if not stats_df.empty else 0
    total_hits = int(stats_df["H"].sum()) if not stats_df.empty else 0
    total_hr = int(stats_df["HR"].sum()) if not stats_df.empty else 0
    team_avg = total_hits / total_ab if total_ab else 0.0

    metric1, metric2, metric3, metric4, metric5 = st.columns(5)
    with metric1:
        st.metric("Games", int(game_keys.nunique()))
    with metric2:
        st.metric("Plate Appearances", total_pa)
    with metric3:
        st.metric("Hits", total_hits)
    with metric4:
        st.metric("Home Runs", total_hr)
    with metric5:
        st.metric("Team AVG", f"{team_avg:.3f}".replace("0.", "."))

st.markdown("---")
st.subheader("Player Batting Stats")

if not stats_df.empty:
    display_cols = [
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
    st.dataframe(stats_df[display_cols], use_container_width=True, hide_index=True)
else:
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

st.markdown("---")
if st.button("Rebuild player_stats.csv export"):
    export_df = rebuild_player_stats_export()
    st.success(f"player_stats.csv rebuilt with {len(export_df)} player row(s).")

with st.expander("Raw completed plate appearances"):
    if all_events.empty:
        st.write("No completed plate appearances yet.")
    else:
        st.dataframe(
            all_events.drop(columns=["game_date_dt"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )
