# KBO 데이터 대시보드 — AI 에이전트 지침

> 이 문서는 모든 AI 코딩 도구 (Claude Code, Cursor Agent 등)가 참조하는 Entry Point입니다.
> 경합이 있는 경우, 상위 섹션이 우선됩니다.

---

## 프로젝트 개요

- 프로젝트명: KBO 데이터 대시보드
- 한 줄 정의: "네이버가 못 하는 KBO 복합 조건 질의를 드롭다운 조합으로 해결하는 데이터 대시보드"
- 기술 스택: React + Chart.js (프론트) / Python + FastAPI (백엔드) / SQLite (DB)
- 1인 개발, 비용 0원 제약

---

## 참조 문서 (우선순위 순)

### 1. 프레임워크 고유 가이드라인 (최우선)
- adf/03_guidelines/frameworks/react.md (작성 시)
- adf/03_guidelines/frameworks/fastapi.md (작성 시)
- adf/03_guidelines/frameworks/data-pipeline.md (작성 시)

### 2. 공통 가이드라인
- adf/03_guidelines/common/code.md

### 3. 프로젝트 고유 규칙
- docs/steering.md — 프로젝트 헌법 (원칙, 제약, 경계선)
- docs/requirements.md — 15개 기능 상세 요구사항
- docs/design.md — DB 스키마, API 설계, 컴포넌트 구조 (작성 시)

### 4. 사상 및 원칙 (암묵적 전제)
- adf/01_philosophy/dev-philosophy.md (작성 시)
- adf/02_principles/dev-principles.md (작성 시)

---

## 핵심 원칙 (steering.md에서 추출)

### P1. 드롭다운이 핵심이다
- 이 서비스의 가치는 "드롭다운 5단 조합으로 복합 조건 질의"에 있다
- AI/SLM은 보너스. 드롭다운 없이는 서비스가 안 된다

### P2. 네이버와 경쟁하지 않는다
- 네이버가 이미 하는 것(기본 스코어, 일정)을 더 잘 만들려고 하지 않는다
- 네이버가 못 하는 것만 한다: 복합 조건 질의, 세이버메트릭스, 상황별 스플릿

### P3. 데이터 정확도가 생명이다
- 세이버메트릭스 계산은 반드시 단위 테스트로 검증
- 결과를 KBReport/STATIZ와 크로스체크

### P4. 하나를 제대로 만든다
- 1순위 MVP 완성 전에 2순위 기능에 손대지 않는다
- "더 넣자"보다 "이것을 완벽하게" 우선

### P5. 비용 0원 유지
- 유료 API, 유료 호스팅 사용하지 않는다

---

## 코딩 규칙 요약

### Python (백엔드)
- PEP 8, snake_case, 타입 힌트 필수
- Any 금지, Pydantic으로 API 타입 정의
- SQL은 파라미터 바인딩 필수, f-string SQL 금지
- 외부 API/크롤링은 실패를 전제로 작성

### React (프론트)
- 함수형 컴포넌트, camelCase, PascalCase 컴포넌트
- Props 구조 분해 할당
- API 호출은 커스텀 훅으로 분리
- 로딩/에러 상태 표시 필수

### 수치 표시
- 타율/승률: .328 (소수점 3자리)
- ERA/FIP: 3.45 (소수점 2자리)
- WAR/wRC+: 7.2 (소수점 1자리)

### Git
- 작은 단위 커밋, 기능별 브랜치
- .env 절대 커밋 금지
- AI 변경은 반드시 Git diff로 확인

---

## 기능 우선순위

코드 생성 시 반드시 이 우선순위를 따를 것:

1순위 MVP: ① 데이터 탐색기 ② 선수 세부정보 ③ 순위
2순위: ④ 일정/결과 ⑤ 풀 라인업 ⑥ 기록 조회
3순위: ⑦~⑫ (이색통계, 핫/콜드, 커뮤니티, 직관로그, 응원가, SNS허브)
향후: ⑬~⑮ (AI질의, 승부예측, SNS자동생성)

→ 1순위 완성 전에 2순위 기능을 구현하지 말 것

---

## 금지 사항

- 유료 API 호출 코드 작성 금지
- Next.js, MongoDB 사용 금지 (기술 스택은 React + FastAPI + SQLite)
- any 타입 사용 금지 (Python의 Any, TypeScript의 any 모두)
- console.log 프로덕션 코드에 남기기 금지
- f-string으로 SQL 쿼리 조합 금지
- 테스트 없이 세이버메트릭스 계산 함수 작성 금지

---

> 이 문서는 프로젝트 진행에 따라 업데이트됩니다.
> 역산 어프로치: AI 출력에서 문제를 발견하면 여기에 규칙을 추가합니다.
