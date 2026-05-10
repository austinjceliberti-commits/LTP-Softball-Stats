from __future__ import annotations

import csv
import re
import uuid
from pathlib import Path
from typing import Iterable

import pandas as pd

ROSTER_PATH = Path("players.csv")
GAME_LOG_PATH = Path("gameday_log.csv")
SEASON_HISTORY_PATH = Path("season_history.csv")
PLAYER_STATS_PATH = Path("player_stats.csv")

LOG_COLUMNS = [
    "event_id",
    "game_id",
    "timestamp",
    "game_date",
    "opponent",
    "inning",
    "half",
    "first_name",
    "last_name",
    "jersey_number",
    "player_name",
    "outcome",
    "batter_destination",
    "runs_scored_players",
    "runs",
    "rbis",
    "outs_on_play",
]

SEASON_COLUMNS = [
    "game_id",
    "date",
    "opponent",
    "ltp_runs",
    "opp_runs",
    "result",
    "ltp_role",
]

EXPORT_COLUMNS = [
    "Player",
    "First Name",
    "Last Name",
    "Jersey",
    "G",
    "PA",
    "AB",
    "R",
    "H",
    "1B",
    "2B",
    "3B",
    "HR",
    "RBI",
    "BB",
    "K",
    "AVG",
    "OBP",
    "SLG",
    "OPS",
]

HIT_OUTCOMES = {"Single", "Double", "Triple", "Home Run"}
WALK_EVENTS = {"Walk"}
STRIKEOUT_EVENTS = {"Strikeout", "Strikeout Looking"}
AB_OUTCOMES = HIT_OUTCOMES | {
    "Out",
    "Strikeout",
    "Strikeout Looking",
    "Double Play",
    "Triple Play",
    "Fielder's Choice",
    "Error",
}


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_player_name(value) -> str:
    """Turns 'First Last (#7)' into 'First Last'."""
    name = clean_text(value)
    name = re.sub(r"\s*\(#.*?\)\s*$", "", name).strip()
    return re.sub(r"\s+", " ", name)


def make_player_name(first: str, last: str) -> str:
    return f"{clean_text(first)} {clean_text(last)}".strip()


def make_game_id(game_date: str, opponent: str) -> str:
    opp_slug = re.sub(r"[^a-z0-9]+", "-", clean_text(opponent).lower()).strip("-")
    if not opp_slug:
        opp_slug = "opponent"
    return f"{clean_text(game_date)}-{opp_slug}-{uuid.uuid4().hex[:8]}"


def make_event_id() -> str:
    return uuid.uuid4().hex


def ensure_csv_schema(path: Path, required_columns: list[str]) -> list[str]:
    """
    Make sure a CSV exists with at least required_columns.
    Keeps any extra legacy columns at the end.
    Returns the actual header order to use when appending rows.
    """
    if not path.exists() or path.stat().st_size == 0:
        pd.DataFrame(columns=required_columns).to_csv(path, index=False)
        return required_columns.copy()

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        pd.DataFrame(columns=required_columns).to_csv(path, index=False)
        return required_columns.copy()

    original_cols = list(df.columns)
    changed = False
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""
            changed = True

    # Required columns first, then any old columns the app does not currently use.
    final_cols = required_columns + [c for c in original_cols if c not in required_columns]
    if final_cols != original_cols:
        changed = True

    if changed:
        df = df[final_cols]
        df.to_csv(path, index=False)

    return final_cols


def load_roster(path: Path = ROSTER_PATH) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame(columns=["first_name", "last_name", "jersey_number", "email"])

    for col in ["first_name", "last_name", "jersey_number", "email"]:
        if col not in df.columns:
            df[col] = ""

    df["first_name"] = df["first_name"].apply(clean_text)
    df["last_name"] = df["last_name"].apply(clean_text)
    df["jersey_number"] = pd.to_numeric(df["jersey_number"], errors="coerce").fillna(0).astype(int)
    df["email"] = df["email"].apply(clean_text)
    df["display_name"] = (
        df["first_name"]
        + " "
        + df["last_name"]
        + " (#"
        + df["jersey_number"].astype(str)
        + ")"
    )
    return df


def load_game_log(path: Path = GAME_LOG_PATH) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=LOG_COLUMNS)

    ensure_csv_schema(path, LOG_COLUMNS)
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=LOG_COLUMNS)

    for col in LOG_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Normalize important fields.
    df["game_id"] = df["game_id"].apply(clean_text)
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["game_date"] = df["game_date"].fillna("")
    df["opponent"] = df["opponent"].apply(clean_text)
    df["first_name"] = df["first_name"].apply(clean_text)
    df["last_name"] = df["last_name"].apply(clean_text)
    df["player_name"] = df.apply(
        lambda r: clean_player_name(r.get("player_name"))
        or make_player_name(r.get("first_name"), r.get("last_name")),
        axis=1,
    )
    df["outcome"] = df["outcome"].apply(clean_text)
    df["jersey_number"] = pd.to_numeric(df["jersey_number"], errors="coerce").fillna(0).astype(int)
    df["rbis"] = pd.to_numeric(df["rbis"], errors="coerce").fillna(0).astype(int)
    df["runs"] = pd.to_numeric(df["runs"], errors="coerce").fillna(0).astype(int)
    df["outs_on_play"] = pd.to_numeric(df["outs_on_play"], errors="coerce").fillna(0).astype(int)
    return df


def append_game_event(event: dict, path: Path = GAME_LOG_PATH) -> None:
    headers = ensure_csv_schema(path, LOG_COLUMNS)
    row = {col: event.get(col, "") for col in headers}

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow(row)


def remove_last_event_for_game(game_id: str, path: Path = GAME_LOG_PATH) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return

    df = load_game_log(path)
    if df.empty:
        return

    game_id = clean_text(game_id)
    if game_id:
        matches = df.index[df["game_id"] == game_id].tolist()
    else:
        matches = []

    drop_idx = matches[-1] if matches else df.index[-1]
    df = df.drop(index=drop_idx).reset_index(drop=True)
    df.to_csv(path, index=False)


def load_season_history(path: Path = SEASON_HISTORY_PATH) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=SEASON_COLUMNS)

    ensure_csv_schema(path, SEASON_COLUMNS)
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=SEASON_COLUMNS)

    for col in SEASON_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["game_id"] = df["game_id"].apply(clean_text)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["date"] = df["date"].fillna("")
    df["opponent"] = df["opponent"].apply(clean_text)
    for col in ["ltp_runs", "opp_runs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["result"] = df["result"].apply(clean_text)
    df["ltp_role"] = df["ltp_role"].apply(clean_text)
    return df


def save_game_record(record: dict, path: Path = SEASON_HISTORY_PATH) -> None:
    ensure_csv_schema(path, SEASON_COLUMNS)
    df = load_season_history(path)

    row = {col: record.get(col, "") for col in SEASON_COLUMNS}
    row["date"] = pd.to_datetime(row["date"], errors="coerce").strftime("%Y-%m-%d")
    row["opponent"] = clean_text(row["opponent"])
    row["ltp_runs"] = int(row.get("ltp_runs") or 0)
    row["opp_runs"] = int(row.get("opp_runs") or 0)

    game_id = clean_text(row.get("game_id"))
    if game_id and not df.empty and (df["game_id"] == game_id).any():
        idx = df.index[df["game_id"] == game_id][0]
        for col, val in row.items():
            df.at[idx, col] = val
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    df.to_csv(path, index=False)


def update_game_record_and_log(
    selected_index: int,
    new_date: str,
    new_opponent: str,
    new_ltp_runs: int,
    new_opp_runs: int,
    history_path: Path = SEASON_HISTORY_PATH,
    log_path: Path = GAME_LOG_PATH,
) -> None:
    hist = load_season_history(history_path)
    if hist.empty or selected_index not in hist.index:
        return

    old_row = hist.loc[selected_index].copy()
    game_id = clean_text(old_row.get("game_id"))
    old_date = clean_text(old_row.get("date"))
    old_opp = clean_text(old_row.get("opponent"))

    result = "W" if new_ltp_runs > new_opp_runs else "L" if new_ltp_runs < new_opp_runs else "T"
    hist.at[selected_index, "date"] = clean_text(new_date)
    hist.at[selected_index, "opponent"] = clean_text(new_opponent)
    hist.at[selected_index, "ltp_runs"] = int(new_ltp_runs)
    hist.at[selected_index, "opp_runs"] = int(new_opp_runs)
    hist.at[selected_index, "result"] = result
    hist.to_csv(history_path, index=False)

    if log_path.exists() and log_path.stat().st_size > 0:
        log = load_game_log(log_path)
        if game_id:
            mask = log["game_id"] == game_id
        else:
            mask = (log["game_date"] == old_date) & (log["opponent"] == old_opp)
        if mask.any():
            log.loc[mask, "game_date"] = clean_text(new_date)
            log.loc[mask, "opponent"] = clean_text(new_opponent)
            log.to_csv(log_path, index=False)


def delete_game_and_events(
    selected_index: int,
    history_path: Path = SEASON_HISTORY_PATH,
    log_path: Path = GAME_LOG_PATH,
) -> None:
    hist = load_season_history(history_path)
    if hist.empty or selected_index not in hist.index:
        return

    row = hist.loc[selected_index]
    game_id = clean_text(row.get("game_id"))
    game_date = clean_text(row.get("date"))
    opponent = clean_text(row.get("opponent"))

    hist = hist.drop(index=selected_index).reset_index(drop=True)
    hist.to_csv(history_path, index=False)

    if log_path.exists() and log_path.stat().st_size > 0:
        log = load_game_log(log_path)
        if game_id:
            mask = log["game_id"] == game_id
        else:
            mask = (log["game_date"] == game_date) & (log["opponent"] == opponent)
        log = log[~mask].reset_index(drop=True)
        log.to_csv(log_path, index=False)


def completed_game_log(
    history_path: Path = SEASON_HISTORY_PATH,
    log_path: Path = GAME_LOG_PATH,
) -> pd.DataFrame:
    """Plate appearances that belong to games saved in season_history.csv."""
    log = load_game_log(log_path)
    hist = load_season_history(history_path)

    if log.empty or hist.empty:
        return pd.DataFrame(columns=LOG_COLUMNS)

    completed_parts = []

    valid_ids = set(hist["game_id"].dropna().astype(str).str.strip()) - {""}
    if valid_ids:
        with_ids = log[log["game_id"].astype(str).str.strip().isin(valid_ids)]
        if not with_ids.empty:
            completed_parts.append(with_ids)

    # Legacy support for old rows that do not have a game_id.
    legacy_log = log[~log["game_id"].astype(str).str.strip().isin(valid_ids)]
    if not legacy_log.empty and {"date", "opponent"}.issubset(hist.columns):
        valid_games = hist[["date", "opponent"]].dropna().drop_duplicates().copy()
        valid_games["date"] = valid_games["date"].apply(clean_text)
        valid_games["opponent"] = valid_games["opponent"].apply(clean_text)
        legacy = legacy_log.merge(
            valid_games,
            left_on=["game_date", "opponent"],
            right_on=["date", "opponent"],
            how="inner",
        )
        if not legacy.empty:
            # Drop merge-only column if present.
            legacy = legacy[[c for c in legacy.columns if c != "date"]]
            completed_parts.append(legacy)

    if not completed_parts:
        return pd.DataFrame(columns=LOG_COLUMNS)

    out = pd.concat(completed_parts, ignore_index=True)
    # Avoid double-counting if a row matched both ways.
    if "event_id" in out.columns and out["event_id"].astype(str).str.strip().any():
        out = out.drop_duplicates(subset=["event_id"], keep="last")
    else:
        out = out.drop_duplicates(keep="last")
    return out.reset_index(drop=True)


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame(columns=EXPORT_COLUMNS)


def build_player_stats(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return _empty_stats()

    df = events.copy()
    for col in LOG_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["first_name"] = df["first_name"].apply(clean_text)
    df["last_name"] = df["last_name"].apply(clean_text)
    df["player_name"] = df.apply(
        lambda r: clean_player_name(r.get("player_name"))
        or make_player_name(r.get("first_name"), r.get("last_name")),
        axis=1,
    )
    df["outcome"] = df["outcome"].apply(clean_text)
    df["jersey_number"] = pd.to_numeric(df["jersey_number"], errors="coerce").fillna(0).astype(int)
    df["rbis"] = pd.to_numeric(df["rbis"], errors="coerce").fillna(0).astype(int)
    df["game_key"] = df.apply(
        lambda r: clean_text(r.get("game_id"))
        or f"{clean_text(r.get('game_date'))}|{clean_text(r.get('opponent'))}",
        axis=1,
    )

    run_counts: dict[str, int] = {}
    if "runs_scored_players" in df.columns:
        for value in df["runs_scored_players"].fillna(""):
            for raw_name in str(value).split("|"):
                name = clean_player_name(raw_name)
                if name:
                    run_counts[name] = run_counts.get(name, 0) + 1

    rows = []
    group_cols = ["first_name", "last_name", "jersey_number"]
    for (first, last, jersey), group in df.groupby(group_cols, dropna=False):
        player_name = make_player_name(first, last)
        outcomes = group["outcome"]

        singles = int((outcomes == "Single").sum())
        doubles = int((outcomes == "Double").sum())
        triples = int((outcomes == "Triple").sum())
        homers = int((outcomes == "Home Run").sum())
        hits = singles + doubles + triples + homers
        walks = int(outcomes.isin(WALK_EVENTS).sum())
        strikeouts = int(outcomes.isin(STRIKEOUT_EVENTS).sum())
        pa = int(len(group))
        ab = int(outcomes.isin(AB_OUTCOMES).sum())
        games = int(group["game_key"].dropna().nunique())
        rbi = int(group["rbis"].sum())
        runs = int(run_counts.get(player_name, 0))

        total_bases = singles + (2 * doubles) + (3 * triples) + (4 * homers)
        avg = hits / ab if ab > 0 else 0.0
        obp = (hits + walks) / pa if pa > 0 else 0.0
        slg = total_bases / ab if ab > 0 else 0.0
        ops = obp + slg

        rows.append(
            {
                "Player": player_name,
                "First Name": first,
                "Last Name": last,
                "Jersey": int(jersey),
                "G": games,
                "PA": pa,
                "AB": ab,
                "R": runs,
                "H": hits,
                "1B": singles,
                "2B": doubles,
                "3B": triples,
                "HR": homers,
                "RBI": rbi,
                "BB": walks,
                "K": strikeouts,
                "AVG": round(avg, 3),
                "OBP": round(obp, 3),
                "SLG": round(slg, 3),
                "OPS": round(ops, 3),
            }
        )

    if not rows:
        return _empty_stats()

    return (
        pd.DataFrame(rows)[EXPORT_COLUMNS]
        .sort_values(by=["OPS", "AVG", "H"], ascending=False)
        .reset_index(drop=True)
    )


def rebuild_player_stats_export(
    history_path: Path = SEASON_HISTORY_PATH,
    log_path: Path = GAME_LOG_PATH,
    export_path: Path = PLAYER_STATS_PATH,
) -> pd.DataFrame:
    stats = build_player_stats(completed_game_log(history_path, log_path))
    stats.to_csv(export_path, index=False)
    return stats


def box_score_for_game(game_row: pd.Series, log_path: Path = GAME_LOG_PATH) -> pd.DataFrame:
    log = load_game_log(log_path)
    if log.empty:
        return _empty_stats()

    game_id = clean_text(game_row.get("game_id"))
    game_date = clean_text(game_row.get("date"))
    opponent = clean_text(game_row.get("opponent"))

    if game_id:
        events = log[log["game_id"] == game_id]
    else:
        events = log[(log["game_date"] == game_date) & (log["opponent"] == opponent)]

    return build_player_stats(events)
