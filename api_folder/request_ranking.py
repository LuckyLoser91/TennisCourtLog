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
    # 示例：后续可继续添加，例如
    # "Some Wrong Name": "Correct Name",
    # "Alexander Zverev Jr.": "Alexander Zverev",
}

# 排名 JSON 文件的存放目录（根据你的项目结构调整）。
# 常见情况：脚本所在目录 or output 子目录。
# 如果文件实际保存在别处，把下面的路径改成对应目录即可。
RANKINGS_DIR = "./output"


def find_latest_rankings_file(tour):
    """根据巡回赛代码，在 RANKINGS_DIR 里找到最新的 rankings_<tour>_*.json。"""
    pattern = os.path.join(RANKINGS_DIR, f"rankings_{tour}_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    # 按修改时间取最新
    return max(files, key=os.path.getmtime)


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

    # 原逻辑：抓取并保存 WTA / ATP 排名
    rank_data = api.request_rank(tour="wta", enrich=True)
    rank_data_atp = api.request_rank(tour="atp", enrich=True)

    # 保存完成后，对最新的排名文件应用手动姓名修正
    for tour in ("wta", "atp"):
        filepath = find_latest_rankings_file(tour)
        print(f"[info] 最新 {tour.upper()} 排名文件：{filepath}")
        apply_name_corrections(filepath, NAME_CORRECTIONS)


if __name__ == "__main__":
    main()