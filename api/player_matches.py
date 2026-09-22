from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, os
import unicodedata
import pandas as pd
from datetime import datetime

# (tour, year) -> DataFrame | None
_cache = {}
# (tour, player_norm, mode, year) -> result dict
_player_cache = {}

ROUND_ORDER = {'RR': 0, 'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4, 'QF': 5, 'SF': 6, 'F': 7}
CAREER_START_YEAR = 2009

WTA_LEVEL_LABEL = {
    'G':  'Grand Slam',
    'PM': 'WTA 1000',
    'P':  'WTA 500/700',
    'IT': 'WTA 250',
    'F':  'WTA Finals',
}
ATP_LEVEL_LABEL = {
    'G': 'Grand Slam',
    'M': 'ATP 1000',
    'A': 'ATP 500 / 250',
    'F': 'ATP Finals',
    'D': 'Davis Cup',
}


def normalize_name(s):
    if s is None:
        return ''
    s = str(s)
    if not s or s.lower() == 'nan':
        return ''
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.strip().lower()


def safe_int(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    try:
        return int(float(val))
    except Exception:
        return None


def safe_str(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    if not s or s.lower() == 'nan':
        return None
    return s


def get_csv_path(tour, year):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if tour == 'atp':
        folder, prefix = 'tennis_atp', 'atp_matches'
    else:
        folder, prefix = 'tennis_wta', 'wta_matches'
    return os.path.join(base, folder, f'{prefix}_{year}.csv')


def load_year(tour, year):
    key = (tour, year)
    if key in _cache:
        return _cache[key]

    path = get_csv_path(tour, year)
    if not os.path.exists(path):
        _cache[key] = None
        return None

    try:
        df = pd.read_csv(path, dtype=str)
    except Exception:
        _cache[key] = None
        return None

    if 'tourney_date' not in df.columns or 'winner_name' not in df.columns:
        _cache[key] = None
        return None

    # 日期解析：兼容 YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD
    raw = df['tourney_date'].astype(str).str.replace(r'\D', '', regex=True)
    df['tourney_date'] = pd.to_datetime(raw, errors='coerce', format='%Y%m%d')
    df = df.dropna(subset=['tourney_date']).copy()
    if df.empty:
        _cache[key] = df
        return df

    df['_w_norm'] = df['winner_name'].fillna('').map(normalize_name)
    df['_l_norm'] = df['loser_name'].fillna('').map(normalize_name)

    _cache[key] = df
    return df


def extract_matches(sub_df, player_norm, tour):
    level_map = WTA_LEVEL_LABEL if tour == 'wta' else ATP_LEVEL_LABEL
    matches = []
    for _, row in sub_df.iterrows():
        is_win = row['_w_norm'] == player_norm
        opponent = row['loser_name'] if is_win else row['winner_name']
        opp_rank = safe_int(row.get('loser_rank') if is_win else row.get('winner_rank'))
        p_rank = safe_int(row.get('winner_rank') if is_win else row.get('loser_rank'))
        level_raw = safe_str(row.get('tourney_level'))
        level_label = level_map.get(level_raw, level_raw) if level_raw else None

        matches.append({
            'year': int(row['tourney_date'].year),
            'tourney_date': row['tourney_date'].strftime('%Y-%m-%d'),
            'tourney_name': safe_str(row.get('tourney_name')),
            'tourney_level': level_raw,
            'level_label': level_label,
            'surface': safe_str(row.get('surface')),
            'round': safe_str(row.get('round')),
            'result': 'W' if is_win else 'L',
            'player_rank': p_rank,
            'opponent': safe_str(opponent),
            'opponent_rank': opp_rank,
            'score': safe_str(row.get('score')),
        })

    matches.sort(key=lambda m: (
        m['tourney_date'],
        ROUND_ORDER.get(m['round'] or '', 0)
    ))
    return matches


def find_player_matches(tour, year, player_norm):
    df = load_year(tour, year)
    if df is None or df.empty:
        return None
    mask = (df['_w_norm'] == player_norm) | (df['_l_norm'] == player_norm)
    return df[mask]


def get_career_matches(tour, player_norm, current_year):
    key = (tour, player_norm, 'career', 0)
    if key in _player_cache:
        return _player_cache[key]

    all_matches = []
    seasons = []
    for year in range(CAREER_START_YEAR, current_year + 1):
        sub = find_player_matches(tour, year, player_norm)
        if sub is None or sub.empty:
            continue
        seasons.append(year)
        all_matches.extend(extract_matches(sub, player_norm, tour))

    result = {'matches': all_matches, 'seasons': sorted(seasons, reverse=True)}
    _player_cache[key] = result
    return result


def get_season_matches(tour, player_norm, year):
    key = (tour, player_norm, 'season', year)
    if key in _player_cache:
        return _player_cache[key]

    sub = find_player_matches(tour, year, player_norm)
    if sub is None:
        return None
    matches = extract_matches(sub, player_norm, tour)
    result = {'matches': matches, 'seasons': [year]}
    _player_cache[key] = result
    return result


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        player = params.get('player', [None])[0]
        tour = (params.get('tour', ['wta'])[0] or 'wta').lower()
        mode = (params.get('mode', ['career'])[0] or 'career').lower()
        year_s = params.get('year', [None])[0]

        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        def send_err(msg):
            self.wfile.write(json.dumps({'error': msg}, ensure_ascii=False).encode())

        if not player:
            return send_err('player parameter is required')
        if tour not in ('wta', 'atp'):
            return send_err('tour must be wta or atp')
        if mode not in ('career', 'season'):
            return send_err('mode must be career or season')

        player_norm = normalize_name(player)
        if not player_norm:
            return send_err('invalid player name')

        current_year = datetime.now().year

        if mode == 'career':
            data = get_career_matches(tour, player_norm, current_year)
            matches = data['matches']
            seasons = data['seasons']
        else:
            if not year_s:
                return send_err('year is required for season mode')
            try:
                year = int(year_s)
            except ValueError:
                return send_err('year must be an integer')
            data = get_season_matches(tour, player_norm, year)
            if data is None:
                return send_err(f'no data file for year {year}')
            matches = data['matches']
            seasons = data['seasons']

        wins = sum(1 for m in matches if m['result'] == 'W')
        losses = sum(1 for m in matches if m['result'] == 'L')

        payload = {
            'player': player,
            'tour': tour,
            'mode': mode,
            'seasons': seasons,
            'total_matches': len(matches),
            'wins': wins,
            'losses': losses,
            'matches': matches,
        }
        self.wfile.write(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode())

    def log_message(self, format, *args):
        pass