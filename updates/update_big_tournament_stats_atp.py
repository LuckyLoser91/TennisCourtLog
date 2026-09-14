"""
ATP Big Tournament 球员数据统计脚本

功能：统计 ATP 当前排名前 topn 的球员在 2009 年起各大赛事的参赛表现数据。

与 WTA 版本的差异：
- 不依赖任何 calendar / 历史冠军日历，ATP 的 4 大满贯 + 9 站 1000 赛自 2009 年起固定。
- 赛事名跨年份归一化：
    * 2025 年之前每站 1000 赛名带 "Masters" 后缀，2025 年起去掉。
    * 加拿大站历史名为 "Canada Masters"，2025 年起叫 "Toronto" 或 "Montreal"，
      统一归一化为 "Canada"。

输入文件：
- ./output/rankings_atp_*.json : ATP 排名数据（取文件名日期最新的一个）
  格式：包含 data[].position, data[].point,
        data[].player.name, data[].player.countryAcr, data[].player.birthday 等字段
- ./tennis_atp/atp_matches_{year}.csv : 清洗后的比赛数据（必需）
  列包含：tourney_name, winner_name, loser_name, round, score

输出文件：
- ./output/top{topn}_big_tournament_stats_atp.json : 球员大赛统计结果

运行方式：
    python update_big_tournament_stats_atp.py
"""

import os
import glob
import json
import time
import pandas as pd
from typing import List, Dict

# ---------------------------------------------------------------------------
# 固定的 ATP 大赛集合（4 大满贯 + 9 站 ATP 1000）
# key 为归一化后的赛事名，value 为赛事级别
# ---------------------------------------------------------------------------
BIG_TOURNAMENTS: Dict[str, str] = {
    # Grand Slam
    "Australian Open": "Grand Slam",
    "Roland Garros":   "Grand Slam",
    "Wimbledon":       "Grand Slam",
    "Us Open":         "Grand Slam",
    # ATP 1000
    "Indian Wells":    "ATP 1000",
    "Miami":           "ATP 1000",
    "Monte Carlo":     "ATP 1000",
    "Madrid":          "ATP 1000",
    "Rome":            "ATP 1000",
    "Canada":          "ATP 1000",
    "Cincinnati":      "ATP 1000",
    "Shanghai":        "ATP 1000",
    "Paris":           "ATP 1000",
}

ROUND_ORDER = {
    "R128": 1,
    "R64":  2,
    "R32":  3,
    "R16":  4,
    "QF":   5,
    "SF":   6,
    "F":    7,
}


# ---------------------------------------------------------------------------
# 名字/赛事名归一化
# ---------------------------------------------------------------------------
def to_title_case(s: str) -> str:
    """转换为 Title Case 用于匹配"""
    return s.strip().title()


def normalize_tourney_name(raw_name) -> str:
    """
    将 CSV 中的赛事名归一化为 BIG_TOURNAMENTS 中的标准名称。

    - 2025 年之前：每站 ATP 1000 名带 "Masters" 后缀（如 "Indian Wells Masters"）
    - 2025 年起：去掉后缀（如 "Indian Wells"）
    - 加拿大站：历史上为 "Canada Masters"，2025 年起为 "Toronto" / "Montreal"，
      统一归一化为 "Canada"
    """
    if not isinstance(raw_name, str) or not raw_name.strip():
        return ""
    name = to_title_case(raw_name)

    # 去掉 " Masters" 后缀
    if name.endswith(" Masters"):
        name = name[: -len(" Masters")].strip()

    # 加拿大站统一为 "Canada"
    if name in ("Toronto", "Montreal", "Canada"):
        name = "Canada"

    return name


def normalize_player_name(name) -> str:
    """
    统一球员姓名格式，用于匹配：
    - 去掉连字符（Auger-Aliassime -> Auger Aliassime）
    - 合并多余空格
    """
    if not isinstance(name, str):
        return ""
    return " ".join(name.replace("-", " ").split())


# ---------------------------------------------------------------------------
# 排名数据加载
# ---------------------------------------------------------------------------
def find_latest_rankings_file(rank_dir: str) -> str:
    """在 rank_dir 下查找最新的 rankings_atp_*.json（兼容 ranking_atp_*.json）"""
    patterns = ["rankings_atp_*.json", "ranking_atp_*.json"]
    files = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(rank_dir, pat)))
    if not files:
        raise FileNotFoundError(
            f"在目录 {rank_dir} 下未找到 rankings_atp_*.json 或 ranking_atp_*.json 文件"
        )
    files.sort()
    return files[-1]


def load_atp_rankings(rank_dir: str, topn: int) -> List[Dict]:
    """加载本地 ATP 排名 JSON，按 position 升序排序后返回前 topn 条记录"""
    path = find_latest_rankings_file(rank_dir)
    print(f"✓ 使用排名文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        data = raw.get("data", [])
    else:
        data = raw

    data = sorted(data, key=lambda x: x.get("position", 10 ** 9))
    return data[:topn]


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------
def get_topn_big_tournament_stats_json_atp(
    years: range,
    topn: int = 100,
    matches_dir: str = "tennis_atp",
    rank_dir: str = "output",
    output_json_path: str = "output/top100_big_tournament_stats_atp.json",
) -> List[Dict]:
    # 1. 加载 Top n 球员
    rank_data = load_atp_rankings(rank_dir=rank_dir, topn=topn)

    player_info: Dict[str, Dict] = {}
    # 归一化名 -> 原始名，便于 CSV 匹配
    norm_to_name: Dict[str, str] = {}
    topn_norm_names = set()

    for item in rank_data:
        p = item["player"]
        full_name = p["name"]
        norm_name = normalize_player_name(full_name)

        topn_norm_names.add(norm_name)
        norm_to_name[norm_name] = full_name
        player_info[full_name] = {
            "rank":   item.get("position"),
            "dob":    p.get("birthday"),
            "ioc":    p.get("countryAcr"),
            "points": item.get("point", item.get("rankingPoints")),
        }

    # 2. 初始化统计结构：player_name -> tourney_name -> {...}
    stats: Dict[str, Dict[str, Dict]] = {}

    # 3. 遍历 CSV 文件
    for year in years:
        file_path = os.path.join(matches_dir, f"atp_matches_{year}.csv")
        if not os.path.exists(file_path):
            print(f"警告：文件 {file_path} 不存在，跳过")
            continue

        df = pd.read_csv(file_path)

        for _, row in df.iterrows():
            tourney_name = normalize_tourney_name(row.get("tourney_name"))
            if tourney_name not in BIG_TOURNAMENTS:
                continue
            level = BIG_TOURNAMENTS[tourney_name]

            winner_raw = row.get("winner_name")
            loser_raw = row.get("loser_name")
            winner_norm = normalize_player_name(winner_raw)
            loser_norm = normalize_player_name(loser_raw)

            round_val = row.get("round")
            score = str(row.get("score", "")).strip()
            is_wo = score.upper() == "W/O"

            # 处理胜者
            if winner_norm in topn_norm_names:
                winner = norm_to_name[winner_norm]
                stats.setdefault(winner, {}).setdefault(tourney_name, {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": level,
                    "has_won_final": 0,
                })
                entry = stats[winner][tourney_name]
                if not is_wo:
                    entry["wins"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
                if round_val == "F":
                    entry["has_won_final"] += 1

            # 处理负者
            if loser_norm in topn_norm_names:
                loser = norm_to_name[loser_norm]
                stats.setdefault(loser, {}).setdefault(tourney_name, {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": level,
                    "has_won_final": 0,
                })
                entry = stats[loser][tourney_name]
                if not is_wo:
                    entry["losses"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)

    # 4. 补齐未参赛记录（保证每个 topn 球员都覆盖所有固定大赛）
    for norm_name, player in norm_to_name.items():
        for tname, level in BIG_TOURNAMENTS.items():
            if player not in stats or tname not in stats[player]:
                stats.setdefault(player, {})[tname] = {
                    "rounds_seen": set(),
                    "wins": 0,
                    "losses": 0,
                    "level": level,
                    "has_won_final": 0,
                }

    # 5. 构建 JSON 结果
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
                "titles": data["has_won_final"],
            })

        tournaments_data.sort(key=lambda x: x["W"], reverse=True)

        result_list.append({
            "player_name": player,
            "rank": info.get("rank"),
            "dob": info.get("dob"),
            "ioc": info.get("ioc"),
            "points": info.get("points"),
            "tournaments": tournaments_data,
        })

    result_list.sort(key=lambda x: x["player_name"])

    # 6. 保存 JSON
    output = {
        "last_updated": int(time.time()),
        "data": result_list,
    }
    out_dir = os.path.dirname(output_json_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"已保存至 {output_json_path}")

    return result_list


def main():
    topn = 100
    get_topn_big_tournament_stats_json_atp(
        years=range(2009, 2027),
        topn=topn,
        matches_dir="tennis_atp",
        rank_dir="output",
        output_json_path=f"output/top{topn}_big_tournament_stats_atp.json",
    )


if __name__ == "__main__":
    main()