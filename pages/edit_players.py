import streamlit as st
import pandas as pd
from pathlib import Path
import auth
auth.require_login()


# Single source of truth for roster
DATA_PATH = Path("players.csv")


def load_players() -> pd.DataFrame:
    """Load players from CSV, or create an empty one if it doesn't exist."""
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
    else:
        df = pd.DataFrame(
            columns=["first_name", "last_name", "jersey_number", "email"]
        )

    # Ensure expected columns
    for col in ["first_name", "last_name", "jersey_number", "email"]:
        if col not in df.columns:
            df[col] = ""

    # Basic cleanup
    df["first_name"] = df["first_name"].astype(str).str.strip()
    df["last_name"] = df["last_name"].astype(str).str.strip()
    df["jersey_number"] = (
        pd.to_numeric(df["jersey_number"], errors="coerce").fillna(0).astype(int)
    )
    df["email"] = df["email"].astype(str).str.strip()

    return df


def save_players(df: pd.DataFrame) -> None:
    df.to_csv(DATA_PATH, index=False)


st.set_page_config(
    page_title="Manage Players",
    page_icon="",
    layout="wide",
)

st.title("Manage Roster")

players_df = load_players()

# ----------------- Current Roster -----------------
st.subheader("Current Roster")

if players_df.empty:
    st.info("No players in roster yet. Add a player below.")
else:
    display_df = players_df.copy()
    display_df = display_df[
        ["first_name", "last_name", "jersey_number", "email"]
    ].rename(
        columns={
            "first_name": "First Name",
            "last_name": "Last Name",
            "jersey_number": "Jersey #",
            "email": "Email",
        }
    )
    st.dataframe(display_df, use_container_width=True)

# Optional: Remove player
if not players_df.empty:
    st.markdown("### Remove a Player")

    players_df["display_name"] = (
        players_df["first_name"]
        + " "
        + players_df["last_name"]
        + " (#"
        + players_df["jersey_number"].astype(str)
        + ")"
    )

    to_remove = st.selectbox(
        "Select a player to remove",
        options=["-- None --"] + players_df["display_name"].tolist(),
    )

    if to_remove != "-- None --":
        if st.button("Remove Selected Player"):
            first, rest = to_remove.split(" ", 1)
            last = rest.split(" (#")[0]
            jersey = int(
                rest.split(" (#")[-1].rstrip(")")
            )  # extract jersey number

            mask = ~(
                (players_df["first_name"] == first)
                & (players_df["last_name"] == last)
                & (players_df["jersey_number"] == jersey)
            )
            updated = players_df[mask].drop(columns=["display_name"])
            save_players(updated)
            st.success(f"Removed {to_remove} from roster.")
            st.rerun()

st.markdown("---")

# ----------------- Edit Player -----------------
st.markdown("---")
st.subheader("Edit a Player")

if players_df.empty:
    st.info("No players to edit yet. Add someone to the roster first.")
else:
    # Build display name (do it again here in case we didn't above)
    players_df["display_name"] = (
        players_df["first_name"]
        + " "
        + players_df["last_name"]
        + " (#"
        + players_df["jersey_number"].astype(str)
        + ")"
    )

    player_to_edit = st.selectbox(
        "Select a player to edit",
        options=players_df["display_name"].tolist(),
        key="edit_select",
    )

    # Get the row + index for the selected player
    row = players_df.loc[players_df["display_name"] == player_to_edit].iloc[0]
    idx = row.name  # index in the DataFrame

    # Pre-filled inputs
    new_first = st.text_input("First name", value=row["first_name"], key="edit_first")
    new_last = st.text_input("Last name", value=row["last_name"], key="edit_last")
    new_jersey = st.number_input(
        "Jersey #",
        min_value=0,
        max_value=999,
        step=1,
        value=int(row["jersey_number"]),
        key="edit_jersey",
    )
    new_email = st.text_input("Email", value=str(row["email"]), key="edit_email")

    if st.button("Save changes", key="edit_save"):
        players_df.at[idx, "first_name"] = new_first.strip()
        players_df.at[idx, "last_name"] = new_last.strip()
        players_df.at[idx, "jersey_number"] = int(new_jersey)
        players_df.at[idx, "email"] = new_email.strip()

        # Drop helper col before saving
        to_save = players_df.drop(columns=["display_name"], errors="ignore")
        save_players(to_save)

        st.success(f"Updated {player_to_edit}.")
        st.rerun()


# ----------------- Add New Player -----------------
st.subheader("Add a New Player")

with st.form("add_player_form"):
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    jersey_number = st.number_input(
        "Jersey #", min_value=0, max_value=999, step=1, value=0
    )
    email = st.text_input("Email (optional)")

    submitted = st.form_submit_button("Add Player")

    if submitted:
        if not first_name or not last_name:
            st.error("First and last name are required.")
        else:
            new_player = {
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "jersey_number": int(jersey_number),
                "email": email.strip(),
            }

            updated_df = pd.concat(
                [players_df.drop(columns=["display_name"], errors="ignore"),
                 pd.DataFrame([new_player])],
                ignore_index=True,
            )
            save_players(updated_df)

            st.success(
                f"Added {first_name} {last_name} (#{int(jersey_number)}) to the roster."
            )
            st.rerun()

