import bcrypt
import streamlit as st
from db import get_conn

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def login_form():
    st.subheader("Team Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and verify_password(password, user["password_hash"]):
            st.session_state["user"] = {
                "user_id": user["user_id"],
                "name": user["name"],
                "username": user["username"],
                "team_id": user["team_id"],
                "role": user["role"],
            }
            st.success(f"Welcome, {user['name']}!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def require_login():
    if "user" not in st.session_state:
        login_form()
        st.stop()

def logout_button():
    if st.button("Logout"):
        st.session_state.pop("user", None)
        st.rerun()
