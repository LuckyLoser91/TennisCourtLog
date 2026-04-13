"""
历史大满贯冠军 Leaderboard
================================
统计所有曾赢得过大满贯冠军的球员在大满贯赛事中的详细战绩
输出：./cur_output/tour_gs_champions.html

依赖：pip install pandas openpyxl
用法：python grandslam_champions_leaderboard.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from scripts.config import PROJECT_ROOT, DATA_PATHS


# ══════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════
GS_TIER     = "Grand Slam"

SLAMS = {
    "AO":  ["Australian Open", "Australian Open 2"],
    "RG":  ["Roland Garros"],
    "WIM": ["Wimbledon"],
    "USO": ["US Open"],
}

# IOC -> ISO2 映射（用于国旗 emoji），覆盖主要网球国家
IOC_TO_ISO2 = {
    "ARG": "AR", "AUS": "AU", "AUT": "AT", "BEL": "BE", "BLR": "BY",
    "BRA": "BR", "BUL": "BG", "CAN": "CA", "CHI": "CL", "CHN": "CN",
    "COL": "CO", "CRO": "HR", "CYP": "CY", "CZE": "CZ", "DEN": "DK",
    "ECU": "EC", "EGY": "EG", "ESP": "ES", "EST": "EE", "FIN": "FI",
    "FRA": "FR", "GBR": "GB", "GER": "DE", "GRE": "GR", "HUN": "HU",
    "IND": "IN", "IRL": "IE", "ISR": "IL", "ITA": "IT", "JPN": "JP",
    "KAZ": "KZ", "KOR": "KR", "LAT": "LV", "LTU": "LT", "LUX": "LU",
    "MAR": "MA", "MEX": "MX", "MDA": "MD", "MNE": "ME", "NED": "NL",
    "NZL": "NZ", "NOR": "NO", "PER": "PE", "POL": "PL", "POR": "PT",
    "ROU": "RO", "RSA": "ZA", "RUS": "RU", "SRB": "RS", "SVK": "SK",
    "SLO": "SI", "SWE": "SE", "SUI": "CH", "THA": "TH", "TUN": "TN",
    "TUR": "TR", "UKR": "UA", "URU": "UY", "USA": "US", "UZB": "UZ",
    "VEN": "VE", "ZIM": "ZW", "FRG": "DE", "URS": "RU"
}

def ioc_to_flag(ioc):
    """将 IOC 代码转为国旗图片 HTML"""
    if pd.isna(ioc) or not ioc:
        return '<span title="Unknown">🏳</span>'
    iso2 = IOC_TO_ISO2.get(ioc.upper().strip(), "")
    if not iso2:
        print(f"⚠️  未知 IOC 代码: {ioc}，使用 🏳")
        return '<span title="Unknown">🏳</span>'
    iso2_lower = iso2.lower()
    return f'<img src="https://flagcdn.com/16x12/{iso2_lower}.png" width="16" height="12" alt="{iso2}" title="{ioc}" style="vertical-align:middle;margin-right:6px;border-radius:1px;">'



def calc_age(birth_date, event_date):
    """
    计算年龄（年），保留一位小数。
    birth_date: datetime 对象或字符串 YYYY-MM-DD / YYYY/MM/DD
    event_date: 字符串，格式 YYYY/MM/DD（例如 1999/09/11）
    """
    try:
        if isinstance(birth_date, str):
            bd = datetime.strptime(birth_date.strip(), "%Y/%m/%d")
        else:
            bd = birth_date  # 假设已经是 datetime
        ed = datetime.strptime(event_date.strip(), "%Y/%m/%d")
        days = (ed - bd).days
        return round(days / 365.25, 1)
    except:
        return None


# ══════════════════════════════════════════════════════════════
# 2. 找出所有历史大满贯冠军及首冠年份
# ══════════════════════════════════════════════════════════════
def get_champions(gs):
    finals = gs[gs["round"].astype(str).str.strip() == 'F'].copy()
    if finals.empty:
        print(f"⚠️  未找到 Round='F' 的比赛")
        print(f"   round 唯一值: {gs['round'].dropna().unique().tolist()}")
        return {}
    first_title = finals.groupby("winner_name")["year"].min().to_dict()
    print(f"\n🏆 找到 {len(first_title)} 位历史大满贯冠军")
    return first_title


# ══════════════════════════════════════════════════════════════
# 3. 识别满贯归属
# ══════════════════════════════════════════════════════════════
def get_slam_key(tournament_name):
    if pd.isna(tournament_name):
        return None
    t = str(tournament_name).strip()
    for key, keywords in SLAMS.items():
        if any(kw.lower() in t.lower() for kw in keywords):
            return key
    return None


# ══════════════════════════════════════════════════════════════
# 4. 计算单个球员战绩
# ══════════════════════════════════════════════════════════════
def calc_stats(gs, player, first_year, player_info):
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
    finals_won = wins[wins["round"] == 'F']
    slam_titles = finals_won["_slam"].value_counts().to_dict()
    titles_total = sum(slam_titles.values())
    ao = slam_titles.get("AO", 0)
    rg = slam_titles.get("RG", 0)
    wim = slam_titles.get("WIM", 0)
    uso = slam_titles.get("USO", 0)

    parts = []
    if ao: parts.append(f"AO×{ao}")
    if rg: parts.append(f"RG×{rg}")
    if wim: parts.append(f"WIM×{wim}")
    if uso: parts.append(f"USO×{uso}")
    titles_str = "  ".join(parts) if parts else "—"

    # 最后夺冠年份 & 跨度
    last_year = int(finals_won["year"].max()) if not finals_won.empty else first_year
    span = last_year - first_year + 1

    # 年龄计算：需要比赛日期和出生日期
    info = player_info.get(player, {})
    dob = info.get("dob")
    age_first = None
    age_last = None

    if dob and not pd.isna(dob):
        # 首冠比赛日期
        first_final = finals_won[finals_won["year"] == first_year].iloc[0] if not finals_won[finals_won["year"] == first_year].empty else None
        if first_final is not None and "tourney_date" in first_final:
            age_first = calc_age(dob, first_final["tourney_date"])

        # 末冠比赛日期
        last_final = finals_won[finals_won["year"] == last_year].iloc[-1] if not finals_won[finals_won["year"] == last_year].empty else None
        if last_final is not None and "tourney_date" in last_final:
            age_last = calc_age(dob, last_final["tourney_date"])

    return {
        "W": W, "L": L,
        "titles": titles_total,
        "titles_str": titles_str,
        "agg": agg,
        "win_h": surf_wr("Hard"),
        "win_c": surf_wr("Clay"),
        "win_g": surf_wr("Grass"),
        "last_year": last_year,
        "span": span,
        "age_first": age_first,
        "age_last": age_last,
        "ioc": info.get("ioc"),
        "birth_year": info.get("birth_year"),
    }


# ══════════════════════════════════════════════════════════════
# 5. 颜色工具（保持不变）
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

def titles_bg(n):
    if n >= 10: return "#f5c842"
    if n >= 5:  return "#e8a838"
    if n >= 2:  return "#4a9eff"
    return "transparent"

def titles_fc(n):
    return "#111111" if n >= 2 else "#e5e5e5"


# ══════════════════════════════════════════════════════════════
# 6. 生成 HTML（后端拼接完整玩家显示名）
# ══════════════════════════════════════════════════════════════
def build_gs_leaderboard(rows_dict, output_path):
    tours = list(rows_dict.keys())

    import json

    def rows_to_js(rows):
        arr = []
        for e in rows:
            s = e["stats"]
            flag_emoji = ioc_to_flag(s.get('ioc', ''))
            birth_year = s.get('birth_year', '')
            birth_display = f" ({birth_year})" if birth_year else ""
            # 后端拼接完整显示名：国旗 + 名字 + (出生年份)
            player_display = f"{flag_emoji}{e['player']}{birth_display}"
            arr.append([
                e['rank'],
                player_display,                 # 直接包含国旗的完整字符串
                e['first_year'],
                s['age_first'] if s['age_first'] is not None else None,
                s['last_year'],
                s['age_last'] if s['age_last'] is not None else None,
                s['span'],
                s['titles'],
                s['titles_str'],
                s['W'],
                s['L'],
                s['agg'] if s['agg'] is not None else None,
                s['win_h'] if s['win_h'] is not None else None,
                s['win_c'] if s['win_c'] is not None else None,
                s['win_g'] if s['win_g'] is not None else None,
            ])
        return json.dumps(arr)

    js_data = {tour: rows_to_js(rows_dict[tour]) for tour in tours}
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
  <title>Grand Slam Champions · {" · ".join(t.upper() for t in tours)}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #111827;
      font-family: 'Segoe UI', 'Apple Color Emoji', 'Noto Color Emoji', 'EmojiOne Color', 'Twemoji Mozilla', sans-serif;
      padding: 36px 44px 60px;
      min-width: 1400px;
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
    table {{ border-collapse: collapse; width: 100%; }}
    thead tr {{ border-bottom: 1px solid #374151; }}
    thead th {{
      color: #6b7280; font-size: 10.5px; font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase;
      padding: 5px 8px 9px; text-align: center; white-space: nowrap;
    }}
    thead th.left {{ text-align: left; padding-left: 8px; }}
    thead .gr th {{
      color: #4b5563; font-size: 10px; border-bottom: none; padding-bottom: 2px;
    }}
    .dl {{ border-left: 1px solid #374151; }}
    tbody tr {{ border-bottom: 1px solid #1f2937; }}
    tbody tr:hover {{ background: #1f2937; }}
    tbody td {{ padding: 6px 8px; font-size: 12.5px; }}
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
    .flag {{ font-size: 1.2em; margin-right: 6px; vertical-align: middle; }}
  </style>
</head>
<body>

<h1>Grand Slam Singles · Champions Leaderboard</h1>
<div class="sub">
  <div>
    <span id="champion-count">0 champions</span> &nbsp;|&nbsp;
    Grand Slam matches only &nbsp;|&nbsp;
    Walkovers excluded &nbsp;|&nbsp;
    <span style="color:#9ca3af;">Click headers to sort</span>
  </div>
  <div class="tour-selector" {selector_style}>
    <label for="tourSelect">TOUR:</label>
    <select id="tourSelect">
      {options}
    </select>
  </div>
</div>

<table>
  <thead>
    <tr class="gr">
      <th colspan="11"></th>
      <th colspan="4" class="dl" style="text-align:center;color:#9ca3af;">WINRATE</th>
    </tr>
    <tr>
      <th>#</th>
      <th class="left sortable" data-col="player">PLAYER</th>
      <th class="sortable" data-col="firstYear">1ST TITLE</th>
      <th class="sortable" data-col="ageFirst">AGE 1ST</th>
      <th class="sortable" data-col="lastYear">LAST TITLE</th>
      <th class="sortable" data-col="ageLast">AGE LAST</th>
      <th class="sortable" data-col="span">SPAN</th>
      <th class="sortable" data-col="titles">TITLES</th>
      <th class="left">BREAKDOWN</th>
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
    <tr><td colspan="15" id="table-footer"></td></tr>
  </tfoot>
</table>

<script>
  const dataMap = {{
    {", ".join(f'"{tour}": {js_data[tour]}' for tour in tours)}
  }};

  const footerText = `        1ST TITLE = year of first Grand Slam title &nbsp;·&nbsp;
        AGE 1ST = age at first title &nbsp;·&nbsp;
        LAST TITLE = year of last Grand Slam title &nbsp;·&nbsp;
        AGE LAST = age at last title &nbsp;·&nbsp;
        SPAN = last - first + 1 &nbsp;·&nbsp;
        AO = Australian Open &nbsp; RG = Roland Garros &nbsp;
        WIM = Wimbledon &nbsp; USO = US Open &nbsp;·&nbsp; <br>
        AGG = aggregate GS win rate &nbsp;·&nbsp;
        H = Hard · C = Clay · G = Grass &nbsp;·&nbsp;
        Titles: ≥2 <span style="color:#4a9eff">■</span>
        ≥5 <span style="color:#e8a838">■</span>
        ≥10 <span style="color:#f5c842">■</span> &nbsp;·&nbsp;
        Win rate: ≥70%/75% <span style="color:#e8a838">■</span>
        ≥80%/85% <span style="color:#2dd4b0">■</span>`;

  function titlesBg(titles) {{
    if (titles >= 10) return '#f5c842';
    if (titles >= 5) return '#e8a838';
    if (titles >= 2) return '#4a9eff';
    return 'transparent';
  }}
  function titlesFc(titles) {{
    return titles >= 2 ? '#111111' : '#e5e5e5';
  }}
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
  function fmtAge(age) {{
    return (age === null || age === undefined) ? '—' : age.toFixed(1);
  }}

  let sortState = [];
  let userSorted = false;

  const colIndex = {{
    'player': 1,
    'firstYear': 2,
    'ageFirst': 3,
    'lastYear': 4,
    'ageLast': 5,
    'span': 6,
    'titles': 7,
    'W': 9,
    'L': 10,
    'agg': 11,
    'hard': 12,
    'clay': 13,
    'grass': 14
  }};

  function compareValues(a, b, col, order) {{
    let valA = a[colIndex[col]];
    let valB = b[colIndex[col]];
    
    const isNullA = valA === null || valA === undefined;
    const isNullB = valB === null || valB === undefined;
    if (isNullA && isNullB) return 0;
    if (isNullA) return 1;
    if (isNullB) return -1;
    
    if (col !== 'player') {{
      valA = Number(valA);
      valB = Number(valB);
    }} else {{
      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
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

  let currentTour = '{tours[0]}';

  function renderTable() {{
    const rows = dataMap[currentTour] || [];
    const sorted = sortRows(rows);
    
    const tbody = document.getElementById('table-body');
    const countSpan = document.getElementById('champion-count');
    const footerTd = document.getElementById('table-footer');
    
    countSpan.textContent = sorted.length + ' champions';
    footerTd.innerHTML = footerText;

    let html = '';
    sorted.forEach((row, idx) => {{
      const [
        origRank, playerDisplay, firstYear, ageFirst, lastYear, ageLast, span,
        titles, titlesStr, W, L, agg, hard, clay, grass
      ] = row;
      const titlesNum = parseInt(titles);
      const titleBg = titlesBg(titlesNum);
      const titleColor = titlesFc(titlesNum);

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
        <td style="color:#f3f4f6;font-weight:600;padding-left:8px;">${{playerDisplay}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{firstYear}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{fmtAge(ageFirst)}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{lastYear}}</td>
        <td style="text-align:center;color:#e5e5e5;">${{fmtAge(ageLast)}}</td>
        <td style="text-align:center;color:#f5c842;font-weight:bold;">${{span}}</td>
        <td style="text-align:center;background:${{titleBg}};color:${{titleColor}};font-weight:bold;">${{titles}}</td>
        <td style="color:#9ca3af;font-size:11px;white-space:nowrap;padding-left:6px;">${{titlesStr}}</td>
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
    sortState = [
      {{ col: 'titles', order: 'desc' }},
      {{ col: 'firstYear', order: 'asc' }},
      {{ col: 'W', order: 'desc' }}
    ];
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

  renderTable();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已保存: {output_path}")


# ══════════════════════════════════════════════════════════════
# 7. 主入口
# ══════════════════════════════════════════════════════════════
def main(tour='wta'):
    gs_data_path = DATA_PATHS[tour]['gs_matches']
    players_path = DATA_PATHS[tour]['players']

    # 读取大满贯比赛数据
    gs = pd.read_csv(gs_data_path)
    champions = get_champions(gs)
    if not champions:
        return

    # 读取球员信息，只提取冠军列表中的球员
    players_df = pd.read_csv(players_path)
    # 将 dob 转换为 datetime，支持多种格式，如 YYYY/MM/DD
    players_df['dob'] = pd.to_datetime(players_df['dob'], errors='coerce')
    # 筛选出冠军
    champ_players_df = players_df[players_df['name'].isin(champions.keys())]
    player_info = {}
    missing_dob = []
    missing_ioc = []

    for _, row in champ_players_df.iterrows():
        name = row['name']
        dob = row['dob'] if not pd.isna(row['dob']) else None
        ioc = row['ioc'] if not pd.isna(row['ioc']) else None
        birth_year = dob.year if dob else None
        player_info[name] = {'dob': dob, 'ioc': ioc, 'birth_year': birth_year}

    # 检查冠军列表中缺失信息的球员（即在 players 中没找到或字段为空）
    for player in champions.keys():
        if player not in player_info:
            missing_dob.append(player)
            missing_ioc.append(player)
        else:
            info = player_info[player]
            if not info.get('dob') or pd.isna(info['dob']):
                missing_dob.append(player)
            if not info.get('ioc') or pd.isna(info['ioc']):
                missing_ioc.append(player)

    # 打印缺失信息列表
    if missing_dob:
        print(f"\n⚠️  以下 {len(missing_dob)} 位球员缺少出生日期 (dob)，年龄显示为 '—'：")
        for p in sorted(missing_dob):
            print(f"   - {p}")
    if missing_ioc:
        print(f"\n⚠️  以下 {len(missing_ioc)} 位球员缺少国籍代码 (ioc)，国旗显示为 🏳：")
        for p in sorted(missing_ioc):
            print(f"   - {p}")

    print("\n📊 计算战绩...")
    rows = []
    for player, first_year in champions.items():
        stats = calc_stats(gs, player, first_year, player_info)
        if stats:
            rows.append({"player": player, "first_year": first_year, "stats": stats})

    # 排序：冠军数降序 → 首冠年份升序 → 总胜场降序
    rows.sort(key=lambda r: (-r["stats"]["titles"], r["first_year"], -r["stats"]["W"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # 控制台预览前20
    print(f"\n  {'#':<4} {'Player':<28} {'1st':<6} {'Age1':<6} {'Last':<6} {'AgeL':<6} {'Span':<5} {'GS':<4} {'W':<5} {'L':<4} {'AGG'}")
    print("  " + "-" * 105)
    for r in rows[:10]:
        s = r["stats"]
        age1 = f"{s['age_first']:.1f}" if s['age_first'] else "—"
        agel = f"{s['age_last']:.1f}" if s['age_last'] else "—"
        print(f"  {r['rank']:<4} {r['player']:<28} {r['first_year']:<6} "
              f"{age1:<6} {s['last_year']:<6} {agel:<6} "
              f"{s['span']:<5} {s['titles']:<4} {s['W']:<5} {s['L']:<4} {s['agg']}%")
    if len(rows) > 20:
        print(f"  ... 共 {len(rows)} 位冠军")

    return rows


if __name__ == "__main__":
    rows_atp = main(tour='atp')
    rows_wta = main(tour='wta')
    build_gs_leaderboard({'wta': rows_wta, 'atp': rows_atp}, output_path='./analysis/leaderboards/tour_gs_champions.html')
    # only build wta
    build_gs_leaderboard({'wta': rows_wta}, output_path='./analysis/leaderboards/wta_gs_champions.html')
    # only build atp
    build_gs_leaderboard({'atp': rows_atp}, output_path='./analysis/leaderboards/atp_gs_champions.html')
