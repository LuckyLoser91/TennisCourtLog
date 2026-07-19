from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, glob, os
import pandas as pd

_cache = {}   # year → DataFrame，按年缓存避免重复 IO


# 轮次在返回结果中保留原始值，前端自行排序
ROUND_ORDER = {'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7}

# 赛事级别标签（tourney_level 字段）
# G=Grand Slam, PM=Premier Mandatory(1000), P=Premier(500/700), IT=International(250)
LEVEL_LABEL = {
    'G':  'Grand Slam',
    'PM': 'WTA 1000',
    'P':  'WTA 500/700',
    'IT': 'WTA 250',
    'F':  'WTA Finals',
}


def load_year(year: int):
    """加载指定年份的 CSV，返回 DataFrame，出错返回 None。"""
    global _cache
    if year in _cache:
        return _cache[year]

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, 'tennis_wta', f'wta_matches_{year}.csv')

    if not os.path.exists(path):
        # 兼容：扫描 glob 以防文件名含子目录
        candidates = glob.glob(os.path.join(base, 'tennis_wta', f'wta_matches_{year}.csv'))
        if not candidates:
            _cache[year] = None
            return None
        path = candidates[0]

    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        _cache[year] = None
        return None

    # 解析日期
    df['tourney_date'] = pd.to_datetime(
        df['tourney_date'].str.replace('/', '-', regex=False),
        errors='coerce'
    )
    df = df.dropna(subset=['tourney_date'])
    df['_date_int'] = df['tourney_date'].dt.strftime('%Y%m%d').astype(int)

    _cache[year] = df
    return df


def safe_int(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except Exception:
        return None


def safe_str(val):
    return val if (val and not pd.isna(val)) else None


def get_season(player: str, year: int):
    """
    返回 player 在 year 赛季的所有比赛列表，
    按赛事日期升序、轮次升序排列。
    """
    df = load_year(year)
    if df is None:
        return None   # 文件不存在

    mask = (df['winner_name'] == player) | (df['loser_name'] == player)
    player_df = df[mask].copy()

    if player_df.empty:
        return []

    player_df['_round_order'] = player_df['round'].map(ROUND_ORDER).fillna(0).astype(int)
    player_df = player_df.sort_values(['_date_int', '_round_order']).reset_index(drop=True)

    matches = []
    for _, row in player_df.iterrows():
        is_win   = row['winner_name'] == player
        opponent = row['loser_name'] if is_win else row['winner_name']
        opp_rank = safe_int(row['loser_rank']  if is_win else row['winner_rank'])
        p_rank   = safe_int(row['winner_rank'] if is_win else row['loser_rank'])

        level_raw = safe_str(row.get('tourney_level'))
        level_label = LEVEL_LABEL.get(level_raw, level_raw) if level_raw else None

        matches.append({
            'tourney_date':  row['tourney_date'].strftime('%Y-%m-%d'),
            'tourney_name':  safe_str(row.get('tourney_name')),
            'tourney_level': level_raw,
            'level_label':   level_label,
            'surface':       safe_str(row.get('surface')),
            'round':         safe_str(row.get('round')),
            'result':        'W' if is_win else 'L',
            'player_rank':   p_rank,
            'opponent':      opponent,
            'opponent_rank': opp_rank,
            'score':         safe_str(row.get('score')),
        })

    return matches


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        player = params.get('player', [None])[0]
        year_s = params.get('year',   [None])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not player or not year_s:
            self.wfile.write(json.dumps(
                {'error': 'player and year parameters are required'}
            ).encode())
            return

        try:
            year = int(year_s)
        except ValueError:
            self.wfile.write(json.dumps({'error': 'year must be an integer'}).encode())
            return

        matches = get_season(player, year)

        if matches is None:
            self.wfile.write(json.dumps(
                {'error': f'no data file found for year {year}'}
            ).encode())
            return

        wins   = sum(1 for m in matches if m['result'] == 'W')
        losses = sum(1 for m in matches if m['result'] == 'L')

        self.wfile.write(json.dumps({
            'player':        player,
            'year':          year,
            'total_matches': len(matches),
            'wins':          wins,
            'losses':        losses,
            'matches':       matches,
        }, allow_nan=False).encode())

    def log_message(self, format, *args):
        pass