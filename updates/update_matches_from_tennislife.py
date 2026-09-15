import csv
import os
import re
import urllib.request
from datetime import datetime

# ===================== 配置 =====================
SOURCES = {
    "wta": {
        "urls": [
            "https://stats.tennismylife.org/data/2026_wta.csv",
            "https://stats.tennismylife.org/data/wta_ongoing_tourneys.csv",
        ],
        "output_dir": "tennis_wta",
        "output_filename": "wta_matches_2026.csv",
        "level_map": {
            "250": "WTA 250",
            "500": "WTA 500",
            "1000": "WTA 1000",
            "G": "Grand Slam",
        },
    },
    "atp": {
        "urls": [
            "https://stats.tennismylife.org/data/2026.csv",
            "https://stats.tennismylife.org/data/ongoing_tourneys.csv",
        ],
        "output_dir": "tennis_atp",
        "output_filename": "atp_matches_2026.csv",
        "level_map": {
            "250": "ATP 250",
            "500": "ATP 500",
            "M": "ATP 1000",
            "G": "Grand Slam",
        },
    },
}

# 最终输出的列，顺序固定
OUTPUT_COLUMNS = [
    "tourney_name",
    "tourney_level",
    "tourney_date",
    "surface",
    "round",
    "best_of",
    "winner_name",
    "loser_name",
    "score",
    "winner_rank",
    "loser_rank",
    "winner_rank_points",
    "loser_rank_points",
]


# ===================== 工具函数 =====================
def convert_level(value: str, level_map: dict) -> str:
    value = (value or "").strip()
    return level_map.get(value, value)


def convert_date(value: str) -> str:
    value = (value or "").strip()
    if len(value) == 8 and value.isdigit():
        return datetime.strptime(value, "%Y%m%d").strftime("%Y/%m/%d")
    return value
def normalize_player_name(name: str) -> str:
    """球员姓名规范化：
    - 把 '-' 替换为空格（'Elena-Gabriela Ruse' -> 'Elena Gabriela Ruse'）
    - 每个单词首字母大写、其余小写（保持 Title Case）
    - 修正撇号后误大写（O'Sullivan -> O'sullivan，一般球员名不会出现，稳妥处理）
    - 压缩多余空格
    """
    if not name:
        return ""
    name = name.replace("-", " ")
    name = " ".join(name.split()).strip()
    name = name.title()
    name = re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), name)
    return name


def title_case_tourney_name(name: str) -> str:
    """每个单词首字母大写，其余小写。
    'US Open'         -> 'Us Open'
    'ROLEX PARIS...'  -> 'Rolex Paris Masters'
    "Queen's Club"    -> "Queen's Club"   （修正 title() 的撇号问题）
    'S-Hertogenbosch' -> 'S-Hertogenbosch'
    """
    if not name:
        return ""
    result = name.title()
    # 把 "'S" 修正为 "'s"；例如 Queen'S -> Queen's
    result = re.sub(r"'([A-Z])", lambda m: "'" + m.group(1).lower(), result)
    return result


# ===================== 下载 =====================
def download_csv(url: str) -> str:
    """下载 CSV 并返回文本内容；失败返回 None"""
    print(f"正在下载：{url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"  [警告] 下载失败：{e}")
        return None

    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def parse_csv(text: str):
    """把 CSV 文本解析成 list[dict]"""
    if not text:
        return []
    reader = csv.DictReader(text.splitlines())
    return list(reader)


# ===================== 处理与保存 =====================
def process_and_save(records, output_path: str, level_map: dict):
    """把合并后的记录转换成统一格式并保存"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as fout:
        writer = csv.DictWriter(
            fout,
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()

        count = 0
        for row in records:
            out_row = {
                "tourney_name": title_case_tourney_name(row.get("tourney_name", "")),
                "tourney_level": convert_level(row.get("tourney_level", ""), level_map),
                "tourney_date": convert_date(row.get("tourney_date", "")),
                "surface": row.get("surface", ""),
                "round": row.get("round", ""),
                "best_of": row.get("best_of", ""),
                "winner_name": normalize_player_name(row.get("winner_name", "")),   # ← 新增
                "loser_name":  normalize_player_name(row.get("loser_name", "")),    # ← 新增
                "score": row.get("score", ""),
                "winner_rank": row.get("winner_rank", ""),
                "loser_rank": row.get("loser_rank", ""),
                "winner_rank_points": row.get("winner_rank_points", ""),
                "loser_rank_points": row.get("loser_rank_points", ""),
            }
            writer.writerow(out_row)
            count += 1

    print(f"已保存：{output_path}（共 {count} 行）")


# ===================== 主流程 =====================
def main():
    for key, cfg in SOURCES.items():
        print(f"\n===== 处理 {key.upper()} =====")

        # 1. 下载并解析所有来源，合并记录（主 CSV 在前，ongoing 在后）
        merged_records = []
        for url in cfg["urls"]:
            text = download_csv(url)
            records = parse_csv(text)
            print(f"  {url} -> {len(records)} 行")
            merged_records.extend(records)

        print(f"  合并后共 {len(merged_records)} 行")

        # 2. 转换 + 保存
        output_path = os.path.join(cfg["output_dir"], cfg["output_filename"])
        process_and_save(merged_records, output_path, cfg["level_map"])


if __name__ == "__main__":
    main()