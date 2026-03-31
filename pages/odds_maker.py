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

st.title(" Team LTP Stats")
st.caption("Filter player stats by season year")

LOG_PATH = Path("gameday_log.csv")

if not LOG_PATH.exists():
    st.error("gameday_log.csv was not found in the project folder.")
    st.stop()

@st.cache_data
def load_log():
    df = pd.read_csv(LOG_PATH)

    if df.empty:
        return df

    # Clean dates
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")
    df = df.dropna(subset=["game_date"]).copy()
    df["year"] = df["game_date"].dt.year

    # Clean text columns
    df["first_name"] = df["first_name"].fillna("").astype(str).str.strip()
    df["last_name"] = df["last_name"].fillna("").astype(str).str.strip()
    df["player_name"] = (df["first_name"] + " " + df["last_name"]).str.strip()

    df["outcome"] = df["outcome"].fillna("").astype(str).str.strip()
    df["rbis"] = pd.to_numeric(df["rbis"], errors="coerce").fillna(0).astype(int)

    return df

def build_stats(df):
    if df.empty:
        return pd.DataFrame()

    hit_map = {
        "Single": "1B",
        "Double": "2B",
        "Triple": "3B",
        "Home Run": "HR",
    }

    strikeout_events = {"Strikeout", "Strikeout Looking"}
    walk_events = {"Walk"}

    rows = []

    for player, group in df.groupby("player_name"):
        outcomes = group["outcome"]

        singles = (outcomes == "Single").sum()
        doubles = (outcomes == "Double").sum()
        triples = (outcomes == "Triple").sum() if "Triple" in outcomes.values else 0
        homers = (outcomes == "Home Run").sum()

        hits = singles + doubles + triples + homers
        walks = outcomes.isin(walk_events).sum()
        strikeouts = outcomes.isin(strikeout_events).sum()

        # Everything except walks counts as an AB here
        ab = len(group) - walks
        pa = len(group)

        avg = hits / ab if ab > 0 else 0
        obp = (hits + walks) / pa if pa > 0 else 0
        total_bases = singles + (2 * doubles) + (3 * triples) + (4 * homers)
        slg = total_bases / ab if ab > 0 else 0

        jersey = group["jersey_number"].dropna()
        jersey_number = int(jersey.iloc[0]) if not jersey.empty else ""

        rows.append(
            {
                "Player": player,
                "Jersey": jersey_number,
                "PA": pa,
                "AB": ab,
                "H": hits,
                "1B": singles,
                "2B": doubles,
                "3B": triples,
                "HR": homers,
                "BB": walks,
                "K": strikeouts,
                "RBI": int(group["rbis"].sum()),
                "AVG": round(avg, 3),
                "OBP": round(obp, 3),
                "SLG": round(slg, 3),
            }
        )

    stats_df = pd.DataFrame(rows).sort_values(
        by=["AVG", "OBP", "SLG", "H"],
        ascending=False
    ).reset_index(drop=True)

    return stats_df

log_df = load_log()

if log_df.empty:
    st.warning("No gameday data found yet.")
    st.stop()

years = sorted(log_df["year"].dropna().unique().tolist())
year_options = ["All Years"] + years

selected_year = st.selectbox("Select year", year_options)

filtered_df = log_df.copy()
if selected_year != "All Years":
    filtered_df = filtered_df[filtered_df["year"] == selected_year]

stats_df = build_stats(filtered_df)

top1, top2, top3, top4 = st.columns(4)

with top1:
    st.metric("Plate Appearances", len(filtered_df))

with top2:
    st.metric("Hits", int(stats_df["H"].sum()) if not stats_df.empty else 0)

with top3:
    st.metric("Home Runs", int(stats_df["HR"].sum()) if not stats_df.empty else 0)

with top4:
    st.metric("RBIs", int(stats_df["RBI"].sum()) if not stats_df.empty else 0)

st.markdown("---")

search = st.text_input("Search player name").strip().lower()

display_df = stats_df.copy()
if search:
    display_df = display_df[
        display_df["Player"].str.lower().str.contains(search, na=False)
    ]

st.subheader("Player Stats")

if display_df.empty:
    st.info("No players found for that filter.")
else:
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

st.subheader("Leaderboard")

lead1, lead2, lead3 = st.columns(3)

if not stats_df.empty:
    qualified = stats_df[stats_df["PA"] >= 1].copy()

    with lead1:
        st.markdown("### Batting Average")
        st.dataframe(
            qualified[["Player", "AVG"]]
            .sort_values("AVG", ascending=False)
            .head(5),
            use_container_width=True,
            hide_index=True,
        )

    with lead2:
        st.markdown("### Home Runs")
        st.dataframe(
            qualified[["Player", "HR"]]
            .sort_values("HR", ascending=False)
            .head(5),
            use_container_width=True,
            hide_index=True,
        )

    with lead3:
        st.markdown("### RBIs")
        st.dataframe(
            qualified[["Player", "RBI"]]
            .sort_values("RBI", ascending=False)
            .head(5),
            use_container_width=True,
            hide_index=True,
        )


