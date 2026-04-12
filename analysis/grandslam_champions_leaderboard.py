"""
历史大满贯冠军 Leaderboard
================================
统计所有曾赢得过大满贯冠军的球员在大满贯赛事中的详细战绩
输出：./cur_output/tour_gs_champions.html

依赖：pip install pandas openpyxl
用法：python grandslam_champions_leaderboard.py
"""

import os
import glob
import pandas as pd
from scripts.config import PROJECT_ROOT,DATA_PATHS


# ══════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════
OUTPUT_DIR  = PROJECT_ROOT / "./output"
GS_TIER     = "Grand Slam"

SLAMS = {
    "AO":  ["Australian Open", "Australian Open 2"],
    "RG":  ["Roland Garros"],
    "WIM": ["Wimbledon"],
    "USO": ["US Open"],
}




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
def calc_stats(gs, player):
    # 计算score不是W/O的比赛的wins和losses
    wins = gs[(gs["winner_name"] == player) & (gs["score"] != "W/O")].copy()
    losses = gs[(gs["loser_name"] == player) & (gs["score"] != "W/O")].copy()
    # wins   = gs[gs["winner_name"] == player].copy()
    # losses = gs[gs["loser_name"] == player].copy()
    W, L   = len(wins), len(losses)
    if W + L == 0:
        return None

    agg = round(W / (W + L) * 100, 1)

    # # vs Top 8
    # top8_w = wins[pd.to_numeric(wins["loser_rank"],   errors="coerce") <= 8]
    # top8_l = losses[pd.to_numeric(losses["winner_rank"], errors="coerce") <= 8]
    # vs_top8 = f"{len(top8_w)}-{len(top8_l)}"

    # # 检测排名缺失：该球员所有大满贯比赛中有多少场对手排名为空
    # all_opp_ranks = pd.concat([
    #     pd.to_numeric(wins["loser_rank"],   errors="coerce"),
    #     pd.to_numeric(losses["winner_rank"], errors="coerce"),
    # ])
    # missing_rank = int(all_opp_ranks.isna().sum())
    # vs_top8_uncertain = missing_rank > 0

    # 场地胜率
    def surf_wr(surface):
        sw = wins[wins["surface"].astype(str).str.lower() == surface.lower()]
        sl = losses[losses["surface"].astype(str).str.lower() == surface.lower()]
        t  = len(sw) + len(sl)
        return round(len(sw) / t * 100) if t > 0 else None

    # 各满贯冠军数
    wins["_slam"]    = wins["tourney_name"].apply(get_slam_key)
    finals_won       = wins[wins["round"] == 'F']
    slam_titles      = finals_won["_slam"].value_counts().to_dict()
    titles_total     = sum(slam_titles.values())
    ao  = slam_titles.get("AO",  0)
    rg  = slam_titles.get("RG",  0)
    wim = slam_titles.get("WIM", 0)
    uso = slam_titles.get("USO", 0)
    # 冠军分项：只显示非零项
    parts = []
    if ao:  parts.append(f"AO×{ao}")
    if rg:  parts.append(f"RG×{rg}")
    if wim: parts.append(f"WIM×{wim}")
    if uso: parts.append(f"USO×{uso}")
    titles_str = "  ".join(parts) if parts else "—"

    return {
        "W": W, "L": L,
        "titles":          titles_total,
        "titles_str":      titles_str,
        # "vs_top8":         vs_top8,
        # "vs_top8_uncertain": vs_top8_uncertain,
        "agg":             agg,
        "win_h":           surf_wr("Hard"),
        "win_c":           surf_wr("Clay"),
        "win_g":           surf_wr("Grass"),
    }


# ══════════════════════════════════════════════════════════════
# 5. 颜色工具
# ══════════════════════════════════════════════════════════════
def rate_to_bg(v, lo=70, hi=90):
    """
    双段渐变（深色背景版）：
      70 ~ 80 : 浅黄  → 深橙黄   （黄色段）
      80 ~ hi : 浅青绿 → 深青绿   （绿色段）
      低于 70 : 透明
    """
    if v is None or v < lo:
        return "transparent", "#6b7280"

    if v < 80:
        # 黄色段：lo→80，浅黄(253,230,138) → 深橙(217,119,6)
        t  = (v - lo) / (80 - lo)
        t  = max(0.0, min(1.0, t))
        r  = int(253 + t * (217 - 253))
        g  = int(230 + t * (119 - 230))
        b  = int(138 + t * (6   - 138))
        fc = "#111111"   # 黄色背景用深色字
    else:
        # 绿色段：80→hi，浅青绿(110,231,183) → 深青绿(4,120,87)
        t  = (v - 80) / (hi - 80)
        t  = max(0.0, min(1.0, t))
        r  = int(110 + t * (4   - 110))
        g  = int(231 + t * (120 - 231))
        b  = int(183 + t * (87  - 183))
        fc = "#111111" if t < 0.5 else "#ffffff"
    return f"rgb({r},{g},{b})", fc

def agg_bg(v):
    bg, fc = rate_to_bg(v, lo=70, hi=90)
    return bg, fc

def surf_bg(v):
    bg, fc = rate_to_bg(v, lo=70, hi=95)
    return bg, fc

def on_col(bg):
    return "#111111" if bg != "transparent" else "#cccccc"

def titles_bg(n):
    if n >= 10: return "#f5c842"
    if n >= 5:  return "#e8a838"
    if n >= 2:  return "#4a9eff"
    return "transparent"

def titles_fc(n):
    return "#111111" if n >= 2 else "#e5e5e5"


# ══════════════════════════════════════════════════════════════
# 6. 生成 HTML
# ══════════════════════════════════════════════════════════════
def build_gs_leaderboard(rows_dict, output_path):
    """
    生成大满贯冠军排行榜 HTML 页面，支持点击表头排序（累加式，新点击列成为主键）。

    Args:
        rows_dict: dict, 例如 {'wta': wta_rows, 'atp': atp_rows}
        output_path: str, 输出 HTML 文件路径
    """
    tours = list(rows_dict.keys())

    # ---------- 辅助函数 ----------
    def fmt(val):
        return "—" if val is None else f"{val}%"

    def td_r(val, bg_tuple):
        bg, fc = bg_tuple if isinstance(bg_tuple, tuple) else (bg_tuple, "#111111")
        st = f"background:{bg};color:{fc};" if bg != "transparent" else "color:#6b7280;"
        return f'<td style="text-align:center;{st}">{fmt(val)}</td>'

    # 将数据转换为 JavaScript 友好格式
    import json

    def rows_to_js(rows):
        arr = []
        for e in rows:
            s = e["stats"]
            arr.append([
                e['rank'],
                e['player'],
                e['first_year'],
                s['titles'],
                s['titles_str'],
                s['W'],
                s['L'],
                s['agg'] if s['agg'] is not None else None,
                s['win_h'] if s['win_h'] is not None else None,
                s['win_c'] if s['win_c'] is not None else None,
                s['win_g'] if s['win_g'] is not None else None
            ])
        return json.dumps(arr)

    js_data = {tour: rows_to_js(rows_dict[tour]) for tour in tours}
    options = "\n".join(
        f'<option value="{tour}" {"selected" if i==0 else ""}>{tour.upper()}</option>'
        for i, tour in enumerate(tours)
    )

    # 如果只有一个巡回赛，隐藏选择器
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
      font-family: 'Segoe UI', Arial, sans-serif;
      padding: 36px 44px 60px;
      min-width: 960px;
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
    /* 可排序表头样式 */
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
      <th colspan="8"></th>
      <th colspan="4" class="dl" style="text-align:center;color:#9ca3af;">WINRATE</th>
    </tr>
    <tr>
      <th>#</th>
      <th class="left sortable" data-col="player">PLAYER</th>
      <th class="sortable" data-col="firstYear">1ST TITLE</th>
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
    <tr><td colspan="12" id="table-footer"></td></tr>
  </tfoot>
</table>

<script>
  const dataMap = {{
    {", ".join(f'"{tour}": {js_data[tour]}' for tour in tours)}
  }};

  const footerText = `        1ST TITLE = year of first Grand Slam title &nbsp;·&nbsp;
        AO = Australian Open &nbsp; RG = Roland Garros &nbsp;
        WIM = Wimbledon &nbsp; USO = US Open &nbsp;·&nbsp; <br>
        AGG = aggregate GS win rate &nbsp;·&nbsp;
        H = Hard · C = Clay · G = Grass &nbsp;·&nbsp;
        Titles: ≥2 <span style="color:#4a9eff">■</span>
        ≥5 <span style="color:#e8a838">■</span>
        ≥10 <span style="color:#f5c842">■</span> &nbsp;·&nbsp;
        Win rate: ≥70%/75% <span style="color:#e8a838">■</span>
        ≥80%/85% <span style="color:#2dd4b0">■</span>`;

  // ---------- 颜色函数（与 Python 端一致）----------
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

  // ---------- 排序状态 ----------
  // 默认排序：titles desc → firstYear asc → W desc（不显示指示器）
  let sortState = [
    // {{ col: 'titles', order: 'desc' }},
    // {{ col: 'firstYear', order: 'asc' }},
    // {{ col: 'W', order: 'desc' }}
  ];
  let userSorted = false;  // 是否经过用户手动排序（决定是否显示指示器）

  // 列到数据索引的映射 (基于 rows_to_js 的顺序)
  const colIndex = {{
    'player': 1,      // 字符串
    'firstYear': 2,   // 数字
    'titles': 3,      // 数字
    'W': 5,           // 数字
    'L': 6,           // 数字
    'agg': 7,         // 数字或null
    'hard': 8,
    'clay': 9,
    'grass': 10
  }};

  // 比较函数（处理 null/undefined 放最后）
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

  // 更新表头排序指示器（仅当 userSorted 为 true 时显示）
  function updateSortIndicators() {{
    // 清除所有指示器
    document.querySelectorAll('.sortable').forEach(th => {{
      const ind = th.querySelector('.sort-indicator');
      if (ind) ind.remove();
    }});
    
    if (!userSorted) return;
    
    // 为 sortState 中的主排序键添加指示器（只显示第一个，保持简洁）
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

  // ---------- 渲染表格 ----------
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
      const [origRank, player, firstYear, titles, titlesStr, W, L, agg, hard, clay, grass] = row;
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
        <td style="color:#f3f4f6;font-weight:600;padding-left:8px;">${{player}}</td>
        <td style="text-align:center;color:#f5c842;font-weight:bold;">${{firstYear}}</td>
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

  // ---------- 排序事件绑定 ----------
  function handleSortClick(e) {{
    const th = e.currentTarget;
    const col = th.getAttribute('data-col');
    if (!col) return;
    
    userSorted = true;
    const existingIdx = sortState.findIndex(s => s.col === col);
    
    // 确定新列的顺序：默认降序；若已存在则翻转顺序
    let newOrder = 'desc';
    if (existingIdx !== -1) {{
      newOrder = sortState[existingIdx].order === 'asc' ? 'desc' : 'asc';
    }}
    
    if (existingIdx !== -1) {{
      // 如果该列已在排序条件中，将其移到首位并更新顺序
      const [existing] = sortState.splice(existingIdx, 1);
      existing.order = newOrder;
      sortState.unshift(existing);
    }} else {{
      // 新列：插入到开头，原有排序全部后移成为次级条件
      sortState.unshift({{ col, order: newOrder }});
    }}
    
    renderTable();
  }}

  // 重置为默认排序（切换巡回赛时调用，不视为用户排序）
  function resetToDefault() {{
    sortState = [
      {{ col: 'titles', order: 'desc' }},
      {{ col: 'firstYear', order: 'asc' }},
      {{ col: 'W', order: 'desc' }}
    ];
    userSorted = false;
  }}

  // 初始化事件监听
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

  // 初始渲染
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    gs_data_path = DATA_PATHS[tour]['gs_matches']
    # load grand slam matches
    gs = pd.read_csv(gs_data_path)
    champions  = get_champions(gs)
    if not champions:
        return

    print("\n📊 计算战绩...")
    rows = []
    for player, first_year in champions.items():
        stats = calc_stats(gs, player)
        if stats:
            rows.append({"player": player, "first_year": first_year, "stats": stats})

    # 排序：冠军数降序 → 首冠年份升序 → 总胜场降序
    
    rows.sort(key=lambda r: (-r["stats"]["titles"], r["first_year"], -r["stats"]["W"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # 控制台预览前20
    print(f"\n  {'#':<4} {'Player':<28} {'1st':<6} {'GS':<4} {'W':<5} {'L':<4} {'AGG'}")
    print("  " + "-" * 65)
    for r in rows[:10]:
        s = r["stats"]
        print(f"  {r['rank']:<4} {r['player']:<28} {r['first_year']:<6} "
              f"{s['titles']:<4} {s['W']:<5} {s['L']:<4} {s['agg']}%")
    if len(rows) > 20:
        print(f"  ... 共 {len(rows)} 位冠军")

    # out = os.path.join(OUTPUT_DIR, f"{tour}_gs_champions.html")
    # build_html(tour, rows, out)
    # print(f"\n用浏览器打开查看: {out}")
    return rows

    # # ── 截图为 PNG
    # try:
    #     from screenshot_html import screenshot
    #     png_out = out.replace(".html", ".png")
    #     screenshot(out, png_out, width=1300)
    # except Exception as e:
    #     print(f"   截图跳过: {e}")
    #     print("   如需截图请单独运行 screenshot_html.py")


if __name__ == "__main__":
    rows_atp = main(tour='atp')
    rows_wta = main(tour='wta')
    build_gs_leaderboard({'wta': rows_wta, 'atp': rows_atp}, output_path='./analysis/leaderboards/tour_gs_champions.html')
    # only build wta
    build_gs_leaderboard({'wta': rows_wta}, output_path='./analysis/leaderboards/wta_gs_champions.html')
    # only build atp
    build_gs_leaderboard({'atp': rows_atp}, output_path='./analysis/leaderboards/atp_gs_champions.html')
    # out = os.path.join(OUTPUT_DIR, f"{tour}_gs_champions.html")
    # build_html(tour, rows, out)
    # print(f"\n用浏览器打开查看: {out}")
