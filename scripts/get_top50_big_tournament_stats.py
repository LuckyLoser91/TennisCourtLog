import os
import json
import pandas as pd
from typing import List, Dict, Tuple

from fetch_live_data import fetch_live_rank_topn, fetch_calendar

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

def to_title_case(s: str) -> str:
    """转换为 Title Case 用于匹配"""
    return s.title()

def load_historical_calendar(calendar_path: str) -> Dict[Tuple[int, str], str]:
    """
    从 wta_calendar_champs_start_2009.json 加载每年每项赛事的级别映射。
    返回 {(year, tourney_name_title_case): level}
    """
    with open(calendar_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    mapping = {}
    for entry in data:
        year = entry.get("year")
        name = entry.get("tourney_name")
        level = entry.get("tourney_level")
        if year is None or not name or not level:
            continue
        # 统一转换为 Title Case 以便与 CSV 中的名称匹配
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
                tourney_map[to_title_case(name)] = level
    return tourney_map

def get_top50_big_tournament_stats_json(
    years: range,
    matches_dir: str = "tennis_wta",
    save_dir: str = "scrape/temp_output",
    historical_calendar_path: str = "scrape/temp_output/wta_calendar_champs_start_2009.json",
    output_json_path: str = "scrape/temp_output/top50_big_tournament_stats.json"
) -> List[Dict]:
    # 1. 获取 Top 50 球员数据
    rank_data = fetch_live_rank_topn(save_dir=save_dir, topn=50)
    
    player_info = {}
    top50_names = set()
    for item in rank_data:
        p = item["player"]
        full_name = p["fullName"]
        top50_names.add(full_name)
        player_info[full_name] = {
            "rank": item["ranking"],
            "dob": p.get("dateOfBirth"),
            "ioc": p.get("countryCode"),
            "points": item["points"]
        }

    # 2. 加载历史日历映射 (year, tourney_name) -> level
    hist_cal = load_historical_calendar(historical_calendar_path)
    print(f"加载历史日历，共 {len(hist_cal)} 条记录")

    # 3. 获取当前年份 Big Tournament 列表（最终输出范围）
    big_tourney_map = get_current_year_big_tournaments(save_dir)
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
            if winner in top50_names:
                stats.setdefault(winner, {}).setdefault(tourney_title, {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": actual_level,  # 使用真实级别
                    "has_won_final": False
                })
                entry = stats[winner][tourney_title]
                if score.upper() != "W/O":
                    entry["wins"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
                if round_val == "F":
                    entry["has_won_final"] = True

            # 处理负者
            if loser in top50_names:
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
    for player in top50_names:
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
            if data["has_won_final"]:
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
                "winrate": round(winrate, 3)
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

    # 7. 保存 JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)
    print(f"已保存至 {output_json_path}")

    return result_list

if __name__ == "__main__":
    get_top50_big_tournament_stats_json(
        years=range(2009, 2027),
        matches_dir="tennis_wta",
        save_dir="output/",
        historical_calendar_path="output/wta_calendar_champs_start_2009.json",
        output_json_path="output/top50_big_tournament_stats.json"
    )