"""마이그레이션: at_bat_situations 테이블 생성

실행:
    python -m src.data.migrations.create_at_bat_situations
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"


def run(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS at_bat_situations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            game_int_id INTEGER,
            inning INTEGER NOT NULL,
            is_top_half BOOLEAN NOT NULL,
            batter_name TEXT NOT NULL,
            batter_team_id INTEGER,
            pitcher_name TEXT NOT NULL,
            pitcher_team_id INTEGER,
            runners_on_1b BOOLEAN DEFAULT FALSE,
            runners_on_2b BOOLEAN DEFAULT FALSE,
            runners_on_3b BOOLEAN DEFAULT FALSE,
            runners_on_scoring BOOLEAN DEFAULT FALSE,
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            score_diff INTEGER DEFAULT 0,
            out_count INTEGER DEFAULT 0,
            at_bat_order INTEGER,
            polled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game_id, batter_name, inning, at_bat_order)
        );

        CREATE INDEX IF NOT EXISTS idx_abs_game ON at_bat_situations(game_id);
        CREATE INDEX IF NOT EXISTS idx_abs_game_int ON at_bat_situations(game_int_id);
        CREATE INDEX IF NOT EXISTS idx_abs_batter ON at_bat_situations(batter_name);
    """)

    conn.commit()
    conn.close()
    print(f"at_bat_situations 테이블 생성 완료: {db_path}")


if __name__ == "__main__":
    run()
