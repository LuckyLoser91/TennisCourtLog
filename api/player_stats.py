from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, glob, os
import pandas as pd

_cache = None

def load_wta_data():
    global _cache
    if _cache is not None:
        return _cache
    
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = sorted(glob.glob(os.path.join(base, 'tennis_wta', 'wta_matches_*.csv')))
    
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
    data = data.sort_values('tourney_date').reset_index(drop=True)
    
    _cache = data
    return _cache


def safe(val):
    if pd.isna(val):
        return None
    return str(val)

def safe_rank(val):
    if pd.isna(val):
        return None
    try:
        return int(float(val))
    except:
        return None


def compute_rolling(player, window=20):
    data = load_wta_data()
    if data is None:
        return None
    
    wins = data[data['winner_name'] == player][
        ['tourney_date','tourney_name','tourney_level','surface','round','loser_name','winner_rank','loser_rank','score']
    ].copy()
    wins['result'] = 1
    wins = wins.rename(columns={'loser_name': 'opponent', 'winner_rank': 'player_rank', 'loser_rank': 'opponent_rank'})

    losses = data[data['loser_name'] == player][
        ['tourney_date','tourney_name','tourney_level','surface','round','winner_name','loser_rank','winner_rank','score']
    ].copy()
    losses['result'] = 0
    losses = losses.rename(columns={'winner_name': 'opponent', 'loser_rank': 'player_rank', 'winner_rank': 'opponent_rank'})

    matches = pd.concat([wins, losses], ignore_index=True)
    matches = matches.sort_values('tourney_date').reset_index(drop=True)
    
    if len(matches) < 5:
        return None
    
    matches['rolling_win_rate'] = (
        matches['result']
        .rolling(window=window, min_periods=min(window, len(matches)))
        .mean()
        .round(4)
    )
    
    result = []
    for _, row in matches.iterrows():
        result.append({
            'date': row['tourney_date'].strftime('%Y-%m-%d'),
            'tournament': safe(row['tourney_name']),
            'level': safe(row['tourney_level']),
            'surface': safe(row['surface']),
            'round': safe(row['round']),
            'opponent': safe(row['opponent']),
            'opponent_rank': safe_rank(row['opponent_rank']),
            'score': safe(row['score']),
            'result': int(row['result']),
            'rolling_win_rate': round(float(row['rolling_win_rate']), 4) if pd.notna(row['rolling_win_rate']) else None,
        })
    
    return result


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        player = params.get('player', [None])[0]
        window = int(params.get('window', ['20'])[0])
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if not player:
            self.wfile.write(json.dumps({'error': 'player parameter required'}).encode())
            return
        
        data = compute_rolling(player, window)
        
        if data is None:
            self.wfile.write(json.dumps({'error': 'player not found or insufficient data'}).encode())
            return
        
        self.wfile.write(json.dumps({
            'player': player,
            'window': window,
            'total_matches': len(data),
            'matches': data
        }, allow_nan=False).encode())
    
    def log_message(self, format, *args):
        pass