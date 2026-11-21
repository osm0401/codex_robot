from contextlib import closing
from dataclasses import astuple
from pathlib import Path
from sqlite3 import connect

from app.baby.engine import State

SCHEMA = """
CREATE TABLE IF NOT EXISTS baby_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    started_at INTEGER NOT NULL CHECK (typeof(started_at) = 'integer' AND started_at >= 0),
    age_months INTEGER NOT NULL CHECK (typeof(age_months) = 'integer' AND age_months BETWEEN 0 AND 12),
    care_points INTEGER NOT NULL CHECK (typeof(care_points) = 'integer' AND care_points >= 0),
    hunger REAL NOT NULL CHECK (hunger BETWEEN 0 AND 1),
    sleepiness REAL NOT NULL CHECK (sleepiness BETWEEN 0 AND 1),
    diaper REAL NOT NULL CHECK (diaper BETWEEN 0 AND 1),
    gas REAL NOT NULL CHECK (gas BETWEEN 0 AND 1),
    attachment REAL NOT NULL CHECK (attachment BETWEEN 0 AND 1),
    stimulation REAL NOT NULL CHECK (stimulation BETWEEN -1 AND 1),
    mood REAL NOT NULL CHECK (mood BETWEEN -1 AND 1),
    arousal REAL NOT NULL CHECK (arousal BETWEEN 0 AND 1)
)
"""


class BabyStore:
    def __init__(self, database: Path) -> None:
        self.database = database

    def load(self, *, now: int) -> State:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(connect(self.database)) as db, db:
            db.execute(SCHEMA)
            row = db.execute("""
                SELECT started_at, age_months, care_points, hunger, sleepiness, diaper,
                       gas, attachment, stimulation, mood, arousal
                FROM baby_state WHERE id = 1
            """).fetchone()
        return State(*row) if row is not None else State(started_at=now)

    def save(self, state: State) -> None:
        with closing(connect(self.database)) as db, db:
            db.execute("""
                INSERT OR REPLACE INTO baby_state (
                    id, started_at, age_months, care_points, hunger, sleepiness, diaper,
                    gas, attachment, stimulation, mood, arousal
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, astuple(state))
