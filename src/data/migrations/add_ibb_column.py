"""DB 스키마 마이그레이션: batter_stats에 ibb 컬럼 추가

table2 파서에서 고의사구(고4)를 분리 추출할 수 있으므로
batter_stats와 batter_season에 ibb 컬럼을 추가합니다.

사용법:
    python -m src.data.migrations.add_ibb_column

기존 데이터는 ibb=0으로 초기화됩니다 (재수집 시 정확한 값으로 갱신).
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "kbo.db"


def migrate():
    """ibb 컬럼 추가 마이그레이션"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 이미 컬럼이 있는지 확인
    cols = [
        row[1]
        for row in cursor.execute("PRAGMA table_info(batter_stats)").fetchall()
    ]

    if "ibb" not in cols:
        cursor.execute(
            "ALTER TABLE batter_stats ADD COLUMN ibb INTEGER DEFAULT 0"
        )
        print("batter_stats.ibb 컬럼 추가 완료")
    else:
        print("batter_stats.ibb 컬럼 이미 존재")

    # batter_season에도 ibb 추가 (시즌 누적용)
    cols_season = [
        row[1]
        for row in cursor.execute("PRAGMA table_info(batter_season)").fetchall()
    ]

    if "ibb" not in cols_season:
        cursor.execute(
            "ALTER TABLE batter_season ADD COLUMN ibb INTEGER DEFAULT 0"
        )
        print("batter_season.ibb 컬럼 추가 완료")
    else:
        print("batter_season.ibb 컬럼 이미 존재")

    conn.commit()
    conn.close()
    print("마이그레이션 완료")


if __name__ == "__main__":
    migrate()
