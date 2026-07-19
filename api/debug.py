from http.server import BaseHTTPRequestHandler
import json, glob, os
import pandas as pd

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        files = sorted(glob.glob(os.path.join(base, 'tennis_wta', 'wta_matches_*.csv')))
        
        samples = {}
        for f in files:
            year = os.path.basename(f).replace('wta_matches_','').replace('.csv','')
            try:
                df = pd.read_csv(f, dtype=str, nrows=1)
                samples[year] = df['tourney_date'].iloc[0] if len(df) > 0 else 'empty'
            except:
                samples[year] = 'error'
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(samples).encode())
    
    def log_message(self, format, *args):
        pass