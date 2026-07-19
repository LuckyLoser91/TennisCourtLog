"""
Big Tournament 球员数据统计脚本

功能：统计 WTA 当前排名前 topn 的球员在指定年份范围内各大赛事的参赛表现数据。

输入文件：
- ./output/live-rank-top{topn}-{周一日期}.json : 实时排名缓存（自动获取/生成）
  格式：包含 player.fullName, ranking, points, dateOfBirth, countryCode 等字段
- ./output/calendar-{year}.json : 年度赛事日历（自动获取/生成）
  格式：包含 content[].tournamentGroup.name, level 等字段
- ./output/wta_calendar_champs_start_2009.json : 历史冠军日历（必需）
  格式：包含 year, tourney_name, tourney_level 等字段
  用途：用于准确匹配每站赛事的真实级别（因为 CSV 中的级别可能不准确）
- ./tennis_wta/wta_matches_{year}.csv : 清洗后的比赛数据（必需）
  来源：由 update_tour_matches_uk.py 生成

输出文件：
- ./output/top{topn}_big_tournament_stats.json : 球员大赛统计结果

运行方式：
    python update_big_tournament_stats.py

依赖脚本：
    需先运行 update_tour_matches_uk.py 生成 wta_matches_{year}.csv

注意：
- 仅统计 BIG_LEVELS 中定义的赛事（Grand Slam, WTA1000）
- 使用历史日历映射确保赛事级别准确匹配
"""

import os
import json
import pandas as pd
from typing import List, Dict, Tuple
import requests
import time
from datetime import datetime, timedelta

# 我们关注的大赛级别（用于筛选和最终输出）
BIG_LEVELS = {"Grand Slam", "WTA 1000", "WTA1000"}

ROUND_ORDER = {
    "R128": 1,
    "R64": 2,
    "R32": 3,
    "R16": 4,
    "QF": 5,
    "SF": 6,
    "F": 7
}

def get_monday_date(date: datetime = None) -> str:
    """
    获取给定日期所属周的周一日期。
    
    Args:
        date: 目标日期（默认为今天）
    
    Returns:
        格式为 YYYY-MM-DD 的周一日期字符串
    """
    if date is None:
        date = datetime.now()
    # datetime.weekday() 返回 0-6，0 表示周一
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")

def fix_live_rank_bug(data):
    """
    修正 live-rank 数据中 player.fullName 的错误：
    1. 将 "Jaqueline  Cristian"（双空格）修正为 "Jaqueline Cristian"（单空格）
    2. 将 "Elena-Gabriela Ruse" 修正为 "Elena Gabriela Ruse"
    
    Args:
        data: list，包含排名数据的列表
        
    Returns:
        list: 修正后的排名数据
    """
    for entry in data:
        player = entry.get("player", {})
        old_name = player.get("fullName", "")
        
        if "Jaqueline  Cristian" in old_name:
            new_name = old_name.replace("Jaqueline  Cristian", "Jaqueline Cristian")
            player["fullName"] = new_name
            # 同步修正 firstName（去掉多余空格）
            if player.get("firstName", "").endswith(" "):
                player["firstName"] = player["firstName"].rstrip()
            print(f"[FIX] #{entry.get('ranking', '?')} {old_name!r} -> {new_name!r}")
            
        elif "Elena-Gabriela Ruse" in old_name:
            new_name = old_name.replace("Elena-Gabriela Ruse", "Elena Gabriela Ruse")
            player["fullName"] = new_name
            # 同步修正 firstName（去掉连字符）
            if "Elena-Gabriela" in player.get("firstName", ""):
                player["firstName"] = player["firstName"].replace("Elena-Gabriela", "Elena Gabriela")
            print(f"[FIX] #{entry.get('ranking', '?')} {old_name!r} -> {new_name!r}")
    
    return data

def fetch_live_rank_topn(save_dir, topn=100) -> dict:
    """
    获取 WTA 单打 Live Rank 前 topn 名球员数据。
    
    逻辑：
    1. 计算当前周一的日期
    2. 检查 save_dir 下是否存在 live-rank-topn-{周一日}.json
    3. 如果文件存在且日期匹配，直接加载返回
    4. 如果存在但日期不匹配，删除旧文件并重新获取
    5. 如果不存在，从 WTA API 获取并保存
    
    Args:
        save_dir: 保存文件的目录（默认为 tennis_wta）
    
    Returns:
        解析后的 JSON 数据（list 或 dict，取决于 API 返回）
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 计算当前周的周一日期
    monday_date = get_monday_date()
    target_filename = f"live-rank-top{topn}-{monday_date}.json"
    target_path = os.path.join(save_dir, target_filename)
    
    # 检查是否已存在符合条件的文件
    if os.path.exists(target_path):
        print(f"✓ 找到缓存文件: {target_path}")
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # 清理旧的排名文件（如果存在但日期不匹配）
    for filename in os.listdir(save_dir):
        if filename.startswith(f"live-rank-top{topn}-") and filename.endswith(".json"):
            old_path = os.path.join(save_dir, filename)
            print(f"✗ 删除旧文件: {old_path}")
            os.remove(old_path)
    
    # 从 API 获取新数据
    api_url = f"https://api.wtatennis.com/tennis/players/ranked?metric=SINGLES&type=rankSingles&sort=asc&at={monday_date}&pageSize={topn}"
    print(f"↓ 正在从 API 获取数据: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")
    
    data = fix_live_rank_bug(data)
    
    # 保存到文件
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存: {target_path}")
    
    return data

def fix_calendar_bug(calendar_data):
    """
    将赛历中 tournamentGroup.name 为 'MONTREAL' 或 'TORONTO' 的赛事修正为 'CANADA'
    
    Args:
        calendar_data: dict，包含赛历数据的字典
        
    Returns:
        dict: 修正后的赛历数据
    """
    for entry in calendar_data.get("content", []):
        group = entry.get("tournamentGroup", {})
        name = group.get("name", "")
        
        if name in ("MONTREAL", "TORONTO"):
            print(f" 原 tournamentGroup.name: {name} -> 修正为: CANADA")
            group["name"] = "CANADA"
            
    return calendar_data

def fetch_calendar(year: int = None, save_dir: str = "tennis_wta") -> dict:
    """
    获取指定年份的 WTA 赛事日历数据（过滤掉低级别赛事）。
    
    逻辑：
    1. 确定目标年份（默认当前年份）
    2. 检查 save_dir 下是否存在 calendar-{year}.json
    3. 如果文件存在，直接加载返回
    4. 如果不存在，从 WTA API 获取并保存
    
    Args:
        year: 目标年份（默认为当前年份）
        save_dir: 保存文件的目录（默认为 tennis_wta）
    
    Returns:
        解析后的 JSON 数据（包含赛事列表）
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 确定年份
    if year is None:
        year = datetime.now().year
    
    target_filename = f"calendar-{year}.json"
    target_path = os.path.join(save_dir, target_filename)
    
    # # 检查是否已存在缓存文件
    # if os.path.exists(target_path):
    #     print(f"✓ 找到缓存文件: {target_path}")
    #     with open(target_path, "r", encoding="utf-8") as f:
    #         return json.load(f)
    
    # 构建 API URL（排除低级别赛事）
    exclude_levels = "250k,WTA 125k Series,125K,ITF,WTA 125"
    api_url = (
        f"https://api.wtatennis.com/tennis/tournaments/"
        f"?page=0&pageSize=100&excludeLevels={requests.utils.quote(exclude_levels)}"
        f"&from={year}-01-01&to={year}-12-31"
    )
    print(f"↓ 正在从 API 获取数据: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")
    
    # 保存到文件
    data = fix_calendar_bug(data)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存: {target_path}")
    
    
    return data

def to_title_case(s: str) -> str:
    """转换为 Title Case 用于匹配"""
    return s.strip().title()

def load_historical_calendar(calendar_path: str) -> Dict[Tuple[int, str], str]:
    """
    从 wta_calendar_champs_start_2009.json 加载每年每项赛事的级别映射。
    返回 {(year, tourney_name_title_case): level}
    """
    with open(calendar_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 兼容新旧格式：新格式为 {"last_updated": ..., "data": [...]}，旧格式为直接数组
    data = raw if isinstance(raw, list) else raw.get("data", [])

    mapping = {}
    for entry in data:
        year = entry.get("year")
        name = entry.get("tourney_name")
        level = entry.get("tourney_level")
        if year is None or not name or not level:
            continue
        # 统一转换为 Title Case 以便与 CSV 中的名称匹配
        if to_title_case(name) in ['Montreal', 'Toronto']:
            name = 'Canada'
        key = (year, to_title_case(name))
        mapping[key] = level
    return mapping

def get_current_year_big_tournaments(save_dir: str) -> Dict[str, str]:
    """
    从当前年份的 calendar API 获取 Big Tournament 的 {TitleCase名称: level} 映射。
    用于确定最终输出哪些赛事。
    """
    calendar = fetch_calendar(year=None, save_dir=save_dir)
    tourney_map = {}
    for t in calendar.get("content", []):
        level = t.get("level")
        if level in BIG_LEVELS:
            group = t.get("tournamentGroup", {})
            name = group.get("name")
            if name:
                if to_title_case(name) in ['Montreal', 'Toronto']:
                    name = 'Canada'
                tourney_map[to_title_case(name)] = level
    return tourney_map

def get_topn_big_tournament_stats_json(
    years: range,
    topn: int = 100,
    matches_dir: str = "tennis_wta",
    rank_calendar_dir: str = "output",
    historical_calendar_path: str = "scrape/temp_output/wta_calendar_champs_start_2009.json",
    output_json_path: str = "scrape/temp_output/top50_big_tournament_stats.json"
) -> List[Dict]:
    # 1. 获取 Top n 球员数据
    rank_data = fetch_live_rank_topn(save_dir=rank_calendar_dir, topn=topn)
    
    player_info = {}
    topn_names = set()
    for item in rank_data:
        p = item["player"]
        full_name = p["fullName"]         
        topn_names.add(full_name)
        player_info[full_name] = {
            "rank": item["ranking"],
            "dob": p.get("dateOfBirth"),
            "ioc": p.get("countryCode"),
            "points": item["points"]
        }

    # 2. 加载历史日历映射 (year, tourney_name) -> level
    hist_cal = load_historical_calendar(historical_calendar_path)
    # ✓ 找到缓存文件: output/calendar-2026.json
    print(f'✓ 找到缓存文件:{historical_calendar_path}')

    # 3. 获取当前年份 Big Tournament 列表（最终输出范围）
    big_tourney_map = get_current_year_big_tournaments(rank_calendar_dir)
    print(f"当前年份 Big Tournaments 共 {len(big_tourney_map)} 站: {list(big_tourney_map.keys())}")

    # 4. 初始化统计结构
    stats: Dict[str, Dict[str, Dict]] = {}  # player_name -> tourney_title -> {...}

    # 5. 遍历 CSV 文件
    for year in years:
        file_path = os.path.join(matches_dir, f"wta_matches_{year}.csv")
        if not os.path.exists(file_path):
            print(f"警告：文件 {file_path} 不存在，跳过")
            continue

        df = pd.read_csv(file_path)
        # 注意：不再使用 CSV 自带的 tourney_level，而是用历史日历判定

        for _, row in df.iterrows():
            raw_tourney = row["tourney_name"]
            tourney_title = to_title_case(raw_tourney)
            if to_title_case(tourney_title) in ['Montreal', 'Toronto']:
                tourney_title = 'Canada'
            
            # 仅当该赛事在最终输出列表中才继续（节省处理时间）
            if tourney_title not in big_tourney_map:
                continue

            # 根据年份和赛事名查找历史真实级别
            
            actual_level = hist_cal.get((year, tourney_title))
            if actual_level not in BIG_LEVELS:
                continue  # 该年此赛事不是 Big Level，跳过

            winner = row["winner_name"]
            loser = row["loser_name"]
            round_val = row["round"]
            score = str(row.get("score", "")).strip()

            # 处理胜者
            if winner in topn_names:
                stats.setdefault(winner, {}).setdefault(tourney_title, {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": actual_level,  # 使用真实级别
                    "has_won_final": 0
                })
                entry = stats[winner][tourney_title]
                if score.upper() != "W/O":
                    entry["wins"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
                if round_val == "F":
                    entry["has_won_final"] += 1

            # 处理负者
            if loser in topn_names:
                stats.setdefault(loser, {}).setdefault(tourney_title, {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": actual_level,
                    "has_won_final": False
                })
                entry = stats[loser][tourney_title]
                if score.upper() != "W/O":
                    entry["losses"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
    
    # 补充未参赛记录
    for player in topn_names:
        for tname, level in big_tourney_map.items():
            if player not in stats or tname not in stats[player]:
                stats.setdefault(player, {})[tname] = {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": level,
                    "has_won_final": False
                }

    # 6. 构建 JSON 结果
    result_list = []
    for player, tourneys in stats.items():
        info = player_info.get(player, {})
        tournaments_data = []
        for tname, data in tourneys.items():
            if data["has_won_final"] > 0:
                best_round = "W"
            else:
                rounds = data["rounds_seen"]
                if rounds:
                    max_num = max(ROUND_ORDER[r] for r in rounds if r in ROUND_ORDER)
                    best_round = next(r for r, num in ROUND_ORDER.items() if num == max_num)
                else:
                    best_round = None

            wins = data["wins"]
            losses = data["losses"]
            total = wins + losses
            winrate = wins / total if total > 0 else 0.0

            tournaments_data.append({
                "tourney_name": tname,
                "level": data["level"],
                "best_round": best_round,
                "W": wins,
                "L": losses,
                "winrate": round(winrate, 3),
                "titles": data["has_won_final"]
            })

        tournaments_data.sort(key=lambda x: x["W"], reverse=True)

        result_list.append({
            "player_name": player,
            "rank": info.get("rank"),
            "dob": info.get("dob"),
            "ioc": info.get("ioc"),
            "points": info.get("points"),
            "tournaments": tournaments_data
        })

    result_list.sort(key=lambda x: x["player_name"])

    # 7. 保存 JSON（外层包裹时间戳和数据）
    output = {
        "last_updated": int(time.time()),
        "data": result_list
    }
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"已保存至 {output_json_path}")

    return result_list

def main():
    topn = 100
    get_topn_big_tournament_stats_json(
        years=range(2009, 2027),
        topn=topn,
        matches_dir="tennis_wta",
        rank_calendar_dir="output/",
        historical_calendar_path="output/wta_calendar_champs_start_2009.json", # matches里的level可能存在错误和混乱，所以用calendar_champ文件
        output_json_path=f"output/top{topn}_big_tournament_stats.json"
    )

if __name__ == "__main__":
    main()