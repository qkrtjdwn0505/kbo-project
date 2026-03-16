"""KBO 데이터 대시보드 — FastAPI 백엔드"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.backend.routers import explorer, players, teams, games

app = FastAPI(
    title="KBO 데이터 대시보드 API",
    description="네이버가 못 하는 KBO 복합 조건 질의를 해결하는 데이터 대시보드",
    version="0.1.0",
)

# CORS 설정 (개발 중 React 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(explorer.router, prefix="/api/v1", tags=["탐색기"])
app.include_router(players.router, prefix="/api/v1", tags=["선수"])
app.include_router(teams.router, prefix="/api/v1", tags=["팀/순위"])
app.include_router(games.router, prefix="/api/v1", tags=["일정/결과"])


@app.get("/api/health")
def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "service": "KBO 데이터 대시보드"}


# 프로덕션: React 빌드 정적 파일 서빙
build_path = Path("src/frontend/build")
if build_path.exists():
    app.mount("/", StaticFiles(directory=str(build_path), html=True), name="static")
