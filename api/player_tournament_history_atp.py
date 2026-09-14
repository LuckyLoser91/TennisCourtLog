"""
player_tournament_history_atp.py

ATP 球员赛事历史 API

功能：给定球员名 + 赛事名，返回该球员在该赛事中的所有比赛记录（按年份降序、轮次深→浅）。

与 WTA 版的差异：
- 只读 tennis_atp/atp_matches_*.csv
- 赛事名映射覆盖 ATP 1000 赛的历史命名（"Xxx Masters" / "Xxx"）
- Canada 站统一映射到 ['Canada Masters', 'Toronto', 'Montreal']
- 每条记录保留 CSV 里的原始 tourney_name（如 "Toronto" / "Montreal" / "Canada Masters"），
  便于前端在弹窗里标注当年实际举办城市

路由：
    GET /api/player_tournament_history_atp?player=<name>&tournament=<name>

返回：
    {
      "player": "...",
      "tournament": "...",
      "tour": "atp",
      "total_matches": N,
      "matches": [
        {
          "year": 2025,
          "tourney_name": "Toronto",       # ← 原始名，非归一化名
          "surface": "Hard",
          "round": "F",
          "winner_name": "...",
          "winner_rank": 1,
          "loser_name": "...",
          "loser_rank": 3,
          "score": "6-4 7-5",
          "result": "W"                    # 相对于 player
        },
        ...
      ]
    }
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, glob, os
import pandas as pd

_cache = None

# ---------------------------------------------------------------------------
# 赛事名映射：前端传入的归一化赛事名 → CSV 中可能出现的所有原始名
# 覆盖 2009 年至今 ATP 1000 赛的命名演变
# ---------------------------------------------------------------------------
TOURNAMENT_MAP = {
    # Grand Slam
    'Australian Open': ['Australian Open'],
    'Roland Garros':   ['Roland Garros'],
    'Wimbledon':       ['Wimbledon'],
    'Us Open':         ['Us Open'],

    # ATP 1000（2025 年前带 Masters 后缀，2025 年起不带）
    'Indian Wells':    ['Indian Wells Masters', 'Indian Wells'],
    'Miami':           ['Miami Masters', 'Miami'],
    'Monte Carlo':     ['Monte Carlo Masters', 'Monte Carlo'],
    'Madrid':          ['Madrid Masters', 'Madrid'],
    'Rome':            ['Rome Masters', 'Rome'],
    'Canada':          ['Canada Masters', 'Toronto', 'Montreal'],
    'Cincinnati':      ['Cincinnati Masters', 'Cincinnati'],
    'Shanghai':        ['Shanghai Masters', 'Shanghai'],
    'Paris':           ['Paris Masters', 'Paris'],
}

# 赛事在 CSV 中可能出现的大小写变体（比如 "US Open" 被 title case 成 "Us Open"）
# 这些会在 load_data 里统一处理


def _norm_key(s):
    """把赛事名归一化为 Title Case 用于匹配"""
    if not isinstance(s, str):
        return ""
    return s.strip().title()


# 展开成一个 set，方便快速过滤（同时也存原始大小写，后面匹配用 Title Case 后的）
_ALL_ATP_TOURNEY_RAW_NAMES = set()
for _names in TOURNAMENT_MAP.values():
    for _n in _names:
        _ALL_ATP_TOURNEY_RAW_NAMES.add(_norm_key(_n))


def load_data():
    global _cache
    if _cache is not None:
        return _cache

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = sorted(glob.glob(os.path.join(base, 'tennis_atp', 'atp_matches_*.csv')))
    # 只读 2009 年及以后
    files = [
        f for f in files
        if int(os.path.basename(f).replace('atp_matches_', '').replace('.csv', '')) >= 2009
    ]

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

    # 归一化赛事名，加一列 norm_tourney_name 用于匹配，原始名保留在 tourney_name
    data['norm_tourney_name'] = data['tourney_name'].map(_norm_key)

    # 解析日期
    data['tourney_date'] = pd.to_datetime(
        data['tourney_date'].str.replace('/', '-', regex=False),
        errors='coerce'
    )
    data = data.dropna(subset=['tourney_date'])
    data['year'] = data['tourney_date'].dt.year.astype(int)

    # 只保留 ATP 大赛，减小后续过滤量
    data = data[data['norm_tourney_name'].isin(_ALL_ATP_TOURNEY_RAW_NAMES)].copy()

    _cache = data
    return _cache


def safe_rank(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except Exception:
        return None


def get_history(player, tournament):
    data = load_data()
    if data is None:
        return None

    # 赛事名映射
    tourney_names = TOURNAMENT_MAP.get(tournament)
    if not tourney_names:
        return None

    # 用归一化后的名字过滤
    norm_names = {_norm_key(n) for n in tourney_names}
    df = data[data['norm_tourney_name'].isin(norm_names)].copy()

    # 过滤出该球员参与的比赛
    player_matches = df[
        (df['winner_name'] == player) | (df['loser_name'] == player)
    ].copy()

    if player_matches.empty:
        return []

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
            'tourney_name': row['tourney_name'],       # 原始名（Toronto / Montreal / Canada Masters…）
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
            self.wfile.write(json.dumps(
                {'error': 'player and tournament parameters required'}
            ).encode())
            return

        matches = get_history(player, tournament)

        if matches is None:
            self.wfile.write(json.dumps({'error': 'unknown tournament'}).encode())
            return

        self.wfile.write(json.dumps({
            'player': player,
            'tournament': tournament,
            'tour': 'atp',
            'total_matches': len(matches),
            'matches': matches,
        }, allow_nan=False).encode())

    def log_message(self, format, *args):
        pass