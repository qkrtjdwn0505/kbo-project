"""샘플 데이터 생성기 — API 접근 없이 파이프라인 테스트용

실제 2024 시즌 주요 선수들의 근사 데이터를 생성합니다.
로컬에서 실제 수집이 가능해지면 이 파일은 테스트용으로만 사용합니다.
"""

import random
from datetime import date, timedelta


# 2024 시즌 주요 선수 (근사 데이터)
SAMPLE_PLAYERS = [
    # (이름, 팀ID, 포지션, 포지션상세, 등번호, 타석, 투구)
    ("김도영", 1, "내야수", "유격수", 5, "우타", "우투"),
    ("최형우", 1, "내야수", "지명타자", 34, "좌타", "우투"),
    ("나성범", 1, "외야수", "좌익수", 47, "좌타", "우투"),
    ("양현종", 1, "투수", "선발", 54, "좌타", "좌투"),
    ("이의리", 1, "투수", "선발", 29, "우타", "우투"),
    ("구자욱", 2, "외야수", "좌익수", 51, "좌타", "우투"),
    ("김영웅", 2, "내야수", "유격수", 2, "우타", "우투"),
    ("오승환", 2, "투수", "마무리", 26, "우타", "우투"),
    ("오스틴", 3, "외야수", "좌익수", 33, "우타", "우투"),
    ("박동원", 3, "포수", "포수", 10, "좌타", "우투"),
    ("임찬규", 3, "투수", "선발", 43, "좌타", "좌투"),
    ("양의지", 4, "포수", "포수", 25, "우타", "우투"),
    ("김재환", 4, "내야수", "지명타자", 32, "우타", "우투"),
    ("곽빈", 4, "투수", "선발", 21, "우타", "우투"),
    ("강백호", 5, "내야수", "1루수", 50, "좌타", "우투"),
    ("소형준", 5, "투수", "선발", 18, "우타", "우투"),
    ("최정", 6, "내야수", "3루수", 14, "우타", "우투"),
    ("김광현", 6, "투수", "선발", 29, "좌타", "좌투"),
    ("전준우", 7, "외야수", "우익수", 39, "우타", "우투"),
    ("나균안", 7, "투수", "선발", 11, "우타", "우투"),
    ("노시환", 8, "내야수", "3루수", 52, "좌타", "우투"),
    ("문동주", 8, "투수", "선발", 1, "좌타", "좌투"),
    ("박건우", 9, "외야수", "중견수", 27, "좌타", "우투"),
    ("에르난데스", 9, "투수", "선발", 37, "우타", "우투"),
    ("이정후", 10, "외야수", "중견수", 51, "좌타", "우투"),
    ("안우진", 10, "투수", "선발", 43, "우타", "우투"),
]


def generate_sample_players() -> list[dict]:
    """선수 프로필 데이터 생성"""
    players = []
    for i, (name, team_id, pos, pos_detail, num, bat, throw) in enumerate(SAMPLE_PLAYERS, 1):
        players.append({
            "id": i,
            "name": name,
            "team_id": team_id,
            "position": pos,
            "position_detail": pos_detail,
            "back_number": num,
            "birth_date": f"199{random.randint(0,9)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "height": random.randint(175, 190),
            "weight": random.randint(78, 100),
            "bat_hand": bat,
            "throw_hand": throw,
            "is_active": True,
        })
    return players


def generate_sample_games(season: int = 2024, num_games: int = 50) -> list[dict]:
    """경기 데이터 생성"""
    games = []
    start_date = date(season, 4, 1)
    team_ids = list(range(1, 11))

    for i in range(num_games):
        game_date = start_date + timedelta(days=i // 5)
        home = random.choice(team_ids)
        away = random.choice([t for t in team_ids if t != home])
        home_score = random.randint(0, 12)
        away_score = random.randint(0, 12)

        stadiums = {
            1: "챔피언스필드", 2: "라이온즈파크", 3: "잠실야구장",
            4: "잠실야구장", 5: "KT위즈파크", 6: "랜더스필드",
            7: "사직야구장", 8: "한화생명볼파크", 9: "NC파크", 10: "고척스카이돔"
        }
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]

        games.append({
            "id": i + 1,
            "date": str(game_date),
            "time": random.choice(["14:00", "17:00", "18:30"]),
            "stadium": stadiums[home],
            "home_team_id": home,
            "away_team_id": away,
            "home_score": home_score,
            "away_score": away_score,
            "status": "final",
            "day_of_week": weekdays[game_date.weekday()],
            "is_night_game": True if random.random() > 0.3 else False,
        })
    return games


def generate_sample_batter_stats(players: list[dict], games: list[dict]) -> list[dict]:
    """경기별 타자 기록 생성"""
    stats = []
    batters = [p for p in players if p["position"] != "투수"]

    for game in games:
        for batter in random.sample(batters, min(8, len(batters))):
            ab = random.randint(2, 5)
            hits = random.randint(0, min(ab, 3))
            hr = 1 if random.random() < 0.08 else 0
            bb = 1 if random.random() < 0.12 else 0

            stats.append({
                "game_id": game["id"],
                "player_id": batter["id"],
                "team_id": batter["team_id"],
                "pa": ab + bb + (1 if random.random() < 0.05 else 0),
                "ab": ab,
                "hits": hits,
                "doubles": 1 if hits > 1 and random.random() < 0.3 else 0,
                "triples": 1 if hits > 1 and random.random() < 0.05 else 0,
                "hr": hr,
                "rbi": random.randint(0, 3) if hits > 0 else 0,
                "runs": 1 if random.random() < 0.25 else 0,
                "sb": 1 if random.random() < 0.08 else 0,
                "cs": 0,
                "bb": bb,
                "hbp": 1 if random.random() < 0.03 else 0,
                "so": 1 if hits == 0 and random.random() < 0.4 else 0,
                "gdp": 0,
                "sf": 1 if random.random() < 0.03 else 0,
                "runners_on_scoring": random.random() < 0.3,
                "opponent_pitcher_hand": random.choice(["좌투", "우투"]),
                "is_home": batter["team_id"] == game["home_team_id"],
                "score_diff": random.randint(-5, 5),
            })
    return stats


def generate_sample_pitcher_stats(players: list[dict], games: list[dict]) -> list[dict]:
    """경기별 투수 기록 생성"""
    stats = []
    pitchers = [p for p in players if p["position"] == "투수"]

    for game in games:
        for pitcher in random.sample(pitchers, min(3, len(pitchers))):
            ip_outs = random.randint(3, 21)  # 1~7이닝
            so = random.randint(1, 8)
            hits_a = random.randint(2, 8)
            er = random.randint(0, 5)

            stats.append({
                "game_id": game["id"],
                "player_id": pitcher["id"],
                "team_id": pitcher["team_id"],
                "ip_outs": ip_outs,
                "hits_allowed": hits_a,
                "hr_allowed": 1 if random.random() < 0.3 else 0,
                "bb_allowed": random.randint(0, 4),
                "hbp_allowed": 1 if random.random() < 0.1 else 0,
                "so_count": so,
                "runs_allowed": er + (1 if random.random() < 0.2 else 0),
                "er": er,
                "is_starter": pitcher["position_detail"] == "선발",
                "decision": random.choice(["W", "L", None, None]),
                "batter_hand": random.choice(["좌타", "우타"]),
                "is_home": pitcher["team_id"] == game["home_team_id"],
            })
    return stats
