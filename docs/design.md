# KBO 데이터 대시보드 — Design Document

> 상위 문서: steering.md → requirements.md → 이 문서
> 이 문서는 DB 스키마, API 엔드포인트, 컴포넌트 구조를 정의합니다.
> AI 에이전트에게 구현을 지시할 때 이 문서를 @file로 참조합니다.
> 최종 수정일: 2026-03-16

---

## 1. 시스템 아키텍처

```
[사용자 브라우저]
      │
      ▼
[React SPA]  ← Chart.js (시각화)
      │
      ▼  (REST API, JSON)
[FastAPI 백엔드]
      │
      ├── 동적 SQL 빌더 (탐색기 핵심)
      ├── 세이버메트릭스 계산 엔진
      └── 데이터 수집 배치
      │
      ▼
[SQLite DB]  → (확장 시 PostgreSQL)
```

### 배포 구조 (MVP)
```
[Render 무료 티어]
  └── FastAPI 서버
       ├── /api/* → REST API 응답
       └── /* → React 빌드 정적 파일 서빙
```

---

## 2. DB 스키마

### 테이블 목록

| 테이블 | 설명 | 주요 용도 |
|--------|------|----------|
| teams | 10개 구단 정보 | 팀 순위, 필터 |
| players | 선수 프로필 | 선수 검색, 세부정보 |
| games | 경기 정보 | 일정/결과, 스코어보드 |
| batter_stats | 타자 경기별 기록 | 탐색기, 기록 조회 |
| pitcher_stats | 투수 경기별 기록 | 탐색기, 기록 조회 |
| batter_season | 타자 시즌 누적 + 세이버 | 선수 세부정보, 순위 |
| pitcher_season | 투수 시즌 누적 + 세이버 | 선수 세부정보, 순위 |
| lineups | 경기별 라인업 | 풀 라인업 |
| player_sns | 선수 SNS 링크 | SNS 허브 |
| team_sns | 구단 SNS 링크 | SNS 허브 |
| cheer_songs | 응원가 데이터 | 응원가 페이지 |
| users | 회원 정보 | 커뮤니티, 직관로그 (3순위) |
| posts | 게시글 | 커뮤니티 (3순위) |
| game_logs | 직관 기록 | 직관로그 (3순위) |

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
    date DATE NOT NULL,
    time TEXT,                    -- "18:30"
    stadium TEXT,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_score INTEGER,
    away_score INTEGER,
    status TEXT DEFAULT 'scheduled', -- "scheduled", "in_progress", "final"
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
```

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
    ibb INTEGER DEFAULT 0,        -- 고의사구
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
    season INTEGER NOT NULL,      -- 2025
    team_id INTEGER REFERENCES teams(id),
    -- 누적 클래식
    games INTEGER, pa INTEGER, ab INTEGER, hits INTEGER,
    doubles INTEGER, triples INTEGER, hr INTEGER, rbi INTEGER,
    runs INTEGER, sb INTEGER, cs INTEGER, bb INTEGER, hbp INTEGER,
    so INTEGER, gdp INTEGER, sf INTEGER, ibb INTEGER,
    -- 계산 클래식
    avg REAL,                     -- 타율
    obp REAL,                     -- 출루율
    slg REAL,                     -- 장타율
    ops REAL,                     -- OPS
    -- 세이버메트릭스 (자체 계산 엔진)
    woba REAL,
    wrc_plus REAL,
    war REAL,
    babip REAL,
    iso REAL,                     -- 순장타율
    bb_pct REAL,                  -- 볼넷%
    k_pct REAL,                   -- 삼진%
    -- 스플릿 누적
    ops_vs_lhp REAL,              -- vs 좌투 OPS
    ops_vs_rhp REAL,              -- vs 우투 OPS
    ops_risp REAL,                -- 득점권 OPS
    ops_home REAL,                -- 홈 OPS
    ops_away REAL,                -- 원정 OPS
    -- 메타
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season)
);
CREATE INDEX idx_bseason_player ON batter_season(player_id, season);
```

#### pitcher_season (시즌 누적 + 세이버메트릭스)
```sql
CREATE TABLE pitcher_season (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    season INTEGER NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    -- 누적 클래식
    games INTEGER, wins INTEGER, losses INTEGER, saves INTEGER, holds INTEGER,
    ip_outs INTEGER,              -- 이닝 (아웃 카운트)
    hits_allowed INTEGER, hr_allowed INTEGER, bb_allowed INTEGER,
    hbp_allowed INTEGER, so_count INTEGER, runs_allowed INTEGER, er INTEGER,
    -- 계산 클래식
    era REAL,
    whip REAL,
    -- 세이버메트릭스
    fip REAL,
    xfip REAL,
    war REAL,
    babip REAL,
    lob_pct REAL,
    k_per_9 REAL,
    bb_per_9 REAL,
    hr_per_9 REAL,
    k_bb_ratio REAL,
    -- 스플릿 누적
    era_vs_lhb REAL,              -- vs 좌타 ERA
    era_vs_rhb REAL,              -- vs 우타 ERA
    era_home REAL,
    era_away REAL,
    -- 메타
    is_starter BOOLEAN,           -- 선발/불펜 구분
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, season)
);
CREATE INDEX idx_pseason_player ON pitcher_season(player_id, season);
```

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
    pitched_yesterday BOOLEAN DEFAULT FALSE,  -- 전날 등판 여부
    UNIQUE(game_id, team_id, player_id)
);
CREATE INDEX idx_lineups_game ON lineups(game_id, team_id);
```

#### cheer_songs
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
CREATE INDEX idx_cheers_team ON cheer_songs(team_id);
```

---

## 3. API 엔드포인트

### Base URL: `/api/v1`

### 탐색기 (REQ-01) — 핵심

| Method | Path | 설명 | 쿼리 파라미터 |
|--------|------|------|-------------|
| GET | `/explorer` | 복합 조건 질의 | target, condition, stat, sort, limit |

**쿼리 파라미터 상세:**
```
target: batter | pitcher | pitcher_starter | pitcher_bullpen | team
condition: all | vs_lhb | vs_rhb | vs_lhp | vs_rhp | risp | bases_loaded |
           no_runners | inning_1_3 | inning_4_6 | inning_7_9 |
           home | away | weekday | weekend | night | day |
           leading | tied | trailing | vs_team:{team_id}
stat: (대상에 따라 다름 — requirements 참고)
sort: desc | asc
limit: 5 | 10 | 20 | all
season: 2025 (기본값: 현재 시즌)
```

**응답 예시:**
```json
{
  "query": {
    "target": "batter",
    "condition": "risp",
    "stat": "ops",
    "sort": "desc",
    "limit": 5
  },
  "results": [
    {
      "rank": 1,
      "player_id": 101,
      "player_name": "김도영",
      "team_name": "KIA",
      "primary_stat": 1.145,
      "secondary_stats": {
        "avg": 0.328,
        "hr": 32,
        "rbi": 105
      }
    }
  ],
  "total_count": 5
}
```

### 선수 (REQ-02, REQ-06)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/players/search` | 선수 검색 (자동완성) — ?q=김도&limit=10 |
| GET | `/players/{id}` | 선수 프로필 + 시즌 기록 |
| GET | `/players/{id}/classic` | 클래식 스탯 탭 |
| GET | `/players/{id}/sabermetrics` | 세이버메트릭스 탭 |
| GET | `/players/{id}/splits` | 스플릿 탭 |
| GET | `/players/list` | 선수 목록 (기록 조회) — ?team_id=&position=&season= |

### 팀/순위 (REQ-03)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/teams/standings` | 팀 순위표 — ?season= |
| GET | `/teams/comparison` | 팀스탯 종합 비교 카드 4개 |
| GET | `/teams/{id}` | 팀 상세 정보 |
| GET | `/rankings/top` | 주요 지표별 선수 TOP5 — ?stat=&limit= |

### 일정/결과 (REQ-04)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/games/today` | 오늘 경기 목록 |
| GET | `/games/date/{date}` | 특정 날짜 경기 — date=2025-10-22 |
| GET | `/games/{id}` | 경기 상세 (스코어보드, 박스스코어) |
| GET | `/games/{id}/preview` | 선발투수 프리뷰 |
| GET | `/games/calendar` | 월간 캘린더 — ?year=&month= |

### 라인업 (REQ-05)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/games/{id}/lineups` | 경기별 풀 라인업 (선발+불펜+벤치) |

### 이색 통계 / 핫콜드 (REQ-07, REQ-08)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/fun-stats` | 이색 통계 카드 목록 |
| GET | `/hot-cold` | 핫/콜드 선수 TOP5 |

### 응원가 (REQ-11)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/cheer-songs` | 응원가 목록 — ?team_id= |

### SNS 허브 (REQ-12)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/sns/teams` | 구단별 SNS 링크 |
| GET | `/sns/teams/{id}/youtube` | 구단 유튜브 최신 영상 |

### 커뮤니티/직관로그 (REQ-09, REQ-10) — 3순위

| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/register` | 회원가입 |
| POST | `/auth/login` | 로그인 |
| GET | `/posts` | 게시글 목록 — ?board=&page= |
| POST | `/posts` | 게시글 작성 |
| GET | `/posts/{id}` | 게시글 상세 |
| POST | `/game-logs` | 직관 기록 추가 |
| GET | `/game-logs/my` | 내 직관 통계 |

---

## 4. 동적 SQL 빌더 (탐색기 핵심 로직)

탐색기(REQ-01)의 핵심은 드롭다운 조합을 SQL WHERE절로 변환하는 것이다.

### 설계 원칙
- f-string SQL 금지 — 반드시 파라미터 바인딩
- SQLAlchemy Core 사용 (ORM보다 동적 쿼리에 적합)
- 조건별 WHERE 절을 함수로 분리 → 조합

### 의사 코드
```python
def build_explorer_query(target, condition, stat, sort, limit):
    # 1. 기본 테이블 선택
    if target == "batter":
        base = select(batter_season, players, teams)
    elif target in ("pitcher", "pitcher_starter", "pitcher_bullpen"):
        base = select(pitcher_season, players, teams)
    elif target == "team":
        base = select(teams, ...)

    # 2. 조건 WHERE절 추가
    query = apply_condition(base, target, condition)

    # 3. 정렬 + 제한
    query = query.order_by(stat_column(stat, sort))
    if limit != "all":
        query = query.limit(int(limit))

    return query

def apply_condition(query, target, condition):
    """조건별 WHERE절을 동적으로 추가"""
    if condition == "vs_lhp":
        # 경기별 스탯에서 상대 투수 좌투인 경우만 필터
        query = query.where(batter_stats.c.opponent_pitcher_hand == "좌투")
    elif condition == "risp":
        query = query.where(batter_stats.c.runners_on_scoring == True)
    elif condition == "home":
        query = query.where(batter_stats.c.is_home == True)
    elif condition == "night":
        query = query.join(games).where(games.c.is_night_game == True)
    # ... 조건별 분기
    return query
```

### 조건 → SQL 매핑

| 조건 | WHERE절 |
|-----|---------|
| vs_lhb | batter_stats.opponent_pitcher_hand = '좌투' |
| vs_rhb | batter_stats.opponent_pitcher_hand = '우투' |
| risp | batter_stats.runners_on_scoring = TRUE |
| home | batter_stats.is_home = TRUE |
| away | batter_stats.is_home = FALSE |
| night | games.is_night_game = TRUE |
| inning_1_3 | batter_stats.inning BETWEEN 1 AND 3 |
| leading | batter_stats.score_diff > 0 |
| tied | batter_stats.score_diff = 0 |
| trailing | batter_stats.score_diff < 0 |
| vs_team:{id} | games.away_team_id = {id} OR games.home_team_id = {id} |

---

## 5. 세이버메트릭스 계산 엔진

### 계산 공식 (FanGraphs Library + KBO 리그 상수)

#### 타자 지표

```python
# wOBA (Weighted On-Base Average)
# KBO 리그 상수는 시즌별로 KBReport STAT Dic에서 가져옴
def calc_woba(bb, hbp, singles, doubles, triples, hr, ab, sf):
    # 리그 상수 (예시 — 시즌별 조정 필요)
    w_bb, w_hbp, w_1b, w_2b, w_3b, w_hr = 0.69, 0.72, 0.89, 1.27, 1.62, 2.10
    numerator = (w_bb*bb + w_hbp*hbp + w_1b*singles +
                 w_2b*doubles + w_3b*triples + w_hr*hr)
    denominator = ab + bb - ibb + sf + hbp
    return numerator / denominator if denominator > 0 else 0

# wRC+ (Weighted Runs Created Plus)
def calc_wrc_plus(woba, league_woba, woba_scale, rppa, league_rpw):
    wrc = ((woba - league_woba) / woba_scale + rppa) * pa
    wrc_plus = (wrc / pa) / (league_runs / league_pa) * 100
    return wrc_plus

# BABIP
def calc_babip(hits, hr, ab, so, sf):
    return (hits - hr) / (ab - so - hr + sf) if (ab - so - hr + sf) > 0 else 0

# ISO (순장타율)
def calc_iso(slg, avg):
    return slg - avg
```

#### 투수 지표

```python
# FIP (Fielding Independent Pitching)
def calc_fip(hr, bb, hbp, so, ip, fip_constant):
    # fip_constant는 시즌별 KBO 리그 상수
    return ((13*hr + 3*(bb+hbp) - 2*so) / ip) + fip_constant

# xFIP (Expected FIP)
def calc_xfip(hr, fb, bb, hbp, so, ip, fip_constant, league_hr_fb_rate):
    expected_hr = fb * league_hr_fb_rate
    return ((13*expected_hr + 3*(bb+hbp) - 2*so) / ip) + fip_constant

# ⚠️ xFIP: FB(플라이볼) 데이터 미수집 — MVP에서는 None 반환
# ⚠️ WAR: 수비(UZR)/구장(Park Factor) 보정 제외 — UI에 "간소화 WAR" 표시 필요

# K/9, BB/9, HR/9
def calc_per_9(count, ip):
    return (count * 9) / ip if ip > 0 else 0
```

### table2 타석 결과 파서

KBO 박스스코어 API(GetBoxScoreScroll)의 arrHitter 응답에는 3개 테이블이 있다:
- table1: [타순, 포지션, 선수명]
- table2: [1회 결과, 2회 결과, ..., 9회 결과] — 이닝별 타석 결과 코드
- table3: [타수, 안타, 타점, 득점, 타율] — 요약 (5개 컬럼만)

**table3만으로는 2B/3B/HR/BB/HBP/SO/SF/GDP를 알 수 없다.**
table2의 타석 결과 코드를 파싱하여 상세 기록을 추출한다.

코드 체계: [위치][결과]
- 위치: 좌, 우, 중, 좌중, 우중, 유, 1, 2, 3, 투, 포
- 결과: 안(1B), 2(2B), 3(3B), 홈(HR), 비(플라이), 땅(그라운드) 등

주요 매핑:
| 코드 패턴 | 분류 | 예시 |
|-----------|------|------|
| *홈 | HR | 좌홈, 우중홈 |
| (좌\|우\|중\|좌중\|우중)3 | 3B | 우3, 좌중3 |
| (좌\|우\|중\|좌중\|우중)2 | 2B | 좌2, 우중2 |
| *안 | 1B | 좌안, 우중안, 투안 |
| 4구 | BB | |
| 고4 | IBB | |
| 사구 | HBP | |
| 삼진, 스낫 | SO | |
| *희비 | SF | 우희비, 좌희비 |
| *희번, *희선 | SH | 투희번, 포희선 |
| *병 | GDP | 유병, 2병 |

복합 타석: "4구<br />/ 투땅" → 첫 번째 결과만 해당 타자 기록.

구현: `src/data/processors/at_bat_parser.py`

### 리그 상수 관리
```sql
CREATE TABLE league_constants (
    season INTEGER PRIMARY KEY,
    woba_scale REAL,
    league_woba REAL,
    league_wrc REAL,
    fip_constant REAL,
    league_hr_fb_rate REAL,
    rppa REAL,                    -- runs per plate appearance
    league_rpw REAL               -- runs per win
);
```

---

## 6. 프론트엔드 컴포넌트 구조

```
src/
├── App.jsx                 # 라우터 설정
├── components/
│   ├── layout/
│   │   ├── Navbar.jsx      # 상단 네비게이션
│   │   └── Footer.jsx
│   ├── common/
│   │   ├── StatTable.jsx   # 공용 테이블 (정렬, 클릭 등)
│   │   ├── BarChart.jsx    # Chart.js 막대 그래프 래퍼
│   │   ├── LineChart.jsx   # Chart.js 라인 그래프 래퍼
│   │   ├── PlayerLink.jsx  # 선수 이름 클릭 → 세부정보
│   │   ├── TeamBadge.jsx   # 팀 로고/이니셜
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorMessage.jsx
│   ├── explorer/           # ① 탐색기
│   │   ├── ExplorerPage.jsx
│   │   ├── DropdownBar.jsx     # 5단 드롭다운
│   │   ├── ResultTable.jsx     # 결과 테이블
│   │   └── ResultChart.jsx     # 결과 차트
│   ├── player/             # ② 선수 세부정보
│   │   ├── PlayerPage.jsx
│   │   ├── PlayerHeader.jsx    # 프로필 헤더
│   │   ├── ClassicTab.jsx
│   │   ├── SaberTab.jsx
│   │   ├── SplitsTab.jsx
│   │   └── PlayerSearch.jsx    # 검색 + 자동완성
│   ├── standings/          # ③ 순위
│   │   ├── StandingsPage.jsx
│   │   ├── TeamRankTable.jsx
│   │   ├── TeamCompareCards.jsx
│   │   └── PlayerRankings.jsx
│   ├── schedule/           # ④ 일정/결과
│   │   ├── SchedulePage.jsx
│   │   ├── GameCard.jsx
│   │   ├── StarterPreview.jsx
│   │   └── CalendarView.jsx
│   ├── lineup/             # ⑤ 풀 라인업
│   │   ├── LineupPage.jsx
│   │   ├── StarterList.jsx
│   │   ├── BullpenList.jsx
│   │   └── BenchList.jsx
│   └── records/            # ⑥ 기록 조회
│       ├── RecordsPage.jsx
│       └── SaberToggle.jsx     # 클래식 ↔ 세이버 토글
├── hooks/
│   ├── useExplorer.js      # 탐색기 API 호출
│   ├── usePlayer.js        # 선수 데이터
│   ├── useStandings.js     # 순위 데이터
│   ├── useSchedule.js      # 일정 데이터
│   └── useApi.js           # 공용 API 호출 (로딩/에러 처리)
├── utils/
│   ├── formatStat.js       # 수치 포맷 (.328, 3.45 등)
│   └── constants.js        # 드롭다운 옵션 값 등
└── styles/
```

### 페이지 라우팅
```
/                  → 홈 (오늘 경기 + 순위 요약)
/explorer          → ① 탐색기
/players/:id       → ② 선수 세부정보
/standings         → ③ 순위
/schedule          → ④ 일정/결과
/schedule/:gameId  → 경기 상세
/lineup/:gameId    → ⑤ 풀 라인업
/records           → ⑥ 기록 조회
/fun-stats         → ⑦ 이색 통계 (3순위)
/cheer-songs       → ⑪ 응원가 (3순위)
/sns               → ⑫ SNS 허브 (3순위)
```

---

## 7. 데이터 수집 파이프라인 구조

```
src/data/
├── collectors/
│   ├── kbo_data_collector.py     # kbo-data 라이브러리 래퍼
│   ├── kbo_web_scraper.py        # KBO 홈페이지 직접 크롤링
│   └── kbreport_scraper.py       # KBReport 크롤링 (리그 상수 등)
├── processors/
│   ├── data_cleaner.py           # 데이터 정제 (결측값, 타입 변환)
│   ├── at_bat_parser.py          # table2 타석 결과 코드 파서 (신규)
│   └── sabermetrics_engine.py    # 세이버메트릭스 계산 엔진
├── loaders/
│   └── db_loader.py              # DB 저장 (upsert 로직)
├── batch/
│   └── daily_update.py           # 매일 배치 실행 스크립트
└── tests/
    ├── test_sabermetrics.py      # 계산 정확도 테스트
    └── test_collector.py         # 수집 동작 테스트
```

### 배치 실행 흐름
```
daily_update.py 실행
  ├── 1. 오늘 경기 결과 수집 (kbo_data_collector)
  ├── 2. 박스스코어/라인업 수집 (kbo_web_scraper)
  ├── 3. 데이터 정제 (data_cleaner)
  ├── 4. DB 저장 (db_loader — upsert)
  ├── 5. 시즌 누적 재계산 (sabermetrics_engine)
  ├── 6. 핫/콜드 선수 갱신
  └── 7. 실행 로그 기록
```

---

## 8. 구현 순서 (tasks 사전 정의)

### Phase 1: 기반 (1~2주)
1. 프로젝트 초기화 (React + FastAPI + SQLite)
2. DB 스키마 생성 (위 SQL 실행)
3. 데이터 수집 파이프라인 구축 + 초기 데이터 적재
4. 세이버메트릭스 계산 엔진 + TDD 테스트

### Phase 2: MVP 백엔드 (1~2주)
5. 동적 SQL 빌더 구현
6. 탐색기 API (`/api/v1/explorer`)
7. 선수 API (검색, 상세, 3탭)
8. 순위 API (팀 순위, 팀스탯 비교, 선수 TOP5)

### Phase 3: MVP 프론트 (1~2주)
9. 레이아웃 (Navbar, 라우팅)
10. 탐색기 페이지 (드롭다운 + 테이블 + 차트)
11. 선수 세부정보 페이지 (3탭)
12. 순위 페이지

### Phase 4: 통합 + 배포 (1주)
13. 프론트-백엔드 통합 테스트
14. Render 배포
15. 버그 수정 + 성능 튜닝

---

> 이 문서는 steering.md의 원칙과 requirements.md의 요구사항을 기반으로 작성되었습니다.
> 구현 시 AI 에이전트에게 이 문서를 @file:design.md로 참조시킵니다.
> 구현 중 설계 변경이 필요하면 이 문서를 먼저 수정하고, 코드에 반영합니다.
