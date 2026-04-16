import streamlit as st
import auth
auth.require_login()


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
        "<h4 style='color:#888;margin-top:0;'>Beer league softball lineup, gameday, and season stats dashboard</h4>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        The LTP Softball app tracks lineup management, gameday box scores, and season stats.

        Use the sidebar in this order:
        """
    )

    st.markdown(
        """
        - **Add / Remove Players** – captain edits/adds/removes lineup players.
        - **Gameday** – record live box score and plate appearances.
        - **Season History** – stores each completed game and box score.
        - **LTP Stats** – shows season-to-date basic baseball stats.
        """
    )

with col_side:
    # Main hero image
    st.image("softball_3.jpeg", caption="Team photo", use_container_width=True)

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
        st.markdown("### Basic Stats")
        st.write(
            "Season-to-date baseball stats generated from completed games and box scores."
        )
        st.caption("Sidebar page: *odds maker* (Basic Stats)")

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