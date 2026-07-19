"""
非大满贯冠军大满贯战绩排行榜（按胜率排序，Top 100）
前后端分离版本：只生成 JSON 数据文件
====================================================
统计所有未曾赢得大满贯冠军的球员在大满贯赛事中的战绩，
按总胜率降序展示前100名（总胜场 > 5）。

输出：./output/tour_non_gs_champions.json

新增：vs_top8 字段，统计对阵世界排名前8球员的胜负场次
      数据来源：CSV 中的 winner_rank / loser_rank 字段（如存在）

依赖：pip install pandas
用法：python non_gs_champions_leaderboard.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pandas as pd
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

# 轮次优先级（数值越小成绩越好）
ROUND_ORDER = {
    'W': 1,
    'F': 2,
    'SF': 3,
    'QF': 4,
    'R16': 5,
    'R32': 6,
    'R64': 7,
    'R128': 8,
}

ROUND_DISPLAY = {
    'W': 'W',
    'F': 'F',
    'SF': 'SF',
    'QF': 'QF',
    'R16': 'R16',
    'R32': 'R32',
    'R64': 'R64',
    'R128': 'R128',
}

# vs Top N 阈值（可按需调整）
TOP_N = 8


# ══════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════
def get_slam_key(tournament_name):
    if pd.isna(tournament_name):
        return None
    t = str(tournament_name).strip()
    for key, keywords in SLAMS.items():
        if any(kw.lower() in t.lower() for kw in keywords):
            return key
    return None


def normalize_round(r):
    if pd.isna(r):
        return None
    r_str = str(r).strip().upper()
    if r_str in ROUND_ORDER:
        return r_str
    if r_str.startswith('R') and r_str[1:].isdigit():
        return r_str
    mapping = {
        'FINAL': 'F', 'FINALS': 'F',
        'SEMIFINAL': 'SF', 'SEMI FINAL': 'SF', 'SEMIS': 'SF',
        'QUARTERFINAL': 'QF', 'QUARTER FINAL': 'QF', 'QUARTERS': 'QF',
        '4TH ROUND': 'R16', '3RD ROUND': 'R32', '2ND ROUND': 'R64', '1ST ROUND': 'R128',
        'ROUND OF 16': 'R16', 'ROUND OF 32': 'R32',
        'ROUND OF 64': 'R64', 'ROUND OF 128': 'R128',
    }
    for k, v in mapping.items():
        if k in r_str:
            return v
    return None


def round_rank(r):
    if r is None:
        return 999
    return ROUND_ORDER.get(r, 999)


def has_rank_columns(df):
    """检查 DataFrame 是否包含排名字段"""
    return 'winner_rank' in df.columns and 'loser_rank' in df.columns


# ══════════════════════════════════════════════════════════════
# 计算 vs Top N 胜负
# ══════════════════════════════════════════════════════════════
def calc_vs_topn(wins, losses, n=TOP_N):
    """
    计算该球员对阵世界排名前 N 球员的胜负场次（排除 W/O）。

    wins   : 以该球员为 winner 的大满贯比赛 DataFrame
    losses : 以该球员为 loser  的大满贯比赛 DataFrame
    n      : 排名阈值（含），默认 TOP_N=8

    返回字典：
        {
          "w": <胜场数>,
          "l": <负场数>,
          "pct": <胜率，保留1位小数，无记录则 null>
        }
    若 CSV 中不含排名字段，则三项均为 null。
    """
    # 排名字段缺失时返回 null
    if 'loser_rank' not in wins.columns or 'winner_rank' not in losses.columns:
        return {"w": None, "l": None, "pct": None}

    # 该球员赢球时，对手排名存在 loser_rank
    top_wins = wins[
        pd.to_numeric(wins['loser_rank'], errors='coerce').fillna(9999) <= n
    ]
    # 该球员输球时，对手排名存在 winner_rank
    top_losses = losses[
        pd.to_numeric(losses['winner_rank'], errors='coerce').fillna(9999) <= n
    ]

    w = len(top_wins)
    l = len(top_losses)
    total = w + l

    if total == 0:
        pct = None
    else:
        pct = round(w / total * 100, 1)

    return {"w": w, "l": l, "pct": pct}


# ══════════════════════════════════════════════════════════════
# 计算单个非冠军球员战绩
# ══════════════════════════════════════════════════════════════
def calc_non_champion_stats(gs, player):
    wins   = gs[(gs["winner_name"] == player) & (gs["score"] != "W/O")].copy()
    losses = gs[(gs["loser_name"]  == player) & (gs["score"] != "W/O")].copy()

    W, L = len(wins), len(losses)
    if W + L == 0:
        return None

    agg = round(W / (W + L) * 100, 3)

    def surf_wr(surface):
        sw = wins[wins["surface"].astype(str).str.lower() == surface.lower()]
        sl = losses[losses["surface"].astype(str).str.lower() == surface.lower()]
        t = len(sw) + len(sl)
        return round(len(sw) / t * 100) if t > 0 else None

    wins["_slam"]       = wins["tourney_name"].apply(get_slam_key)
    losses["_slam"]     = losses["tourney_name"].apply(get_slam_key)
    wins["_round_norm"] = wins["round"].apply(normalize_round)
    losses["_round_norm"] = losses["round"].apply(normalize_round)

    all_matches = pd.concat([
        wins[["_slam", "_round_norm"]],
        losses[["_slam", "_round_norm"]]
    ])

    slam_best = {}
    for slam in ["AO", "RG", "WIM", "USO"]:
        slam_rounds = all_matches[all_matches["_slam"] == slam]["_round_norm"]
        if slam_rounds.empty:
            slam_best[slam] = None
        else:
            best = min(slam_rounds, key=lambda x: round_rank(x))
            slam_best[slam] = best

    all_rounds   = all_matches["_round_norm"].dropna()
    best_overall = min(all_rounds, key=lambda x: round_rank(x)) if not all_rounds.empty else None

    def format_best(round_key):
        if round_key is None:
            return "—"
        return ROUND_DISPLAY.get(round_key, round_key)

    best_display = format_best(best_overall)
    ao_best  = format_best(slam_best.get("AO"))
    rg_best  = format_best(slam_best.get("RG"))
    wim_best = format_best(slam_best.get("WIM"))
    uso_best = format_best(slam_best.get("USO"))

    best_rank = round_rank(best_overall)

    combined_years = pd.concat([wins["year"], losses["year"]])
    last_year      = int(combined_years.max()) if not combined_years.empty else 0
    last_win_year  = int(wins["year"].max())   if not wins.empty           else 0

    # ── 新增：vs Top 8 胜负 ────────────────────────────────────
    vs_top8 = calc_vs_topn(wins, losses, n=TOP_N)
    # ──────────────────────────────────────────────────────────

    return {
        "W": W, "L": L,
        "agg": agg,
        "win_h": surf_wr("Hard"),
        "win_c": surf_wr("Clay"),
        "win_g": surf_wr("Grass"),
        "best_display": best_display,
        "best_rank": best_rank,
        "ao_best":  ao_best,
        "rg_best":  rg_best,
        "wim_best": wim_best,
        "uso_best": uso_best,
        "last_year":     last_year,
        "last_win_year": last_win_year,
        "vs_top8": vs_top8,   # {"w": int, "l": int, "pct": float|null}
    }


# ══════════════════════════════════════════════════════════════
# 主处理函数（返回 JSON 可序列化的数据）
# ══════════════════════════════════════════════════════════════
def get_non_champions_data(tour='wta'):
    gs_data_path = DATA_PATHS[tour]['gs_matches']
    players_path = DATA_PATHS[tour]['players']
    gs = pd.read_csv(gs_data_path)

    # 检查排名字段是否存在
    if not has_rank_columns(gs):
        print(f"⚠️  [{tour.upper()}] CSV 中未找到 winner_rank / loser_rank 字段，vs_top8 将输出 null")

    # 读取球员信息（ioc、出生年份）
    players_df = pd.read_csv(players_path)
    players_df['dob'] = pd.to_datetime(players_df['dob'], errors='coerce')
    player_info = {}
    for _, row in players_df.iterrows():
        name = row['name']
        dob  = row['dob'] if not pd.isna(row['dob']) else None
        ioc  = row['ioc'] if not pd.isna(row['ioc']) else None
        player_info[name] = {
            'ioc':        ioc,
            'birth_year': dob.year if dob else None,
            'dob':        dob.strftime('%Y-%m-%d') if dob else None,
        }

    # 找出所有大满贯冠军
    finals    = gs[gs["round"].astype(str).str.strip() == 'F'].copy()
    champions = set(finals["winner_name"].unique()) if not finals.empty else set()

    # 所有球员
    all_players  = set(gs["winner_name"].dropna().unique()) | set(gs["loser_name"].dropna().unique())
    non_champions = all_players - champions

    print(f"🏆 {tour.upper()} 冠军人数: {len(champions)}")
    print(f"👥 非冠军球员总数: {len(non_champions)}")

    # 使用 groupby 计算每位球员的总胜场数（排除 Walkover）
    valid_matches      = gs[gs["score"] != "W/O"]
    win_counts         = valid_matches[valid_matches["winner_name"].isin(non_champions)].groupby("winner_name").size()
    players_gt5_wins   = set(win_counts[win_counts > 5].index)

    print(f"📊 非冠军球员中总胜场 > 5 的人数: {len(players_gt5_wins)}")

    data_year_max = gs["year"].max()
    rows = []
    for player in players_gt5_wins:
        stats = calc_non_champion_stats(gs, player)
        if stats:
            info = player_info.get(player, {})
            rows.append({
                "rank":       None,   # 稍后填充
                "player":     player,
                "ioc":        info.get('ioc'),
                "birth_year": info.get('birth_year'),
                "dob":        info.get('dob'),
                "stats":      stats,
            })

    # 按总胜率降序排序，取前100名
    rows.sort(key=lambda r: -r["stats"]["agg"])
    rows = rows[:100]
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    print(f"✅ 最终生成 Top {len(rows)} 非冠军球员榜单")
    return rows, data_year_max


# ══════════════════════════════════════════════════════════════
# 导出 JSON
# ══════════════════════════════════════════════════════════════
def export_to_json(rows_atp, rows_wta, max_year_atp, max_year_wta, output_path):
    data = {
        "meta": {
            "max_years": {
                "atp": int(max_year_atp),
                "wta": int(max_year_wta),
            },
            "vs_top_n": TOP_N,   # 方便前端读取阈值
        },
        "atp": rows_atp,
        "wta": rows_wta,
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已生成: {output_path}")


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    rows_atp, max_year_atp = get_non_champions_data(tour='atp')
    rows_wta, max_year_wta = get_non_champions_data(tour='wta')
    output_path = os.path.join(PROJECT_ROOT, './output/tour_non_gs_champions.json')
    export_to_json(rows_atp, rows_wta, max_year_atp, max_year_wta, output_path)