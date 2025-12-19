import streamlit as st
import pandas as pd
from pathlib import Path

SEASON_HISTORY_PATH = Path("season_history.csv")

st.set_page_config(
    page_title="LTP Season History",
    page_icon="",
    layout="wide",
)

st.title("LTP Season History")

if not SEASON_HISTORY_PATH.exists():
    st.info("No games recorded yet. Finish a game on the Gameday page to log it here.")
    st.stop()

df = pd.read_csv(SEASON_HISTORY_PATH)

# Basic cleaning / ordering
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date", ascending=False)

st.subheader("Game Log")
st.dataframe(df, use_container_width=True)

# Summary
st.markdown("---")
st.subheader("Season Summary")

wins = (df["result"] == "W").sum()
losses = (df["result"] == "L").sum()
ties = (df["result"] == "T").sum()

total_scored = df["ltp_runs"].sum()
total_allowed = df["opp_runs"].sum()
run_diff = total_scored - total_allowed

col1, col2, col3 = st.columns(3)
col1.metric("Record", f"{wins}-{losses}-{ties}")
col2.metric("Runs For", int(total_scored))
col3.metric("Runs Against", int(total_allowed))

st.write(f"**Run Differential:** {run_diff:+d}")
