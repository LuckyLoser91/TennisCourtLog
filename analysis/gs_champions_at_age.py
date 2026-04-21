"""
大满贯冠军「指定年龄对应年份」表现数据生成器
================================================
根据球员出生年份 + 年龄 = 目标年份，提取该年四大满贯成绩。
输出：./output/gs_champions_by_age_year.json
"""
import sys
import os
import json
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import PROJECT_ROOT, DATA_PATHS

# 配置
MIN_AGE = 18
MAX_AGE = 45

SLAMS = {
    "AO": ["Australian Open", "Australian Open 2"],
    "RG": ["Roland Garros"],
    "WIM": ["Wimbledon"],
    "USO": ["US Open"],
}

# 轮次优先级（数字越小越靠前）
ROUND_ORDER = {"F": 1, "SF": 2, "QF": 3, "R16": 4, "R32": 5, "R64": 6, "R128": 7}

def get_slam_key(tourney_name):
    """识别大满贯简称"""
    if pd.isna(tourney_name):
        return None
    t = str(tourney_name).strip()
    for key, keywords in SLAMS.items():
        if any(kw.lower() in t.lower() for kw in keywords):
            return key
    return None

def process_tour(tour):
    """处理单个巡回赛（atp 或 wta）"""
    gs_path = DATA_PATHS[tour]['gs_matches']
    players_path = DATA_PATHS[tour]['players']

    gs = pd.read_csv(gs_path)
    players_df = pd.read_csv(players_path)
    players_df['dob'] = pd.to_datetime(players_df['dob'], errors='coerce')
    players_df['birth_year'] = players_df['dob'].dt.year

    # 所有大满贯冠军（决赛获胜者）
    finals = gs[gs["round"].astype(str).str.strip().str.upper() == 'F']
    champions = finals["winner_name"].unique().tolist()
    print(f"🏆 {tour.upper()} 冠军数: {len(champions)}")

    # 生涯总冠军数统计
    career_titles_map = finals["winner_name"].value_counts().to_dict()

    # 构建球员信息字典
    player_info = {}
    for _, row in players_df[players_df['name'].isin(champions)].iterrows():
        player_info[row['name']] = {
            'dob': row['dob'],
            'birth_year': row['birth_year'] if pd.notna(row['birth_year']) else None,
            'ioc': row['ioc'] if pd.notna(row['ioc']) else None,
        }

    result = []
    for player in champions:
        info = player_info.get(player)
        if not info or info['birth_year'] is None:
            continue

        birth_year = int(info['birth_year'])
        career_titles = career_titles_map.get(player, 0)

        # 获取该球员所有比赛记录（排除 walkover）
        player_matches = gs[
            ((gs["winner_name"] == player) | (gs["loser_name"] == player)) &
            (gs["score"] != "W/O")
        ].copy()
        # 添加 slam_key 列
        player_matches["slam_key"] = player_matches["tourney_name"].apply(get_slam_key)

        age_entries = []
        cumulative_titles = 0
        for age in range(MIN_AGE, MAX_AGE + 1):
            target_year = birth_year + age

            # 筛选该年份的比赛
            year_matches = player_matches[player_matches["year"] == target_year]

            # 初始化数据结构
            entry = {
                "age": age,
                "year": target_year,
                "AO": None, "RG": None, "WIM": None, "USO": None,
                "W": 0, "L": 0, "titles": 0
            }

            if not year_matches.empty:
                # 统计四大满贯成绩
                for slam in ["AO", "RG", "WIM", "USO"]:
                    slam_matches = year_matches[year_matches["slam_key"] == slam]
                    if slam_matches.empty:
                        continue

                    # 找出最佳轮次（按优先级）
                    best_round = None
                    best_val = 999
                    is_champion = False
                    for _, match in slam_matches.iterrows():
                        r = str(match["round"]).strip().upper()
                        val = ROUND_ORDER.get(r, 99)
                        if val < best_val:
                            best_val = val
                            best_round = r
                        # 检查是否为冠军：轮次为F且球员是胜者
                        if r == "F" and match["winner_name"] == player:
                            is_champion = True
                            break

                    # 如果球员在该站夺冠，则记录为 "W"，否则记录最佳轮次
                    if is_champion:
                        display_round = "W"
                        entry["titles"] += 1
                    else:
                        display_round = best_round

                    entry[slam] = display_round

                    # 累计胜负数
                    entry["W"] += len(slam_matches[slam_matches["winner_name"] == player])
                    entry["L"] += len(slam_matches[slam_matches["loser_name"] == player])

            cumulative_titles += entry["titles"]
            entry["cumulative_titles"] = cumulative_titles
            age_entries.append(entry)

        result.append({
            "name": player,
            "ioc": info["ioc"],
            "dob": info["dob"].strftime("%Y-%m-%d") if info["dob"] and pd.notna(info["dob"]) else None,
            "birth_year": birth_year,
            "career_titles": career_titles,
            "age_entries": age_entries
        })

    # 按姓名排序
    result.sort(key=lambda x: x["name"])
    return result

def main():
    print("处理 ATP ...")
    atp_data = process_tour('atp')
    print("处理 WTA ...")
    wta_data = process_tour('wta')

    output = {
        "meta": {"min_age": MIN_AGE, "max_age": MAX_AGE},
        "atp": atp_data,
        "wta": wta_data
    }

    out_path = os.path.join(PROJECT_ROOT, "output", "gs_champions_by_age_year.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ 输出文件：{out_path}")

if __name__ == "__main__":
    main()