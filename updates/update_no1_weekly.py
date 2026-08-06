"""
每周更新 world_no1_club.json：
1. 更新现役 WTA 和 ATP 世界第一（ACTIVE_PLAYERS 名单）的生涯胜率（硬地、红土、草地、总体）
2. 更新当前 WTA 和 ATP 世界第一的 weeks_total、last_no1_date
3. 根据本次登顶起始日期计算当前连续周数，若超过历史最长（weeks_consecutive）则更新该记录

用法：python update_no1_weekly.py
（在 repo 根目录下运行）

换世界第一时：手动修改 CURRENT_WTA / CURRENT_ATP 以及对应的 START_DATE，
同时需将该球员的 last_no1_date 手动设为与 START_DATE 一致的起始周日，
并将 weeks_consecutive 手动重置为 1（或 0，但建议设为 1）。
"""

import json
import csv
import glob
from collections import defaultdict
from datetime import date, timedelta

# ================================================================
# ── 配置区（每周需关注）──────────────────────────────────────────
# ================================================================

# 当前 WTA 世界第一（换人时手动修改）
CURRENT_WTA = "Aryna Sabalenka"
CURRENT_WTA_START_DATE = "2024-10-21"   # 本次登顶起始周日（格式 YYYY-MM-DD）

# 当前 ATP 世界第一（换人时手动修改）
CURRENT_ATP = "Jannik Sinner"
CURRENT_ATP_START_DATE = "2026-04-13"   # 本次登顶起始周日（格式 YYYY-MM-DD）

# 现役球员名单（包括所有需要更新胜率的现役/近期退役的前世界第一）
# 只要她们仍在打球，就需要每周刷新胜率；退役后可移除
ACTIVE_PLAYERS = {
    # WTA
    "Victoria Azarenka",
    "Karolina Pliskova",
    "Naomi Osaka",
    "Iga Swiatek",
    "Aryna Sabalenka",
    "Serena Williams",
    "Venus Williams",
    # ATP（现役世界第一及相关球员）
    "Novak Djokovic",
    "Daniil Medvedev",
    "Carlos Alcaraz",
    "Jannik Sinner",
    # 如有其他现役 ATP 前世界第一，可继续添加
}

# ── 路径配置 ──────────────────────────────────────────────────────
JSON_PATH      = "output/world_no1_club.json"
WTA_MATCHES    = "tennis_wta/wta_matches_*.csv"
ATP_MATCHES    = "tennis_atp/atp_matches_*.csv"

# ================================================================
# ── 1. 计算本周周日日期 ──────────────────────────────────────────
# ================================================================
today = date.today()
days_to_sunday = 6 - today.weekday()   # Monday=0, Sunday=6
this_sunday = today + timedelta(days=days_to_sunday)
print(f"今天：{today}，本周周日：{this_sunday}")

# ================================================================
# ── 2. 统计所有现役球员的胜率（WTA + ATP）───────────────────────
# ================================================================
def read_matches(matches_glob, active_lower):
    """读取比赛文件，只统计 active_lower 中的球员，返回 {name_lower: {"overall": {"w":,"l":}, "hard":..., ...}}"""
    stats = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0}))
    surface_map = {"hard": "hard", "clay": "clay", "grass": "grass"}
    files = sorted(glob.glob(matches_glob))
    if not files:
        print(f"⚠️ 未找到匹配文件: {matches_glob}")
        return stats
    print(f"  读取 {len(files)} 个比赛文件")
    for fpath in files:
        with open(fpath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                score = row.get("score", "").strip().upper()
                if score == "W/O":
                    continue
                winner = row.get("winner_name", "").strip()
                loser  = row.get("loser_name", "").strip()
                if not winner or not loser:
                    continue
                winner_key = winner.lower()
                loser_key  = loser.lower()
                # 只统计活跃球员
                if winner_key not in active_lower and loser_key not in active_lower:
                    continue

                surface_raw = row.get("surface", "").strip().lower()
                surface = surface_map.get(surface_raw, "other")

                if winner_key in active_lower:
                    stats[winner_key]["overall"]["w"] += 1
                    if surface != "other":
                        stats[winner_key][surface]["w"] += 1
                if loser_key in active_lower:
                    stats[loser_key]["overall"]["l"] += 1
                    if surface != "other":
                        stats[loser_key][surface]["l"] += 1
    return stats

def win_rate(w, l):
    total = w + l
    if total == 0:
        return None
    return round(w / total * 100, 1)

print("\n读取 WTA 比赛数据...")
wta_stats = read_matches(WTA_MATCHES, {p.lower() for p in ACTIVE_PLAYERS})
print("读取 ATP 比赛数据...")
atp_stats = read_matches(ATP_MATCHES, {p.lower() for p in ACTIVE_PLAYERS})

# 合并统计（因为同一个球员不会同时出现在 WTA 和 ATP，所以直接合并字典）
all_stats = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0}))
for stats_dict in [wta_stats, atp_stats]:
    for player, surfaces in stats_dict.items():
        for surf, wl in surfaces.items():
            all_stats[player][surf]["w"] += wl["w"]
            all_stats[player][surf]["l"] += wl["l"]

# ================================================================
# ── 3. 读取并更新 JSON ──────────────────────────────────────────
# ================================================================
print("\n更新 JSON...")
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

# 辅助函数：更新单个球员的胜率
def update_winrate(player_obj, stats):
    key = player_obj["player"].lower()
    s = stats.get(key)
    if s:
        ov = s.get("overall", {"w": 0, "l": 0})
        h  = s.get("hard",    {"w": 0, "l": 0})
        c  = s.get("clay",    {"w": 0, "l": 0})
        g  = s.get("grass",   {"w": 0, "l": 0})
        player_obj["win_rate_overall"]  = win_rate(ov["w"], ov["l"])
        player_obj["hard"]["win_rate"]  = win_rate(h["w"],  h["l"])
        player_obj["clay"]["win_rate"]  = win_rate(c["w"],  c["l"])
        player_obj["grass"]["win_rate"] = win_rate(g["w"],  g["l"])
        return True
    return False

# 更新 WTA 列表中的现役球员
for p in data["wta"]:
    if p["player"] in ACTIVE_PLAYERS:
        if update_winrate(p, all_stats):
            print(f"  ✓ WTA {p['player']}: overall={p['win_rate_overall']}% "
                  f"H={p['hard']['win_rate']}% C={p['clay']['win_rate']}% G={p['grass']['win_rate']}%")
        else:
            print(f"  ⚠️ WTA {p['player']}: 未找到比赛数据")

# 更新 ATP 列表中的现役球员
for p in data["atp"]:
    if p["player"] in ACTIVE_PLAYERS:
        if update_winrate(p, all_stats):
            print(f"  ✓ ATP {p['player']}: overall={p['win_rate_overall']}% "
                  f"H={p['hard']['win_rate']}% C={p['clay']['win_rate']}% G={p['grass']['win_rate']}%")
        else:
            print(f"  ⚠️ ATP {p['player']}: 未找到比赛数据")

# ================================================================
# ── 4. 更新当前世界第一的周数 ──────────────────────────────────
# ================================================================
def update_weeks_for_player(player_obj, current_name, start_date_str, this_sunday):
    if player_obj["player"] != current_name:
        return
    start_date = date.fromisoformat(start_date_str)
    # 计算本次连续周数（从起始周日算起，包含起始周）
    current_streak = (this_sunday - start_date).days // 7 + 1

    old_last = date.fromisoformat(player_obj["last_no1_date"])
    added_weeks = (this_sunday - old_last).days // 7
    if added_weeks <= 0:
        print(f"  ℹ️  {current_name}: last_no1_date 已是本周或更晚，无需更新")
        return

    old_total = player_obj["weeks_total"]
    old_cons  = player_obj["weeks_consecutive"]

    # 更新总周数
    player_obj["weeks_total"] = old_total + added_weeks
    # 更新 last_no1_date 为本周日
    player_obj["last_no1_date"] = this_sunday.isoformat()

    # 判断是否更新最长连续记录
    if current_streak > old_cons:
        player_obj["weeks_consecutive"] = current_streak
        print(f"\n  ✓ 周数更新 {current_name}:")
        print(f"      weeks_total:       {old_total} → {player_obj['weeks_total']} (+{added_weeks})")
        print(f"      weeks_consecutive: {old_cons} → {player_obj['weeks_consecutive']} (本次连续 {current_streak} 周，新纪录)")
    else:
        print(f"\n  ✓ 周数更新 {current_name}:")
        print(f"      weeks_total:       {old_total} → {player_obj['weeks_total']} (+{added_weeks})")
        print(f"      weeks_consecutive: 保持 {old_cons} (本次连续 {current_streak} 周，未超纪录)")
    print(f"      last_no1_date:     {old_last} → {player_obj['last_no1_date']}")

# 更新 WTA 当前世界第一
for p in data["wta"]:
    update_weeks_for_player(p, CURRENT_WTA, CURRENT_WTA_START_DATE, this_sunday)

# 更新 ATP 当前世界第一
for p in data["atp"]:
    update_weeks_for_player(p, CURRENT_ATP, CURRENT_ATP_START_DATE, this_sunday)

# ================================================================
# ── 5. 更新 last_updated 并写回 ────────────────────────────────
# ================================================================
data["meta"]["last_updated"] = today.isoformat()

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 完成，已写回 {JSON_PATH}")