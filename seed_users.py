import os
from db import init_db, get_conn
from auth import hash_password

def seed():
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    # Create team if not exists
    team_name = "Connor Team"
    cur.execute("INSERT OR IGNORE INTO teams(team_name) VALUES (?)", (team_name,))
    conn.commit()

    team = cur.execute("SELECT team_id FROM teams WHERE team_name = ?", (team_name,)).fetchone()
    team_id = team["team_id"]

    # Create user
    name = "Connor Moloughny"
    username = "connor"  # login username (simple)
    plain_pw = os.environ.get("CAPTAIN_PASSWORD")

    if not plain_pw:
        raise ValueError("Set CAPTAIN_PASSWORD environment variable before running seed_users.py")

    pw_hash = hash_password(plain_pw)

    cur.execute("""
    INSERT OR REPLACE INTO users(name, username, password_hash, team_id, role)
    VALUES (?, ?, ?, ?, 'captain')
    """, (name, username, pw_hash, team_id))

    conn.commit()
    conn.close()
    print("Seed complete: created/updated captain user.")

if __name__ == "__main__":
    seed()
