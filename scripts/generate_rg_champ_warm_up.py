#!/usr/bin/env python3
"""
生成法网冠军的红土热身赛可视化报告（2000–2025）
输出 HTML 文件：scripts/rg_clay_warmup.html
"""

import pandas as pd
import os
from datetime import datetime

# ----------------------------- 路径设置 -----------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ATP_DIR = os.path.join(PROJECT_ROOT, 'tennis_atp')
WTA_DIR = os.path.join(PROJECT_ROOT, 'tennis_wta')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'rg_clay_warmup.html')

# 目标年份范围
START_YEAR = 2000
END_YEAR = 2025

# ----------------------------- 数据读取与处理 -----------------------------
def load_year_data(year):
    """加载指定年份的 ATP 和 WTA 数据，返回两个 DataFrame"""
    atp_path = os.path.join(ATP_DIR, f'atp_matches_{year}.csv')
    wta_path = os.path.join(WTA_DIR, f'wta_matches_{year}.csv')

    atp_df = pd.read_csv(atp_path) if os.path.exists(atp_path) else pd.DataFrame()
    wta_df = pd.read_csv(wta_path) if os.path.exists(wta_path) else pd.DataFrame()
    return atp_df, wta_df

def get_rg_final(df):
    """从 DataFrame 中筛选出法网决赛，返回 Series 或 None"""
    if df.empty:
        return None
    mask = (df['tourney_name'].str.contains('Roland Garros', case=False, na=False)) & \
           (df['round'] == 'F')
    finals = df[mask]
    if len(finals) == 0:
        return None
    return finals.iloc[0]
def get_clay_warmup_matches(df, player_name, rg_date):
    """
    获取某位选手在当年的全部红土比赛（包括法网）
    返回 DataFrame，包含所需字段
    """
    if df.empty:
        return pd.DataFrame()

    # 选手参与的比赛
    player_mask = (df['winner_name'] == player_name) | (df['loser_name'] == player_name)
    # 红土场地
    clay_mask = df['surface'] == 'Clay'

    # 解析法网开始日期，用于过滤法网之后的赛事
    def parse_date_only(x):
        s = str(int(x)) if isinstance(x, (int, float)) else str(x).strip()
        if '-' in s:
            s = s.replace('-', '')
        if '/' in s:
            parts = s.split('/')
            s = f"{int(parts[0]):04d}{int(parts[1]):02d}{int(parts[2]):02d}"
        return int(s)
    
    rg_date_int = parse_date_only(rg_date)
    
    matches = df[player_mask & clay_mask].copy()
    
    # 只保留法网及之前的赛事（过滤法网之后的红土赛事）
    matches['_date_int'] = matches['tourney_date'].apply(parse_date_only)
    matches = matches[matches['_date_int'] <= rg_date_int]
    if matches.empty:
        return pd.DataFrame()

    # 为每场比赛标记该选手是赢还是输，并提取对手姓名和比分
    matches['result'] = matches.apply(
        lambda row: 'Win' if row['winner_name'] == player_name else 'Loss', axis=1
    )
    matches['opponent'] = matches.apply(
        lambda row: row['loser_name'] if row['winner_name'] == player_name else row['winner_name'],
        axis=1
    )
    # 日期格式化为可读字符串
    def format_date(x):
        s = str(int(x)) if isinstance(x, (int, float)) else str(x).strip()
        if '-' in s:
            return datetime.strptime(s, '%Y-%m-%d').strftime('%Y-%m-%d')
        if '/' in s:
            return datetime.strptime(s, '%Y/%m/%d').strftime('%Y-%m-%d')
        else:
            return datetime.strptime(s, '%Y%m%d').strftime('%Y-%m-%d')
    
    matches['date_str'] = matches['tourney_date'].apply(format_date)
    
    # 按日期升序排列
    def parse_date(x):
        s = str(int(x)) if isinstance(x, (int, float)) else str(x).strip()
        if '-' in s:
            s = s.replace('-', '')
        if '/' in s:
            parts = s.split('/')
            s = f"{int(parts[0]):04d}{int(parts[1]):02d}{int(parts[2]):02d}"
        return int(s)
    
    matches['date_int'] = matches['tourney_date'].apply(parse_date).astype(int)
    # 定义轮次排序权重（越大越靠后，决赛权重最大）
    round_order = {
        'R128': 1, 'R64': 2, 'R32': 3, 'R16': 4,
        'QF': 5, 'SF': 6, 'F': 7
    }
    matches['round_order'] = matches['round'].map(round_order).fillna(0)
    # 确保 date_int 是整数
    matches['date_int'] = matches['date_int'].astype(int)
    # 先按日期倒序（最新的在前），再按轮次倒序（决赛在前）
    matches.sort_values(['date_int', 'round_order'], ascending=[False, False], inplace=True)

     # 只保留需要显示的列
    display_cols = ['date_str', 'tourney_name', 'round', 'opponent', 'result', 'score']
    return matches[display_cols]

def build_champions_data():
    """构建冠军热身数据列表"""
    champions = []

    for year in range(END_YEAR, START_YEAR - 1, -1):
        atp_df, wta_df = load_year_data(year)

        # 处理 ATP 冠军
        atp_final = get_rg_final(atp_df)
        if atp_final is not None:
            champ_name = atp_final['winner_name']
            rg_date = atp_final['tourney_date']
            warmup = get_clay_warmup_matches(atp_df, champ_name, rg_date)
            champions.append({
                'year': year,
                'sex': 'ATP',
                'champion': champ_name,
                'rg_date': rg_date,
                'warmup_df': warmup
            })

        # 处理 WTA 冠军
        wta_final = get_rg_final(wta_df)
        if wta_final is not None:
            champ_name = wta_final['winner_name']
            rg_date = wta_final['tourney_date']
            warmup = get_clay_warmup_matches(wta_df, champ_name, rg_date)
            champions.append({
                'year': year,
                'sex': 'WTA',
                'champion': champ_name,
                'rg_date': rg_date,
                'warmup_df': warmup
            })

    return champions

# ----------------------------- HTML 生成 -----------------------------
def build_html(champions):
    """根据冠军数据生成完整的 HTML 字符串"""
    card_template = """
    <div class="card" data-sex="{sex}">
        <div class="card-header">
            <span class="year">{year}</span>
            <span class="sex {sex_class}">{sex}</span>
            <span class="name">{name}</span>
            <span class="record">{wins}W / {losses}L</span>
        </div>
        <div class="card-body">
            {table}
        </div>
    </div>
    """

    table_rows = """
    <tr class="{result_class}">
        <td>{date}</td>
        <td>{tourney}</td>
        <td>{round}</td>
        <td>{opponent}</td>
        <td class="result">{result}</td>
        <td>{score}</td>
    </tr>
    """

    cards_html = ""
    for champ in champions:
        df = champ['warmup_df']
        if df.empty:
            table = '<p class="no-data">No clay warm-up matches found.</p>'
            wins, losses = 0, 0
        else:
            rows = ""
            for _, row in df.iterrows():
                result_class = 'win' if row['result'] == 'Win' else 'loss'
                rows += table_rows.format(
                    date=row['date_str'],
                    tourney=row['tourney_name'],
                    round=row['round'],
                    opponent=row['opponent'],
                    result=row['result'],
                    score=row['score'],
                    result_class=result_class
                )
            table = f"""
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Tournament</th>
                        <th>Round</th>
                        <th>Opponent</th>
                        <th>Result</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            """
            wins = (df['result'] == 'Win').sum()
            losses = (df['result'] == 'Loss').sum()

        sex_class = 'atp' if champ['sex'] == 'ATP' else 'wta'
        cards_html += card_template.format(
            year=champ['year'],
            sex=champ['sex'],
            name=champ['champion'],
            wins=wins,
            losses=losses,
            sex_class=sex_class,
            table=table
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>French Open Champions - Clay Warm-up (2000–2025)</title>
<style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 2rem;
        background: #f5f5f5;
        color: #333;
    }}
    h1 {{
        text-align: center;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }}
    .filter-bar {{
        text-align: center;
        margin: 1.5rem 0;
    }}
    .filter-bar button {{
        padding: 0.6rem 2rem;
        margin: 0 0.5rem;
        border: 2px solid #ccc;
        border-radius: 8px;
        background: white;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }}
    .filter-bar button:hover {{
        border-color: #3498db;
    }}
    .filter-bar button.active {{
        background: #3498db;
        color: white;
        border-color: #3498db;
    }}
    .card {{
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 1.5rem 0;
        overflow: hidden;
        transition: all 0.3s;
    }}
    .card.hidden {{
        display: none;
    }}
    .card-header {{
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.5rem;
        background: linear-gradient(135deg, #2c3e50, #3498db);
        color: white;
        font-size: 1.2rem;
    }}
    .card-header .year {{
        font-weight: bold;
        font-size: 1.5rem;
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 8px;
    }}
    .card-header .sex {{
        font-weight: bold;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }}
    .atp {{ background: #e67e22; color: white; }}
    .wta {{ background: #9b59b6; color: white; }}
    .card-header .name {{
        font-weight: 600;
    }}
    .record {{
        margin-left: auto;
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 8px;
    }}
    .card-body {{
        padding: 1rem 1.5rem;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.5rem;
    }}
    th {{
        text-align: left;
        background: #ecf0f1;
        padding: 0.5rem;
        font-size: 0.9rem;
    }}
    td {{
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #eee;
    }}
    .win td.result {{
        color: #27ae60;
        font-weight: bold;
    }}
    .loss td.result {{
        color: #e74c3c;
        font-weight: bold;
    }}
    .win {{
        border-left: 4px solid #27ae60;
    }}
    .loss {{
        border-left: 4px solid #e74c3c;
    }}
    .no-data {{
        font-style: italic;
        color: #777;
        padding: 0.5rem;
    }}
    footer {{
        text-align: center;
        margin-top: 3rem;
        color: #aaa;
        font-size: 0.9rem;
    }}
</style>
</head>
<body>
    <h1>🇫🇷 French Open Champions - Clay Warm-up <small>(2000–2025)</small></h1>
    <div class="filter-bar">
        <button id="btn-all" class="active" onclick="filter('all')">All</button>
        <button id="btn-atp" onclick="filter('ATP')">ATP</button>
        <button id="btn-wta" onclick="filter('WTA')">WTA</button>
    </div>
    {cards_html}
    <footer>Generated on {datetime.now().strftime('%Y-%m-%d')} · Data source: TennisCourtLog</footer>
    <script>
        function filter(sex) {{
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                if (sex === 'all' || card.dataset.sex === sex) {{
                    card.classList.remove('hidden');
                }} else {{
                    card.classList.add('hidden');
                }}
            }});
            // 更新按钮状态
            document.querySelectorAll('.filter-bar button').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + sex).classList.add('active');
        }}
    </script>
</body>
</html>
"""
    return html

# ----------------------------- 主流程 -----------------------------
if __name__ == '__main__':
    print("🔄 正在读取数据并构建冠军热身报告...")
    champions = build_champions_data()
    html_content = build_html(champions)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    atp_count = sum(1 for c in champions if c['sex'] == 'ATP')
    wta_count = sum(1 for c in champions if c['sex'] == 'WTA')
    print(f"✅ 成功生成报告（ATP: {atp_count} 位, WTA: {wta_count} 位）")
    print(f"📄 文件位置：{OUTPUT_FILE}")