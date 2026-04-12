"""
非大满贯冠军大满贯战绩排行榜（按胜率排序，Top 100）
====================================================
统计所有未曾赢得大满贯冠军的球员在大满贯赛事中的战绩，
按总胜率降序展示前100名（总胜场 > 5）。支持巡回赛切换、活跃球员筛选、累加式排序。

输出：./analysis/leaderboards/tour_gs_champions_non.html 等

依赖：pip install pandas
用法：python non_gs_champions_leaderboard.py
"""

import os
import pandas as pd
from scripts.config import PROJECT_ROOT, DATA_PATHS


# ══════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════
OUTPUT_DIR = PROJECT_ROOT / "./analysis/leaderboards"
GS_TIER = "Grand Slam"

SLAMS = {
    "AO":  ["Australian Open", "Australian Open 2"],
    "RG":  ["Roland Garros"],
    "WIM": ["Wimbledon"],
    "USO": ["US Open"],
}

# 轮次优先级（数值越小成绩越好）
ROUND_ORDER = {
    'W': 1,
    'F': 2,
    'SF': 3,
    'QF': 4,
    'R16': 5,
    'R32': 6,
    'R64': 7,
    'R128': 8,
}

ROUND_DISPLAY = {
    'W': 'W',
    'F': 'F',
    'SF': 'SF',
    'QF': 'QF',
    'R16': 'R16',
    'R32': 'R32',
    'R64': 'R64',
    'R128': 'R128',
}


# ══════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════
def get_slam_key(tournament_name):
    if pd.isna(tournament_name):
        return None
    t = str(tournament_name).strip()
    for key, keywords in SLAMS.items():
        if any(kw.lower() in t.lower() for kw in keywords):
            return key
    return None


def normalize_round(r):
    if pd.isna(r):
        return None
    r_str = str(r).strip().upper()
    if r_str in ROUND_ORDER:
        return r_str
    if r_str.startswith('R') and r_str[1:].isdigit():
        return r_str
    mapping = {
        'FINAL': 'F', 'FINALS': 'F',
        'SEMIFINAL': 'SF', 'SEMI FINAL': 'SF', 'SEMIS': 'SF',
        'QUARTERFINAL': 'QF', 'QUARTER FINAL': 'QF', 'QUARTERS': 'QF',
        '4TH ROUND': 'R16', '3RD ROUND': 'R32', '2ND ROUND': 'R64', '1ST ROUND': 'R128',
        'ROUND OF 16': 'R16', 'ROUND OF 32': 'R32',
        'ROUND OF 64': 'R64', 'ROUND OF 128': 'R128',
    }
    for k, v in mapping.items():
        if k in r_str:
            return v
    return None


def round_rank(r):
    if r is None:
        return 999
    return ROUND_ORDER.get(r, 999)


# ══════════════════════════════════════════════════════════════
# 颜色工具
# ══════════════════════════════════════════════════════════════
def rate_to_bg(v, lo=70, hi=90):
    if v is None or v < lo:
        return "transparent", "#6b7280"
    if v < 80:
        t = (v - lo) / (80 - lo)
        t = max(0.0, min(1.0, t))
        r = int(253 + t * (217 - 253))
        g = int(230 + t * (119 - 230))
        b = int(138 + t * (6 - 138))
        fc = "#111111"
    else:
        t = (v - 80) / (hi - 80)
        t = max(0.0, min(1.0, t))
        r = int(110 + t * (4 - 110))
        g = int(231 + t * (120 - 231))
        b = int(183 + t * (87 - 183))
        fc = "#111111" if t < 0.5 else "#ffffff"
    return f"rgb({r},{g},{b})", fc


def agg_bg(v):
    bg, fc = rate_to_bg(v, lo=70, hi=90)
    return bg, fc


def surf_bg(v):
    bg, fc = rate_to_bg(v, lo=70, hi=95)
    return bg, fc


# ══════════════════════════════════════════════════════════════
# 计算单个非冠军球员战绩
# ══════════════════════════════════════════════════════════════
def calc_non_champion_stats(gs, player):
    wins = gs[(gs["winner_name"] == player) & (gs["score"] != "W/O")].copy()
    losses = gs[(gs["loser_name"] == player) & (gs["score"] != "W/O")].copy()

    W, L = len(wins), len(losses)
    if W + L == 0:
        return None

    agg = round(W / (W + L) * 100, 1)

    def surf_wr(surface):
        sw = wins[wins["surface"].astype(str).str.lower() == surface.lower()]
        sl = losses[losses["surface"].astype(str).str.lower() == surface.lower()]
        t = len(sw) + len(sl)
        return round(len(sw) / t * 100) if t > 0 else None

    wins["_slam"] = wins["tourney_name"].apply(get_slam_key)
    losses["_slam"] = losses["tourney_name"].apply(get_slam_key)

    wins["_round_norm"] = wins["round"].apply(normalize_round)
    losses["_round_norm"] = losses["round"].apply(normalize_round)

    all_matches = pd.concat([
        wins[["_slam", "_round_norm"]],
        losses[["_slam", "_round_norm"]]
    ])

    slam_best = {}
    for slam in ["AO", "RG", "WIM", "USO"]:
        slam_rounds = all_matches[all_matches["_slam"] == slam]["_round_norm"]
        if slam_rounds.empty:
            slam_best[slam] = None
        else:
            best = min(slam_rounds, key=lambda x: round_rank(x))
            slam_best[slam] = best

    all_rounds = all_matches["_round_norm"].dropna()
    best_overall = min(all_rounds, key=lambda x: round_rank(x)) if not all_rounds.empty else None

    def format_best(round_key):
        if round_key is None:
            return "—"
        return ROUND_DISPLAY.get(round_key, round_key)

    best_display = format_best(best_overall)
    ao_best = format_best(slam_best.get("AO"))
    rg_best = format_best(slam_best.get("RG"))
    wim_best = format_best(slam_best.get("WIM"))
    uso_best = format_best(slam_best.get("USO"))

    best_rank = round_rank(best_overall)

    combined_years = pd.concat([wins["year"], losses["year"]])
    last_year = int(combined_years.max()) if not combined_years.empty else 0
    last_win_year = int(wins["year"].max()) if not wins.empty else 0

    return {
        "W": W, "L": L,
        "agg": agg,
        "win_h": surf_wr("Hard"),
        "win_c": surf_wr("Clay"),
        "win_g": surf_wr("Grass"),
        "best_display": best_display,
        "best_rank": best_rank,
        "ao_best": ao_best,
        "rg_best": rg_best,
        "wim_best": wim_best,
        "uso_best": uso_best,
        "last_year": last_year,
        "last_win_year": last_win_year,
    }


# ══════════════════════════════════════════════════════════════
# 主处理函数
# ══════════════════════════════════════════════════════════════
def get_non_champions_leaderboard(tour='wta'):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    gs_data_path = DATA_PATHS[tour]['gs_matches']
    gs = pd.read_csv(gs_data_path)

    # 找出所有大满贯冠军
    finals = gs[gs["round"].astype(str).str.strip() == 'F'].copy()
    champions = set(finals["winner_name"].unique()) if not finals.empty else set()

    # 所有球员
    all_players = set(gs["winner_name"].dropna().unique()) | set(gs["loser_name"].dropna().unique())
    non_champions = all_players - champions

    print(f"🏆 {tour.upper()} 冠军人数: {len(champions)}")
    print(f"👥 非冠军球员总数: {len(non_champions)}")

    # 使用 groupby 计算每位球员的总胜场数（排除 Walkover）
    valid_matches = gs[gs["score"] != "W/O"]
    win_counts = valid_matches[valid_matches["winner_name"].isin(non_champions)].groupby("winner_name").size()
    players_gt5_wins = set(win_counts[win_counts > 5].index)

    print(f"📊 非冠军球员中总胜场 > 5 的人数: {len(players_gt5_wins)}")

    data_year_max = gs["year"].max()
    rows = []
    for player in players_gt5_wins:
        stats = calc_non_champion_stats(gs, player)
        if stats:
            rows.append({"player": player, "stats": stats})

    # 按总胜率降序排序，取前100名
    rows.sort(key=lambda r: -r["stats"]["agg"])
    rows = rows[:100]
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    print(f"✅ 最终生成 Top {len(rows)} 非冠军球员榜单")
    return rows, data_year_max


# ══════════════════════════════════════════════════════════════
# HTML 生成函数
# ══════════════════════════════════════════════════════════════
def build_non_gs_leaderboard(rows_dict, data_years, output_path):
    tours = list(rows_dict.keys())

    import json

    def rows_to_js(rows):
        arr = []
        for e in rows:
            s = e["stats"]
            arr.append([
                e['rank'],
                e['player'],
                s['best_display'],
                s['best_rank'],
                s['ao_best'],
                s['rg_best'],
                s['wim_best'],
                s['uso_best'],
                s['W'],
                s['L'],
                s['agg'] if s['agg'] is not None else None,
                s['win_h'] if s['win_h'] is not None else None,
                s['win_c'] if s['win_c'] is not None else None,
                s['win_g'] if s['win_g'] is not None else None,
                s['last_win_year'],
            ])
        return json.dumps(arr)

    js_data = {tour: rows_to_js(rows_dict[tour]) for tour in tours}
    max_years = {tour: data_years[tour] for tour in tours}
    options = "\n".join(
        f'<option value="{tour}" {"selected" if i==0 else ""}>{tour.upper()}</option>'
        for i, tour in enumerate(tours)
    )

    hide_selector = len(tours) == 1
    selector_style = 'style="display:none;"' if hide_selector else ''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Non-GS Champions · GS Win Rate Top 100</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #111827;
      font-family: 'Segoe UI', Arial, sans-serif;
      padding: 36px 44px 60px;
      min-width: 1200px;
    }}
    h1 {{ color: #f5c842; font-size: 22px; font-weight: 800; margin-bottom: 6px; }}
    .sub {{
      color: #6b7280; font-size: 11px; letter-spacing: 0.07em;
      text-transform: uppercase; margin-bottom: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .sub span {{ color: #f5c842; }}
    .controls {{
      display: flex;
      align-items: center;
      gap: 24px;
    }}
    .tour-selector {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .tour-selector label {{ color: #9ca3af; font-size: 12px; }}
    .tour-selector select {{
      background: #1f2937;
      color: #f3f4f6;
      border: 1px solid #374151;
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      outline: none;
    }}
    .tour-selector select:hover {{ border-color: #f5c842; }}
    .active-toggle {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .active-toggle label {{
      color: #9ca3af;
      font-size: 12px;
      cursor: pointer;
    }}
    .active-toggle input {{
      accent-color: #f5c842;
      width: 16px;
      height: 16px;
      cursor: pointer;
    }}
    table {{ border-collapse: collapse; width: 100%; }}
    thead tr {{ border-bottom: 1px solid #374151; }}
    thead th {{
      color: #6b7280; font-size: 10px; font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase;
      padding: 5px 6px 9px; text-align: center; white-space: nowrap;
    }}
    thead th.left {{ text-align: left; padding-left: 8px; }}
    thead .gr th {{
      color: #4b5563; font-size: 9px; border-bottom: none; padding-bottom: 2px;
    }}
    .dl {{ border-left: 1px solid #374151; }}
    tbody tr {{ border-bottom: 1px solid #1f2937; }}
    tbody tr:hover {{ background: #1f2937; }}
    tbody td {{ padding: 6px 6px; font-size: 12px; }}
    tfoot td {{
      padding-top: 20px; color: #4b5563;
      font-size: 10px; letter-spacing: 0.04em;
    }}
    th.sortable {{
      cursor: pointer;
      user-select: none;
      transition: color 0.15s;
    }}
    th.sortable:hover {{
      color: #f5c842;
    }}
    .sort-indicator {{
      display: inline-block;
      margin-left: 4px;
      font-size: 9px;
      color: #f5c842;
    }}
  </style>
</head>
<body>

<h1>Grand Slam Singles · Non-Champions Leaderboard (Top 100 by Win%, Wins > 5)</h1>
<div class="sub">
  <div>
    <span id="champion-count">0 players</span> &nbsp;|&nbsp;
    Grand Slam matches only &nbsp;|&nbsp;
    Walkovers excluded &nbsp;|&nbsp;
    <span style="color:#9ca3af;">Click headers to sort</span>
  </div>
  <div class="controls">
    <div class="active-toggle">
      <input type="checkbox" id="activeOnlyCheckbox">
      <label for="activeOnlyCheckbox">🎾 ACTIVE ONLY (won GS match in last 2 years)</label>
    </div>
    <div class="tour-selector" {selector_style}>
      <label for="tourSelect">TOUR:</label>
      <select id="tourSelect">
        {options}
      </select>
    </div>
  </div>
</div>

<table>
  <thead>
    <tr class="gr">
      <th colspan="3"></th>
      <th colspan="4" style="text-align:center;color:#9ca3af;">BEST RESULT (BY SLAM)</th>
      <th colspan="2"></th>
      <th colspan="4" class="dl" style="text-align:center;color:#9ca3af;">WINRATE</th>
    </tr>
    <tr>
      <th>#</th>
      <th class="left sortable" data-col="player">PLAYER</th>
      <th class="sortable" data-col="best">BEST</th>
      <th class="sortable" data-col="AO">AO</th>
      <th class="sortable" data-col="RG">RG</th>
      <th class="sortable" data-col="WIM">WIM</th>
      <th class="sortable" data-col="USO">USO</th>
      <th class="sortable" data-col="W">W</th>
      <th class="sortable" data-col="L">L</th>
      <th class="dl sortable" data-col="agg">AGG</th>
      <th class="sortable" data-col="hard">H</th>
      <th class="sortable" data-col="clay">C</th>
      <th class="sortable" data-col="grass">G</th>
    </tr>
  </thead>
  <tbody id="table-body"></tbody>
  <tfoot>
    <tr><td colspan="13" id="table-footer"></td></tr>
  </tfoot>
</table>

<script>
  const dataMap = {{
    {", ".join(f'"{tour}": {js_data[tour]}' for tour in tours)}
  }};
  const maxYears = {json.dumps(max_years)};

  const footerText = `        BEST = Career best GS result &nbsp;·&nbsp;
        AO/RG/WIM/USO = Best result at each major &nbsp;·&nbsp;
        W = Winner · F = Final · SF = Semi-final · QF = Quarter-final · R16/R32/R64/R128 &nbsp;·&nbsp; <br>
        AGG = aggregate GS win rate &nbsp;·&nbsp;
        H = Hard · C = Clay · G = Grass &nbsp;·&nbsp;
        Win rate: ≥70% <span style="color:#e8a838">■</span> ≥80% <span style="color:#2dd4b0">■</span>`;

  // ---------- 颜色函数 ----------
  function aggBg(pct) {{
    if (pct === null) return 'transparent';
    if (pct >= 90) return 'rgb(4,120,87)';
    if (pct >= 85) return 'rgb(7,123,89)';
    if (pct >= 80) return 'rgb(42,159,121)';
    if (pct >= 75) return 'rgb(227,152,45)';
    if (pct >= 70) return 'rgb(247,213,118)';
    return 'transparent';
  }}
  function aggColor(pct) {{
    if (pct === null) return '#6b7280';
    if (pct >= 85) return '#ffffff';
    if (pct >= 70) return '#111111';
    return '#6b7280';
  }}
  function surfBg(pct) {{
    if (pct === null) return 'transparent';
    if (pct >= 90) return 'rgb(4,120,87)';
    if (pct >= 85) return 'rgb(39,157,119)';
    if (pct >= 80) return 'rgb(67,186,144)';
    if (pct >= 75) return 'rgb(235,174,72)';
    if (pct >= 70) return 'rgb(249,218,124)';
    return 'transparent';
  }}
  function surfColor(pct) {{
    if (pct === null) return '#6b7280';
    if (pct >= 85) return '#ffffff';
    if (pct >= 75) return '#111111';
    if (pct >= 70) return '#111111';
    return '#6b7280';
  }}

  function fmt(val) {{
    return (val === null || val === undefined) ? '—' : val + '%';
  }}

  // ---------- 排序状态 ----------
  let sortState = [{{ col: 'agg', order: 'desc' }}];
  let userSorted = false;
  let currentTour = '{tours[0]}';
  let activeOnly = false;

  const colIndex = {{
    'player': 1,
    'best': 3,
    'AO': 4,
    'RG': 5,
    'WIM': 6,
    'USO': 7,
    'W': 8,
    'L': 9,
    'agg': 10,
    'hard': 11,
    'clay': 12,
    'grass': 13,
  }};

  const roundRank = {{
    'W': 1, 'F': 2, 'SF': 3, 'QF': 4, 'R16': 5, 'R32': 6, 'R64': 7, 'R128': 8, '—': 999
  }};

  function getRoundValue(val) {{
    if (val === null || val === undefined) return 999;
    return roundRank[val] || 999;
  }}

  function compareValues(a, b, col, order) {{
    let valA, valB;
    if (col === 'AO' || col === 'RG' || col === 'WIM' || col === 'USO') {{
      const idx = colIndex[col];
      valA = getRoundValue(a[idx]);
      valB = getRoundValue(b[idx]);
    }} else if (col === 'best') {{
      valA = a[colIndex[col]];
      valB = b[colIndex[col]];
    }} else {{
      valA = a[colIndex[col]];
      valB = b[colIndex[col]];
    }}
    
    const isNullA = valA === null || valA === undefined;
    const isNullB = valB === null || valB === undefined;
    if (isNullA && isNullB) return 0;
    if (isNullA) return 1;
    if (isNullB) return -1;
    
    if (col === 'player') {{
      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
    }} else {{
      valA = Number(valA);
      valB = Number(valB);
    }}
    
    if (valA < valB) return order === 'asc' ? -1 : 1;
    if (valA > valB) return order === 'asc' ? 1 : -1;
    return 0;
  }}

  function sortRows(rows) {{
    if (!sortState.length) return rows;
    return [...rows].sort((a, b) => {{
      for (let rule of sortState) {{
        const cmp = compareValues(a, b, rule.col, rule.order);
        if (cmp !== 0) return cmp;
      }}
      return 0;
    }});
  }}

  function updateSortIndicators() {{
    document.querySelectorAll('.sortable').forEach(th => {{
      const ind = th.querySelector('.sort-indicator');
      if (ind) ind.remove();
    }});
    if (!userSorted) return;
    if (sortState.length > 0) {{
      const primary = sortState[0];
      const th = document.querySelector(`th[data-col="${{primary.col}}"]`);
      if (th) {{
        const arrow = primary.order === 'asc' ? '▲' : '▼';
        const span = document.createElement('span');
        span.className = 'sort-indicator';
        span.textContent = ' ' + arrow;
        th.appendChild(span);
      }}
    }}
  }}

  function isActive(row) {{
    const maxYear = maxYears[currentTour];
    const lastWinYear = row[14];
    return (maxYear - lastWinYear) < 2;
  }}

  function renderTable() {{
    let rows = dataMap[currentTour] || [];
    if (activeOnly) {{
      rows = rows.filter(row => isActive(row));
    }}
    const sorted = sortRows(rows);
    
    const tbody = document.getElementById('table-body');
    const countSpan = document.getElementById('champion-count');
    const footerTd = document.getElementById('table-footer');
    
    countSpan.textContent = sorted.length + ' players';
    footerTd.innerHTML = footerText;

    let html = '';
    sorted.forEach((row, idx) => {{
      const [origRank, player, bestDisp, bestRank, ao, rg, wim, uso, W, L, agg, hard, clay, grass] = row;
      const aggBgColor = aggBg(agg);
      const aggTextColor = aggColor(agg);
      const hardBgColor = surfBg(hard);
      const hardTextColor = surfColor(hard);
      const clayBgColor = surfBg(clay);
      const clayTextColor = surfColor(clay);
      const grassBgColor = surfBg(grass);
      const grassTextColor = surfColor(grass);

      html += `<tr>
        <td style="color:#6b7280;text-align:center;font-size:11px;">${{idx + 1}}</td>
        <td style="color:#f3f4f6;font-weight:600;padding-left:8px;">${{player}}</td>
        <td style="text-align:center;color:#f5c842;font-weight:bold;">${{bestDisp}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{ao}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{rg}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{wim}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{uso}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{W}}</td>
        <td style="text-align:center;color:#6b7280;">${{L}}</td>
        <td style="text-align:center;background:${{aggBgColor}};color:${{aggTextColor}};">${{fmt(agg)}}</td>
        <td style="text-align:center;background:${{hardBgColor}};color:${{hardTextColor}};">${{fmt(hard)}}</td>
        <td style="text-align:center;background:${{clayBgColor}};color:${{clayTextColor}};">${{fmt(clay)}}</td>
        <td style="text-align:center;background:${{grassBgColor}};color:${{grassTextColor}};">${{fmt(grass)}}</td>
      </tr>`;
    }});
    tbody.innerHTML = html;
    updateSortIndicators();
  }}

  function handleSortClick(e) {{
    const th = e.currentTarget;
    const col = th.getAttribute('data-col');
    if (!col) return;
    userSorted = true;
    const existingIdx = sortState.findIndex(s => s.col === col);
    let newOrder = 'desc';
    if (existingIdx !== -1) {{
      newOrder = sortState[existingIdx].order === 'asc' ? 'desc' : 'asc';
    }}
    if (existingIdx !== -1) {{
      const [existing] = sortState.splice(existingIdx, 1);
      existing.order = newOrder;
      sortState.unshift(existing);
    }} else {{
      sortState.unshift({{ col, order: newOrder }});
    }}
    renderTable();
  }}

  function resetToDefault() {{
    sortState = [{{ col: 'agg', order: 'desc' }}];
    userSorted = false;
  }}

  document.querySelectorAll('.sortable').forEach(th => {{
    th.addEventListener('click', handleSortClick);
  }});

  const selectEl = document.getElementById('tourSelect');
  if (selectEl) {{
    selectEl.addEventListener('change', e => {{
      currentTour = e.target.value;
      resetToDefault();
      renderTable();
    }});
  }}

  const activeCheck = document.getElementById('activeOnlyCheckbox');
  activeCheck.addEventListener('change', e => {{
    activeOnly = e.target.checked;
    renderTable();
  }});

  renderTable();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已保存: {output_path}")


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    rows_atp, max_year_atp = get_non_champions_leaderboard(tour='atp')
    rows_wta, max_year_wta = get_non_champions_leaderboard(tour='wta')

    # 综合页面（WTA/ATP 切换）
    build_non_gs_leaderboard(
        {'wta': rows_wta, 'atp': rows_atp},
        {'wta': max_year_wta, 'atp': max_year_atp},
        output_path='./analysis/leaderboards/tour_non_gs_champions.html'
    )
    # 单独 WTA
    build_non_gs_leaderboard(
        {'wta': rows_wta},
        {'wta': max_year_wta},
        output_path='./analysis/leaderboards/wta_non_gs_champions.html'
    )
    # 单独 ATP
    build_non_gs_leaderboard(
        {'atp': rows_atp},
        {'atp': max_year_atp},
        output_path='./analysis/leaderboards/atp_non_gs_champions.html'
    )