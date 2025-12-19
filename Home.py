import streamlit as st

st.set_page_config(
    page_title="LTP Home",
    page_icon="",
    layout="wide",
)

st.title("LTP Home")

st.write(
    "Welcome to the LTP Softball Stats dashboard (counting Robert's strikeouts). "
    "Use the bar on the side better, links dont work for shit:"
)

st.markdown(
    """
- **Add / Remove Players** – manage the roster stored in `players.csv`
- **Gameday** – log plate appearances live during games
- **Odds Maker** – view outcome probabilities and betting odds
"""
)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Add / Remove Players")
    st.write(
        "Manage roster: add new players, remove players, and update basic info.\n\n"
        "_Sidebar page: `Add / Remove Players`_"
    )

with col2:
    st.subheader("Gameday")
    st.write(
        "Use this during games to record plate appearances and update live stats.\n\n"
        "_Sidebar page: `Gameday`_"
    )

with col3:
    st.subheader("Odds Maker")
    st.write(
        "Generate outcome probabilities and American odds from combined 2024 and 2025 stats For whatever stats Matt put in.\n\n"
        "_Sidebar page: `Odds Maker`_"
    )
