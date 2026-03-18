# ⚾ KBO 데이터 대시보드

**네이버가 못 하는 KBO 복합 조건 질의를 드롭다운 조합으로 해결하는 데이터 대시보드**

> "2025년 득점권 OPS가 가장 높은 타자 5명은?" — 이 질문에 답할 수 있는 KBO 서비스가 없었습니다.

🌐 **[라이브 데모](https://kbo-dashboard.onrender.com)** | 📊 2025 KBO 정규시즌 720경기 데이터

---

## 핵심 기능

### 🔍 데이터 탐색기 — 5단 드롭다운 복합 조건 질의

네이버, STATIZ, KBReport 어디서도 할 수 없는 **복합 조건 질의**를 드롭다운 5개 조합으로 실행합니다.

```
[대상] → [조건] → [지표] → [정렬] → [범위]
 타자     홈경기    OPS     높은순    5명
```

**지원 조건:** 전체, vs 좌투/우투, 홈/원정, 주간/야간, 평일/주말, 상대팀별

**지원 지표 (타자):** 타율, HR, RBI, OPS, wOBA, wRC+, WAR, BABIP, ISO, BB%, K% 등
**지원 지표 (투수):** ERA, FIP, xFIP, WHIP, K/9, BB/9, WAR 등

### 👤 선수 세부정보 — 3탭 구조

- **클래식 탭:** 전통 기록 (타율, 홈런, 타점, ERA 등)
- **세이버메트릭스 탭:** FanGraphs 방식 고급 지표 (wOBA, wRC+, FIP, xFIP) + 호버 툴팁
- **스플릿 탭:** vs 좌투/우투 OPS, 홈/원정 OPS, 득점권 OPS (최선값 강조)

### 🏆 순위 페이지

- 10팀 순위표 (최근 5경기 흐름 + 연승/연패)
- 팀스탯 비교 카드 4개 (공격력/투수력/수비력/주루)
- 주요 지표 TOP5 (타율, 홈런, 타점, ERA, 승, 탈삼진)

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | React 19 + Vite + Chart.js |
| 백엔드 | Python + FastAPI |
| DB | SQLite (SQLAlchemy) |
| 배포 | Render (무료 티어) |
| 데이터 수집 | KBO 공식 홈페이지 비공식 API (requests + BeautifulSoup) |
| 세이버메트릭스 | FanGraphs 방식 자체 계산 엔진 |

---

## 아키텍처

```
[브라우저] → [React SPA]
                ↓ (REST API)
            [FastAPI 백엔드]
                ├── 동적 SQL 빌더 (탐색기 핵심)
                ├── 세이버메트릭스 계산 엔진
                └── 데이터 수집 파이프라인
                ↓
            [SQLite DB]
                └── 720경기 / 615선수 / 20,000+ 타석 기록
```

### 탐색기 동적 SQL 빌더 — 핵심 엔진

조건에 따라 2가지 경로로 분기:

- **경로 A (condition=all):** 시즌 누적 테이블에서 직접 조회 → SQL만으로 완결
- **경로 B (조건 필터):** 경기별 테이블에서 WHERE 필터 → GROUP BY → Python에서 세이버메트릭스 재계산

경로 B가 이 서비스의 차별점 — SQL로 필터한 raw 데이터를 sabermetrics_engine으로 실시간 계산하여 조건별 wOBA, FIP 등을 반환합니다.

---

## 데이터 정확도

> "데이터 정확도가 생명이다" — 프로젝트 핵심 원칙(P3)

- 데이터 파이프라인: **167개 데이터 테스트** 통과 (세이버 53 + 타석파서 113 + 단일경기 1)
- 백엔드 API: **103개 API 테스트** 통과
- **총 270개 테스트** 통과
- 크로스체크: 디아즈 2025 시즌 **50홈런, 158타점** (공식 기록 일치)
- 더블헤더 수집 누락 발견 → 수정 완료
- 도루 데이터: KBO 기록실 크롤링으로 보강 (박해민 49도루)
- 스플릿: 기록실 상황별 탭 크롤링으로 ops_risp, avg_vs_lhb/rhb 보강

---

## 프로젝트 구조

```
kbo-dashboard/
├── main.py                      # FastAPI 진입점 (SPA 서빙 포함)
├── kbo.db                       # SQLite DB (720경기)
├── src/
│   ├── backend/
│   │   ├── routers/             # API 엔드포인트 (explorer, players, teams, games)
│   │   ├── explorer/            # 동적 SQL 빌더
│   │   ├── schemas/             # Pydantic 응답 모델
│   │   ├── models.py            # SQLAlchemy Table 메타데이터
│   │   └── database.py          # DB 세션 관리
│   ├── data/
│   │   ├── collectors/          # KBO 데이터 수집기 + 실시간 폴링
│   │   ├── processors/          # 세이버메트릭스 엔진 + 시즌 집계
│   │   ├── loaders/             # DB 저장 (upsert)
│   │   ├── batch/               # 시즌 수집 + 일일 업데이트
│   │   └── migrations/          # 데이터 보강 스크립트
│   └── frontend/
│       └── src/
│           ├── pages/           # 홈, 탐색기, 선수, 순위
│           ├── components/      # 공통 + 기능별 컴포넌트
│           ├── hooks/           # API 호출 커스텀 훅
│           └── utils/           # 수치 포맷, 상수
├── render.yaml                  # Render 배포 설정
├── build.sh                     # 빌드 스크립트 (pip + npm)
└── docs/                        # 설계 문서 (SDD)
```

---

## 로컬 실행

### 1. 백엔드

```bash
cd kbo-dashboard
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. 프론트엔드 (개발 모드)

```bash
cd src/frontend
npm install
npm run dev
```

`http://localhost:5173`에서 접속. API 프록시가 자동으로 8000번으로 연결됩니다.

### 3. 통합 빌드 (단일 서버)

```bash
cd src/frontend && npm run build && cd ../..
uvicorn main:app --port 8000
```

`http://localhost:8000`에서 프론트 + API 동시 서빙.

---

## 데이터 수집 + 갱신

### 2026 시즌 일일 업데이트

```bash
# 어제 경기 자동 수집
python -m src.data.batch.daily_update --season 2026

# 특정 날짜 수집
python -m src.data.batch.daily_update --date 20260328 --season 2026

# 날짜 범위 수집
python -m src.data.batch.daily_update --from 20260328 --to 20260330 --season 2026
```

### 실시간 폴링 수집기 (타석별 상황 데이터)

```bash
# 경기일에 실행 → 득점권/점수차/이닝 상황 수집
python -m src.data.collectors.live_game_poller --daemon
```

---

## 개발 방법론

**SDD (Spec-Driven Development)** 기반으로 개발:

```
steering (프로젝트 원칙)
  → requirements (15개 기능 요구사항)
    → design (DB 스키마, API, 컴포넌트)
      → tasks (작업 분해)
        → implementation (AI 에이전트 구현)
          → 검증 → 반복
```

AI 코딩 도구(Claude Code, Cursor Agent)와 협업하여 개발했으며, 모든 설계 결정은 `docs/` 폴더의 스펙 문서에 기반합니다.

---

## 알려진 제한 사항

| 항목 | 상태 | 비고 |
|------|------|------|
| 득점권 탐색기 조건 | ⚠️ 스플릿 탭만 지원 | 경기별 데이터 미보유 (2026 시즌부터 폴링으로 해결) |
| 리드/동점/비하인드 조건 | ❌ 비활성 | play-by-play 필요 (실시간 폴링 수집기로 해결 예정) |
| 이닝별 조건 | ❌ 비활성 | at_bat_parser 재처리 필요 |
| 투수 vs좌타/우타 ERA | ⚠️ 피안타율로 대체 | KBO 기록실 API 제한 |
| 선수 사진 | ❌ 이니셜 아바타 사용 | 저작권 문제 |

---

## 라이선스

이 프로젝트는 개인 포트폴리오/학습 목적으로 제작되었습니다.
데이터 출처: KBO 공식 홈페이지 | 세이버메트릭스 계산 방식: FanGraphs

---

## 만든 사람

1인 개발 프로젝트 | 2026.03
