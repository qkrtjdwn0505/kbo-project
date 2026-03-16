"""DB 설정 및 세션 관리"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

# DB 경로 (기본: 프로젝트 루트의 kbo.db)
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "kbo.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 멀티스레드 허용
    echo=False,  # SQL 로그 (디버깅 시 True)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 의존성 주입용 DB 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
