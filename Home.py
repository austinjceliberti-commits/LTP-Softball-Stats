import streamlit as st

# -------- Page config --------
st.set_page_config(
    page_title="LTP Home For 2025",
    page_icon="",
    layout="wide",
)

# -------- HERO SECTION --------
col_hero, col_side = st.columns([2, 1])

with col_hero:
    st.markdown(
        "<h1 style='margin-bottom:0;'>LTP Home</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='color:#888;margin-top:0;'>Beer league softball stats & odds dashboard</h4>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        The LTP Softball Stats dashboard and game log (Counting Bob's strikeouts).

        Use the sidebar to jump into each page:
        """
    )

    st.markdown(
        """
        - **Add / Remove Players** – manage the roster .
        - **Gameday** – log plate appearances live and update stats.
        - **Odds Maker** – view Player stats and odds.
        - **Season History** – see final scores, record, and per-game box scores.
        """
    )

with col_side:
    # Main hero image
    st.image("Beer_League.jpeg", caption="Connor at the dish", use_container_width=True)

st.markdown("---")

# -------- FEATURE CARDS + SECOND IMAGE --------
top_col, img_col = st.columns([2, 1])

with top_col:
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    with c1:
        st.markdown("### Add / Remove Players")
        st.write(
            "Manage the roster: add new players, remove players, and update jersey numbers & emails."
        )
        st.caption("Sidebar page: *edit players*")

    with c2:
        st.markdown("### Gameday")
        st.write(
            "Live scorebook: record every plate appearance, track base-runners, and update the scoreboard."
        )
        st.caption("Sidebar page: *gameday*")

    with c3:
        st.markdown("### Player Stats and Odds")
        st.write(
            "Track everyones stats live through the season, odds based of whatever stats I have from last year."
        )
        st.caption("Sidebar page: *odds maker*")

    with c4:
        st.markdown("### Season History")
        st.write(
            "View final scores, team record, run differential, and per-game hitting box scores."
        )
        st.caption("Sidebar page: *season history*")

with img_col:
    st.image("kellys.jpeg", caption="Postgame", use_container_width=True)

st.markdown("---")
st.caption("Tip: use the left sidebar to navigate between pages.")
