import streamlit as st
import pandas as pd
from pathlib import Path
import auth
auth.require_login()


# Historical stats files
CSV_SP24 = Path("ltp_SP24 Updated(in)(in).csv")   # 2024 / Spring
CSV_2025 = Path("ltp_2025 1(in).csv")            # 2025
ROSTER_PATH = Path("players.csv")


def load_roster() -> pd.DataFrame:
    """Load roster from players.csv and add Name / display_name columns."""
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

    df["Name"] = (df["first_name"] + " " + df["last_name"]).str.strip()
    df["display_name"] = (
        df["first_name"]
        + " "
        + df["last_name"]
        + " (#"
        + df["jersey_number"].astype(str)
        + ")"
    )
    return df


def load_stats_all_years() -> pd.DataFrame:
    """Load stats from both seasons and concatenate."""
    dfs = []
    for path in [CSV_SP24, CSV_2025]:
        if path.exists():
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="latin1")

            df.columns = [c.strip() for c in df.columns]
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["Name", "PA", "1B", "2B", "3B", "HR", "BB", "K"])

    combined = pd.concat(dfs, ignore_index=True)

    # Drop possible "Totals" rows
    if "Name" in combined.columns:
        combined = combined[
            combined["Name"].astype(str).str.lower() != "totals"
        ]

    return combined


def summarize_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate across years by player name, summing counts,
    computing total PA etc.
    """
    expected = ["Name", "PA", "1B", "2B", "3B", "HR", "BB", "K"]
    for col in expected:
        if col not in df.columns:
            df[col] = 0

    num_cols = ["PA", "1B", "2B", "3B", "HR", "BB", "K"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    agg = df.groupby("Name", as_index=False).agg(
        {
            "PA": "sum",
            "1B": "sum",
            "2B": "sum",
            "3B": "sum",
            "HR": "sum",
            "BB": "sum",
            "K": "sum",
        }
    )
    return agg


def compute_odds_and_betting(row: pd.Series) -> pd.DataFrame:
    """Return outcome -> probability + American odds for a single hitter row."""

    pa = int(row["PA"])
    if pa <= 0:
        return pd.DataFrame(
            columns=["Outcome", "Count", "Probability", "AmericanOdds"]
        )

    singles = int(row["1B"])
    doubles = int(row["2B"])
    triples = int(row["3B"])
    homers = int(row["HR"])
    walks = int(row["BB"])
    strikeouts = int(row["K"])
    batted_outs = pa - (
        singles + doubles + triples + homers + walks + strikeouts
    )
    if batted_outs < 0:
        batted_outs = 0

    events = {
        "Single": singles,
        "Double": doubles,
        "Triple": triples,
        "Home Run": homers,
        "Walk": walks,
        "Strikeout": strikeouts,
        "Ball-in-Play Out": batted_outs,
    }

    data = []
    for outcome, count in events.items():
        prob = count / pa if pa else 0.0

        # American odds only
        if prob > 0:
            if prob >= 0.5:
                # Favorite (negative odds)
                american_odds = round(-100 * (prob / (1 - prob)))
            else:
                # Underdog (positive odds)
                american_odds = round(((1 - prob) / prob) * 100)
        else:
            american_odds = None

        data.append(
            {
                "Outcome": outcome,
                "Count": int(count),
                "Probability": round(prob * 100, 1),  # percent
                "AmericanOdds": american_odds,
            }
        )

    odds_df = (
        pd.DataFrame(data)
        .sort_values("Probability", ascending=False)
        .reset_index(drop=True)
    )
    return odds_df


# ---------------------- STREAMLIT PAGE ----------------------
st.set_page_config(
    page_title="LTP Betting Odds Maker",
    page_icon="🎲",
    layout="wide",
)



col_title, col_img = st.columns([3, 1])

with col_title:
    st.markdown(
        "<h1 style='margin-bottom:0;'>Player Stats & Odds</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#666;margin-top:4px;'>Outcome probabilities, betting lines, and advanced analytics</p>",
        unsafe_allow_html=True,
    )

with col_img:
    st.image(
        "softball_3.jpeg",   # or "Moneyball.png" / whatever image you want
        caption="Jonah Hill says take your base",
        width=220,
    )

roster = load_roster()
if roster.empty:
    st.error("Roster is empty. Go to 'Add / Remove Players' to add hitters first.")
    st.stop()

all_stats = load_stats_all_years()
if all_stats.empty:
    summary_df = pd.DataFrame(
        columns=["Name", "PA", "1B", "2B", "3B", "HR", "BB", "K"]
    )
else:
    summary_df = summarize_player_stats(all_stats)

# Join roster with stats so every page uses the same player pool
if summary_df.empty:
    merged = roster.copy()
    for col in ["PA", "1B", "2B", "3B", "HR", "BB", "K"]:
        merged[col] = 0
else:
    merged = roster.merge(summary_df, on="Name", how="left")
    for col in ["PA", "1B", "2B", "3B", "HR", "BB", "K"]:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = merged[col].fillna(0).astype(int)

selected_batter = st.selectbox(
    "Select Batter", options=merged["display_name"].tolist()
)

player_row = merged[merged["display_name"] == selected_batter].iloc[0]
odds_df = compute_odds_and_betting(player_row)

st.subheader(f"{player_row['Name']} : Stat Line")
st.metric("Plate Appearances", int(player_row["PA"]))
st.write(
    f"- Singles: {int(player_row['1B'])}  \n"
    f"- Doubles: {int(player_row['2B'])}  \n"
    f"- Triples: {int(player_row['3B'])}  \n"
    f"- Home Runs: {int(player_row['HR'])}  \n"
    f"- Walks: {int(player_row['BB'])}  \n"
    f"- Strikeouts: {int(player_row['K'])}"
)

st.subheader("Outcome Betting Odds")
display = odds_df[["Outcome", "Probability", "AmericanOdds"]].copy()
display["Probability"] = display["Probability"].astype(str) + "%"
st.dataframe(display, use_container_width=True, hide_index=True)

st.subheader("Outcome Probability Chart")
chart_df = odds_df.set_index("Outcome")[["Probability"]]
st.bar_chart(chart_df["Probability"], use_container_width=True)

st.caption(
    "American odds and probabilities are derived from combined historical data in "
    "`ltp_SP24 Updated(in)(in).csv` and `ltp_2025 1(in).csv`."
)

