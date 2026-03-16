# KBO 데이터 대시보드 — Tasks (작업 분해)

> 상위 문서: steering.md → requirements.md → design.md → 이 문서
> 이 문서는 design.md의 구현 순서를 구체적인 작업 단위로 분해합니다.
> 각 작업은 에이전트에게 1회 지시로 완료 가능한 크기입니다.
> 체크박스로 진행 상황을 추적합니다.
> 최종 수정일: 2026-03-16

---

## Phase 1: 기반 구축 (예상 1~2주)

### T-1.1 프로젝트 초기화
- [x] FastAPI 프로젝트 생성 (main.py, requirements.txt)
- [x] React 프로젝트 생성 (create-react-app 또는 Vite)
- [x] 프로젝트 디렉토리 구조 생성 (design.md 섹션 6의 구조대로)
- [x] .gitignore 설정 (.env, node_modules/, __pycache__/, *.db)
- [x] .env.example 파일 생성 (DB 경로 등)
- [x] Git 초기화 + 첫 커밋
- [x] ADF 파일 배치 (adf/ 디렉토리)

**완료 조건:** `uvicorn main:app --reload`로 FastAPI 서버 기동, `npm start`로 React 개발 서버 기동

### T-1.2 DB 스키마 생성
- [x] SQLite DB 파일 생성
- [x] teams 테이블 생성 + 10개 구단 초기 데이터 삽입
- [x] players 테이블 생성 + 인덱스
- [x] games 테이블 생성 + 인덱스
- [x] batter_stats 테이블 생성 + 인덱스
- [x] pitcher_stats 테이블 생성 + 인덱스
- [x] batter_season 테이블 생성 + 인덱스
- [x] pitcher_season 테이블 생성 + 인덱스
- [x] lineups 테이블 생성 + 인덱스
- [x] league_constants 테이블 생성
- [x] cheer_songs, player_sns, team_sns 테이블 생성
- [x] 스키마 생성 스크립트를 src/data/init_db.py로 정리

**완료 조건:** `python init_db.py` 실행 시 모든 테이블이 생성되고, teams에 10개 구단 데이터가 삽입됨

### T-1.3 데이터 수집 파이프라인 — kbo-data 연동
- [x] kbo-data 라이브러리 설치 + Chrome driver 확인
- [x] kbo_data_collector.py 작성 — 경기 스케줄 수집 함수
- [x] kbo_data_collector.py — 경기별 타자 기록 수집 함수
- [x] kbo_data_collector.py — 경기별 투수 기록 수집 함수
- [x] 수집 결과를 pandas DataFrame으로 변환하는 로직
- [x] 테스트: 특정 날짜 1경기 데이터 수집 → DataFrame 출력 확인

**완료 조건:** 지정한 날짜의 KBO 경기 데이터가 DataFrame으로 정상 반환됨

### T-1.4 데이터 수집 파이프라인 — DB 저장
- [x] db_loader.py 작성 — SQLAlchemy 엔진/세션 설정
- [x] db_loader.py — games 테이블 upsert 함수
- [x] db_loader.py — batter_stats 테이블 upsert 함수
- [x] db_loader.py — pitcher_stats 테이블 upsert 함수
- [x] db_loader.py — players 테이블 upsert 함수 (신규 선수 자동 추가)
- [x] data_cleaner.py — 결측값 처리, 컬럼명 매핑, 타입 변환
- [x] 통합 테스트: 수집 → 정제 → DB 저장 → DB 조회로 검증

**완료 조건:** 수집한 경기 데이터가 SQLite에 정상 저장되고, SELECT로 조회 가능

### T-1.5 초기 데이터 벌크 적재
- [x] 수집 범위 결정 (최소 현재 시즌 or 최근 N시즌)
- [x] 벌크 수집 스크립트 작성 (날짜 범위 지정 → 전체 수집)
- [x] 실행 + 에러 처리 (실패 시 재시도, 로그 기록)
- [x] 적재 후 데이터 건수 확인 (경기 수, 선수 수, 기록 수)

**완료 조건:** DB에 최소 1시즌 분량의 경기/타자/투수 데이터가 적재됨

### T-1.5b 데이터 수집 보강 — table2 파싱 + 재수집
> T-1.6 구현 중 발견: 현재 batter_stats에 2B/3B/HR/BB/SO가 전부 0.
> table3에 5개 컬럼(AB,H,RBI,R,AVG)만 있고, 상세 기록은 table2 파싱이 필요.
> 이 작업 없이는 세이버메트릭스가 동작하지 않음.

- [x] ibb 마이그레이션 실행
- [x] kbo_data_collector.py — get_boxscore()에서 table2 데이터 반환 포함
- [x] collect_season.py — transform_batters()에서 at_bat_parser 연동
- [ ] 투수 HBP 분리 (→ 후순위로 이동, 세이버메트릭스에 영향 미미)
- [x] 2025 시즌 데이터 재수집 (768경기)
- [x] 재수집 후 데이터 검증

**현재 상태:** 완료. 디아즈 AVG .314 공식과 일치, OPS ±0.004.

### T-1.6 세이버메트릭스 계산 엔진
- [x] sabermetrics_engine.py 작성 — wOBA 계산 함수
- [x] wRC+ 계산 함수
- [x] BABIP 계산 함수
- [x] ISO 계산 함수
- [x] BB%, K% 계산 함수
- [x] FIP 계산 함수
- [x] xFIP 계산 함수 (⚠️ FB 미수집으로 None 반환)
- [x] K/9, BB/9, HR/9 계산 함수
- [x] WAR 계산 함수 (⚠️ 간소화 버전 — 수비/구장 보정 제외)
- [ ] league_constants 테이블에 KBO 리그 상수 삽입 (기본값 사용 중)
- [x] batter_season, pitcher_season 테이블에 계산 결과 저장하는 함수
- [x] **TDD 테스트:** 161개 단위 테스트 통과
- [x] **크로스체크:** 디아즈 AVG .314 일치, OPS ±0.004, HR ±2 (경기 누락분)

**완료 조건 달성:** 클래식 스탯 공식과 거의 일치, 세이버메트릭스 합리적 범위 확인.

### Phase 1 알려진 이슈 (Phase 2 이후 수정)
- [ ] **hash() 비결정적 ID 버그**: game_id를 Python hash()로 생성하여 실행마다 달라짐 → hashlib.md5 등 결정적 해시로 교체 필요
- [ ] **투수 W/L/SV 미수집**: pitcher_stats.decision 컬럼이 파싱되지 않음 → kbo_data_collector.py 수정 필요
- [ ] **경기 누락 (~3경기)**: 중복 정리 시 일부 경기 손실 → hash 버그 수정 후 재수집으로 해결
- [ ] **투수 HBP 분리**: KBO API "4사구" = BB+HBP 합산 → 분리 로직 미구현
- [ ] **리그 상수 실측값**: league_constants에 기본값 사용 중 → KBReport에서 2025 실측값 확보 필요
- [ ] **xFIP**: FB(플라이볼) 데이터 미수집으로 None 반환
- [ ] **WAR 정밀도**: 수비(UZR), 구장 보정(Park Factor) 제외된 간소화 버전

---

## Phase 2: MVP 백엔드 (예상 1~2주)

### T-2.1 FastAPI 기본 설정
- [ ] CORS 설정 (프론트엔드 개발 서버 허용)
- [ ] DB 세션 의존성 주입 설정
- [ ] 에러 핸들러 (404, 500 공통 포맷)
- [ ] API 라우터 분리 (explorer, players, teams, games)
- [ ] Pydantic 응답 모델 정의 (design.md 응답 예시 기반)

**완료 조건:** `/docs`에서 Swagger UI 접근 가능, 빈 라우터가 등록됨

### T-2.2 동적 SQL 빌더 구현
- [ ] explorer/query_builder.py — build_explorer_query() 메인 함수
- [ ] apply_condition() — 조건별 WHERE절 함수 (vs_lhb, risp, home 등)
- [ ] stat_column() — 지표별 컬럼 매핑 함수
- [ ] 대상별 기본 쿼리 (타자/투수/팀)
- [ ] 정렬 + 제한 로직
- [ ] 보조 지표 2~3개 자동 선택 로직
- [ ] **테스트:** 주요 조합 10개에 대한 쿼리 실행 + 결과 검증

**완료 조건:** "타자 + 득점권 + OPS + 높은순 + 5명" 같은 조합이 정확한 결과 반환

### T-2.3 탐색기 API
- [ ] GET `/api/v1/explorer` 엔드포인트 구현
- [ ] 쿼리 파라미터 검증 (잘못된 조합 시 400 에러)
- [ ] 응답 포맷 (rank, player_name, team_name, primary_stat, secondary_stats)
- [ ] 대상 변경 시 가용 지표 목록 반환 API (드롭다운 동적 변경용)
- [ ] **테스트:** 5가지 대표 조합 API 호출 테스트

**완료 조건:** Swagger에서 탐색기 API 호출 시 정확한 JSON 응답

### T-2.4 선수 API
- [ ] GET `/api/v1/players/search` — 자동완성 (이름 LIKE 검색)
- [ ] GET `/api/v1/players/{id}` — 프로필 + 시즌 기본 정보
- [ ] GET `/api/v1/players/{id}/classic` — 클래식 스탯
- [ ] GET `/api/v1/players/{id}/sabermetrics` — 세이버 스탯
- [ ] GET `/api/v1/players/{id}/splits` — 스플릿 (vs좌/우, 홈/원정, 득점권)
- [ ] GET `/api/v1/players/list` — 선수 목록 (팀/포지션/시즌 필터)

**완료 조건:** 김도영 검색 → 프로필 + 3탭 데이터가 모두 정확히 반환

### T-2.5 순위 API
- [ ] GET `/api/v1/teams/standings` — 팀 순위표 (승/패/무/승률/게임차)
- [ ] GET `/api/v1/teams/comparison` — 팀스탯 비교 카드 4개
- [ ] GET `/api/v1/rankings/top` — 주요 지표별 선수 TOP5

**완료 조건:** 팀 순위가 공식 순위와 일치, 팀스탯 카드 4개가 정확한 팀/수치 반환

### T-2.6 최근 5경기 흐름 계산
- [ ] 팀 순위에 최근 5경기 승패 배열 추가
- [ ] 연승/연패 계산 로직

**완료 조건:** 순위 API 응답에 recent_5 필드가 ["W","W","L","W","L"] 형태로 포함

---

## Phase 3: MVP 프론트엔드 (예상 1~2주)

### T-3.1 레이아웃 + 라우팅
- [ ] Navbar 컴포넌트 (로고 + 메뉴: 홈, 탐색기, 선수, 순위)
- [ ] React Router 설정 (/, /explorer, /players/:id, /standings)
- [ ] Footer 컴포넌트 (데이터 출처 표기)
- [ ] 공통 스타일 설정 (폰트, 색상, 반응형 기본)

**완료 조건:** 모든 라우트가 동작하고, Navbar에서 페이지 전환 가능

### T-3.2 공통 컴포넌트
- [ ] useApi.js — 공용 API 호출 훅 (로딩/에러/데이터 상태)
- [ ] formatStat.js — 수치 포맷 유틸 (.328, 3.45, 7.2)
- [ ] StatTable.jsx — 공용 테이블 (헤더 클릭 정렬, 선수 클릭 링크)
- [ ] BarChart.jsx — Chart.js 막대 그래프 래퍼
- [ ] PlayerLink.jsx — 선수 이름 클릭 → /players/:id
- [ ] LoadingSpinner.jsx
- [ ] ErrorMessage.jsx

**완료 조건:** StatTable에 더미 데이터 넣어서 정렬/클릭 동작 확인

### T-3.3 탐색기 페이지 (핵심)
- [ ] ExplorerPage.jsx — 전체 레이아웃
- [ ] DropdownBar.jsx — 5단 드롭다운 (대상→조건→지표→정렬→범위)
- [ ] 대상 변경 시 지표 드롭다운 동적 변경 로직
- [ ] useExplorer.js — 탐색기 API 호출 훅
- [ ] ResultTable.jsx — 결과 테이블 (순위, 선수, 팀, 지표)
- [ ] ResultChart.jsx — Chart.js 막대 그래프
- [ ] 현재 질의 요약 표시 ("타자 · 득점권 · OPS · 높은순 · 5명")
- [ ] 결과 없음 메시지 처리
- [ ] 선수 이름 클릭 → /players/:id 이동

**완료 조건:** 드롭다운 5개 조합 → API 호출 → 테이블 + 차트가 2초 이내 표시

### T-3.4 선수 세부정보 페이지
- [ ] PlayerPage.jsx — 전체 레이아웃
- [ ] PlayerSearch.jsx — 검색창 + 자동완성 (2글자 이상, 300ms 디바운스)
- [ ] PlayerHeader.jsx — 이니셜 아바타, 이름, 팀, 포지션, 등번호, SNS 아이콘
- [ ] 탭 전환 UI (클래식 / 세이버메트릭스 / 스플릿)
- [ ] ClassicTab.jsx — 클래식 스탯 그리드
- [ ] SaberTab.jsx — 세이버메트릭스 스탯 그리드
- [ ] SplitsTab.jsx — vs좌/우, 홈/원정, 득점권 비교 표시
- [ ] usePlayer.js — 선수 데이터 API 호출 훅

**완료 조건:** 김도영 검색 → 프로필 헤더 + 3탭 전환 동작, 모든 수치 정확히 포맷됨

### T-3.5 순위 페이지
- [ ] StandingsPage.jsx — 전체 레이아웃
- [ ] TeamRankTable.jsx — 팀 순위 테이블 (최근5경기 흐름 포함)
- [ ] TeamCompareCards.jsx — 공격력/투수력/수비력/주루 1위 카드 4개
- [ ] PlayerRankings.jsx — 주요 지표별 TOP5
- [ ] useStandings.js — 순위 API 호출 훅

**완료 조건:** 팀 순위 + 팀스탯 카드 + 선수 TOP5가 한 페이지에 표시

### T-3.6 홈 페이지
- [ ] 오늘 경기 요약 (일정 API 미구현 시 순위 요약으로 대체)
- [ ] 탐색기 바로가기 카드
- [ ] 핫/콜드 선수 미리보기 (데이터 있는 경우)

**완료 조건:** 홈에서 주요 페이지로 진입 가능

---

## Phase 4: 통합 + 배포 (예상 1주)

### T-4.1 프론트-백엔드 통합
- [ ] FastAPI에서 React 빌드 정적 파일 서빙 설정
- [ ] `npm run build` → FastAPI static files 연결
- [ ] CORS 설정 최종 확인
- [ ] 전체 페이지 통합 테스트 (탐색기 → 선수 → 순위 흐름)

**완료 조건:** 단일 서버에서 프론트 + API가 모두 동작

### T-4.2 Render 배포
- [ ] Render 계정 생성 + 무료 티어 설정
- [ ] Dockerfile 또는 render.yaml 작성
- [ ] 환경 변수 설정 (Render 대시보드)
- [ ] 배포 + 동작 확인
- [ ] 커스텀 도메인 (선택)

**완료 조건:** https://xxx.onrender.com에서 서비스 접근 가능

### T-4.3 버그 수정 + 성능
- [ ] 느린 쿼리 식별 + 인덱스 최적화
- [ ] 프론트 로딩 속도 확인
- [ ] 모바일 기본 대응 확인
- [ ] 에러 케이스 처리 누락 확인

**완료 조건:** 주요 5개 시나리오가 2초 이내 응답, 에러 시 메시지 표시

### T-4.4 배치 자동화
- [ ] daily_update.py 완성 (T-1.3~1.6의 코드 조합)
- [ ] 실행 로그 기록
- [ ] 수동 실행 테스트 → 데이터 갱신 확인

**완료 조건:** `python daily_update.py` 실행 시 새 경기 데이터가 DB에 반영됨

---

## Phase 5: 2순위 기능 (예상 1.5~2주)

### T-5.1 일정/결과 (REQ-04)
- [ ] GET `/api/v1/games/today` API
- [ ] GET `/api/v1/games/date/{date}` API
- [ ] GET `/api/v1/games/{id}` API (스코어보드)
- [ ] GET `/api/v1/games/{id}/preview` API (선발투수 프리뷰)
- [ ] SchedulePage.jsx + GameCard.jsx
- [ ] StarterPreview.jsx (FIP 포함)
- [ ] CalendarView.jsx

### T-5.2 풀 라인업 (REQ-05)
- [ ] lineups 데이터 수집 추가 (kbo_web_scraper)
- [ ] GET `/api/v1/games/{id}/lineups` API
- [ ] LineupPage.jsx + StarterList/BullpenList/BenchList
- [ ] 전날 등판 여부 표시 로직

### T-5.3 기록 조회 (REQ-06)
- [ ] GET `/api/v1/players/list` API (필터 + 정렬 + 페이지네이션)
- [ ] RecordsPage.jsx
- [ ] SaberToggle.jsx (클래식 ↔ 세이버 컬럼 전환)

---

## Phase 6: 3순위 기능 (예상 5~7주)

### T-6.1 이색 통계 + 핫/콜드 (REQ-07, REQ-08)
- [ ] 이색 통계 카드 SQL 쿼리 10개 작성
- [ ] 핫/콜드 계산 로직 (시즌 vs 최근 N경기 차이)
- [ ] GET `/api/v1/fun-stats` API
- [ ] GET `/api/v1/hot-cold` API
- [ ] FunStatsPage.jsx + HotColdSection.jsx

### T-6.2 응원가 (REQ-11)
- [ ] cheer_songs 데이터 수동 입력 (110개 항목)
- [ ] GET `/api/v1/cheer-songs` API
- [ ] CheerSongsPage.jsx (구단별 탭 + 유튜브 임베드)

### T-6.3 SNS 허브 (REQ-12)
- [ ] player_sns, team_sns 데이터 수동 입력
- [ ] GET `/api/v1/sns/teams` API
- [ ] GET `/api/v1/sns/teams/{id}/youtube` API (YouTube Data API)
- [ ] SNSHubPage.jsx
- [ ] 선수 세부정보 헤더에 SNS 아이콘 연결

### T-6.4 커뮤니티 + 직관로그 (REQ-09, REQ-10)
- [ ] users 테이블 + 인증 시스템 (JWT)
- [ ] POST `/api/v1/auth/register`, `/auth/login`
- [ ] posts 테이블 + CRUD API
- [ ] game_logs 테이블 + 직관 기록 API
- [ ] 직관 통계 계산 (승률, 구장별, 월별)
- [ ] CommunityPage.jsx + GameLogPage.jsx

---

## 작업 진행 규칙

### 에이전트에게 지시하는 방법
```
"@file:design.md의 T-2.2 동적 SQL 빌더를 구현해줘.
@file:requirements.md의 REQ-01 Acceptance Criteria를 만족하도록.
@file:adf/03_guidelines/common/code.md의 Python 규칙을 따라."
```

### 커밋 규칙
- 각 T-번호 완료 시 커밋
- 커밋 메시지: "T-1.2: DB 스키마 생성 완료"
- Phase 완료 시 Git 태그: "phase-1-complete"

### 검증 규칙
- Phase 1 완료 후: 데이터 수집 + 세이버 계산 정확도 검증
- Phase 2 완료 후: Swagger에서 모든 API 동작 확인
- Phase 3 완료 후: 브라우저에서 전체 흐름 테스트
- Phase 4 완료 후: Render 배포 URL에서 동작 확인

---

> 이 문서는 진행하면서 체크박스를 업데이트합니다.
> 작업 중 설계 변경이 필요하면 design.md를 먼저 수정하고, 이 문서에 반영합니다.
> 새로운 작업이 발견되면 해당 Phase에 추가합니다.
