"""KBO 홈페이지 직접 API 호출 수집기

KBO 게임센터의 내부 API를 requests.post로 호출하여 데이터를 수집합니다.
Chrome driver 불필요 — requests만으로 동작합니다.

2025년 KBO 홈페이지 개편 후 API 엔드포인트:
  - /ws/Main.asmx/GetKboGameList    → 날짜별 경기 목록 (JSON)
  - /ws/Main.asmx/GetKboGameDate    → 경기 있는 날짜 탐색
  - /ws/Schedule.asmx/GetScoreBoardScroll → 이닝별 스코어 (JSON)
  - /ws/Schedule.asmx/GetBoxScoreScroll   → 박스스코어 (JSON)

파라미터 변경점 (2025~):
  - 기존: leId, srIdList, date
  - 변경: leId, srId, seasonId, gameId

사용법:
    collector = KBODataCollector()
    games = collector.get_game_list("20250401")
    boxscore = collector.get_boxscore("20250315LGSK0", sr_id=0, season=2025)

참고: https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx
"""

import json
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class KBODataCollector:
    """KBO 홈페이지 API 직접 호출 수집기 (2025 개편 대응)"""

    BASE_URL = "https://www.koreabaseball.com"

    # 2025 개편 후 엔드포인트
    GAME_LIST_URL = f"{BASE_URL}/ws/Main.asmx/GetKboGameList"
    GAME_DATE_URL = f"{BASE_URL}/ws/Main.asmx/GetKboGameDate"
    SCOREBOARD_URL = f"{BASE_URL}/ws/Schedule.asmx/GetScoreBoardScroll"
    BOXSCORE_URL = f"{BASE_URL}/ws/Schedule.asmx/GetBoxScoreScroll"

    HEADERS = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": f"{BASE_URL}/Schedule/GameCenter/Main.aspx",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
    }

    # KBO 팀 영문코드 → team_id (DB teams 테이블 기준)
    TEAM_CODE_TO_ID: dict[str, int] = {
        "HT": 1, "SS": 2, "LG": 3, "OB": 4, "KT": 5,
        "SK": 6, "LT": 7, "HH": 8, "NC": 9, "WO": 10,
    }

    # KBO 팀 한글명 → team_id
    TEAM_NAME_TO_ID: dict[str, int] = {
        "KIA": 1, "기아": 1,
        "삼성": 2,
        "LG": 3,
        "두산": 4,
        "KT": 5, "kt": 5,
        "SSG": 6,
        "롯데": 7,
        "한화": 8,
        "NC": 9,
        "키움": 10,
    }

    # srId: 0=정규시즌, 1=시범경기, 3=와일드카드, 4=준PO, 5=PO, 7=한국시리즈, 9=올스타
    SR_ID_ALL = "0,1,3,4,5,7,9"

    def __init__(self, delay: float = 1.0):
        """
        Args:
            delay: 요청 간 대기 시간 (초). 서버 예의를 위해 최소 1초.
        """
        self.delay = max(delay, 1.0)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _request(self, url: str, data: dict) -> Optional[dict]:
        """API POST 요청 + 재시도 로직 (최대 3회)"""
        for attempt in range(3):
            try:
                time.sleep(self.delay)
                res = self.session.post(url, data=data, timeout=15)
                res.raise_for_status()
                result = res.json()
                # KBO API는 code=100이 성공, code=200은 데이터 없음
                return result
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "요청 실패 (시도 %d/3): %s - %s", attempt + 1, url, e
                )
                if attempt < 2:
                    time.sleep(self.delay * (attempt + 1))
        logger.error("요청 최종 실패: %s", url)
        return None

    # ─── 경기 목록 ─────────────────────────────────────

    def get_game_list(self, date_str: str, sr_id: str = SR_ID_ALL) -> list[dict]:
        """특정 날짜의 경기 목록 수집 (2025 신규 API)

        Args:
            date_str: "YYYYMMDD" 형식
            sr_id: 시리즈 ID 필터 (기본: 전체)

        Returns:
            경기 목록. 각 항목은 KBO API 원본 필드 + 정규화 필드 포함.
        """
        result = self._request(
            self.GAME_LIST_URL,
            {"leId": "1", "srId": sr_id, "date": date_str},
        )
        if not result or "game" not in result:
            return []

        games: list[dict] = []
        for raw in result["game"]:
            game = self._normalize_game(raw, date_str)
            if game:
                games.append(game)

        logger.info("수집 완료: %s - %d경기", date_str, len(games))
        return games

    def _normalize_game(self, raw: dict, date_str: str) -> Optional[dict]:
        """GetKboGameList 원본 → 정규화된 경기 dict 변환"""
        game_id = raw.get("G_ID")
        if not game_id:
            return None

        home_code = raw.get("HOME_ID", "")
        away_code = raw.get("AWAY_ID", "")
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        return {
            # 식별
            "game_id": game_id,
            "date": formatted_date,
            "season": raw.get("SEASON_ID", int(date_str[:4])),
            "sr_id": raw.get("SR_ID", 0),
            # 팀
            "home_team": raw.get("HOME_NM", ""),
            "away_team": raw.get("AWAY_NM", ""),
            "home_code": home_code,
            "away_code": away_code,
            "home_team_id": self.TEAM_CODE_TO_ID.get(home_code, 0),
            "away_team_id": self.TEAM_CODE_TO_ID.get(away_code, 0),
            # 스코어
            "home_score": self._safe_int(raw.get("B_SCORE_CN")),
            "away_score": self._safe_int(raw.get("T_SCORE_CN")),
            # 경기 상태: 1=예정, 2=진행, 3=종료, 4=취소
            "status_code": raw.get("GAME_STATE_SC", ""),
            "cancel_code": raw.get("CANCEL_SC_ID", "99"),
            # 경기 정보
            "time": raw.get("G_TM", ""),
            "stadium": raw.get("S_NM", ""),
            # 선발투수
            "home_starter_id": raw.get("B_PIT_P_ID"),
            "home_starter_name": (raw.get("B_PIT_P_NM") or "").strip(),
            "away_starter_id": raw.get("T_PIT_P_ID"),
            "away_starter_name": (raw.get("T_PIT_P_NM") or "").strip(),
            # 결과 투수
            "winning_pitcher_id": raw.get("W_PIT_P_ID"),
            "losing_pitcher_id": raw.get("L_PIT_P_ID"),
            "save_pitcher_id": raw.get("SV_PIT_P_ID"),
        }

    # ─── 스코어보드 (이닝별 점수) ──────────────────────

    def get_scoreboard(self, game_id: str, sr_id: int, season: int) -> Optional[dict]:
        """특정 경기의 이닝별 스코어보드 수집

        Args:
            game_id: 경기 ID (예: "20250315LGSK0")
            sr_id: 시리즈 ID (경기 목록에서 획득)
            season: 시즌 연도

        Returns:
            {
                "stadium", "crowd", "start_time", "end_time", "game_time",
                "home_name", "away_name",
                "inning_scores": {"away": [0,1,0,...], "home": [0,1,0,...]},
                "summary": {"away": [R,H,E,B], "home": [R,H,E,B]},
            }
        """
        result = self._request(
            self.SCOREBOARD_URL,
            {
                "leId": "1",
                "srId": str(sr_id),
                "seasonId": str(season),
                "gameId": game_id,
            },
        )
        if not result or result.get("code") != "100":
            return None

        scoreboard: dict = {
            "stadium": result.get("S_NM", ""),
            "crowd": result.get("CROWD_CN", ""),
            "start_time": result.get("START_TM", ""),
            "end_time": result.get("END_TM", ""),
            "game_time": result.get("USE_TM", ""),
            "home_name": result.get("FULL_HOME_NM", ""),
            "away_name": result.get("FULL_AWAY_NM", ""),
            "inning_scores": {"away": [], "home": []},
            "summary": {"away": [], "home": []},
        }

        # table2: 이닝별 점수 (away=row[0], home=row[1])
        if result.get("table2"):
            t2 = json.loads(result["table2"])
            rows = t2.get("rows", [])
            if len(rows) >= 2:
                scoreboard["inning_scores"]["away"] = [
                    self._safe_int(c["Text"]) for c in rows[0]["row"]
                ]
                scoreboard["inning_scores"]["home"] = [
                    self._safe_int(c["Text"]) for c in rows[1]["row"]
                ]

        # table3: R, H, E, B (away=row[0], home=row[1])
        if result.get("table3"):
            t3 = json.loads(result["table3"])
            rows = t3.get("rows", [])
            if len(rows) >= 2:
                scoreboard["summary"]["away"] = [
                    self._safe_int(c["Text"]) for c in rows[0]["row"]
                ]
                scoreboard["summary"]["home"] = [
                    self._safe_int(c["Text"]) for c in rows[1]["row"]
                ]

        return scoreboard

    # ─── 박스스코어 (타자/투수 기록) ──────────────────────

    def get_boxscore(self, game_id: str, sr_id: int, season: int) -> Optional[dict]:
        """특정 경기의 박스스코어 수집

        Args:
            game_id: 경기 ID (예: "20250315LGSK0")
            sr_id: 시리즈 ID
            season: 시즌 연도

        Returns:
            {
                "away_batters": [{"name", "position", "batting_order", "ab", "hits", "rbi", "runs", "avg"}, ...],
                "home_batters": [...],
                "away_pitchers": [{"name", "entry", "decision", "wins", "losses", "saves",
                                   "ip", "bf", "np", "ab", "hits_allowed", "hr_allowed",
                                   "bb_allowed", "so_count", "runs_allowed", "er", "era"}, ...],
                "home_pitchers": [...],
            }
        """
        result = self._request(
            self.BOXSCORE_URL,
            {
                "leId": "1",
                "srId": str(sr_id),
                "seasonId": str(season),
                "gameId": game_id,
            },
        )
        if not result or result.get("code") != "100":
            return None

        boxscore: dict = {
            "away_batters": [],
            "home_batters": [],
            "away_pitchers": [],
            "home_pitchers": [],
        }

        # ── 타자 기록 ──
        # arrHitter[0]=원정, arrHitter[1]=홈
        # table1: [타순, 포지션, 선수명]
        # table2: [1회결과, 2회결과, ..., N회결과] — 이닝별 타석 결과 코드
        # table3: [타수, 안타, 타점, 득점, 타율]
        arr_hitter = result.get("arrHitter", [])
        for team_idx, key in enumerate(["away_batters", "home_batters"]):
            if team_idx >= len(arr_hitter):
                break
            hitter_data = arr_hitter[team_idx]
            t1 = json.loads(hitter_data.get("table1", "{}"))
            t2 = json.loads(hitter_data.get("table2", "{}"))
            t3 = json.loads(hitter_data.get("table3", "{}"))

            t1_rows = t1.get("rows", [])
            t2_rows = t2.get("rows", [])
            t3_rows = t3.get("rows", [])

            for i in range(min(len(t1_rows), len(t3_rows))):
                info = [c["Text"] for c in t1_rows[i]["row"]]
                stats = [c["Text"] for c in t3_rows[i]["row"]]

                if len(info) < 3 or len(stats) < 5:
                    continue

                name = info[2].strip()
                if not name or name in ("합계", "TOTALS", "계"):
                    continue

                # table2에서 이닝별 타석 결과 코드 추출
                inning_codes: list[str] = []
                if i < len(t2_rows):
                    inning_codes = [
                        c["Text"] for c in t2_rows[i]["row"]
                    ]

                boxscore[key].append({
                    "batting_order": self._safe_int(info[0]),
                    "position": info[1].strip(),
                    "name": name,
                    # table3 요약 (rbi, runs는 table2에 없으므로 여기서 가져옴)
                    "ab": self._safe_int(stats[0]),
                    "hits": self._safe_int(stats[1]),
                    "rbi": self._safe_int(stats[2]),
                    "runs": self._safe_int(stats[3]),
                    "avg": stats[4].strip() if stats[4].strip() != "&nbsp;" else "",
                    # table2 이닝별 타석 결과 (신규)
                    "inning_codes": inning_codes,
                })

        # ── 투수 기록 ──
        # arrPitcher[0]=원정, arrPitcher[1]=홈
        # headers: [선수명, 등판, 결과, 승, 패, 세, 이닝, 타자, 투구수,
        #           타수, 피안타, 홈런, 4사구, 삼진, 실점, 자책, 평균자책점]
        arr_pitcher = result.get("arrPitcher", [])
        for team_idx, key in enumerate(["away_pitchers", "home_pitchers"]):
            if team_idx >= len(arr_pitcher):
                break
            pitcher_data = arr_pitcher[team_idx]
            table = json.loads(pitcher_data.get("table", "{}"))

            for row in table.get("rows", []):
                cells = [c["Text"].strip() for c in row["row"]]
                if len(cells) < 17:
                    continue

                name = cells[0]
                if not name or name in ("합계", "TOTALS", "계"):
                    continue

                decision = cells[2] if cells[2] != "&nbsp;" else ""

                boxscore[key].append({
                    "name": name,
                    "entry": cells[1],           # 등판 이닝 (예: "선발", "5.3")
                    "decision": decision,        # 승/패/세/홀
                    "wins": self._safe_int(cells[3]),
                    "losses": self._safe_int(cells[4]),
                    "saves": self._safe_int(cells[5]),
                    "ip": cells[6],              # 이닝 (예: "4 2/3", "1")
                    "bf": self._safe_int(cells[7]),   # 상대 타자 수
                    "np": self._safe_int(cells[8]),   # 투구수
                    "ab": self._safe_int(cells[9]),   # 타수
                    "hits_allowed": self._safe_int(cells[10]),
                    "hr_allowed": self._safe_int(cells[11]),
                    "bb_allowed": self._safe_int(cells[12]),  # 4사구
                    "so_count": self._safe_int(cells[13]),
                    "runs_allowed": self._safe_int(cells[14]),
                    "er": self._safe_int(cells[15]),
                    "era": cells[16],
                })

        return boxscore

    # ─── 날짜 탐색 ──────────────────────────────────────

    def get_game_date(self, date_str: str, sr_id: str = SR_ID_ALL) -> Optional[dict]:
        """경기가 있는 전후 날짜 탐색

        Returns:
            {"now": "YYYYMMDD", "before": "YYYYMMDD", "after": "YYYYMMDD"}
        """
        result = self._request(
            self.GAME_DATE_URL,
            {"leId": "1", "srId": sr_id, "date": date_str},
        )
        if not result or result.get("code") != "100":
            return None
        return {
            "now": result.get("NOW_G_DT", ""),
            "before": result.get("BEFORE_G_DT", ""),
            "after": result.get("AFTER_G_DT", ""),
        }

    # ─── 유틸리티 ────────────────────────────────────────

    @staticmethod
    def _safe_int(value: object) -> int:
        """안전한 정수 변환 (&nbsp;, -, 빈 문자열 등 대응)"""
        if value is None:
            return 0
        s = str(value).replace(",", "").replace("&nbsp;", "").replace("-", "").strip()
        if not s:
            return 0
        try:
            return int(s)
        except ValueError:
            return 0

    @staticmethod
    def parse_ip_to_outs(ip_str: str) -> int:
        """이닝 문자열을 아웃 카운트로 변환

        KBO 박스스코어 이닝 표기법:
            "6"     → 18 outs
            "4 2/3" → 14 outs
            "1/3"   → 1 out
            "2/3"   → 2 outs
        """
        ip_str = ip_str.strip()
        if not ip_str:
            return 0

        # "4 2/3" 형태
        if " " in ip_str:
            parts = ip_str.split(" ")
            whole = int(parts[0]) if parts[0].isdigit() else 0
            frac = parts[1] if len(parts) > 1 else ""
            if frac == "1/3":
                return whole * 3 + 1
            elif frac == "2/3":
                return whole * 3 + 2
            return whole * 3

        # "1/3", "2/3" 형태
        if "/" in ip_str:
            if ip_str == "1/3":
                return 1
            elif ip_str == "2/3":
                return 2
            return 0

        # "6" 정수 형태
        try:
            return int(ip_str) * 3
        except ValueError:
            return 0

    def resolve_team_id(self, team_name: str) -> int:
        """팀 이름/코드 → team_id 변환"""
        if not team_name:
            return 0
        name = team_name.strip()
        # 영문 코드 먼저
        if name in self.TEAM_CODE_TO_ID:
            return self.TEAM_CODE_TO_ID[name]
        # 한글명
        if name in self.TEAM_NAME_TO_ID:
            return self.TEAM_NAME_TO_ID[name]
        return 0
