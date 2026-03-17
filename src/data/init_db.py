"""DB 스키마 초기화 + 10개 구단 초기 데이터"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent.parent / "kbo.db"


def init_db():
    """전체 테이블 생성 + 초기 데이터 삽입"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # ===== 테이블 생성 =====

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        short_name TEXT NOT NULL,
        city TEXT NOT NULL,
        stadium TEXT NOT NULL,
        logo_initial TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        team_id INTEGER REFERENCES teams(id),
        position TEXT NOT NULL,
        position_detail TEXT,
        back_number INTEGER,
        birth_date DATE,
        height INTEGER,
        weight INTEGER,
        bat_hand TEXT,
        throw_hand TEXT,
        instagram_url TEXT,
        youtube_url TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_name ON players(name)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY,
        date DATE NOT NULL,
        time TEXT,
        stadium TEXT,
        home_team_id INTEGER REFERENCES teams(id),
        away_team_id INTEGER REFERENCES teams(id),
        home_score INTEGER,
        away_score INTEGER,
        status TEXT DEFAULT 'scheduled',
        home_starter_id INTEGER REFERENCES players(id),
        away_starter_id INTEGER REFERENCES players(id),
        winning_pitcher_id INTEGER REFERENCES players(id),
        losing_pitcher_id INTEGER REFERENCES players(id),
        save_pitcher_id INTEGER REFERENCES players(id),
        inning_scores TEXT,
        day_of_week TEXT,
        is_night_game BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batter_stats (
        id INTEGER PRIMARY KEY,
        game_id INTEGER REFERENCES games(id),
        player_id INTEGER REFERENCES players(id),
        team_id INTEGER REFERENCES teams(id),
        pa INTEGER DEFAULT 0,
        ab INTEGER DEFAULT 0,
        hits INTEGER DEFAULT 0,
        doubles INTEGER DEFAULT 0,
        triples INTEGER DEFAULT 0,
        hr INTEGER DEFAULT 0,
        rbi INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0,
        sb INTEGER DEFAULT 0,
        cs INTEGER DEFAULT 0,
        bb INTEGER DEFAULT 0,
        hbp INTEGER DEFAULT 0,
        so INTEGER DEFAULT 0,
        gdp INTEGER DEFAULT 0,
        sf INTEGER DEFAULT 0,
        runners_on_scoring BOOLEAN,
        opponent_pitcher_hand TEXT,
        inning INTEGER,
        is_home BOOLEAN,
        score_diff INTEGER,
        UNIQUE(game_id, player_id, inning)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_batter_game ON batter_stats(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_batter_player ON batter_stats(player_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_batter_scoring ON batter_stats(runners_on_scoring)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pitcher_stats (
        id INTEGER PRIMARY KEY,
        game_id INTEGER REFERENCES games(id),
        player_id INTEGER REFERENCES players(id),
        team_id INTEGER REFERENCES teams(id),
        ip_outs INTEGER DEFAULT 0,
        hits_allowed INTEGER DEFAULT 0,
        hr_allowed INTEGER DEFAULT 0,
        bb_allowed INTEGER DEFAULT 0,
        hbp_allowed INTEGER DEFAULT 0,
        so_count INTEGER DEFAULT 0,
        runs_allowed INTEGER DEFAULT 0,
        er INTEGER DEFAULT 0,
        is_starter BOOLEAN,
        decision TEXT,
        batter_hand TEXT,
        is_home BOOLEAN,
        UNIQUE(game_id, player_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pitcher_game ON pitcher_stats(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pitcher_player ON pitcher_stats(player_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batter_season (
        id INTEGER PRIMARY KEY,
        player_id INTEGER REFERENCES players(id),
        season INTEGER NOT NULL,
        team_id INTEGER REFERENCES teams(id),
        games INTEGER, pa INTEGER, ab INTEGER, hits INTEGER,
        doubles INTEGER, triples INTEGER, hr INTEGER, rbi INTEGER,
        runs INTEGER, sb INTEGER, cs INTEGER, bb INTEGER, hbp INTEGER,
        so INTEGER, gdp INTEGER, sf INTEGER,
        avg REAL, obp REAL, slg REAL, ops REAL,
        woba REAL, wrc_plus REAL, war REAL, babip REAL,
        iso REAL, bb_pct REAL, k_pct REAL,
        ops_vs_lhp REAL, ops_vs_rhp REAL, ops_risp REAL,
        ops_home REAL, ops_away REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, season)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bseason_player ON batter_season(player_id, season)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pitcher_season (
        id INTEGER PRIMARY KEY,
        player_id INTEGER REFERENCES players(id),
        season INTEGER NOT NULL,
        team_id INTEGER REFERENCES teams(id),
        games INTEGER, wins INTEGER, losses INTEGER, saves INTEGER, holds INTEGER,
        ip_outs INTEGER,
        hits_allowed INTEGER, hr_allowed INTEGER, bb_allowed INTEGER,
        hbp_allowed INTEGER, so_count INTEGER, runs_allowed INTEGER, er INTEGER,
        era REAL, whip REAL,
        fip REAL, xfip REAL, war REAL, babip REAL, lob_pct REAL,
        k_per_9 REAL, bb_per_9 REAL, hr_per_9 REAL, k_bb_ratio REAL,
        avg_vs_lhb REAL, avg_vs_rhb REAL, era_home REAL, era_away REAL,
        is_starter BOOLEAN,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, season)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pseason_player ON pitcher_season(player_id, season)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lineups (
        id INTEGER PRIMARY KEY,
        game_id INTEGER REFERENCES games(id),
        team_id INTEGER REFERENCES teams(id),
        player_id INTEGER REFERENCES players(id),
        batting_order INTEGER,
        position TEXT,
        role TEXT NOT NULL,
        role_detail TEXT,
        pitched_yesterday BOOLEAN DEFAULT FALSE,
        UNIQUE(game_id, team_id, player_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lineups_game ON lineups(game_id, team_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS league_constants (
        season INTEGER PRIMARY KEY,
        woba_scale REAL,
        league_woba REAL,
        league_wrc REAL,
        fip_constant REAL,
        league_hr_fb_rate REAL,
        rppa REAL,
        league_rpw REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cheer_songs (
        id INTEGER PRIMARY KEY,
        team_id INTEGER REFERENCES teams(id),
        player_id INTEGER REFERENCES players(id),
        title TEXT NOT NULL,
        lyrics TEXT NOT NULL,
        youtube_url TEXT,
        song_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheers_team ON cheer_songs(team_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_sns (
        id INTEGER PRIMARY KEY,
        player_id INTEGER REFERENCES players(id),
        platform TEXT NOT NULL,
        url TEXT NOT NULL,
        UNIQUE(player_id, platform)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS team_sns (
        id INTEGER PRIMARY KEY,
        team_id INTEGER REFERENCES teams(id),
        platform TEXT NOT NULL,
        url TEXT NOT NULL,
        UNIQUE(team_id, platform)
    )
    """)

    # ===== 3순위: 커뮤니티/직관로그용 테이블 =====

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        favorite_team_id INTEGER REFERENCES teams(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        board TEXT NOT NULL DEFAULT 'free',
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        likes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_logs (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        game_id INTEGER REFERENCES games(id),
        memo TEXT,
        mvp_player_id INTEGER REFERENCES players(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, game_id)
    )
    """)

    # ===== 10개 구단 초기 데이터 =====

    teams_data = [
        (1, "KIA 타이거즈", "KIA", "광주", "챔피언스필드", "KIA"),
        (2, "삼성 라이온즈", "삼성", "대구", "라이온즈파크", "삼성"),
        (3, "LG 트윈스", "LG", "서울", "잠실야구장", "LG"),
        (4, "두산 베어스", "두산", "서울", "잠실야구장", "두산"),
        (5, "KT 위즈", "KT", "수원", "KT위즈파크", "KT"),
        (6, "SSG 랜더스", "SSG", "인천", "랜더스필드", "SSG"),
        (7, "롯데 자이언츠", "롯데", "부산", "사직야구장", "롯데"),
        (8, "한화 이글스", "한화", "대전", "한화생명볼파크", "한화"),
        (9, "NC 다이노스", "NC", "창원", "NC파크", "NC"),
        (10, "키움 히어로즈", "키움", "서울", "고척스카이돔", "키움"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO teams (id, name, short_name, city, stadium, logo_initial) VALUES (?, ?, ?, ?, ?, ?)",
        teams_data,
    )

    conn.commit()
    conn.close()

    print(f"DB 초기화 완료: {DB_PATH}")
    print(f"  - 테이블 15개 생성")
    print(f"  - 10개 구단 데이터 삽입")


if __name__ == "__main__":
    init_db()
