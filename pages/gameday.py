import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

ROSTER_PATH = Path("players.csv")
GAME_LOG_PATH = Path("gameday_log.csv")
PLAYER_STATS_PATH = Path("player_stats.csv")


# --------- Helpers ---------
def load_roster() -> pd.DataFrame:
    if ROSTER_PATH.exists():
        df = pd.read_csv(ROSTER_PATH)
    else:
        df = pd.DataFrame(
            columns=["first_name", "last_name", "jersey_number", "email"]
        )

    for col in ["first_name", "last_name", "jersey_number", "email"]:
        if col not in df.columns:
            df[col] = ""

    df["first_name"] = df["first_name"].astype(str).str.strip()
    df["last_name"] = df["last_name"].astype(str).str.strip()
    df["jersey_number"] = (
        pd.to_numeric(df["jersey_number"], errors="coerce").fillna(0).astype(int)
    )

    df["display_name"] = (
        df["first_name"]
        + " "
        + df["last_name"]
        + " (#"
        + df["jersey_number"].astype(str)
        + ")"
    )
    return df


def load_player_stats() -> pd.DataFrame:
    if PLAYER_STATS_PATH.exists():
        df = pd.read_csv(PLAYER_STATS_PATH)
    else:
        df = pd.DataFrame(
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
    return df


def save_player_stats(df: pd.DataFrame) -> None:
    df.to_csv(PLAYER_STATS_PATH, index=False)


def append_game_log(event: dict) -> None:
    if GAME_LOG_PATH.exists():
        log_df = pd.read_csv(GAME_LOG_PATH)
    else:
        log_df = pd.DataFrame(columns=event.keys())
    log_df = pd.concat([log_df, pd.DataFrame([event])], ignore_index=True)
    log_df.to_csv(GAME_LOG_PATH, index=False)


def update_player_stats(
    stats_df: pd.DataFrame,
    first: str,
    last: str,
    jersey: int,
    outcome: str,
    rbis: int,
) -> pd.DataFrame:
    """Update counting stats for a single PA and recompute AVG/OBP/SLG."""

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
        stats_df = pd.concat(
            [stats_df, pd.DataFrame([new_row])], ignore_index=True
        )
        mask = (
            (stats_df["first_name"] == first)
            & (stats_df["last_name"] == last)
            & (stats_df["jersey_number"] == jersey)
        )

    row_idx = stats_df.index[mask][0]

    # Plate appearance
    stats_df.at[row_idx, "PA"] += 1

    # Outcome logic
    if outcome in ["Single", "Double", "Triple", "Home Run", "Out", "Strikeout"]:
        stats_df.at[row_idx, "AB"] += 1

    if outcome == "Single":
        stats_df.at[row_idx, "H"] += 1
        stats_df.at[row_idx, "1B"] += 1
    elif outcome == "Double":
        stats_df.at[row_idx, "H"] += 1
        stats_df.at[row_idx, "2B"] += 1
    elif outcome == "Triple":
        stats_df.at[row_idx, "H"] += 1
        stats_df.at[row_idx, "3B"] += 1
    elif outcome == "Home Run":
        stats_df.at[row_idx, "H"] += 1
        stats_df.at[row_idx, "HR"] += 1
    elif outcome == "Walk":
        stats_df.at[row_idx, "BB"] += 1
    elif outcome == "Strikeout":
        stats_df.at[row_idx, "K"] += 1

    # RBIs (already capped in UI, but cap again for safety)
    stats_df.at[row_idx, "RBI"] += max(0, min(4, rbis))

    # Recalculate AVG / OBP / SLG
    AB = stats_df.at[row_idx, "AB"]
    H = stats_df.at[row_idx, "H"]
    BB = stats_df.at[row_idx, "BB"]
    _1B = stats_df.at[row_idx, "1B"]
    _2B = stats_df.at[row_idx, "2B"]
    _3B = stats_df.at[row_idx, "3B"]
    HR = stats_df.at[row_idx, "HR"]

    stats_df.at[row_idx, "AVG"] = H / AB if AB > 0 else 0.0
    PA = stats_df.at[row_idx, "PA"]
    stats_df.at[row_idx, "OBP"] = (H + BB) / PA if PA > 0 else 0.0

    total_bases = _1B + 2 * _2B + 3 * _3B + 4 * HR
    stats_df.at[row_idx, "SLG"] = total_bases / AB if AB > 0 else 0.0

    return stats_df


# --------- Streamlit Page ---------
st.set_page_config(
    page_title="Gameday",
    page_icon="",
    layout="wide",
)

st.title("Gameday: Enter Plate Appearance Entry")

roster = load_roster()
if roster.empty:
    st.error("Roster is empty. Go to 'Add / Remove Players' to add players first.")
    st.stop()

batter = st.selectbox("Select Batter", roster["display_name"].tolist())

st.markdown("---")
st.subheader("Enter Plate Appearance")

outcome = st.selectbox(
    "Result",
    ["Single", "Double", "Triple", "Home Run", "Walk", "Strikeout", "Out"],
)

rbis = st.number_input(
    "RBIs on this PA",
    min_value=0,
    max_value=4,  # ✅ cap at 4
    step=1,
    value=0,
)

if st.button("Submit Plate Appearance"):
    sel = roster[roster["display_name"] == batter].iloc[0]
    first = sel["first_name"]
    last = sel["last_name"]
    jersey = int(sel["jersey_number"])

    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "first_name": first,
        "last_name": last,
        "jersey_number": jersey,
        "outcome": outcome,
        "rbis": int(rbis),
    }
    append_game_log(event)

    stats = load_player_stats()
    stats = update_player_stats(stats, first, last, jersey, outcome, int(rbis))
    save_player_stats(stats)

    st.success(f"Logged: {batter} → {outcome}, {rbis} RBI(s)")

    st.subheader("Updated Live Stats for Batter")
    updated = stats[
        (stats["first_name"] == first)
        & (stats["last_name"] == last)
        & (stats["jersey_number"] == jersey)
    ]
    st.dataframe(updated, use_container_width=True)
