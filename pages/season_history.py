import streamlit as st
import pandas as pd
from pathlib import Path

SEASON_HISTORY_PATH = Path("season_history.csv")
GAME_LOG_PATH = Path("gameday_log.csv")
PLAYER_STATS_PATH = Path("player_stats.csv")

# --------- helpers for box score + stat rebuild (copied from gameday) ----------
def empty_stats_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "first_name",
            "last_name",
            "jersey_number",
            "PA",
            "AB",
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
        ]
    )


def update_player_stats(
    stats_df: pd.DataFrame,
    first: str,
    last: str,
    jersey: int,
    outcome: str,
    rbis: int,
) -> pd.DataFrame:
    mask = (
        (stats_df["first_name"] == first)
        & (stats_df["last_name"] == last)
        & (stats_df["jersey_number"] == jersey)
    )

    if not mask.any():
        new_row = {
            "first_name": first,
            "last_name": last,
            "jersey_number": jersey,
            "PA": 0,
            "AB": 0,
            "H": 0,
            "1B": 0,
            "2B": 0,
            "3B": 0,
            "HR": 0,
            "BB": 0,
            "K": 0,
            "RBI": 0,
            "AVG": 0.0,
            "OBP": 0.0,
            "SLG": 0.0,
        }
        stats_df = pd.concat([stats_df, pd.DataFrame([new_row])], ignore_index=True)
        mask = (
            (stats_df["first_name"] == first)
            & (stats_df["last_name"] == last)
            & (stats_df["jersey_number"] == jersey)
        )

    idx = stats_df.index[mask][0]
    stats_df.at[idx, "PA"] += 1

    ab_outcomes = [
        "Single",
        "Double",
        "Triple",
        "Home Run",
        "Out",
        "Strikeout",
        "Double Play",
        "Triple Play",
    ]
    if outcome in ab_outcomes:
        stats_df.at[idx, "AB"] += 1

    if outcome == "Single":
        stats_df.at[idx, "H"] += 1
        stats_df.at[idx, "1B"] += 1
    elif outcome == "Double":
        stats_df.at[idx, "H"] += 1
        stats_df.at[idx, "2B"] += 1
    elif outcome == "Triple":
        stats_df.at[idx, "H"] += 1
        stats_df.at[idx, "3B"] += 1
    elif outcome == "Home Run":
        stats_df.at[idx, "H"] += 1
        stats_df.at[idx, "HR"] += 1
    elif outcome == "Walk":
        stats_df.at[idx, "BB"] += 1
    elif outcome == "Strikeout":
        stats_df.at[idx, "K"] += 1

    stats_df.at[idx, "RBI"] += max(0, min(4, rbis))

    AB = stats_df.at[idx, "AB"]
    H = stats_df.at[idx, "H"]
    BB = stats_df.at[idx, "BB"]
    _1B = stats_df.at[idx, "1B"]
    _2B = stats_df.at[idx, "2B"]
    _3B = stats_df.at[idx, "3B"]
    HR = stats_df.at[idx, "HR"]

    stats_df.at[idx, "AVG"] = H / AB if AB > 0 else 0.0
    PA = stats_df.at[idx, "PA"]
    stats_df.at[idx, "OBP"] = (H + BB) / PA if PA > 0 else 0.0
    total_bases = _1B + 2 * _2B + 3 * _3B + 4 * HR
    stats_df.at[idx, "SLG"] = total_bases / AB if AB > 0 else 0.0

    return stats_df


def recompute_stats_from_log():
    if not GAME_LOG_PATH.exists():
        empty_stats_df().to_csv(PLAYER_STATS_PATH, index=False)
        return

    log_df = pd.read_csv(GAME_LOG_PATH)
    stats_df = empty_stats_df()
    for _, row in log_df.iterrows():
        stats_df = update_player_stats(
            stats_df,
            row["first_name"],
            row["last_name"],
            int(row["jersey_number"]),
            row["outcome"],
            int(row.get("rbis", 0)),
        )
    stats_df.to_csv(PLAYER_STATS_PATH, index=False)


# ---------- UI ----------
st.set_page_config(page_title="LTP Season History", page_icon="📘", layout="wide")
st.title("LTP Season History")

if not SEASON_HISTORY_PATH.exists():
    st.info("No games recorded yet. End a game in the Gameday tab to add one.")
    st.stop()

hist_df = pd.read_csv(SEASON_HISTORY_PATH)

st.subheader("Game Log")
st.dataframe(hist_df, use_container_width=True)

# ---------- Season summary ----------
st.markdown("---")
st.subheader("Season Summary")

w = (hist_df["result"] == "W").sum()
l = (hist_df["result"] == "L").sum()
t = (hist_df["result"] == "T").sum()

runs_for = hist_df["ltp_runs"].sum()
runs_against = hist_df["opp_runs"].sum()
run_diff = runs_for - runs_against

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Record**")
    st.markdown(f"### {w}-{l}-{t}")
with col2:
    st.markdown("**Runs For**")
    st.markdown(f"### {runs_for}")
with col3:
    st.markdown("**Runs Against**")
    st.markdown(f"### {runs_against}")

st.write(f"**Run Differential:** {run_diff:+d}")

# ---------- Select game for box score / edit / delete ----------
st.markdown("---")
st.subheader("Game Details & Box Score")

if hist_df.empty:
    st.info("No games available.")
    st.stop()

game_labels = {}
for idx, row in hist_df.iterrows():
    label = f"{row['date']} vs {row['opponent']} ({row['ltp_runs']}-{row['opp_runs']}, {row['result']})"
    game_labels[idx] = label

selected_label = st.selectbox("Select a game", options=list(game_labels.values()))
selected_idx = [i for i, lbl in game_labels.items() if lbl == selected_label][0]
game_row = hist_df.loc[selected_idx]

st.markdown(f"**Selected game:** {game_labels[selected_idx]}")

# ---------- Box score ----------
st.markdown("### Box Score (LTP hitters)")

if GAME_LOG_PATH.exists():
    log_df = pd.read_csv(GAME_LOG_PATH)
    # game_date stored as ISO string in gameday log
    game_date_str = str(game_row["date"]).split(" ")[0]
    mask = (log_df["game_date"].astype(str) == game_date_str) & (
        log_df["opponent"] == game_row["opponent"]
    )
    game_events = log_df[mask]

    if game_events.empty:
        st.info("No plate appearance log found for this game.")
    else:
        per_game_stats = empty_stats_df()
        for _, r in game_events.iterrows():
            per_game_stats = update_player_stats(
                per_game_stats,
                r["first_name"],
                r["last_name"],
                int(r["jersey_number"]),
                r["outcome"],
                int(r.get("rbis", 0)),
            )

        show_cols = [
            "first_name",
            "last_name",
            "jersey_number",
            "AB",
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
        ]
        per_game_stats = per_game_stats[show_cols].sort_values(
            ["last_name", "first_name"]
        )
        per_game_stats["AVG"] = per_game_stats["AVG"].round(3)
        per_game_stats["OBP"] = per_game_stats["OBP"].round(3)
        per_game_stats["SLG"] = per_game_stats["SLG"].round(3)

        st.dataframe(per_game_stats, use_container_width=True, hide_index=True)
else:
    st.info("No gameday log file found yet (gameday_log.csv).")

# ---------- Edit / Delete controls ----------
st.markdown("---")
st.subheader("Edit / Delete This Game")

col_edit, col_delete = st.columns(2)

with col_edit:
    import datetime as _dt

    try:
        base_date = pd.to_datetime(game_row["date"]).date()
    except Exception:
        base_date = _dt.date.today()

    new_date = st.date_input("Game date", value=base_date, key="edit_date")
    new_opp = st.text_input("Opponent", value=str(game_row["opponent"]), key="edit_opp")
    new_ltp_runs = st.number_input(
        "LTP runs", min_value=0, value=int(game_row["ltp_runs"]), key="edit_ltp_runs"
    )
    new_opp_runs = st.number_input(
        "Opponent runs",
        min_value=0,
        value=int(game_row["opp_runs"]),
        key="edit_opp_runs",
    )

    if st.button("Save Changes"):
        hist_df.at[selected_idx, "date"] = str(new_date)
        hist_df.at[selected_idx, "opponent"] = new_opp
        hist_df.at[selected_idx, "ltp_runs"] = int(new_ltp_runs)
        hist_df.at[selected_idx, "opp_runs"] = int(new_opp_runs)

        if new_ltp_runs > new_opp_runs:
            result = "W"
        elif new_ltp_runs < new_opp_runs:
            result = "L"
        else:
            result = "T"
        hist_df.at[selected_idx, "result"] = result

        hist_df.to_csv(SEASON_HISTORY_PATH, index=False)
        st.success("Game updated.")
        st.rerun()

with col_delete:
    st.warning(
        "Deleting a game will also remove all of its plate appearances from the "
        "gameday log and rebuild season stats."
    )
    if st.button("Delete This Game"):
        # Remove from season history
        hist_df = hist_df.drop(index=selected_idx).reset_index(drop=True)
        hist_df.to_csv(SEASON_HISTORY_PATH, index=False)

        # Remove related entries from gameday log & rebuild stats
        if GAME_LOG_PATH.exists():
            log_df = pd.read_csv(GAME_LOG_PATH)
            game_date_str = str(game_row["date"]).split(" ")[0]
            mask = (log_df["game_date"].astype(str) == game_date_str) & (
                log_df["opponent"] == game_row["opponent"]
            )
            log_df = log_df[~mask]
            log_df.to_csv(GAME_LOG_PATH, index=False)
            recompute_stats_from_log()

        st.success("Game and associated plate appearances deleted.")
        st.rerun()
