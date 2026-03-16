# 공통 코딩 가이드라인

> 계층: 03_guidelines/common
> 유효기간: 6개월~1년
> 업데이트: 역산 어프로치 — AI 출력을 보고 "여기가 다르다"를 발견하면 추가

---

## Python (백엔드 — FastAPI)

### 스타일
- PEP 8 준수
- 들여쓰기: 스페이스 4칸
- 최대 줄 길이: 88자 (Black 포매터 기준)
- 함수/변수명: snake_case
- 클래스명: PascalCase
- 상수: UPPER_SNAKE_CASE

### 타입
- 타입 힌트 필수 (함수 인자 + 반환값)
- Any 사용 금지, Union 또는 Optional 사용
- Pydantic 모델로 API 입출력 타입 정의

### 에러 처리
- 빈 except 금지 — 구체적인 예외 타입 명시
- FastAPI HTTPException으로 API 에러 처리 통일
- 외부 API/크롤링은 반드시 실패를 전제로 작성 (try-except + 재시도 로직)

### 데이터
- SQL 인젝션 방지: 쿼리 파라미터 바인딩 필수, f-string으로 SQL 조합 금지
- pandas DataFrame은 처리 후 반드시 타입 확인
- 세이버메트릭스 계산 함수는 단위 테스트 필수

---

## JavaScript/React (프론트엔드)

### 스타일
- 함수/변수명: camelCase
- 컴포넌트명: PascalCase
- 파일명: 컴포넌트는 PascalCase.jsx, 유틸은 camelCase.js
- 세미콜론 사용

### 컴포넌트
- 함수형 컴포넌트만 사용 (class 컴포넌트 금지)
- Props는 구조 분해 할당으로 받기
- 인라인 스타일 최소화, CSS Modules 또는 Tailwind 사용

### 상태 관리
- useState/useEffect 기본
- 전역 상태가 필요하면 Context API 우선 (Redux는 MVP에서 불필요)
- API 호출은 커스텀 훅으로 분리

### 에러 처리
- API 호출 실패 시 사용자에게 에러 메시지 표시
- 로딩 상태 표시 필수 (스켈레톤 UI 또는 스피너)
- console.log는 개발 중에만, 프로덕션에서는 제거

---

## 공통

### Git
- 커밋 메시지: 한국어 OK, 변경 내용 명확히
- 기능별 브랜치 분리
- .env 절대 커밋 금지
- 작은 단위로 커밋 (AI 변경 내용 Git diff로 확인)

### 보안
- API 키, DB 비밀번호는 환경 변수로 관리 (.env)
- .gitignore에 .env, node_modules/, __pycache__/ 포함
- 크롤링 시 rate limiting 준수 (요청 간 1초 이상)

### 수치 표시 규칙
- 타율/승률: 소수점 3자리 (.328)
- ERA/FIP/WHIP: 소수점 2자리 (3.45)
- WAR/wRC+: 소수점 1자리 (7.2)
- 정수 지표 (홈런, 타점): 천 단위 구분 없음
- 관중 수: 천 단위 구분 (1,231만)

---

> 이 파일은 역산 어프로치로 성장합니다.
> AI가 생성한 코드에서 "여기가 다르다"를 발견하면 여기에 룰을 추가하세요.
