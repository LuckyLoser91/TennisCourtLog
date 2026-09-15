import os
import glob
import json

from tennis_api import TennisApi


# ============================================================
# 手动姓名修正表：原始名 → 修正后名称
# ============================================================
# 当 API 返回的球员名与官方 / 你希望显示的名字不一致时，在这里登记。
# 之后新增修正只需再加一行即可。
NAME_CORRECTIONS = {
    "Cori Gauff": "Coco Gauff",
    "Jan-Lennard Struff": "Jan Lennard Struff",
    "Jaume Antoni Munar Clar": "Jaume Munar",
    "Pablo Carreno-Busta": "Pablo Carreno Busta",
    "Leylah Annie Fernandez": "Leylah Fernandez",
    "Caty McNally": "Caty Mcnally",
    "Paula Badosa Gibert": "Paula Badosa",
    "Maria Camila Osorio Serrano": "Camila Osorio",
    "Daniel Merida Aguilar": "Daniel Merida",
    # 示例：后续可继续添加，例如
    # "Some Wrong Name": "Correct Name",
    # "Alexander Zverev Jr.": "Alexander Zverev",
}

# 排名 JSON 文件的存放目录（根据你的项目结构调整）。
RANKINGS_DIR = "./output"


def find_all_rankings_files(tour):
    """根据巡回赛代码，返回 RANKINGS_DIR 里所有 rankings_<tour>_*.json 路径。"""
    pattern = os.path.join(RANKINGS_DIR, f"rankings_{tour}_*.json")
    return glob.glob(pattern)


def find_latest_rankings_file(tour):
    """在 RANKINGS_DIR 里找到最新的 rankings_<tour>_*.json。"""
    files = find_all_rankings_files(tour)
    if not files:
        return None
    # 按修改时间取最新
    return max(files, key=os.path.getmtime)


def cleanup_old_rankings(tour, keep_file):
    """删除 rankings_<tour>_*.json 中除 keep_file 以外的旧文件。"""
    files = find_all_rankings_files(tour)
    deleted = 0
    for f in files:
        # 用 realpath 比较，避免相对/绝对路径不一致导致误删 keep_file
        if os.path.realpath(f) == os.path.realpath(keep_file):
            continue
        try:
            os.remove(f)
            deleted += 1
            print(f"  已删除旧文件：{f}")
        except OSError as e:
            print(f"  [警告] 删除失败 {f}: {e}")

    if deleted:
        print(f"[清理] 已删除 {tour.upper()} 旧排名文件 {deleted} 个，保留：{keep_file}")
    else:
        print(f"[清理] {tour.upper()} 无旧排名文件需要删除。")


def apply_name_corrections(filepath, corrections):
    """读取 JSON，按 corrections 替换球员姓名，再写回原文件。"""
    if not filepath or not os.path.exists(filepath):
        print(f"[skip] 未找到文件：{filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 兼容两种结构：{"data": [...]} 或直接 [...]
    if isinstance(data, dict) and "data" in data:
        records = data["data"]
    elif isinstance(data, list):
        records = data
    else:
        print(f"[skip] 未知 JSON 结构：{filepath}")
        return

    changed = 0
    for record in records:
        player = record.get("player")
        if not isinstance(player, dict):
            continue
        name = player.get("name")
        if name in corrections:
            new_name = corrections[name]
            player["name"] = new_name
            changed += 1
            print(f"  修正：'{name}' -> '{new_name}'")

    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[完成] 已在 {filepath} 中修正 {changed} 处姓名。")
    else:
        print(f"[完成] {filepath} 无需修正。")


def main():
    api = TennisApi()

    # 1. 抓取并保存 WTA / ATP 排名
    rank_data = api.request_rank(tour="wta", enrich=True)
    rank_data_atp = api.request_rank(tour="atp", enrich=True)

    # 2. 对最新排名文件应用手动姓名修正，并清理旧文件
    for tour in ("wta", "atp"):
        filepath = find_latest_rankings_file(tour)
        print(f"[info] 最新 {tour.upper()} 排名文件：{filepath}")
        if not filepath:
            print(f"[skip] 未找到 {tour.upper()} 排名文件，跳过修正与清理。")
            continue

        apply_name_corrections(filepath, NAME_CORRECTIONS)
        cleanup_old_rankings(tour, keep_file=filepath)


if __name__ == "__main__":
    main()