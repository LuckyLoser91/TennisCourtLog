from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, glob, os
import pandas as pd

_cache = None

# 赛事名映射：前端传入名 → CSV 里实际匹配的名称列表
TOURNAMENT_MAP = {
    'Australian Open': ['Australian Open'],
    'Roland Garros':   ['Roland Garros'],
    'Wimbledon':       ['Wimbledon'],
    'Us Open':         ['Us Open'],
    'Doha':            ['Doha'],
    'Dubai':           ['Dubai'],
    'Indian Wells':    ['Indian Wells'],
    'Miami':           ['Miami'],
    'Madrid':          ['Madrid'],
    'Rome':            ['Rome'],
    'Canada':          ['Toronto', 'Montreal'],
    'Cincinnati':      ['Cincinnati'],
    'Beijing':         ['Beijing'],
    'Wuhan':           ['Wuhan'],
}

# 需要排除的年份（赛事在这些年不是1000级别）
EXCLUDE_YEARS = {
    'Doha':  {2011, 2015, 2017, 2019, 2021, 2023},
    'Dubai': {2012, 2013, 2014, 2016, 2018, 2020, 2022},
}

def load_data():
    global _cache
    if _cache is not None:
        return _cache

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 只读2009年及以后
    files = sorted(glob.glob(os.path.join(base, 'tennis_wta', 'wta_matches_*.csv')))
    files = [f for f in files if int(os.path.basename(f).replace('wta_matches_', '').replace('.csv', '')) >= 2009]

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, dtype=str)
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        return None

    data = pd.concat(dfs, ignore_index=True)
    data['tourney_date'] = pd.to_datetime(
        data['tourney_date'].str.replace('/', '-', regex=False),
        errors='coerce'
    )
    data = data.dropna(subset=['tourney_date'])
    data['year'] = data['tourney_date'].dt.year.astype(int)
    _cache = data
    return _cache


def safe_rank(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except:
        return None


def get_history(player, tournament):
    data = load_data()
    if data is None:
        return None

    # 赛事名映射
    tourney_names = TOURNAMENT_MAP.get(tournament)
    if not tourney_names:
        return None

    # 过滤赛事
    df = data[data['tourney_name'].isin(tourney_names)].copy()

    # 排除特定年份
    if tournament in EXCLUDE_YEARS:
        bad_years = EXCLUDE_YEARS[tournament]
        df = df[~df['year'].isin(bad_years)]

    # 过滤出该球员参与的比赛（胜或负）
    player_matches = df[(df['winner_name'] == player) | (df['loser_name'] == player)].copy()

    if player_matches.empty:
        return []

    # 轮次排序权重
    round_order = {'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7}

    player_matches['round_order'] = player_matches['round'].map(round_order).fillna(0)
    player_matches = player_matches.sort_values(
        ['year', 'round_order'],
        ascending=[False, True]
    ).reset_index(drop=True)

    result = []
    for _, row in player_matches.iterrows():
        result.append({
            'year': int(row['year']),
            'tourney_name': row['tourney_name'],
            'surface': row['surface'] if pd.notna(row['surface']) else None,
            'round': row['round'],
            'winner_name': row['winner_name'],
            'winner_rank': safe_rank(row['winner_rank']),
            'loser_name': row['loser_name'],
            'loser_rank': safe_rank(row['loser_rank']),
            'score': row['score'] if pd.notna(row['score']) else None,
            'result': 'W' if row['winner_name'] == player else 'L',
        })

    return result


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        player = params.get('player', [None])[0]
        tournament = params.get('tournament', [None])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not player or not tournament:
            self.wfile.write(json.dumps({'error': 'player and tournament parameters required'}).encode())
            return

        matches = get_history(player, tournament)

        if matches is None:
            self.wfile.write(json.dumps({'error': 'unknown tournament'}).encode())
            return

        self.wfile.write(json.dumps({
            'player': player,
            'tournament': tournament,
            'total_matches': len(matches),
            'matches': matches
        }, allow_nan=False).encode())

    def log_message(self, format, *args):
        pass