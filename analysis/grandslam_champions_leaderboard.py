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
    wins   = gs[gs["winner_name"] == player].copy()
    losses = gs[gs["loser_name"] == player].copy()
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
    生成大满贯冠军排行榜 HTML 页面。

    Args:
        rows_dict: dict, 例如 {'wta': wta_rows, 'atp': atp_rows}
        output_path: str, 输出 HTML 文件路径
    """
    tours = list(rows_dict.keys())

    # ---------- 辅助函数（直接使用外部定义的 titles_bg, titles_fc, agg_bg, surf_bg）----------
    def fmt(val):
        return "—" if val is None else f"{val}%"

    def td_r(val, bg_tuple):
        bg, fc = bg_tuple if isinstance(bg_tuple, tuple) else (bg_tuple, "#111111")
        st = f"background:{bg};color:{fc};" if bg != "transparent" else "color:#6b7280;"
        return f'<td style="text-align:center;{st}">{fmt(val)}</td>'

    def generate_rows_html(rows):
        parts = []
        for e in rows:
            s = e["stats"]
            ab = agg_bg(s["agg"])
            hb = surf_bg(s["win_h"])
            cb = surf_bg(s["win_c"])
            gb = surf_bg(s["win_g"])
            parts.append(f"""<tr>
          <td style="color:#6b7280;text-align:center;font-size:11px;">{e['rank']}</td>
          <td style="color:#f3f4f6;font-weight:600;padding-left:8px;">{e['player']}</td>
          <td style="text-align:center;color:#f5c842;font-weight:bold;">{e['first_year']}</td>
          <td style="text-align:center;background:{titles_bg(s['titles'])};color:{titles_fc(s['titles'])};font-weight:bold;">{s['titles']}</td>
          <td style="color:#9ca3af;font-size:11px;white-space:nowrap;padding-left:6px;">{s['titles_str']}</td>
          <td style="text-align:center;color:#e5e5e5;">{s['W']}</td>
          <td style="text-align:center;color:#6b7280;">{s['L']}</td>
          {td_r(s['agg'],   ab)}
          {td_r(s['win_h'], hb)}
          {td_r(s['win_c'], cb)}
          {td_r(s['win_g'], gb)}
        </tr>""")
        return "\n".join(parts)

    # 单页模式
    if len(tours) == 1:
        tour = tours[0]
        rows = rows_dict[tour]
        gender = "Women" if tour == "wta" else "Men"
        rows_html = generate_rows_html(rows)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{tour.upper()} Grand Slam Champions Leaderboard</title>
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
    text-transform: uppercase; margin-bottom: 28px;
  }}
  .sub span {{ color: #f5c842; }}
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
</style>
</head>
<body>

<h1>Grand Slam {gender}'s Singles — Champions Leaderboard</h1>
<div class="sub">
  <span>{len(rows)} champions</span> &nbsp;|&nbsp;
  Grand Slam matches only &nbsp;|&nbsp;
  Walkovers excluded &nbsp;|&nbsp;
  Sorted by titles ↓ then first title year ↑
</div>

<table>
  <thead>
    <tr class="gr">
      <th colspan="8"></th>
      <th colspan="4" class="dl" style="text-align:center;color:#9ca3af;">WINRATE</th>
    </tr>
    <tr>
      <th>#</th>
      <th class="left">PLAYER</th>
      <th>1ST TITLE</th>
      <th>TITLES</th>
      <th class="left">BREAKDOWN</th>
      <th>W</th>
      <th>L</th>
      <th class="dl">AGG</th>
      <th>H</th>
      <th>C</th>
      <th>G</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
  <tfoot>
    <tr>
      <td colspan="12">
        1ST TITLE = year of first Grand Slam title &nbsp;·&nbsp;
        AO = Australian Open &nbsp; RG = Roland Garros &nbsp;
        WIM = Wimbledon &nbsp; USO = US Open &nbsp;·&nbsp <br>
        AGG = aggregate GS win rate &nbsp;·&nbsp;
        H = Hard · C = Clay · G = Grass &nbsp;·&nbsp;
        Titles: ≥2 <span style="color:#4a9eff">■</span>
        ≥5 <span style="color:#e8a838">■</span>
        ≥10 <span style="color:#f5c842">■</span> &nbsp;·&nbsp;
        Win rate: ≥70%/75% <span style="color:#e8a838">■</span>
        ≥80%/85% <span style="color:#2dd4b0">■</span>
      </td>
    </tr>
  </tfoot>
</table>
</body>
</html>"""

    else:
        # 交互式页面
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
  </style>
</head>
<body>

<h1>Grand Slam Singles · Champions Leaderboard</h1>
<div class="sub">
  <div>
    <span id="champion-count">0 champions</span> &nbsp;|&nbsp;
    Grand Slam matches only &nbsp;|&nbsp;
    Walkovers excluded &nbsp;|&nbsp;
    Sorted by titles ↓ then first title year ↑
  </div>
  <div class="tour-selector">
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
      <th class="left">PLAYER</th>
      <th>1ST TITLE</th>
      <th>TITLES</th>
      <th class="left">BREAKDOWN</th>
      <th>W</th>
      <th>L</th>
      <th class="dl">AGG</th>
      <th>H</th>
      <th>C</th>
      <th>G</th>
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
        WIM = Wimbledon &nbsp; USO = US Open &nbsp;·&nbsp <br>
        AGG = aggregate GS win rate &nbsp;·&nbsp;
        H = Hard · C = Clay · G = Grass &nbsp;·&nbsp;
        Titles: ≥2 <span style="color:#4a9eff">■</span>
        ≥5 <span style="color:#e8a838">■</span>
        ≥10 <span style="color:#f5c842">■</span> &nbsp;·&nbsp;
        Win rate: ≥70%/75% <span style="color:#e8a838">■</span>
        ≥80%/85% <span style="color:#2dd4b0">■</span>`;

  // 颜色函数（与 Python 端逻辑完全一致）
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

  function renderTable(tour) {{
    const rows = dataMap[tour] || [];
    const tbody = document.getElementById('table-body');
    const countSpan = document.getElementById('champion-count');
    const footerTd = document.getElementById('table-footer');
    
    countSpan.textContent = rows.length + ' champions';
    footerTd.innerHTML = footerText;

    let html = '';
    rows.forEach(row => {{
      const [rank, player, firstYear, titles, titlesStr, W, L, agg, hard, clay, grass] = row;
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
        <td style="color:#6b7280;text-align:center;font-size:11px;">${{rank}}</td>
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
  }}

  const selectEl = document.getElementById('tourSelect');
  selectEl.addEventListener('change', e => renderTable(e.target.value));
  renderTable(selectEl.value);
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
