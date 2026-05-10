import datetime as dt

import pandas as pd
import streamlit as st

import auth
from stats_utils import (
    box_score_for_game,
    delete_game_and_events,
    load_game_log,
    load_season_history,
    rebuild_player_stats_export,
    update_game_record_and_log,
)

st.set_page_config(page_title="LTP Season History", page_icon="📘", layout="wide")
auth.require_login()

st.title("LTP Season History")
st.caption("Completed games, box scores, and edit/delete tools")

hist_df = load_season_history()

if hist_df.empty:
    st.info("No games recorded yet. End a game in the Gameday tab to add one.")
    st.stop()

# ---------- Game log display ----------
st.subheader("Game Log")
display_history = hist_df.copy()
if "game_id" in display_history.columns:
    display_history = display_history.drop(columns=["game_id"])
st.dataframe(display_history, use_container_width=True, hide_index=True)

# ---------- Season summary ----------
st.markdown("---")
st.subheader("Season Summary")

w = int((hist_df["result"] == "W").sum())
l = int((hist_df["result"] == "L").sum())
t = int((hist_df["result"] == "T").sum())
runs_for = int(pd.to_numeric(hist_df["ltp_runs"], errors="coerce").fillna(0).sum())
runs_against = int(pd.to_numeric(hist_df["opp_runs"], errors="coerce").fillna(0).sum())
run_diff = runs_for - runs_against

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Record", f"{w}-{l}-{t}")
with col2:
    st.metric("Runs For", runs_for)
with col3:
    st.metric("Runs Against", runs_against)
with col4:
    st.metric("Run Differential", f"{run_diff:+d}")

# ---------- Select game ----------
st.markdown("---")
st.subheader("Game Details & Box Score")


def game_label(idx: int) -> str:
    row = hist_df.loc[idx]
    return f"{row['date']} vs {row['opponent']} ({row['ltp_runs']}-{row['opp_runs']}, {row['result']})"


selected_idx = st.selectbox(
    "Select a game",
    options=hist_df.index.tolist(),
    format_func=game_label,
)
game_row = hist_df.loc[selected_idx]
st.markdown(f"**Selected game:** {game_label(selected_idx)}")

# ---------- Box score ----------
st.markdown("### Box Score (LTP hitters)")
box_df = box_score_for_game(game_row)

if box_df.empty:
    st.info("No plate appearance log found for this game.")
else:
    show_cols = [
        "Player",
        "Jersey",
        "AB",
        "R",
        "H",
        "1B",
        "2B",
        "3B",
        "HR",
        "BB",
        "K",
        "RBI",
        "AVG",
        "OBP",
        "SLG",
        "OPS",
    ]
    st.dataframe(box_df[show_cols], use_container_width=True, hide_index=True)

with st.expander("Raw plate appearances for this game"):
    log_df = load_game_log()
    if log_df.empty:
        st.write("No gameday_log.csv data found.")
    else:
        game_id = str(game_row.get("game_id", "")).strip()
        if game_id:
            raw_events = log_df[log_df["game_id"] == game_id]
        else:
            raw_events = log_df[
                (log_df["game_date"] == str(game_row["date"]))
                & (log_df["opponent"] == str(game_row["opponent"]).strip())
            ]
        st.dataframe(raw_events, use_container_width=True, hide_index=True)

# ---------- Edit / Delete controls ----------
st.markdown("---")
st.subheader("Edit / Delete This Game")

col_edit, col_delete = st.columns(2)

with col_edit:
    try:
        base_date = pd.to_datetime(game_row["date"]).date()
    except Exception:
        base_date = dt.date.today()

    new_date = st.date_input("Game date", value=base_date, key="edit_date")
    new_opp = st.text_input("Opponent", value=str(game_row["opponent"]), key="edit_opp")
    new_ltp_runs = st.number_input(
        "LTP runs", min_value=0, value=int(game_row["ltp_runs"]), key="edit_ltp_runs"
    )
    new_opp_runs = st.number_input(
        "Opponent runs", min_value=0, value=int(game_row["opp_runs"]), key="edit_opp_runs"
    )

    if st.button("Save Changes"):
        if not str(new_opp).strip():
            st.error("Opponent name cannot be blank.")
            st.stop()

        update_game_record_and_log(
            selected_index=int(selected_idx),
            new_date=str(new_date),
            new_opponent=str(new_opp).strip(),
            new_ltp_runs=int(new_ltp_runs),
            new_opp_runs=int(new_opp_runs),
        )
        rebuild_player_stats_export()
        st.success("Game updated and player_stats.csv rebuilt.")
        st.rerun()

with col_delete:
    st.warning(
        "Deleting a game removes it from season_history.csv, removes its plate appearances "
        "from gameday_log.csv, and rebuilds player_stats.csv."
    )
    confirm_delete = st.checkbox("I understand this will delete the selected game.")
    if st.button("Delete This Game"):
        if not confirm_delete:
            st.error("Check the confirmation box before deleting.")
            st.stop()

        delete_game_and_events(int(selected_idx))
        rebuild_player_stats_export()
        st.success("Game and associated plate appearances deleted. Stats rebuilt.")
        st.rerun()
