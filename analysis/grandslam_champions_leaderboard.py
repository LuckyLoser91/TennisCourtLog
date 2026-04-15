"""
历史大满贯冠军 Leaderboard（支持年龄截止筛选）
================================
统计所有曾赢得过大满贯冠军的球员在大满贯赛事中的详细战绩
输出：./output/tour_gs_champions.json

依赖：pip install pandas openpyxl
用法：python grandslam_champions_leaderboard.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import pandas as pd
from datetime import datetime
from scripts.config import PROJECT_ROOT, DATA_PATHS

# ══════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════
GS_TIER = "Grand Slam"

SLAMS = {
    "AO":  ["Australian Open", "Australian Open 2"],
    "RG":  ["Roland Garros"],
    "WIM": ["Wimbledon"],
    "USO": ["US Open"],
}

# 年龄统计范围
MIN_AGE = 18
MAX_AGE = 45
STEP = 1  # 整数年龄

def calc_age(birth_date, event_date):
    """
    计算年龄（年），保留一位小数。
    birth_date: datetime 对象或字符串 YYYY-MM-DD / YYYY/MM/DD
    event_date: 字符串，格式 YYYY/MM/DD
    """
    try:
        if isinstance(birth_date, str):
            bd = datetime.strptime(birth_date.strip(), "%Y/%m/%d")
        else:
            bd = birth_date
        ed = datetime.strptime(event_date.strip(), "%Y/%m/%d")
        days = (ed - bd).days
        return round(days / 365.25, 1)
    except:
        return None

def get_slam_key(tournament_name):
    """将赛事名称映射到 AO/RG/WIM/USO"""
    if pd.isna(tournament_name):
        return None
    t = str(tournament_name).strip()
    for key, keywords in SLAMS.items():
        if any(kw.lower() in t.lower() for kw in keywords):
            return key
    return None

def build_match_records(gs, player, player_info):
    """
    为单个球员构建按年龄排序的比赛记录列表（胜场和负场）。
    返回列表，每个元素为 dict，包含：
        age_int: 比赛时年龄向下取整（整数）
        age_float: 实际年龄（一位小数）
        is_win: bool
        surface: 场地
        round: 轮次
        tourney_name: 赛事名称
        year: 年份
        tourney_date: 比赛日期 YYYY/MM/DD
        slam_key: 大满贯简称（AO/RG/WIM/USO）
    """
    wins = gs[(gs["winner_name"] == player) & (gs["score"] != "W/O")].copy()
    losses = gs[(gs["loser_name"] == player) & (gs["score"] != "W/O")].copy()

    records = []
    info = player_info.get(player, {})
    dob = info.get("dob")

    for _, row in wins.iterrows():
        if dob and pd.notna(dob) and "tourney_date" in row and pd.notna(row["tourney_date"]):
            age_float = calc_age(dob, row["tourney_date"])
            age_int = int(age_float) if age_float is not None else None
        else:
            age_float = None
            age_int = None
        records.append({
            "age_int": age_int,
            "age_float": age_float,
            "is_win": True,
            "surface": row.get("surface"),
            "round": row.get("round"),
            "tourney_name": row.get("tourney_name"),
            "year": int(row["year"]) if "year" in row else None,
            "tourney_date": row.get("tourney_date"),
            "slam_key": get_slam_key(row.get("tourney_name")),
        })

    for _, row in losses.iterrows():
        if dob and pd.notna(dob) and "tourney_date" in row and pd.notna(row["tourney_date"]):
            age_float = calc_age(dob, row["tourney_date"])
            age_int = int(age_float) if age_float is not None else None
        else:
            age_float = None
            age_int = None
        records.append({
            "age_int": age_int,
            "age_float": age_float,
            "is_win": False,
            "surface": row.get("surface"),
            "round": row.get("round"),
            "tourney_name": row.get("tourney_name"),
            "year": int(row["year"]) if "year" in row else None,
            "tourney_date": row.get("tourney_date"),
            "slam_key": get_slam_key(row.get("tourney_name")),
        })

    # 按年龄排序（缺失年龄的放最后，但一般不会有缺失）
    records.sort(key=lambda x: (x["age_float"] is None, x["age_float"]))
    return records

def accumulate_stats(records, max_age):
    """
    根据比赛记录，计算每个整数年龄（从 MIN_AGE 到 max_age）的累计统计数据。
    返回列表，每个元素对应一个年龄节点（从 MIN_AGE 开始，连续到 max_age）。
    """
    cumulative = {
        "W": 0,
        "L": 0,
        "titles": 0,
        "titles_by_slam": {"AO": 0, "RG": 0, "WIM": 0, "USO": 0},
        "first_title_year": None,
        "first_title_age": None,
        "last_title_year": None,
        "last_title_age": None,
        "win_by_surface": {"Hard": 0, "Clay": 0, "Grass": 0},
        "loss_by_surface": {"Hard": 0, "Clay": 0, "Grass": 0},
    }

    age_entries = []
    record_idx = 0
    total_records = len(records)

    for age in range(MIN_AGE, max_age + 1):
        # 累加所有 age_int <= age 且尚未累加的记录
        while record_idx < total_records and records[record_idx]["age_float"] is not None and records[record_idx]["age_float"] <= age:
            rec = records[record_idx]
            if rec["is_win"]:
                cumulative["W"] += 1
                surf = rec["surface"]
                if surf in cumulative["win_by_surface"]:
                    cumulative["win_by_surface"][surf] += 1
                if rec["round"] == 'F' and rec["slam_key"]:
                    cumulative["titles"] += 1
                    slam = rec["slam_key"]
                    if slam in cumulative["titles_by_slam"]:
                        cumulative["titles_by_slam"][slam] += 1
                    if cumulative["first_title_year"] is None:
                        cumulative["first_title_year"] = rec["year"]
                        cumulative["first_title_age"] = rec["age_float"]
                    cumulative["last_title_year"] = rec["year"]
                    cumulative["last_title_age"] = rec["age_float"]
            else:
                cumulative["L"] += 1
                surf = rec["surface"]
                if surf in cumulative["loss_by_surface"]:
                    cumulative["loss_by_surface"][surf] += 1
            record_idx += 1

        total = cumulative["W"] + cumulative["L"]
        agg = round(cumulative["W"] / total * 100, 1) if total > 0 else 0

        def surf_wr(win_dict, loss_dict, surf):
            w = win_dict.get(surf, 0)
            l = loss_dict.get(surf, 0)
            if w + l == 0:
                return None
            return round(w / (w + l) * 100)

        win_h = surf_wr(cumulative["win_by_surface"], cumulative["loss_by_surface"], "Hard")
        win_c = surf_wr(cumulative["win_by_surface"], cumulative["loss_by_surface"], "Clay")
        win_g = surf_wr(cumulative["win_by_surface"], cumulative["loss_by_surface"], "Grass")

        parts = []
        for slam in ["AO", "RG", "WIM", "USO"]:
            cnt = cumulative["titles_by_slam"].get(slam, 0)
            if cnt:
                parts.append(f"{slam}×{cnt}")
        titles_str = "  ".join(parts) if parts else "—"

        first_year = cumulative["first_title_year"]
        last_year = cumulative["last_title_year"]
        span = (last_year - first_year + 1) if first_year is not None and last_year is not None else 0

        age_entries.append({
            "age": age,
            "first_year": first_year,
            "age_first": cumulative["first_title_age"],
            "last_year": last_year,
            "age_last": cumulative["last_title_age"],
            "span": span,
            "titles": cumulative["titles"],
            "titles_str": titles_str,
            "W": cumulative["W"],
            "L": cumulative["L"],
            "agg": agg,
            "win_h": win_h,
            "win_c": win_c,
            "win_g": win_g,
        })

    return age_entries

def process_tour(tour):
    """
    处理单个巡回赛（atp 或 wta），返回球员列表，每个球员包含：
        顶层字段（职业生涯总计） + age_entries 数组
    """
    gs_data_path = DATA_PATHS[tour]['gs_matches']
    players_path = DATA_PATHS[tour]['players']

    gs = pd.read_csv(gs_data_path)
    finals = gs[gs["round"].astype(str).str.strip() == 'F'].copy()
    if finals.empty:
        print(f"⚠️  未找到决赛记录 for {tour}")
        return []
    champions = finals.groupby("winner_name")["year"].min().to_dict()
    print(f"\n🏆 {tour.upper()} 历史大满贯冠军数: {len(champions)}")

    # 读取球员信息
    players_df = pd.read_csv(players_path)
    players_df['dob'] = pd.to_datetime(players_df['dob'], errors='coerce')
    champ_players_df = players_df[players_df['name'].isin(champions.keys())]
    player_info = {}
    for _, row in champ_players_df.iterrows():
        name = row['name']
        dob = row['dob'] if pd.notna(row['dob']) else None
        ioc = row['ioc'] if pd.notna(row['ioc']) else None
        birth_year = dob.year if dob else None
        player_info[name] = {'dob': dob, 'ioc': ioc, 'birth_year': birth_year}

    result = []
    for player, first_year in champions.items():
        records = build_match_records(gs, player, player_info)
        if not records:
            continue
        age_entries = accumulate_stats(records, MAX_AGE)
        info = player_info.get(player, {})

        # 职业生涯总计 = age_entries 最后一个元素（年龄 = MAX_AGE）
        career = age_entries[-1] if age_entries else {}

        # 构建顶层字段（与原格式一致）
        player_data = {
            "rank": None,  # 稍后统一排序并填充
            "player": player,
            "tour": tour.upper(),
            "first_year": career.get("first_year"),
            "age_first": career.get("age_first"),
            "last_year": career.get("last_year"),
            "age_last": career.get("age_last"),
            "span": career.get("span"),
            "titles": career.get("titles"),
            "titles_str": career.get("titles_str"),
            "W": career.get("W"),
            "L": career.get("L"),
            "agg": career.get("agg"),
            "win_h": career.get("win_h"),
            "win_c": career.get("win_c"),
            "win_g": career.get("win_g"),
            "ioc": info.get("ioc"),
            "birth_year": info.get("birth_year"),
            "age_entries": age_entries,   # 新增字段
        }
        result.append(player_data)

    # 按冠军数降序排序，并填充 rank
    result.sort(key=lambda x: x["titles"], reverse=True)
    for i, item in enumerate(result, 1):
        item["rank"] = i

    return result

def export_to_json(atp_data, wta_data, output_path):
    data = {
        "meta": {
            "min_age": MIN_AGE,
            "max_age": MAX_AGE,
            "step": STEP
        },
        "atp": atp_data,
        "wta": wta_data
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已生成: {output_path}")

if __name__ == "__main__":
    print("处理 ATP 数据...")
    atp_data = process_tour('atp')
    print("处理 WTA 数据...")
    wta_data = process_tour('wta')
    output_path = os.path.join(PROJECT_ROOT, './output/tour_gs_champions.json')
    export_to_json(atp_data, wta_data, output_path)