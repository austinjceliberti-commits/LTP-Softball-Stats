import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date

# ---------- File paths ----------
ROSTER_PATH = Path("players.csv")
GAME_LOG_PATH = Path("gameday_log.csv")
PLAYER_STATS_PATH = Path("player_stats.csv")
SEASON_HISTORY_PATH = Path("season_history.csv")
STATS_2025_PATH = Path("ltp_2025 1(in).csv")   # historical file used by Odds Maker


# ---------- Helper functions ----------
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

    # Outcomes that count as AB
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
    # Out / Double Play / Triple Play: just AB, no hits, no BB, no K

    # RBIs (cap at 4 for safety)
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


# ---------- In-game stat aggregation for 2025 CSV (Option A) ----------
def record_game_stat(first: str, last: str, outcome: str):
    """
    Aggregate per-game stats for merging into 2025 CSV.
    Only used at End Game to update ltp_2025 1(in).csv.
    """
    name = f"{first} {last}".strip()
    if "game_stats" not in st.session_state:
        st.session_state.game_stats = {}

    if name not in st.session_state.game_stats:
        st.session_state.game_stats[name] = {
            "PA": 0,
            "1B": 0,
            "2B": 0,
            "3B": 0,
            "HR": 0,
            "BB": 0,
            "K": 0,
        }

    s = st.session_state.game_stats[name]
    s["PA"] += 1

    if outcome == "Single":
        s["1B"] += 1
    elif outcome == "Double":
        s["2B"] += 1
    elif outcome == "Triple":
        s["3B"] += 1
    elif outcome == "Home Run":
        s["HR"] += 1
    elif outcome == "Walk":
        s["BB"] += 1
    elif outcome == "Strikeout":
        s["K"] += 1
    # Out / Double Play / Triple Play: no extra columns, just PA

    st.session_state.game_stats[name] = s


def merge_game_stats_into_2025():
    """
    Merge st.session_state.game_stats into ltp_2025 1(in).csv.
    Called ONLY when End Game & Upload Stats button is pressed.
    """
    stats_dict = st.session_state.get("game_stats", {})
    if not stats_dict:
        return

    if STATS_2025_PATH.exists():
        try:
            df = pd.read_csv(STATS_2025_PATH)
        except UnicodeDecodeError:
            df = pd.read_csv(STATS_2025_PATH, encoding="latin1")
    else:
        df = pd.DataFrame(columns=["Name", "PA", "1B", "2B", "3B", "HR", "BB", "K"])

    # Ensure columns exist and numeric
    for col in ["Name", "PA", "1B", "2B", "3B", "HR", "BB", "K"]:
        if col not in df.columns:
            df[col] = 0
    num_cols = ["PA", "1B", "2B", "3B", "HR", "BB", "K"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    for name, s in stats_dict.items():
        mask = df["Name"].astype(str) == name
        if mask.any():
            for col in num_cols:
                df.loc[mask, col] = df.loc[mask, col] + s[col]
        else:
            new_row = {"Name": name}
            for col in num_cols:
                new_row[col] = s[col]
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(STATS_2025_PATH, index=False)


# ---------- Streamlit setup ----------
st.set_page_config(
    page_title="Gameday",
    page_icon="📊",
    layout="wide",
)

st.title("Gameday: Enter Plate Appearance Entry")


# ---------- Initialize session_state for game flow ----------
def init_game_state():
    st.session_state.game_active = False
    st.session_state.game_date = str(date.today())
    st.session_state.opponent = ""
    st.session_state.inning = 1             # start in 1st
    st.session_state.half = "Top"           # Top / Bottom
    st.session_state.offense = "LTP"        # LTP or Opponent
    st.session_state.outs = 0
    st.session_state.ltp_role = "Away"      # Home or Away; default

    st.session_state.ltp_scores = {}        # inning -> runs
    st.session_state.opp_scores = {}
    st.session_state.current_ltp_runs = 0
    st.session_state.current_opp_runs = 0

    st.session_state.game_stats = {}        # per-game hitting for 2025 CSV


if "game_active" not in st.session_state:
    init_game_state()


# ---------- Start new game UI ----------
roster = load_roster()
if roster.empty:
    st.error("Roster is empty. Go to 'Add / Remove Players' to add players first.")
    st.stop()

with st.expander("Start / Reset Game", expanded=not st.session_state.game_active):
    game_date = st.date_input(
        "Game date",
        value=date.fromisoformat(st.session_state.game_date),
        key="game_date_input",
    )
    opponent = st.text_input(
        "Opponent name",
        value=st.session_state.opponent,
        placeholder="e.g., Beer League Bandits",
    )

    ltp_role = st.radio(
        "LTP is:",
        ["Home", "Away"],
        index=0 if st.session_state.get("ltp_role", "Home") == "Home" else 1,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Start New Game"):
            init_game_state()
            st.session_state.game_active = True
            st.session_state.game_date = str(game_date)
            st.session_state.opponent = opponent or "Unknown Opponent"
            st.session_state.ltp_role = ltp_role

            # Set who bats first based on Home/Away
            st.session_state.inning = 1
            st.session_state.half = "Top"
            if ltp_role == "Away":
                st.session_state.offense = "LTP"       # LTP bats in top 1
            else:
                st.session_state.offense = "Opponent"  # Opponent bats in top 1

            st.success(
                f"Game started vs {st.session_state.opponent} on {st.session_state.game_date}. "
                f"LTP is {ltp_role} team."
            )
            st.rerun()
    with col_b:
        if st.button("Reset Current Game (Discard Progress)"):
            init_game_state()
            st.warning("Current game state cleared (historical 2025 stats NOT touched).")

if not st.session_state.game_active:
    st.stop()

# ---------- Scoreboard ----------
st.markdown("---")
st.subheader("Scoreboard")

ltp_scores = st.session_state.ltp_scores
opp_scores = st.session_state.opp_scores

max_inning = max(
    6, st.session_state.inning, *(ltp_scores.keys() or [1]), *(opp_scores.keys() or [1])
)

innings = list(range(1, max_inning + 1))

ltp_row = []
opp_row = []

for inn in innings:
    ltp_val = ltp_scores.get(inn, 0)
    opp_val = opp_scores.get(inn, 0)
    # Add current-half runs in-progress
    if inn == st.session_state.inning:
        if st.session_state.offense == "LTP":
            ltp_val += st.session_state.current_ltp_runs
        else:
            opp_val += st.session_state.current_opp_runs

    ltp_row.append(ltp_val)
    opp_row.append(opp_val)

score_df = pd.DataFrame(
    {
        "Inning": innings,
        "LTP": ltp_row,
        st.session_state.opponent or "Opponent": opp_row,
    }
)

st.dataframe(score_df, use_container_width=True, hide_index=True)

total_ltp = sum(ltp_scores.values()) + st.session_state.current_ltp_runs
total_opp = sum(opp_scores.values()) + st.session_state.current_opp_runs

st.write(f"**Total Score:** LTP {total_ltp} — {total_opp} {st.session_state.opponent}")

if st.session_state.inning > 6:
    st.caption("Regulation 6 innings complete. Extra innings in progress.")


# ---------- Current half-inning status ----------
st.markdown("---")
half_label = f"{st.session_state.half} {st.session_state.inning}"
offense_label = (
    "LTP batting" if st.session_state.offense == "LTP" else f"{st.session_state.opponent} batting"
)
st.subheader(f"Inning {st.session_state.inning} — {half_label} ({offense_label})")
st.write(f"**Outs:** {st.session_state.outs} / 3")


# ---------- LTP batting flow ----------
if st.session_state.offense == "LTP":
    st.markdown("### Enter Plate Appearance")

    batter = st.selectbox("Select Batter", roster["display_name"].tolist())

    outcome = st.selectbox(
        "Result",
        [
            "Single",
            "Double",
            "Triple",
            "Home Run",
            "Walk",
            "Strikeout",
            "Out",
            "Double Play",
            "Triple Play",
        ],
    )

    rbis = st.number_input(
        "RBIs on this PA",
        min_value=0,
        max_value=4,
        step=1,
        value=0,
    )

    if st.button("Submit Plate Appearance"):
        sel = roster[roster["display_name"] == batter].iloc[0]
        first = sel["first_name"]
        last = sel["last_name"]
        jersey = int(sel["jersey_number"])

        # Log event
        event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_date": st.session_state.game_date,
            "opponent": st.session_state.opponent,
            "inning": st.session_state.inning,
            "half": st.session_state.half,
            "first_name": first,
            "last_name": last,
            "jersey_number": jersey,
            "outcome": outcome,
            "rbis": int(rbis),
        }
        append_game_log(event)

        # Update live stats
        stats = load_player_stats()
        stats = update_player_stats(
            stats, first, last, jersey, outcome, int(rbis)
        )
        save_player_stats(stats)

        # Record per-game stats for 2025 CSV (Option A)
        record_game_stat(first, last, outcome)

        # Update runs + outs in game state
        st.session_state.current_ltp_runs += int(rbis)

        # Outs: regular, double play, triple play
        if outcome in ["Out", "Strikeout"]:
            st.session_state.outs += 1
        elif outcome == "Double Play":
            st.session_state.outs += 2
        elif outcome == "Triple Play":
            st.session_state.outs += 3

        # Cap outs at 3
        if st.session_state.outs > 3:
            st.session_state.outs = 3

        # Check end of half-inning
        if st.session_state.outs >= 3:
            # Commit inning runs
            prev = st.session_state.ltp_scores.get(
                st.session_state.inning, 0
            )
            st.session_state.ltp_scores[st.session_state.inning] = (
                prev + st.session_state.current_ltp_runs
            )
            st.session_state.current_ltp_runs = 0
            st.session_state.outs = 0

            # Switch to opponent half
            st.session_state.offense = "Opponent"
            st.session_state.half = "Bottom" if st.session_state.half == "Top" else "Top"

        st.rerun()

# ---------- Opponent batting flow ----------
else:
    st.markdown("### Opponent Half-Inning")

    runs_this_half = st.number_input(
        f"Runs scored by {st.session_state.opponent} this half-inning",
        min_value=0,
        max_value=50,
        step=1,
        value=0,
        key="opp_runs_input",
    )

    outs_this_half = st.number_input(
        "Outs recorded this half (should end at 3)",
        min_value=0,
        max_value=3,
        step=1,
        value=3,
        key="opp_outs_input",
    )

    if st.button("Submit Opponent Half"):
        st.session_state.current_opp_runs = int(runs_this_half)
        # We don't track individual opponent PAs, just runs & outs

        prev = st.session_state.opp_scores.get(st.session_state.inning, 0)
        st.session_state.opp_scores[st.session_state.inning] = (
            prev + st.session_state.current_opp_runs
        )
        st.session_state.current_opp_runs = 0

        # End of inning when opponent half finishes
        st.session_state.outs = 0
        st.session_state.inning += 1
        st.session_state.half = "Top"
        st.session_state.offense = "LTP"

        st.rerun()


# ---------- End game + save to season history + upload stats ----------
st.markdown("---")
st.subheader("End Game")

if st.button("End Game & Upload Stats"):
    # Make sure current half-inning runs are committed
    if st.session_state.offense == "LTP" and st.session_state.current_ltp_runs > 0:
        prev = st.session_state.ltp_scores.get(st.session_state.inning, 0)
        st.session_state.ltp_scores[st.session_state.inning] = (
            prev + st.session_state.current_ltp_runs
        )
        st.session_state.current_ltp_runs = 0
    elif st.session_state.offense == "Opponent" and st.session_state.current_opp_runs > 0:
        prev = st.session_state.opp_scores.get(st.session_state.inning, 0)
        st.session_state.opp_scores[st.session_state.inning] = (
            prev + st.session_state.current_opp_runs
        )
        st.session_state.current_opp_runs = 0

    total_ltp = sum(st.session_state.ltp_scores.values())
    total_opp = sum(st.session_state.opp_scores.values())

    if total_ltp > total_opp:
        result = "W"
    elif total_ltp < total_opp:
        result = "L"
    else:
        result = "T"

    game_record = {
        "date": st.session_state.game_date,
        "opponent": st.session_state.opponent,
        "ltp_runs": total_ltp,
        "opp_runs": total_opp,
        "result": result,
        "ltp_role": st.session_state.ltp_role,
    }

    if SEASON_HISTORY_PATH.exists():
        hist_df = pd.read_csv(SEASON_HISTORY_PATH)
    else:
        hist_df = pd.DataFrame(columns=game_record.keys())

    hist_df = pd.concat(
        [hist_df, pd.DataFrame([game_record])], ignore_index=True
    )
    hist_df.to_csv(SEASON_HISTORY_PATH, index=False)

    # ✅ Merge per-game stats into 2025 historical CSV (used by Odds Maker)
    merge_game_stats_into_2025()

    st.success(
        f"Game saved & stats uploaded: LTP {total_ltp} – {total_opp} "
        f"{st.session_state.opponent} ({result})"
    )

    # Reset game state (but do NOT touch existing historical CSVs)
    init_game_state()
    st.session_state.game_active = False
    st.stop()
