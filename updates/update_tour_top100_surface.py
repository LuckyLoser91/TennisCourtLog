#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_top100_surface_stats.py

从下面三个数据源生成 ATP / WTA Top100 的 surface stats：
  - output/rankings_{tour}_*.json            (最新一期 Top100 排名)
  - output/calendar_{tour}_since_2009.json   (冠军数据)
  - tennis_{tour}/{tour}_matches_YYYY.csv    (2009 至今的比赛结果)

用法（在项目根目录运行）:
  python build_top100_surface_stats.py               # atp + wta
  python build_top100_surface_stats.py --tour wta    # 仅 wta
  python build_top100_surface_stats.py --tour atp    # 仅 atp
"""

import argparse
import csv
import glob
import json
import os
import re
import time
import unicodedata
from collections import defaultdict
from datetime import datetime


# ─── Config ───────────────────────────────────────────────────────────────────

OUTPUT_DIR = "output"
START_YEAR = 2009

# 赛事级别名称（rank.name） -> 内部键
CHAMPS_LEVEL_MAP = {
    "Grand Slam":         "grandSlam",
    "ATP 1000":           "atp1000",
    "ATP 500":            "atp500",
    "ATP 250":            "atp250",
    "WTA 1000":           "wta1000",
    "WTA 500":            "wta500",
    "WTA 250":            "wta250",
    "Tour finals":        "yearEndFinals",
    "Finals":             "yearEndFinals",
    # WTA 旧级别（老数据里可能出现）
    "Premier Mandatory":  "wta1000",
    "Premier 5":          "wta1000",
    "Premier":            "wta500",
    "International":      "wta250",
}

# 场地名称规范化（I.hard -> Hard）
SURFACE_MAP = {
    "Hard":   "Hard",
    "Clay":   "Clay",
    "Grass":  "Grass",
    "Carpet": "Carpet",
    "I.hard": "Hard",
}

VALID_SURFACES = {"Hard", "Clay", "Grass"}
OUTPUT_SURFACES = ("Hard", "Clay", "Grass")

# 排名/日历中的名字 -> CSV 中的名字（如需补充可加到这里）
NAME_ALIASES = {
    # "Elena-Gabriela Ruse": "Elena Gabriela Ruse",
}

# 各 tour 的 titles 键
TITLE_KEYS_BY_TOUR = {
    "wta": ["grandSlam", "wta1000", "wta500", "wta250", "yearEndFinals"],
    "atp": ["grandSlam", "atp1000", "atp500", "atp250", "yearEndFinals"],
}


def get_title_keys(tour: str):
    return TITLE_KEYS_BY_TOUR.get(tour, TITLE_KEYS_BY_TOUR["wta"])


def empty_title_counts(tour: str):
    return {k: 0 for k in get_title_keys(tour)}


def canonical(name: str) -> str:
    return NAME_ALIASES.get(name, name)


def normalize_name(name: str) -> str:
    """去掉变音符号、多余空格，统一 Title Case（与 CSV 对齐）"""
    if not name:
        return ""
    name = " ".join(name.split()).strip().title()
    name = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return name


# ─── 文件定位 ──────────────────────────────────────────────────────────────────

def find_rank_file(tour: str) -> str:
    pattern = os.path.join(OUTPUT_DIR, f"rankings_{tour}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No rank file found: {pattern}")
    return files[-1]


def load_top100(rank_file: str) -> list:
    """读取最新一期 Top100 排名，返回前 100 条。"""
    with open(rank_file, encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("data", data) if isinstance(data, dict) else data

    result = []
    for e in entries[:100]:
        player = e.get("player", {}) or {}
        name = player.get("name") or player.get("fullName") or ""
        result.append({
            "rank":          e.get("position") or e.get("ranking"),
            "fullName":      name,
            "canonicalName": canonical(name),
            "countryCode":   player.get("countryAcr")
                             or player.get("countryCode") or "",
            "dateOfBirth":   player.get("birthday")
                             or player.get("dateOfBirth") or "",
            "height":       player.get("height") or "",
            "points":        e.get("point") or e.get("points") or 0,
        })
    return result


def get_season_year(rank_file: str) -> int:
    """从排名文件第一条的 date 字段推断当前赛季年份。"""
    try:
        with open(rank_file, encoding="utf-8") as f:
            raw = json.load(f)
        entries = raw.get("data", raw) if isinstance(raw, dict) else raw
        if entries and entries[0].get("date"):
            return int(str(entries[0]["date"])[:4])
    except Exception:
        pass
    return datetime.now().year


# ─── Titles（冠军统计） ────────────────────────────────────────────────────────

def load_titles(champs_file: str, player_set: set, tour: str, year: int = None):
    """
    读取 calendar_{tour}_since_2009.json，按级别统计冠军。

    返回:
      overall_titles[name] -> {grandSlam, atp1000/wta1000, ..., yearEndFinals, total}
      surface_titles[name][surface] -> {grandSlam, ..., yearEndFinals}

    year=None 表示全部年份；否则只统计指定年份。
    """
    with open(champs_file, encoding="utf-8") as f:
        data = json.load(f)

    # 兼容两种格式：list 或 {"data": [...]}
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    title_keys = get_title_keys(tour)

    overall = defaultdict(lambda: empty_title_counts(tour))
    by_surface = defaultdict(lambda: defaultdict(lambda: empty_title_counts(tour)))

    for entry in data:
        # 年份过滤
        entry_year = entry.get("year")
        if entry_year is None:
            entry_date = entry.get("date") or ""
            try:
                entry_year = int(str(entry_date)[:4]) if entry_date else None
            except (ValueError, TypeError):
                entry_year = None
        if year is not None and entry_year != year:
            continue

        # 未完成赛事跳过
        if entry.get("completed") is False:
            continue

        # 冠军
        winner = ((entry.get("winner") or {}).get("name") or "").strip()
        if not winner:
            continue
        winner = normalize_name(winner)
        if winner not in player_set:
            continue

        # 级别
        level_raw = ((entry.get("rank") or {}).get("name") or "").strip()
        level_key = CHAMPS_LEVEL_MAP.get(level_raw)
        if level_key is None:
            continue  # ITF / Next Gen / 未知
        if level_key not in title_keys:
            continue  # 跨 tour 的键，忽略

        # 场地
        surface_raw = ((entry.get("court") or {}).get("name") or "").strip()
        surface = SURFACE_MAP.get(surface_raw)
        if surface is None:
            surface = surface_raw.capitalize() if surface_raw else ""
        if surface not in VALID_SURFACES:
            surface = "Hard"

        overall[winner][level_key] += 1
        by_surface[winner][surface][level_key] += 1

    # 计算 total
    for name in overall:
        overall[name]["total"] = sum(
            overall[name].get(k, 0) for k in title_keys
        )

    return overall, by_surface


# ─── 胜 / 负（按场地） ─────────────────────────────────────────────────────────

def load_surface_records(matches_dir: str, tour: str, player_set: set,
                         year: int = None):
    """返回 {name: {surface: {"w": int, "l": int}}}。"""
    records = defaultdict(
        lambda: defaultdict(lambda: {"w": 0, "l": 0})
    )

    pattern = os.path.join(matches_dir, f"{tour}_matches_*.csv")
    for fpath in sorted(glob.glob(pattern)):
        m = re.search(r"(\d{4})", os.path.basename(fpath))
        if not m:
            continue
        file_year = int(m.group(1))
        if year is not None and file_year != year:
            continue
        if file_year < START_YEAR:
            continue

        with open(fpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if "W/O" in (row.get("score") or ""):
                    continue
                surface = (row.get("surface") or "").strip().capitalize()
                if surface not in VALID_SURFACES:
                    continue
                winner = normalize_name((row.get("winner_name") or "").strip())
                loser  = normalize_name((row.get("loser_name")  or "").strip())
                if winner in player_set:
                    records[winner][surface]["w"] += 1
                if loser in player_set:
                    records[loser][surface]["l"] += 1

    return records


# ─── vs Top 8 ────────────────────────────────────────────────────────────────

TOP8_RANK_THRESHOLD = 8


def load_vs_top8_records(matches_dir: str, tour: str, player_set: set,
                         year: int = None):
    """返回 {name: {"w": int, "l": int}}，只统计对手当时排名 <= 8 的比赛。"""
    records = defaultdict(lambda: {"w": 0, "l": 0})

    def parse_rank(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    pattern = os.path.join(matches_dir, f"{tour}_matches_*.csv")
    for fpath in sorted(glob.glob(pattern)):
        m = re.search(r"(\d{4})", os.path.basename(fpath))
        if not m:
            continue
        file_year = int(m.group(1))
        if year is not None and file_year != year:
            continue
        if file_year < START_YEAR:
            continue

        with open(fpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if "W/O" in (row.get("score") or ""):
                    continue
                winner = normalize_name((row.get("winner_name") or "").strip())
                loser  = normalize_name((row.get("loser_name")  or "").strip())

                loser_rank  = parse_rank(row.get("loser_rank"))
                winner_rank = parse_rank(row.get("winner_rank"))

                if (winner in player_set and loser_rank is not None
                        and loser_rank <= TOP8_RANK_THRESHOLD):
                    records[winner]["w"] += 1
                if (loser in player_set and winner_rank is not None
                        and winner_rank <= TOP8_RANK_THRESHOLD):
                    records[loser]["l"] += 1

    return records


# ─── 单球员统计对象 ───────────────────────────────────────────────────────────

def build_player_stat(player: dict, tour: str,
                      overall_titles: dict, surface_titles: dict,
                      records: dict, vs_top8_records: dict) -> dict:
    cname = player["canonicalName"]
    title_keys = get_title_keys(tour)

    ot = overall_titles.get(cname, {**empty_title_counts(tour), "total": 0})

    surface_stats = {}
    for surf in OUTPUT_SURFACES:
        rec = records.get(cname, {}).get(surf, {"w": 0, "l": 0})
        w, l = rec["w"], rec["l"]
        total = w + l
        st = surface_titles.get(cname, {}).get(surf, empty_title_counts(tour))
        surface_stats[surf] = {
            "w":     w,
            "l":     l,
            "total": total,
            "pct":   round(w / total * 100, 1) if total > 0 else None,
            "titles": {k: st.get(k, 0) for k in title_keys},
        }

    all_w = sum(surface_stats[s]["w"] for s in surface_stats)
    all_l = sum(surface_stats[s]["l"] for s in surface_stats)
    all_t = all_w + all_l

    vt8 = vs_top8_records.get(cname, {"w": 0, "l": 0})
    vt8_w, vt8_l = vt8["w"], vt8["l"]
    vt8_total = vt8_w + vt8_l

    titles_obj = {"total": ot.get("total", 0)}
    for k in title_keys:
        titles_obj[k] = ot.get(k, 0)

    return {
        "titles": titles_obj,
        "surface": surface_stats,
        "overall": {
            "w":     all_w,
            "l":     all_l,
            "total": all_t,
            "pct":   round(all_w / all_t * 100, 1) if all_t > 0 else None,
        },
        "vsTop8": {
            "w":     vt8_w,
            "l":     vt8_l,
            "total": vt8_total,
            "pct":   round(vt8_w / vt8_total * 100, 1) if vt8_total > 0 else None,
        },
    }


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def build_stats(tour: str) -> list:
    rank_file   = find_rank_file(tour)
    champs_file = os.path.join(OUTPUT_DIR, f"calendar_{tour}_since_2009.json")

    print(f"[{tour.upper()}] Rank file  : {rank_file}")
    print(f"[{tour.upper()}] Champs file: {champs_file}")

    if not os.path.exists(champs_file):
        raise FileNotFoundError(f"Calendar file not found: {champs_file}")

    players = load_top100(rank_file)
    player_set = {p["canonicalName"] for p in players}
    print(f"[{tour.upper()}] Top 100 players loaded: {len(players)}")

    current_year = get_season_year(rank_file)
    print(f"[{tour.upper()}] Current season year: {current_year}")

    matches_dir = f"tennis_{tour}"
    if not os.path.isdir(matches_dir):
        raise FileNotFoundError(f"Matches dir not found: {matches_dir}")

    # ── Career ──
    overall_titles_career, surface_titles_career = load_titles(
        champs_file, player_set, tour, year=None
    )
    records_career = load_surface_records(
        matches_dir, tour, player_set, year=None
    )
    vs_top8_career = load_vs_top8_records(
        matches_dir, tour, player_set, year=None
    )

    # ── Season ──
    overall_titles_season, surface_titles_season = load_titles(
        champs_file, player_set, tour, year=current_year
    )
    records_season = load_surface_records(
        matches_dir, tour, player_set, year=current_year
    )
    vs_top8_season = load_vs_top8_records(
        matches_dir, tour, player_set, year=current_year
    )

    # ── 组装 ──
    output = []
    for p in players:
        career = build_player_stat(
            p, tour, overall_titles_career, surface_titles_career,
            records_career, vs_top8_career,
        )
        season = build_player_stat(
            p, tour, overall_titles_season, surface_titles_season,
            records_season, vs_top8_season,
        )

        output.append({
            "rank":        p["rank"],
            "fullName":    p["fullName"],
            "countryCode": p["countryCode"],
            "dateOfBirth": p["dateOfBirth"],
            "height":      p["height"],
            "points":      p["points"],
            "career":      career,
            "season":      season,
        })

    return output


def process_tour(tour: str):
    print(f"\n===== 开始处理 {tour.upper()} =====")
    try:
        stats = build_stats(tour)
    except FileNotFoundError as e:
        print(f"跳过 {tour.upper()}: {e}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{tour}_top100_surface_stats.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": int(time.time()),
                "tour":         tour,
                "data":         stats,
            },
            f, ensure_ascii=False, indent=2,
        )

    print(f"[{tour.upper()}] Output → {out_path}  ({len(stats)} records)")


def main():
    parser = argparse.ArgumentParser(
        description="生成 ATP / WTA Top100 surface stats"
    )
    parser.add_argument(
        "--tour", type=str, default=None,
        choices=["atp", "wta"],
        help="只处理指定 tour；不指定则两个都处理",
    )
    args = parser.parse_args()

    tours = [args.tour] if args.tour else ["atp", "wta"]
    for tour in tours:
        process_tour(tour)


if __name__ == "__main__":
    main()