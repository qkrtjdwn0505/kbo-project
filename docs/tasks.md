# KBO 데이터 대시보드 — Tasks (작업 분해)

> 상위 문서: steering.md → requirements.md → design.md → 이 문서
> 이 문서는 design.md의 구현 순서를 구체적인 작업 단위로 분해합니다.
> 각 작업은 에이전트에게 1회 지시로 완료 가능한 크기입니다.
> 체크박스로 진행 상황을 추적합니다.
> 최종 수정일: 2026-03-18

---

## Phase 1: 기반 구축 ✅ 완료

### T-1.1 프로젝트 초기화
- [x] FastAPI 프로젝트 생성 (main.py, requirements.txt)
- [x] React 프로젝트 생성 (Vite)
- [x] 프로젝트 디렉토리 구조 생성
- [x] .gitignore 설정 (.env, node_modules/, __pycache__/)
- [x] Git 초기화 + GitHub 연결 (qkrtjdwn0505/kbo-project)
- [x] ADF 파일 배치 (adf/ 디렉토리)

**기술 스택 확정:** React 19 + Vite + Chart.js / FastAPI + SQLAlchemy / SQLite (kbo.db)

### T-1.2 DB 스키마 생성
- [x] SQLite DB 파일 생성 (kbo.db)
- [x] teams 테이블 + 10개 구단 초기 데이터
- [x] players, games, batter_stats, pitcher_stats 테이블
- [x] batter_season, pitcher_season 테이블
- [x] lineups 테이블
- [x] league_constants 테이블
- [x] games 테이블에 game_type 컬럼 추가 (preseason/regular/postseason)

### T-1.3 데이터 수집 파이프라인
- [x] kbo_data_collector.py — KBO API 연동 (GetKboGameList, GetBoxScoreScroll)
- [x] kbo_schedule_collector.py — 일정 수집
- [x] kbo_season_stats_scraper.py — KBO 기록실 크롤링 (도루 sb/cs 보강)
- [x] kbo_situation_scraper.py — 기록실 상황별탭 (ops_risp, avg_vs_lhb/rhb 보강)
- [x] 수집 결과 → DB 저장 (upsert)

**참고:** KBO 박스스코어 API에 도루(sb/cs) 없음 → 기록실 크롤링으로만 보강

### T-1.4 초기 데이터 벌크 적재
- [x] collect_season.py — 시즌 전체 수집 스크립트
- [x] collect_missing.py — 누락 경기 보충 스크립트
- [x] 2025 시즌: preseason 42 + regular 720 + postseason 16 = 768경기 수집 완료
- [x] season_aggregator.py — 경기별 → 시즌 누적 집계 (game_type='regular'만)

**데이터 파이프라인 주의사항:**
- season_aggregator 재실행 시 sb/cs가 COALESCE로 보존됨 (도루 덮어쓰기 방지)
- kbo.db를 Git에 포함 (~8MB) → Render 배포 시 자동 포함. DB 변경 후 반드시 `git add kbo.db` + push

### T-1.5 세이버메트릭스 계산 엔진
- [x] sabermetrics_engine.py — wOBA, wRC+, BABIP, ISO, BB%, K%, FIP, xFIP, K/9, BB/9, HR/9, WAR
- [x] calc_league_constants.py — 리그 상수 자체 계산 (FIP상수 3.44, league_wOBA 0.338)
- [x] 167개 데이터 테스트 통과 (세이버 53 + 타석파서 113 + 단일경기 1)

**알려진 이슈:** 파크팩터 미반영으로 wRC+/WAR가 STATIZ 기준과 차이남. 클래식 지표 + wOBA는 정확.

---

## Phase 2: MVP 백엔드 ✅ 완료

### T-2.1 FastAPI 기본 설정
- [x] CORS 설정
- [x] DB 세션 의존성 주입
- [x] API 라우터 분리 (explorer, players, teams, games)
- [x] Pydantic 응답 모델 정의

### T-2.2 동적 SQL 빌더
- [x] 경로 A: condition=all → batter_season/pitcher_season 시즌 테이블 직접 조회
- [x] 경로 B: 조건 필터 → 경기별 스탯 집계 + Python 세이버 재계산
- [x] 주요 조합 테스트 통과

### T-2.3 탐색기 API
- [x] GET `/api/v1/explorer` — 복합 조건 질의

### T-2.4 선수 API
- [x] GET `/api/v1/players/search` — 자동완성
- [x] GET `/api/v1/players/{id}/classic` — 클래식 스탯
- [x] GET `/api/v1/players/{id}/sabermetrics` — 세이버 스탯
- [x] GET `/api/v1/players/{id}/splits` — 스플릿
- [x] GET `/api/v1/players/records` — 기록 조회 (전체 선수 테이블)

### T-2.5 순위 API
- [x] GET `/api/v1/standings` — 팀 순위표
- [x] GET `/api/v1/standings/comparison` — 팀스탯 비교 카드
- [x] GET `/api/v1/rankings/top` — 주요 지표별 TOP5
- [x] GET `/api/v1/standings/seasons` — 시즌 목록

### T-2.6 일정/경기 API
- [x] GET `/api/v1/games/dates` — 월간 경기 일자
- [x] GET `/api/v1/games/schedule` — 날짜별 경기 목록
- [x] GET `/api/v1/games/{id}/detail` — 경기 상세 (스코어보드)
- [x] GET `/api/v1/games/{id}/lineups` — 라인업

**백엔드 총 103개 API 테스트 통과**

---

## Phase 3: MVP 프론트엔드 ✅ 완료

### T-3.1 레이아웃 + 라우팅
- [x] Navbar (홈 | 탐색기 | 순위 | 일정 | 기록)
- [x] React Router 설정
- [x] 공통 스타일

### T-3.2 탐색기 페이지 (핵심)
- [x] ExplorerPage.jsx — 5단 드롭다운 + 결과 테이블 + 차트
- [x] 대상 변경 시 지표 드롭다운 동적 변경
- [x] 선수 이름 클릭 → /players/:id 이동

### T-3.3 선수 세부정보 페이지
- [x] PlayerPage.jsx — 검색 + 프로필 헤더 + 3탭 (클래식/세이버/스플릿)
- [x] 자동완성 검색

### T-3.4 순위 페이지
- [x] StandingsPage.jsx — 팀 순위 + 팀스탯 카드 + 선수 TOP5

### T-3.5 홈 페이지
- [x] Home.jsx — 순위 요약 + 탐색기 바로가기

---

## Phase 4: 통합 + 배포 ✅ 완료

### T-4.1 빌드 통합
- [x] FastAPI에서 React 빌드 정적 파일 서빙
- [x] `npm run build` → FastAPI static files 연결

### T-4.2 Render 배포
- [x] Render 무료 티어 배포 (https://kbo-dashboard.onrender.com)
- [x] Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [x] UptimeRobot 5분 핑 설정
- [x] Public Git 연결 → auto-deploy 안됨, Manual Deploy 필요

### T-4.3 배치 자동화
- [x] daily_update.py 완성 — `python -m src.data.batch.daily_update --season 2026`

---

## Phase 5: 2순위 기능 ✅ 완료

### T-5.1 일정/결과
- [x] SchedulePage.jsx — 캘린더 + 날짜별 경기 카드
- [x] 스코어보드 상세 (이닝별 점수)
- [x] 라인업 탭

### T-5.2 기록 조회
- [x] RecordsPage.jsx — 전체 선수 테이블
- [x] 클래식 ↔ 세이버 토글
- [x] 페이지네이션

**Phase 1~5 총 270개 테스트 통과**

---

## Phase 5.5: 2026 시즌 개막 준비 🔧 진행중

### T-5.5.1 데이터 준비
- [x] 2026 시범경기 60경기 박스스코어 수집 완료
- [x] 2026 정규시즌 일정 675경기 DB 저장 완료
- [x] get_latest_season()이 MAX(season) 반환 → 2026 데이터 들어오면 자동 전환

### T-5.5.2 live_game_poller (실시간 경기 추적)
- [x] live_game_poller.py 작성 완료 — 경기 중 30초 폴링, at_bat_situations 테이블에 주자/점수/이닝 저장
- [ ] **개막일(3/28) 실전 테스트** — `--daemon`으로 실행, B_P_NM/T_P_NM 필드가 실제 타자/투수인지 로그 검증

### T-5.5.3 세이버 면책문구
- [x] 프론트 세이버메트릭스 표시 영역에 면책문구 추가 (SaberDisclaimer.jsx → SaberTab에 적용)

### T-5.5.4 모바일 UI 개선
- [ ] 탐색기 드롭다운 모바일 대응
- [ ] 테이블 가로 스크롤 처리
- [ ] Navbar 모바일 메뉴

---

## Phase 6: 3순위 기능 (예상 5~7주)

### T-6.1 이색 통계 + 핫/콜드 (REQ-07, REQ-08)
- [ ] 이색 통계 카드 SQL 쿼리 10개 작성
- [ ] 핫/콜드 계산 로직 (시즌 vs 최근 N경기 차이)
- [ ] GET `/api/v1/fun-stats` API
- [ ] GET `/api/v1/hot-cold` API
- [ ] FunStatsPage.jsx + HotColdSection.jsx

### T-6.2 응원가 (REQ-11)
- [ ] cheer_songs 데이터 수동 입력 (~110개 항목)
- [ ] GET `/api/v1/cheer-songs` API
- [ ] CheerSongsPage.jsx (구단별 탭 + 유튜브 임베드)

### T-6.3 SNS 허브 (REQ-12)
- [ ] player_sns, team_sns 데이터 수동 입력
- [ ] GET `/api/v1/sns/teams` API
- [ ] SNSHubPage.jsx
- [ ] 선수 세부정보 헤더에 SNS 아이콘 연결

### T-6.4 커뮤니티 + 직관로그 (REQ-09, REQ-10)
- [ ] users 테이블 + 인증 시스템 (JWT)
- [ ] posts 테이블 + CRUD API
- [ ] game_logs 테이블 + 직관 기록 API
- [ ] 직관 통계 계산 (승률, 구장별, 월별)
- [ ] CommunityPage.jsx + GameLogPage.jsx

---

## 미해결 이슈 (Backlog)

| 이슈 | 상태 | 비고 |
|------|------|------|
| 파크팩터 미반영 | 보류 | wRC+/WAR 차이 원인. 면책문구로 임시 대응 or 파크팩터 구현 |
| 구단 로고 | 보류 | KBO 저작권 엄격. 팬제작 SVG 아이콘이 안전한 대안 |
| 탐색기 risp/leading/trailing 조건 | 2026~ | play-by-play 데이터 의존. 2025는 기록실 시즌합산만 가능, 경기별은 2026 폴링부터 |
| play-by-play API | 확인완료 | KBO에 존재하지 않음. 폴링(live_game_poller)으로 대체 |

---

## 작업 진행 규칙

### 에이전트 지시 방법 (Claude Code)
```
지시문(.md)을 Claude.ai에서 작성 → Claude Code에서 구현
지시문에 @file로 참조파일 명시, 검증 SQL/assert 포함, 커밋 메시지 지정
```

### 커밋 규칙
- 각 T-번호 완료 시 커밋: "T-1.2: DB 스키마 생성 완료"
- Phase 완료 시 Git 태그

### 배포 규칙
- Render: push 후 Manual Deploy
- kbo.db 변경 시 반드시 `git add kbo.db` + push
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 검증 주의사항
- Claude Code가 가끔 잘못 수정하는 경우 있음 (README 경기수 768→720 사건)
- 검증 assert 필수

---

> 이 문서는 진행하면서 체크박스를 업데이트합니다.
> 작업 중 설계 변경이 필요하면 design.md를 먼저 수정하고, 이 문서에 반영합니다.
