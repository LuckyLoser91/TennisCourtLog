from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, glob, os
import pandas as pd

_cache = None

# ── 与 history API 共用的数据加载 ──────────────────────────────
def load_data():
    global _cache
    if _cache is not None:
        return _cache

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

# ── 头对头查询逻辑 ──────────────────────────────────────────────
def get_h2h(player1, player2):
    data = load_data()
    if data is None:
        return None

    # 过滤出两位球员相遇的比赛（一人胜一人负）
    df = data[
        ((data['winner_name'] == player1) & (data['loser_name'] == player2)) |
        ((data['winner_name'] == player2) & (data['loser_name'] == player1))
    ].copy()

    if df.empty:
        return []

    # 轮次排序权重
    round_order = {'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7}
    df['round_order'] = df['round'].map(round_order).fillna(0)

    # 按年倒序，同一年按轮次升序（决赛在后）
    df = df.sort_values(['year', 'round_order'], ascending=[False, True]).reset_index(drop=True)

    matches = []
    wins_p1 = 0
    wins_p2 = 0

    for _, row in df.iterrows():
        winner = row['winner_name']
        loser  = row['loser_name']
        is_p1_win = (winner == player1)
        if is_p1_win:
            wins_p1 += 1
        else:
            wins_p2 += 1

        matches.append({
            'year': int(row['year']),
            'tourney_name': row['tourney_name'],
            'surface': row['surface'] if pd.notna(row['surface']) else None,
            'round': row['round'],
            'winner': winner,
            'winner_rank': safe_rank(row['winner_rank']),
            'loser': loser,
            'loser_rank': safe_rank(row['loser_rank']),
            'score': row['score'] if pd.notna(row['score']) else None,
        })

    return {
        'total_matches': len(matches),
        'wins_player1': wins_p1,
        'wins_player2': wins_p2,
        'matches': matches
    }

# ── HTTP Handler ──────────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        p1 = params.get('player1', [None])[0]
        p2 = params.get('player2', [None])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not p1 or not p2:
            self.wfile.write(json.dumps({'error': 'player1 and player2 parameters required'}).encode())
            return

        result = get_h2h(p1, p2)

        if result is None:
            self.wfile.write(json.dumps({'error': 'data loading failed'}).encode())
            return

        response = {
            'player1': p1,
            'player2': p2,
            **result   # 展开 total_matches, wins_player1, wins_player2, matches
        }
        self.wfile.write(json.dumps(response, allow_nan=False).encode())

    def log_message(self, format, *args):
        pass