# KBO 데이터 대시보드 — Design Document

> 상위 문서: steering.md → requirements.md → 이 문서
> 이 문서는 DB 스키마, API 엔드포인트, 컴포넌트 구조를 정의합니다.
> AI 에이전트에게 구현을 지시할 때 이 문서를 @file로 참조합니다.
> 최종 수정일: 2026-03-18

---

## 1. 시스템 아키텍처

```
[사용자 브라우저]
      │
      ▼
[React 19 SPA (Vite)]  ← Chart.js (시각화)
      │
      ▼  (REST API, JSON)
[FastAPI 백엔드]
      │
      ├── 동적 SQL 빌더 (탐색기 핵심)
      │   ├── 경로 A: condition=all → 시즌 테이블 직접 조회
      │   └── 경로 B: 조건 필터 → 경기별 집계 + Python 세이버 재계산
      ├── 세이버메트릭스 계산 엔진
      ├── 데이터 수집 배치
      └── live_game_poller (실시간 경기 추적, 실험적)
      │
      ▼
[SQLite DB (kbo.db, ~8MB, Git 포함)]  → (확장 시 PostgreSQL)
```

### 배포 구조
```
[Render 무료 티어]
  └── FastAPI 서버
       ├── /api/* → REST API 응답
       └── /* → React 빌드 정적 파일 서빙

[UptimeRobot] → 5분 핑으로 Render 슬립 방지

GitHub: qkrtjdwn0505/kbo-project (Public Git → Render Manual Deploy)
```

### 실행 방법
```bash
# 백엔드
uvicorn main:app --port 8000

# 프론트엔드 (개발)
cd src/frontend && npm run dev

# Render Start Command
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 2. DB 스키마

### 테이블 목록

| 테이블 | 설명 | 주요 용도 | 상태 |
|--------|------|----------|------|
| teams | 10개 구단 정보 | 팀 순위, 필터 | ✅ |
| players | 선수 프로필 | 선수 검색, 세부정보 | ✅ |
| games | 경기 정보 | 일정/결과, 스코어보드 | ✅ |
| batter_stats | 타자 경기별 기록 | 탐색기, 기록 조회 | ✅ |
| pitcher_stats | 투수 경기별 기록 | 탐색기, 기록 조회 | ✅ |
| batter_season | 타자 시즌 누적 + 세이버 | 선수 세부정보, 순위 | ✅ |
| pitcher_season | 투수 시즌 누적 + 세이버 | 선수 세부정보, 순위 | ✅ |
| lineups | 경기별 라인업 | 풀 라인업 | ✅ |
| league_constants | 시즌별 리그 상수 | 세이버 계산 | ✅ |
| at_bat_situations | 타석별 상황 (실시간) | play-by-play, 탐색기 조건 | ✅ (2026~) |
| cheer_songs | 응원가 데이터 | 응원가 페이지 | 미구현 |
| player_sns | 선수 SNS 링크 | SNS 허브 | 미구현 |
| team_sns | 구단 SNS 링크 | SNS 허브 | 미구현 |
| users | 회원 정보 | 커뮤니티 (3순위) | 미구현 |
| posts | 게시글 | 커뮤니티 (3순위) | 미구현 |
| game_logs | 직관 기록 | 직관로그 (3순위) | 미구현 |

### 테이블 상세

#### teams
```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,           -- "KIA 타이거즈"
    short_name TEXT NOT NULL,     -- "KIA"
    city TEXT NOT NULL,           -- "광주"
    stadium TEXT NOT NULL,        -- "챔피언스필드"
    logo_initial TEXT NOT NULL,   -- "KIA" (이니셜 아바타용)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### players
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    position TEXT NOT NULL,       -- "내야수", "투수", "외야수", "포수"
    position_detail TEXT,         -- "유격수", "선발", "마무리"
    back_number INTEGER,
    birth_date DATE,
    height INTEGER,               -- cm
    weight INTEGER,               -- kg
    bat_hand TEXT,                 -- "좌타", "우타", "스위치"
    throw_hand TEXT,              -- "좌투", "우투"
    instagram_url TEXT,
    youtube_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_players_name ON players(name);
```

#### games
```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    -- 연도 필터: date LIKE '2026%' 또는 date >= '2026-01-01' 사용
    date DATE NOT NULL,
    time TEXT,                    -- "18:30"
    stadium TEXT,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_score INTEGER,
    away_score INTEGER,
    status TEXT DEFAULT 'scheduled', -- "scheduled", "in_progress", "final"
    game_type TEXT DEFAULT 'regular', -- "preseason", "regular", "postseason"
    home_starter_id INTEGER REFERENCES players(id),
    away_starter_id INTEGER REFERENCES players(id),
    winning_pitcher_id INTEGER REFERENCES players(id),
    losing_pitcher_id INTEGER REFERENCES players(id),
    save_pitcher_id INTEGER REFERENCES players(id),
    inning_scores TEXT,           -- JSON: {"home": [0,1,0,...], "away": [2,0,1,...]}
    day_of_week TEXT,             -- "월", "화", ..., "일"
    is_night_game BOOLEAN,        -- 18:00 이후 = 야간
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_games_date ON games(date);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_games_type ON games(game_type);
```

**주의:** season_aggregator는 `game_type='regular'`만 집계 (시범/포스트 제외)

#### batter_stats (경기별 타자 기록)
```sql
CREATE TABLE batter_stats (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    player_id INTEGER REFERENCES players(id),
    team_id INTEGER REFERENCES teams(id),
    -- 기본 기록
    pa INTEGER DEFAULT 0,         -- 타석
    ab INTEGER DEFAULT 0,         -- 타수
    hits INTEGER DEFAULT 0,       -- 안타
    doubles INTEGER DEFAULT 0,    -- 2루타
    triples INTEGER DEFAULT 0,    -- 3루타
    hr INTEGER DEFAULT 0,         -- 홈런
    rbi INTEGER DEFAULT 0,        -- 타점
    runs INTEGER DEFAULT 0,       -- 득점
    sb INTEGER DEFAULT 0,         -- 도루
    cs INTEGER DEFAULT 0,         -- 도실
    bb INTEGER DEFAULT 0,         -- 볼넷
    hbp INTEGER DEFAULT 0,        -- 사구
    so INTEGER DEFAULT 0,         -- 삼진
    gdp INTEGER DEFAULT 0,        -- 병살타
    sf INTEGER DEFAULT 0,         -- 희비
    -- 상황 정보 (스플릿용)
    runners_on_scoring BOOLEAN,   -- 득점권 상황 여부
    opponent_pitcher_hand TEXT,   -- 상대 투수 투구 손 ("좌투"/"우투")
    inning INTEGER,               -- 이닝
    is_home BOOLEAN,              -- 홈 경기 여부
    score_diff INTEGER,           -- 점수차 (양수=리드, 0=동점, 음수=비하인드)
    UNIQUE(game_id, player_id, inning)
);
CREATE INDEX idx_batter_game ON batter_stats(game_id);
CREATE INDEX idx_batter_player ON batter_stats(player_id);
CREATE INDEX idx_batter_scoring ON batter_stats(runners_on_scoring);
```

#### pitcher_stats (경기별 투수 기록)
```sql
CREATE TABLE pitcher_stats (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    player_id INTEGER REFERENCES players(id),
    team_id INTEGER REFERENCES teams(id),
    -- 기본 기록
    ip_outs INTEGER DEFAULT 0,    -- 이닝 (아웃 카운트 기준, 18 = 6이닝)
    hits_allowed INTEGER DEFAULT 0,
    hr_allowed INTEGER DEFAULT 0,
    bb_allowed INTEGER DEFAULT 0,
    hbp_allowed INTEGER DEFAULT 0,
    so_count INTEGER DEFAULT 0,   -- 탈삼진
    runs_allowed INTEGER DEFAULT 0,
    er INTEGER DEFAULT 0,         -- 자책점
    -- 결과
    is_starter BOOLEAN,
    decision TEXT,                 -- "W", "L", "S", "H", NULL
    -- 상황 정보
    batter_hand TEXT,             -- 상대 타자 손 ("좌타"/"우타")
    is_home BOOLEAN,
    UNIQUE(game_id, player_id)
);
CREATE INDEX idx_pitcher_game ON pitcher_stats(game_id);
CREATE INDEX idx_pitcher_player ON pitcher_stats(player_id);
```

#### batter_season (시즌 누적 + 세이버메트릭스)
```sql
CREATE TABLE batter_season (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    season INTEGER NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    -- 누적 클래식
    games INTEGER, pa INTEGER, ab INTEGER, hits INTEGER,
    doubles INTEGER, triples INTEGER, hr INTEGER, rbi INTEGER,
    runs INTEGER, sb INTEGER, cs INTEGER, bb INTEGER, hbp INTEGER,
    so INTEGER, gdp INTEGER, sf INTEGER,
    -- 계산 클래식
    avg REAL, obp REAL, slg REAL, ops REAL,
    -- 세이버메트릭스 (자체 계산 엔진)
    woba REAL, wrc_plus REAL, war REAL, babip REAL,
    iso REAL, bb_pct REAL, k_pct REAL,
    -- 스플릿 누적
    ops_vs_lhp REAL, ops_vs_rhp REAL,
    ops_risp REAL,
    ops_home REAL, ops_away REAL,
    -- 메타
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season)
);
```

**주의:** sb/cs는 KBO 박스스코어 API에 없음. season_aggregator가 COALESCE로 기존 도루 데이터 보존.

#### pitcher_season (시즌 누적 + 세이버메트릭스)
```sql
CREATE TABLE pitcher_season (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    season INTEGER NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    -- 누적 클래식
    games INTEGER, wins INTEGER, losses INTEGER, saves INTEGER, holds INTEGER,
    ip_outs INTEGER,
    hits_allowed INTEGER, hr_allowed INTEGER, bb_allowed INTEGER,
    hbp_allowed INTEGER, so_count INTEGER, runs_allowed INTEGER, er INTEGER,
    -- 계산 클래식
    era REAL, whip REAL,
    -- 세이버메트릭스
    fip REAL, xfip REAL, war REAL, babip REAL, lob_pct REAL,
    k_per_9 REAL, bb_per_9 REAL, hr_per_9 REAL, k_bb_ratio REAL,
    -- 스플릿 누적
    era_vs_lhb REAL, era_vs_rhb REAL,
    era_home REAL, era_away REAL,
    -- 메타
    is_starter BOOLEAN,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season)
);
```

#### league_constants
```sql
CREATE TABLE league_constants (
    season INTEGER PRIMARY KEY,
    woba_scale REAL,
    league_woba REAL,
    league_wrc REAL,
    fip_constant REAL,            -- 2025: 3.44
    league_hr_fb_rate REAL,
    rppa REAL,                    -- runs per plate appearance
    league_rpw REAL               -- runs per win
);
```

**자체 계산:** calc_league_constants.py가 batter_season/pitcher_season 데이터로부터 계산. "기본값 사용" 경고는 이 스크립트 실행 후 사라짐.

#### at_bat_situations (2026~ live_game_poller용)
```sql
CREATE TABLE at_bat_situations (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    inning INTEGER NOT NULL,
    top_bottom TEXT NOT NULL,      -- "top" / "bottom"
    batter_id INTEGER REFERENCES players(id),
    pitcher_id INTEGER REFERENCES players(id),
    runners TEXT,                  -- JSON: 주자 상황
    outs INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    result TEXT,                   -- 타석 결과
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**용도:** 탐색기 risp/leading/trailing 조건을 경기별로 활성화 (2025는 기록실 시즌합산만 가능)

#### lineups
```sql
CREATE TABLE lineups (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    team_id INTEGER REFERENCES teams(id),
    player_id INTEGER REFERENCES players(id),
    batting_order INTEGER,        -- 1~9 (선발), NULL (불펜/벤치)
    position TEXT,                 -- "DH", "SS", "CF", "P" 등
    role TEXT NOT NULL,            -- "starter", "bullpen", "bench"
    role_detail TEXT,              -- "마무리", "셋업", "롱릴리프", "대타", "대주자"
    pitched_yesterday BOOLEAN DEFAULT FALSE,
    UNIQUE(game_id, team_id, player_id)
);
CREATE INDEX idx_lineups_game ON lineups(game_id, team_id);
```

#### cheer_songs (미구현)
```sql
CREATE TABLE cheer_songs (
    id INTEGER PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    player_id INTEGER REFERENCES players(id),  -- NULL이면 팀 공통
    title TEXT NOT NULL,
    lyrics TEXT NOT NULL,
    youtube_url TEXT,
    song_type TEXT NOT NULL,      -- "team", "player", "common"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. API 엔드포인트

### Base URL: `/api/v1`

### 탐색기 (핵심)

| Method | Path | 설명 | 상태 |
|--------|------|------|------|
| GET | `/explorer` | 복합 조건 질의 | ✅ |

**쿼리 파라미터:**
```
target: batter | pitcher | pitcher_starter | pitcher_bullpen | team
condition: all | vs_lhb | vs_rhb | vs_lhp | vs_rhp | risp | home | away |
           night | day | leading | tied | trailing | vs_team:{team_id}
stat: (대상에 따라 다름)
sort: desc | asc
limit: 5 | 10 | 20 | all
season: (기본값: get_latest_season()이 반환하는 최신 시즌)
```

**동적 SQL 빌더 — 2가지 경로:**
- 경로 A: `condition=all` → batter_season/pitcher_season 시즌 테이블 직접 조회 (빠름)
- 경로 B: 조건 필터 → 경기별 batter_stats/pitcher_stats에서 집계 + Python 세이버 재계산

**참고:** risp/leading/trailing 조건은 2025 데이터에서는 기록실 시즌합산만 가능. 경기별 세분화는 2026~ (at_bat_situations 기반)

### 선수

| Method | Path | 설명 | 상태 |
|--------|------|------|------|
| GET | `/players/search` | 자동완성 — ?q=김도&limit=10 | ✅ |
| GET | `/players/{id}/classic` | 클래식 스탯 | ✅ |
| GET | `/players/{id}/sabermetrics` | 세이버메트릭스 스탯 | ✅ |
| GET | `/players/{id}/splits` | 스플릿 (vs좌/우, 홈/원정, 득점권) | ✅ |
| GET | `/players/records` | 전체 선수 테이블 (기록 조회) | ✅ |

### 순위

| Method | Path | 설명 | 상태 |
|--------|------|------|------|
| GET | `/standings` | 팀 순위표 | ✅ |
| GET | `/standings/comparison` | 팀스탯 종합 비교 카드 | ✅ |
| GET | `/rankings/top` | 주요 지표별 선수 TOP5 | ✅ |
| GET | `/standings/seasons` | 시즌 목록 | ✅ |

### 일정/경기

| Method | Path | 설명 | 상태 |
|--------|------|------|------|
| GET | `/games/dates` | 월간 경기 일자 목록 | ✅ |
| GET | `/games/schedule` | 날짜별 경기 목록 | ✅ |
| GET | `/games/{id}/detail` | 경기 상세 (스코어보드, 이닝별 점수) | ✅ |
| GET | `/games/{id}/lineups` | 경기별 라인업 | ✅ |

### 미구현 (Phase 6)

| Method | Path | 설명 | 상태 |
|--------|------|------|------|
| GET | `/fun-stats` | 이색 통계 카드 | 미구현 |
| GET | `/hot-cold` | 핫/콜드 선수 TOP5 | 미구현 |
| GET | `/cheer-songs` | 응원가 목록 | 미구현 |
| GET | `/sns/teams` | 구단별 SNS 링크 | 미구현 |
| POST | `/auth/register` | 회원가입 | 미구현 |
| POST | `/auth/login` | 로그인 | 미구현 |
| GET/POST | `/posts` | 게시글 CRUD | 미구현 |
| GET/POST | `/game-logs` | 직관 기록 | 미구현 |

---

## 4. 동적 SQL 빌더 (탐색기 핵심 로직)

### 설계 원칙
- f-string SQL 금지 — 반드시 파라미터 바인딩
- SQLAlchemy Core 사용 (ORM보다 동적 쿼리에 적합)
- 조건별 WHERE 절을 함수로 분리 → 조합

### 2가지 실행 경로

```python
def build_explorer_query(target, condition, stat, sort, limit, season):
    if condition == "all":
        # 경로 A: 시즌 테이블 직접 조회 (빠름)
        return query_season_table(target, stat, sort, limit, season)
    else:
        # 경로 B: 경기별 스탯 필터 → 집계 → Python 세이버 재계산
        return query_game_stats_with_condition(target, condition, stat, sort, limit, season)
```

### 조건 → SQL 매핑

| 조건 | WHERE절 | 비고 |
|-----|---------|------|
| all | (없음 — 시즌 테이블 직접) | 경로 A |
| vs_lhb | opponent_pitcher_hand = '좌투' | 경로 B |
| vs_rhb | opponent_pitcher_hand = '우투' | 경로 B |
| risp | runners_on_scoring = TRUE | 2025: 시즌합산, 2026~: 경기별 |
| home | is_home = TRUE | 경로 B |
| away | is_home = FALSE | 경로 B |
| night | games.is_night_game = TRUE | JOIN 필요 |
| leading | score_diff > 0 | 2026~ at_bat_situations |
| tied | score_diff = 0 | 2026~ at_bat_situations |
| trailing | score_diff < 0 | 2026~ at_bat_situations |
| vs_team:{id} | 상대 팀 필터 | JOIN games |

---

## 5. 세이버메트릭스 계산 엔진

### 리그 상수 (2025 자체 계산)
- FIP 상수: 3.44
- league_wOBA: 0.338
- 자체 계산: calc_league_constants.py (batter_season + pitcher_season 기반)

### 알려진 정확도 상태

| 지표 | 정확도 | 비고 |
|------|--------|------|
| 클래식 (타율/ERA/HR/RBI) | ✅ 정확 | |
| wOBA | ✅ 거의 정확 | |
| FIP | ✅ 정확 | |
| wRC+ | ⚠️ 차이 있음 | 파크팩터 미반영 (디아즈 176 vs STATIZ ~145~155) |
| WAR | ⚠️ 차이 있음 | 파크팩터 미반영 (폰세 6.5 vs 실제 8.38) |

**해결 방향:** 파크팩터 구현 OR 면책문구 OR STATIZ 크롤링 (한국 IP만 허용)

---

## 6. 프론트엔드 컴포넌트 구조

```
src/frontend/
├── src/
│   ├── App.jsx                 # 라우터 설정
│   ├── pages/
│   │   ├── Home.jsx            # 홈 (순위 요약 + 바로가기)
│   │   ├── Explorer.jsx        # ① 탐색기 (5단 드롭다운 + 테이블 + 차트)
│   │   ├── Player.jsx          # ② 선수 세부정보 (3탭)
│   │   ├── Standings.jsx       # ③ 순위
│   │   ├── Schedule.jsx        # ④ 일정/결과 (캘린더 + 스코어보드 + 라인업)
│   │   └── RecordsPage.jsx     # ⑥ 기록 조회 (전체선수 테이블 + 토글)
│   ├── components/
│   │   ├── layout/
│   │   │   └── Navbar.jsx      # 홈 | 탐색기 | 순위 | 일정 | 기록
│   │   └── common/
│   │       ├── StatTable.jsx
│   │       ├── BarChart.jsx
│   │       └── ...
│   ├── hooks/
│   │   └── useApi.js           # 공용 API 호출 훅
│   └── utils/
│       └── formatStat.js       # 수치 포맷 (.328, 3.45 등)
```

### 페이지 라우팅
```
/                  → 홈
/explorer          → ① 탐색기
/players/:id       → ② 선수 세부정보
/standings         → ③ 순위
/schedule          → ④ 일정/결과 (캘린더 + 스코어보드 + 라인업)
/records           → ⑥ 기록 조회
/fun-stats         → ⑦ 이색 통계 (미구현)
/cheer-songs       → ⑪ 응원가 (미구현)
/sns               → ⑫ SNS 허브 (미구현)
```

---

## 7. 데이터 수집 파이프라인 구조

```
src/data/
├── collectors/
│   ├── kbo_data_collector.py        # KBO API (GetKboGameList, GetBoxScoreScroll)
│   ├── kbo_schedule_collector.py    # 일정 수집
│   ├── kbo_season_stats_scraper.py  # KBO 기록실 크롤링 (도루 sb/cs 보강)
│   └── kbo_situation_scraper.py     # 기록실 상황별탭 (ops_risp, avg_vs_lhb/rhb)
├── processors/
│   ├── season_aggregator.py         # 경기별 → 시즌 누적 집계 (regular만)
│   ├── sabermetrics_engine.py       # 세이버메트릭스 계산 엔진
│   └── calc_league_constants.py     # 리그 상수 자체 계산
├── batch/
│   ├── collect_season.py            # 시즌 전체 벌크 수집
│   ├── collect_missing.py           # 누락 경기 보충
│   └── daily_update.py              # 매일 배치 업데이트
├── live_game_poller.py              # 실시간 경기 추적 (30초 폴링)
└── tests/
    └── (167개 데이터 테스트 + 103개 API 테스트 = 총 270개)
```

### KBO API 엔드포인트
- `GetKboGameList` — 경기 목록
- `GetBoxScoreScroll` — 박스스코어
- play-by-play API는 **없음** (탐색 완료 확인)

### 배치 실행 흐름
```
daily_update.py --season 2026
  ├── 1. 오늘 경기 결과 수집 (kbo_data_collector)
  ├── 2. 박스스코어 수집 + DB 저장
  ├── 3. 시즌 누적 재계산 (season_aggregator — COALESCE로 도루 보존)
  ├── 4. 세이버메트릭스 계산 (sabermetrics_engine)
  └── 5. 리그 상수 갱신 (calc_league_constants)
```

### live_game_poller 실행 흐름 (2026~)
```
live_game_poller.py --daemon
  ├── 경기 중 30초 폴링
  ├── at_bat_situations 테이블에 주자/점수/이닝 저장
  └── 3/28 개막일 실전 테스트 필요 (B_P_NM/T_P_NM 필드 검증)
```

### 데이터 파이프라인 주의사항
1. season_aggregator 재실행 시 sb/cs COALESCE 보존 → 도루 스크래퍼 재실행 불필요
2. season_aggregator는 game_type='regular'만 집계
3. 도루(sb/cs)는 KBO 박스스코어 API에 없음 → 기록실 크롤링으로만 보강
4. 리그상수 "기본값 사용" 경고 → calc_league_constants.py 실행 후 해소
5. kbo.db를 Git에 포함 (~8MB) → DB 변경 후 반드시 `git add kbo.db` + push

### 데이터 현황 (2026-03-18 기준)
- 2025: preseason 42 + regular 720 + postseason 16 = 768경기
- 2026: preseason 60 (시범, 박스스코어 수집완료) + regular 675 (scheduled)
- 주요 기록: 디아즈 50HR/158타점, 폰세 17승1패 ERA1.89 252K, 박해민 49도루

---

## 8. 구현 순서

### 완료
- Phase 1: 기반 구축 ✅
- Phase 2: MVP 백엔드 ✅
- Phase 3: MVP 프론트엔드 ✅
- Phase 4: 통합 + 배포 ✅
- Phase 5: 2순위 기능 ✅

### 진행중
- Phase 5.5: 2026 개막 준비 (poller 테스트, 면책문구, 모바일)

### 예정
- Phase 6: 3순위 기능 (이색통계, 응원가, SNS허브, 커뮤니티)

→ 상세는 tasks.md 참조

---

> 이 문서는 steering.md의 원칙과 requirements.md의 요구사항을 기반으로 작성되었습니다.
> 구현 시 AI 에이전트에게 이 문서를 @file:design.md로 참조시킵니다.
> 구현 중 설계 변경이 필요하면 이 문서를 먼저 수정하고, 코드에 반영합니다.
