from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import auth
from stats_utils import (
    append_game_event,
    clean_player_name,
    make_event_id,
    make_game_id,
    rebuild_player_stats_export,
    remove_last_event_for_game,
    save_game_record,
    load_roster,
)

# ---------- Streamlit setup ----------
st.set_page_config(page_title="Gameday", page_icon="📊", layout="wide")
auth.require_login()


# ---------- Base helpers ----------
def empty_bases() -> dict:
    return {"1B": None, "2B": None, "3B": None}


def render_basepaths(bases: dict) -> None:
    """Visual diamond showing where runners are."""

    def box(label, runner):
        occupied = runner is not None
        text = runner if occupied else label
        bg = "#2e7d32" if occupied else "#424242"
        return f"""
        <div style="
            border: 2px solid white;
            border-radius: 6px;
            padding: 6px;
            text-align:center;
            font-size:0.9rem;
            background:{bg};
            min-height:42px;
        ">{text}</div>
        """

    col_top = st.columns(3)
    col_mid = st.columns(3)
    col_bot = st.columns(3)

    col_top[1].markdown(box("2B", bases.get("2B")), unsafe_allow_html=True)
    col_mid[0].markdown(box("3B", bases.get("3B")), unsafe_allow_html=True)
    col_mid[2].markdown(box("1B", bases.get("1B")), unsafe_allow_html=True)
    col_bot[1].markdown(
        '<div style="text-align:center; margin-top:4px;">Home</div>',
        unsafe_allow_html=True,
    )


def offense_for_half(half: str, ltp_role: str) -> str:
    """Returns who bats in the current half inning."""
    if half == "Top":
        return "LTP" if ltp_role == "Away" else "Opponent"
    return "Opponent" if ltp_role == "Away" else "LTP"


def advance_half_inning() -> None:
    """Move from top to bottom, or bottom to next top, and set the correct offense."""
    if st.session_state.half == "Top":
        st.session_state.half = "Bottom"
    else:
        st.session_state.inning += 1
        st.session_state.half = "Top"

    st.session_state.offense = offense_for_half(
        st.session_state.half, st.session_state.ltp_role
    )
    st.session_state.outs = 0
    st.session_state.bases = empty_bases()


# ---------- Initialize session_state for game flow ----------
def init_game_state() -> None:
    st.session_state.game_active = False
    st.session_state.game_id = ""
    st.session_state.game_date = str(date.today())
    st.session_state.opponent = ""
    st.session_state.inning = 1
    st.session_state.half = "Top"
    st.session_state.offense = "LTP"
    st.session_state.outs = 0
    st.session_state.ltp_role = "Away"

    st.session_state.ltp_scores = {}
    st.session_state.opp_scores = {}
    st.session_state.current_ltp_runs = 0
    st.session_state.current_opp_runs = 0

    st.session_state.bases = empty_bases()
    st.session_state.lineup = []
    st.session_state.batter_index = 0
    st.session_state.last_play = ""
    st.session_state.undo_stack = []


if "game_active" not in st.session_state:
    init_game_state()


def push_snapshot(remove_event_on_undo: bool = False) -> None:
    """Save current game state so we can undo the last action."""
    snap = {
        "game_id": st.session_state.game_id,
        "game_date": st.session_state.game_date,
        "opponent": st.session_state.opponent,
        "inning": st.session_state.inning,
        "half": st.session_state.half,
        "offense": st.session_state.offense,
        "outs": st.session_state.outs,
        "ltp_role": st.session_state.ltp_role,
        "ltp_scores": st.session_state.ltp_scores.copy(),
        "opp_scores": st.session_state.opp_scores.copy(),
        "current_ltp_runs": st.session_state.current_ltp_runs,
        "current_opp_runs": st.session_state.current_opp_runs,
        "bases": st.session_state.bases.copy(),
        "lineup": st.session_state.lineup.copy(),
        "batter_index": st.session_state.batter_index,
        "last_play": st.session_state.last_play,
        "remove_event_on_undo": remove_event_on_undo,
    }
    st.session_state.undo_stack.append(snap)


def apply_snapshot(snap: dict) -> None:
    for key in [
        "game_id",
        "game_date",
        "opponent",
        "inning",
        "half",
        "offense",
        "outs",
        "ltp_role",
        "ltp_scores",
        "opp_scores",
        "current_ltp_runs",
        "current_opp_runs",
        "bases",
        "lineup",
        "batter_index",
        "last_play",
    ]:
        st.session_state[key] = snap[key]


# ---------- Hero header ----------
col_title, col_img = st.columns([3, 1])
with col_title:
    st.markdown(
        "<h1 style='margin-bottom:0px;'>Gameday: Plate Appearance Entry</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#666;margin-top:4px;'>Live scorebook, basepaths, and inning tracker</p>",
        unsafe_allow_html=True,
    )
with col_img:
    if Path("Gameday.png").exists():
        st.image("Gameday.png", caption="", width=220)

st.caption(
    "Stats are stored in gameday_log.csv by plate appearance. "
    "Season totals are rebuilt from the log after the game is saved."
)


# ---------- Start new game + lineup UI ----------
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
        index=0 if st.session_state.get("ltp_role", "Away") == "Home" else 1,
    )

    st.markdown("### Set Lineup (Batting Order)")
    max_spots = min(15, len(roster))
    num_spots = st.number_input(
        "Number of spots in batting order",
        min_value=1,
        max_value=max_spots,
        step=1,
        value=min(max_spots, 10),
        key="num_spots",
    )

    lineup_options = ["-- Select player --"] + roster["display_name"].tolist()
    for i in range(num_spots):
        st.selectbox(f"Spot {i + 1}", options=lineup_options, key=f"lineup_{i}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Start New Game"):
            selected = [st.session_state.get(f"lineup_{i}") for i in range(num_spots)]
            errors = []
            if not opponent.strip():
                errors.append("Enter an opponent name before starting the game.")
            if any((not val) or val == "-- Select player --" for val in selected):
                errors.append("Every lineup spot must have a player selected.")
            if len(set(selected)) != len(selected):
                errors.append("The same player cannot appear in the lineup twice.")

            if errors:
                for err in errors:
                    st.error(err)
                st.stop()

            init_game_state()
            st.session_state.game_active = True
            st.session_state.game_date = str(game_date)
            st.session_state.opponent = opponent.strip()
            st.session_state.game_id = make_game_id(str(game_date), opponent.strip())
            st.session_state.ltp_role = ltp_role
            st.session_state.lineup = selected
            st.session_state.batter_index = 0
            st.session_state.undo_stack = []
            st.session_state.inning = 1
            st.session_state.half = "Top"
            st.session_state.offense = offense_for_half("Top", ltp_role)

            st.success(
                f"Game started vs {st.session_state.opponent} on {st.session_state.game_date}. "
                f"LTP is the {ltp_role} team. Lineup set with {len(selected)} hitters."
            )
            st.rerun()

    with col_b:
        if st.button("Reset Current Game (Discard Unsaved Progress)"):
            init_game_state()
            st.warning("Current game state cleared. Saved CSV stats were not touched.")
            st.rerun()

if not st.session_state.game_active:
    st.stop()

if not st.session_state.lineup:
    st.session_state.lineup = roster["display_name"].tolist()
    st.session_state.batter_index = 0


# ---------- Scoreboard ----------
st.markdown("---")
st.subheader("Scoreboard")

ltp_scores = st.session_state.ltp_scores
opp_scores = st.session_state.opp_scores
max_inning = max(
    6,
    st.session_state.inning,
    *(ltp_scores.keys() or [1]),
    *(opp_scores.keys() or [1]),
)
innings = list(range(1, max_inning + 1))

ltp_row = []
opp_row = []
for inn in innings:
    ltp_val = ltp_scores.get(inn, 0)
    opp_val = opp_scores.get(inn, 0)
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


# ---------- Undo button ----------
if st.session_state.undo_stack:
    if st.button("↩️ Undo Last Action"):
        snap = st.session_state.undo_stack.pop()
        if snap.get("remove_event_on_undo"):
            remove_last_event_for_game(st.session_state.game_id)
            rebuild_player_stats_export()
        apply_snapshot(snap)
        st.info("Last action undone.")
        st.rerun()


# ---------- Current half-inning status ----------
st.markdown("---")
half_label = f"{st.session_state.half} {st.session_state.inning}"
offense_label = (
    "LTP batting"
    if st.session_state.offense == "LTP"
    else f"{st.session_state.opponent} batting"
)
st.subheader(f"Inning {st.session_state.inning} — {half_label} ({offense_label})")
st.write(f"**Outs:** {st.session_state.outs} / 3")

if st.session_state.offense == "LTP":
    st.markdown("#### Base Runners")
    render_basepaths(st.session_state.bases)

if st.session_state.last_play:
    st.caption(f"Last play: {st.session_state.last_play}")


# ---------- LTP batting flow ----------
if st.session_state.offense == "LTP":
    st.markdown("### Current Batter")

    lineup = st.session_state.lineup
    idx = st.session_state.batter_index % len(lineup)
    current_batter_name = lineup[idx]
    st.write(f"**Batter up:** {current_batter_name}")

    batter_row = roster[roster["display_name"] == current_batter_name]
    if batter_row.empty:
        st.error("Current batter not found in roster. Check lineup setup.")
        st.stop()
    batter_info = batter_row.iloc[0]

    OUTCOME_OPTIONS = [
        "-- Select result --",
        "Single",
        "Double",
        "Triple",
        "Home Run",
        "Walk",
        "Strikeout",
        "Strikeout Looking",
        "Out",
        "Double Play",
        "Triple Play",
        "Fielder's Choice",
        "Error",
    ]
    outcome = st.selectbox("Result (for stats)", OUTCOME_OPTIONS, key="outcome_select")

    st.markdown("### Runners & Scoring")
    bases_before = st.session_state.bases
    runner_moves = {}

    MOVE_OPTIONS_TEMPLATE = {
        "3B": ["-- Select movement --", "Stays at 3B", "Scores", "Out", "On 1B", "On 2B"],
        "2B": ["-- Select movement --", "Stays at 2B", "Scores", "Out", "On 1B", "On 3B"],
        "1B": ["-- Select movement --", "Stays at 1B", "Scores", "Out", "On 2B", "On 3B"],
    }

    for base in ["3B", "2B", "1B"]:
        runner = bases_before.get(base)
        if runner:
            choice = st.selectbox(
                f"Runner {runner} (was on {base}) ends up:",
                options=MOVE_OPTIONS_TEMPLATE[base],
                key=f"move_{base}",
            )
            runner_moves[(base, runner)] = choice

    BATTER_OPTIONS = ["-- Select batter outcome --", "Out", "Scores", "On 1B", "On 2B", "On 3B"]
    batter_dest = st.selectbox(
        f"Batter {current_batter_name} ends up:",
        options=BATTER_OPTIONS,
        key="batter_dest",
    )

    if st.button("Submit Plate Appearance"):
        errors = []
        if outcome == OUTCOME_OPTIONS[0]:
            errors.append("Select a result for the plate appearance.")
        for (_, runner), choice in runner_moves.items():
            if choice.startswith("--"):
                errors.append(f"Make a selection for runner {runner}.")
        if batter_dest == BATTER_OPTIONS[0]:
            errors.append("Select where the batter ends up.")

        # Prevent two players ending on the same base.
        requested_bases = []
        for choice in runner_moves.values():
            if choice.startswith("On "):
                requested_bases.append(choice.split(" ")[1])
        if batter_dest.startswith("On "):
            requested_bases.append(batter_dest.split(" ")[1])
        if len(requested_bases) != len(set(requested_bases)):
            errors.append("Two players cannot end on the same base. Adjust runner movement.")

        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        push_snapshot(remove_event_on_undo=True)

        first = str(batter_info["first_name"]).strip()
        last = str(batter_info["last_name"]).strip()
        jersey = int(batter_info["jersey_number"])
        display_name = current_batter_name

        new_bases = empty_bases()
        outs_added = 0
        scored_players = []

        for (start_base, runner), choice in runner_moves.items():
            if choice.startswith("Stays at"):
                new_bases[start_base] = runner
            elif choice == "Scores":
                scored_players.append(runner)
            elif choice == "Out":
                outs_added += 1
            elif choice.startswith("On "):
                dest_base = choice.split(" ")[1]
                new_bases[dest_base] = runner

        if batter_dest == "Out":
            outs_added += 1
        elif batter_dest == "Scores":
            scored_players.append(display_name)
        elif batter_dest.startswith("On "):
            dest_base = batter_dest.split(" ")[1]
            new_bases[dest_base] = display_name

        runs_scored = len(scored_players)
        st.session_state.outs = min(3, st.session_state.outs + outs_added)
        st.session_state.current_ltp_runs += runs_scored

        event = {
            "event_id": make_event_id(),
            "game_id": st.session_state.game_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "game_date": st.session_state.game_date,
            "opponent": st.session_state.opponent,
            "inning": st.session_state.inning,
            "half": st.session_state.half,
            "first_name": first,
            "last_name": last,
            "jersey_number": jersey,
            "player_name": clean_player_name(display_name),
            "outcome": outcome,
            "batter_destination": batter_dest,
            "runs_scored_players": "|".join(scored_players),
            "runs": runs_scored,
            "rbis": runs_scored,
            "outs_on_play": outs_added,
        }
        append_game_event(event)

        st.session_state.bases = new_bases
        st.session_state.last_play = (
            f"{outcome} by {display_name}, {runs_scored} run(s) scored, "
            f"{outs_added} out(s) on the play."
        )

        st.session_state.batter_index = (st.session_state.batter_index + 1) % len(
            st.session_state.lineup
        )

        if st.session_state.outs >= 3:
            prev = st.session_state.ltp_scores.get(st.session_state.inning, 0)
            st.session_state.ltp_scores[st.session_state.inning] = (
                prev + st.session_state.current_ltp_runs
            )
            st.session_state.current_ltp_runs = 0
            advance_half_inning()
            st.session_state.last_play += " (End of half-inning.)"

        for key in ["outcome_select", "batter_dest", "move_3B", "move_2B", "move_1B"]:
            if key in st.session_state:
                del st.session_state[key]

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
        "Outs recorded this half",
        min_value=0,
        max_value=3,
        step=1,
        value=3,
        key="opp_outs_input",
    )

    if st.button("Submit Opponent Half"):
        if int(outs_this_half) != 3:
            st.error("Opponent half-inning should be submitted once 3 outs are recorded.")
            st.stop()

        push_snapshot(remove_event_on_undo=False)

        st.session_state.current_opp_runs = int(runs_this_half)
        prev = st.session_state.opp_scores.get(st.session_state.inning, 0)
        st.session_state.opp_scores[st.session_state.inning] = (
            prev + st.session_state.current_opp_runs
        )
        st.session_state.current_opp_runs = 0
        st.session_state.last_play = (
            f"{st.session_state.opponent} scored {runs_this_half} run(s) in the half."
        )
        advance_half_inning()

        for key in ["opp_runs_input", "opp_outs_input"]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()


# ---------- End game + save to season history ----------
st.markdown("---")
st.subheader("End Game")
st.caption("This saves the game to season_history.csv and rebuilds player_stats.csv from gameday_log.csv.")

if st.button("End Game & Save Stats"):
    if st.session_state.offense == "LTP" and st.session_state.current_ltp_runs > 0:
        prev = st.session_state.ltp_scores.get(st.session_state.inning, 0)
        st.session_state.ltp_scores[st.session_state.inning] = prev + st.session_state.current_ltp_runs
        st.session_state.current_ltp_runs = 0
    elif st.session_state.offense == "Opponent" and st.session_state.current_opp_runs > 0:
        prev = st.session_state.opp_scores.get(st.session_state.inning, 0)
        st.session_state.opp_scores[st.session_state.inning] = prev + st.session_state.current_opp_runs
        st.session_state.current_opp_runs = 0

    total_ltp = int(sum(st.session_state.ltp_scores.values()))
    total_opp = int(sum(st.session_state.opp_scores.values()))
    result = "W" if total_ltp > total_opp else "L" if total_ltp < total_opp else "T"

    game_id = st.session_state.game_id or make_game_id(st.session_state.game_date, st.session_state.opponent)
    game_record = {
        "game_id": game_id,
        "date": st.session_state.game_date,
        "opponent": st.session_state.opponent,
        "ltp_runs": total_ltp,
        "opp_runs": total_opp,
        "result": result,
        "ltp_role": st.session_state.ltp_role,
    }

    save_game_record(game_record)
    rebuild_player_stats_export()

    st.success(
        f"Game saved: LTP {total_ltp} – {total_opp} {st.session_state.opponent} ({result}). "
        "Season stats were rebuilt from the plate appearance log."
    )

    init_game_state()
    st.stop()
