"""
每周更新 wta_no1_players.json：
1. 更新 ACTIVE_NO1 名单里所有球员的生涯胜率（四个字段）
2. 更新 CURRENT_NO1 球员的 weeks_total、weeks_consecutive、last_no1_date

用法：python update_no1_weekly.py
（在 repo 根目录下运行）

换世界第一时：手动修改 CURRENT_NO1，并手动重置该球员的 weeks_consecutive
"""

import json
import csv
import glob
from collections import defaultdict
from datetime import date, timedelta

# ================================================================
# ── 配置区（每周只需关注这里）──────────────────────────────────────
# ================================================================

# 当前世界第一（换人时手动修改）
CURRENT_NO1 = "Aryna Sabalenka"

# 现役球员名单（胜率更新范围；退役时从此处移除）
ACTIVE_NO1 = {
    "Victoria Azarenka",
    "Karolina Pliskova",
    "Naomi Osaka",
    "Iga Swiatek",
    "Aryna Sabalenka",
    "Serena Williams",
    "Venus Williams"
}

# ── 路径配置 ──────────────────────────────────────────────────────
JSON_PATH    = "output/wta_no1_players.json"
MATCHES_GLOB = "tennis_wta/wta_matches_*.csv"

# ================================================================
# ── 1. 计算本周周日日期 ────────────────────────────────────────────
# ================================================================
today = date.today()
days_to_sunday = 6 - today.weekday()   # Monday=0, Sunday=6
this_sunday = today + timedelta(days=days_to_sunday)
print(f"今天：{today}，本周周日：{this_sunday}")

# ================================================================
# ── 2. 统计现役球员胜率 ────────────────────────────────────────────
# ================================================================
print("\n读取比赛数据...")

SURFACE_MAP = {"hard": "hard", "clay": "clay", "grass": "grass"}
stats = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0}))
active_lower = {name.lower() for name in ACTIVE_NO1}

match_files = sorted(glob.glob(MATCHES_GLOB))
print(f"  共找到 {len(match_files)} 个比赛文件")

for fpath in match_files:
    with open(fpath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["score"].strip().upper() == "W/O":
                continue
            winner = row["winner_name"].strip()
            loser  = row["loser_name"].strip()
            if winner.lower() not in active_lower and loser.lower() not in active_lower:
                continue
            surface = SURFACE_MAP.get(row["surface"].strip().lower(), "other")
            if winner.lower() in active_lower:
                stats[winner.lower()]["overall"]["w"] += 1
                if surface != "other":
                    stats[winner.lower()][surface]["w"] += 1
            if loser.lower() in active_lower:
                stats[loser.lower()]["overall"]["l"] += 1
                if surface != "other":
                    stats[loser.lower()][surface]["l"] += 1

def win_rate(w, l):
    total = w + l
    if total == 0:
        return None
    return round(w / total * 100, 1)

# ================================================================
# ── 3. 读取并更新 JSON ────────────────────────────────────────────
# ================================================================
print("\n更新 JSON...")
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

for p in data["players"]:
    name = p["player"]

    # ── 胜率更新（所有 ACTIVE_NO1）──────────────────────────────
    if name in ACTIVE_NO1:
        key = name.lower()
        s   = stats.get(key)
        if s:
            ov = s.get("overall", {"w": 0, "l": 0})
            h  = s.get("hard",    {"w": 0, "l": 0})
            c  = s.get("clay",    {"w": 0, "l": 0})
            g  = s.get("grass",   {"w": 0, "l": 0})
            p["win_rate_overall"]  = win_rate(ov["w"], ov["l"])
            p["hard"]["win_rate"]  = win_rate(h["w"],  h["l"])
            p["clay"]["win_rate"]  = win_rate(c["w"],  c["l"])
            p["grass"]["win_rate"] = win_rate(g["w"],  g["l"])
            print(f"  ✓ 胜率 {name}: overall={p['win_rate_overall']}% "
                  f"H={p['hard']['win_rate']}% "
                  f"C={p['clay']['win_rate']}% "
                  f"G={p['grass']['win_rate']}%")
        else:
            print(f"  ⚠️  {name}: 未找到比赛数据")

    # ── 周数更新（仅 CURRENT_NO1）───────────────────────────────
    if name == CURRENT_NO1:
        old_last = date.fromisoformat(p["last_no1_date"])
        added_weeks = (this_sunday - old_last).days // 7

        if added_weeks > 0:
            old_total = p["weeks_total"]
            old_cons  = p["weeks_consecutive"]
            p["weeks_total"]       = old_total + added_weeks
            p["weeks_consecutive"] = old_cons  + added_weeks
            p["last_no1_date"]     = this_sunday.isoformat()
            print(f"\n  ✓ 周数 {name}:")
            print(f"      weeks_total:       {old_total} → {p['weeks_total']} (+{added_weeks})")
            print(f"      weeks_consecutive: {old_cons}  → {p['weeks_consecutive']} (+{added_weeks})")
            print(f"      last_no1_date:     {old_last} → {p['last_no1_date']}")
        else:
            print(f"\n  ℹ️  {name}: last_no1_date 已是本周或更晚，周数无需更新")

# ================================================================
# ── 4. 更新 last_updated 并写回 ──────────────────────────────────
# ================================================================
data["meta"]["last_updated"] = today.isoformat()

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成，已写回 {JSON_PATH}")
