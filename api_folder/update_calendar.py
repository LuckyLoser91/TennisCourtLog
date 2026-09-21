#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

try:
    from tennis_api import TennisApi
except ImportError:
    raise ImportError("无法导入 tennis_api，请确保 tennis_api.py 在项目根目录")

# ==================== 路径与配置 ====================
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "api_folder" / "config"
OUTPUT_DIR = BASE_DIR / "output"

with open(CONFIG_DIR / "api_config.json", "r", encoding="utf-8") as f:
    API_CONFIG = json.load(f)

with open(CONFIG_DIR / "request_config.json", "r", encoding="utf-8") as f:
    REQUEST_CONFIG = json.load(f)

CALENDAR_API = "tennisapi2"
PLAYER_INFO_API = "tennisapi2"
API_BASE_URL = API_CONFIG[CALENDAR_API]["base_url"]
API_HOST = API_CONFIG[CALENDAR_API]["api_host"]

DEFAULT_PAGE_SIZE = 200
ALLOWED_RANK_IDS = {2, 3, 4, 7}

MIN_REQUEST_INTERVAL = 0.5
_last_request_time: Optional[float] = None
_player_profiles_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}


# ==================== 姓名手动修正表 ====================
# 当 API 返回的球员名与实际想要显示的名字不一致时，在这里登记。
# 后续新增修正只需再加一行即可。
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


def apply_name_correction(name: Optional[str]) -> Optional[str]:
    """对球员姓名应用手动修正。"""
    if not name:
        return name
    return NAME_CORRECTIONS.get(name, name)


# ==================== 从 fetch_calendar.py 复制的函数 ====================
def _wait_for_rate_limit() -> None:
    global _last_request_time
    if _last_request_time is not None:
        elapsed = time.time() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def get_profile_path(tour: str) -> Path:
    return BASE_DIR / f"tennis_{tour}" / "player_profile.csv"


def load_profiles(tour: str) -> Dict[str, Dict[str, Any]]:
    path = get_profile_path(tour)
    profiles: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return profiles
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("id", "").strip()
            if pid:
                profiles[pid] = {
                    "name": row.get("name", ""),
                    "id": pid,
                    "birthday": row.get("birthday", "").strip() or None,
                    "height": row.get("height", "").strip() or None,
                }
    return profiles


def save_profiles(tour: str, profiles: Dict[str, Dict[str, Any]]) -> None:
    path = get_profile_path(tour)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "id", "birthday", "height"])
        writer.writeheader()
        for pid in sorted(profiles.keys(), key=lambda x: int(x) if x.isdigit() else float("inf")):
            p = profiles[pid]
            writer.writerow({
                "name": p.get("name", ""),
                "id": pid,
                "birthday": p.get("birthday") or "",
                "height": str(p.get("height")) if p.get("height") is not None else "",
            })


def get_player_profile(tour: str, player_id: int, player_name: str) -> Dict[str, Any]:
    global _player_profiles_cache
    pid_str = str(player_id)
    if tour not in _player_profiles_cache:
        _player_profiles_cache[tour] = load_profiles(tour)
    profiles = _player_profiles_cache[tour]
    if pid_str in profiles:
        return profiles[pid_str]
    api_data = fetch_player_info(tour, player_id)
    profile = {
        "name": player_name or api_data.get("name", ""),
        "id": pid_str,
        "birthday": api_data.get("birthday"),
        "height": api_data.get("height"),
    }
    profiles[pid_str] = profile
    _player_profiles_cache[tour] = profiles
    save_profiles(tour, profiles)
    return profile


def normalize_date(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if "T" in value:
        return value.split("T", 1)[0]
    return value


def normalize_winner(player: Any) -> Dict[str, Any]:
    if not isinstance(player, dict):
        return {"id": None, "name": "", "seed": None, "countryAcr": ""}
    raw_name = player.get("name", "")
    # 应用姓名修正
    corrected_name = apply_name_correction(raw_name)
    return {
        "id": player.get("id"),
        "name": corrected_name,
        "seed": player.get("seed"),
        "countryAcr": player.get("countryAcr", player.get("countryArc", "")),
    }


def normalize_calendar_record(item: Dict[str, Any]) -> Dict[str, Any]:
    games = item.get("games") or []
    completed = False
    winner = {"id": None, "name": "", "seed": None, "countryAcr": ""}
    if isinstance(games, list) and games:
        for game in games:
            if isinstance(game, dict) and "player1" in game:
                completed = True
                player1 = game.get("player1")
                winner = normalize_winner(player1)
                break
    clean_item = {}
    for key, value in item.items():
        if key == "games":
            continue
        if key == "date":
            clean_item[key] = normalize_date(value)
        else:
            clean_item[key] = value
    clean_item["winner"] = winner
    clean_item["completed"] = completed
    return clean_item


def fetch_calendar_page(tour: str, year: int, page_no: int, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    api = TennisApi()
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api.api_key,
    }
    endpoint_template = REQUEST_CONFIG["calendar"]["endpoint_template"]
    endpoint = endpoint_template.format(tour=tour, year=year)
    url = f"{API_BASE_URL}/{endpoint}?pageNo={page_no}&pageSize={page_size}"
    print(f"Fetching {url}")
    _wait_for_rate_limit()
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        print(f"警告：{tour} {year} 第 {page_no} 页返回非 list 响应，类型={type(payload).__name__}")
        return []
    return payload


def filter_calendar_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = []
    for item in records:
        rank = item.get("rank") or {}
        rank_id = rank.get("id")
        if rank_id is None:
            continue
        try:
            rank_id_int = int(rank_id)
        except (TypeError, ValueError):
            continue
        if rank_id_int in ALLOWED_RANK_IDS:
            filtered.append(item)
    print(f"筛选后保留 {len(filtered)} 条记录")
    return filtered


def fetch_calendar(tour: str, year: int, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    page_no = 1
    while True:
        page_data = fetch_calendar_page(tour, year, page_no, page_size)
        if not page_data:
            print(f"{tour} {year} calendar 已抓取完毕，pageNo={page_no} 返回空 list")
            break
        merged.extend(page_data)
        page_no += 1
    print(f"{tour} {year} calendar 完成，共收集 {len(merged)} 条记录")
    return filter_calendar_records(merged)


def fetch_player_info(tour: str, player_id: int) -> Dict[str, Any]:
    api = TennisApi()
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api.api_key,
    }
    endpoint_template = REQUEST_CONFIG["player_info"]["endpoint_template"]
    endpoint = endpoint_template.format(tour=tour, player_id=player_id)
    url = f"{API_BASE_URL}/{endpoint}"
    print(f"Fetching player info: {url}")
    try:
        _wait_for_rate_limit()
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as e:
        print(f"获取球员 {player_id} 信息失败: {e}")
        return {}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {}
    birthday_raw = data.get("birthday")
    birthday = normalize_date(birthday_raw) if birthday_raw else None
    information = data.get("information") or {}
    height = information.get("height")
    if height is not None:
        try:
            height = int(height)
        except (ValueError, TypeError):
            pass
    return {"birthday": birthday, "height": height}


def calculate_age(event_date_str: str, birthday_str: str) -> Optional[float]:
    if not event_date_str or not birthday_str:
        return None
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
        birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
        age_days = (event_date - birthday).days
        if age_days < 0:
            return None
        age = round(age_days / 365.25, 2)
        return age
    except (ValueError, TypeError):
        return None


def enrich_calendar_with_player_info(records: List[Dict[str, Any]], tour: str) -> List[Dict[str, Any]]:
    if tour not in _player_profiles_cache:
        _player_profiles_cache[tour] = load_profiles(tour)
    profiles = _player_profiles_cache[tour]
    enriched = []
    updated_profiles = False
    for item in records:
        winner = item.get("winner") or {}
        player_id = winner.get("id")
        player_name = winner.get("name", "")
        pid_str = str(player_id) if player_id else None
        if item.get("completed") and player_id:
            existing_birthday = winner.get("birthday")
            existing_height = winner.get("height")
            if pid_str and pid_str not in profiles:
                if existing_birthday or existing_height:
                    profiles[pid_str] = {
                        "name": player_name,
                        "id": pid_str,
                        "birthday": existing_birthday if existing_birthday else None,
                        "height": existing_height if existing_height else None,
                    }
                    updated_profiles = True
            profile = get_player_profile(tour, player_id, player_name)
            birthday = profile.get("birthday")
            height = profile.get("height")
            age = calculate_age(item.get("date"), birthday) if birthday else None
            winner["birthday"] = birthday
            winner["height"] = height
            winner["age"] = age
        else:
            winner["birthday"] = None
            winner["height"] = None
            winner["age"] = None
        item["winner"] = winner
        enriched.append(item)
    if updated_profiles:
        _player_profiles_cache[tour] = profiles
        save_profiles(tour, profiles)
    return enriched


# ==================== 更新逻辑 ====================
def process_latest_records(records: List[Dict[str, Any]], tour: str) -> List[Dict[str, Any]]:
    """对抓取到的最新记录进行规范化和 enrich"""
    normalized = [normalize_calendar_record(item) for item in records]
    enriched = enrich_calendar_with_player_info(normalized, tour)
    return enriched


def clean_existing_records(records: List[Dict[str, Any]]) -> int:
    """
    对已存在的历史记录应用姓名修正（若 winner 名称在 NAME_CORRECTIONS 中）。
    返回修正条数。
    """
    changed = 0
    for item in records:
        winner = item.get("winner")
        if not isinstance(winner, dict):
            continue
        raw_name = winner.get("name")
        if not raw_name:
            continue
        corrected = apply_name_correction(raw_name)
        if corrected != raw_name:
            print(f"  历史记录姓名修正: '{raw_name}' -> '{corrected}'")
            winner["name"] = corrected
            changed += 1
    return changed


def update_calendar_summary(tour: str, year: int):
    summary_path = OUTPUT_DIR / f"calendar_{tour}_since_2009.json"
    if not summary_path.exists():
        print(f"文件不存在: {summary_path}")
        return

    print(f"\n{'='*60}")
    print(f"处理 {tour.upper()} {year} 年数据，文件: {summary_path}")

    with open(summary_path, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # 对已有数据一次性应用姓名修正
    cleaned = clean_existing_records(all_records)
    if cleaned:
        print(f"本地已有记录共修正 {cleaned} 条姓名")

    current_year_prefix = str(year)
    local_current = [item for item in all_records if item.get("date", "").startswith(current_year_prefix)]
    other_years = [item for item in all_records if not item.get("date", "").startswith(current_year_prefix)]

    print(f"本地 {year} 年记录数: {len(local_current)}，其他年份记录数: {len(other_years)}")

    print(f"抓取 {tour} {year} calendar...")
    try:
        raw_records = fetch_calendar(tour=tour, year=year, page_size=DEFAULT_PAGE_SIZE)
    except Exception as e:
        print(f"抓取失败: {e}")
        # 即使抓取失败，也要保存已清理后的数据
        if cleaned:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(all_records, f, indent=2, ensure_ascii=False)
            print("已保存历史记录姓名修正结果")
        return

    if not raw_records:
        print("未抓取到任何记录，跳过更新")
        if cleaned:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(all_records, f, indent=2, ensure_ascii=False)
            print("已保存历史记录姓名修正结果")
        return

    latest_records = process_latest_records(raw_records, tour)
    print(f"最新抓取并处理后的记录数: {len(latest_records)}")

    # 构建最新字典，key = (date, name)
    latest_dict = {}
    for item in latest_records:
        key = (item.get("date"), item.get("name"))
        latest_dict[key] = item

    # 构建本地当前年份字典
    local_dict = {}
    for item in local_current:
        key = (item.get("date"), item.get("name"))
        local_dict[key] = item

    # 更新本地当前年份记录
    updated_current = []
    for item in local_current:
        if item.get("completed") is True:
            updated_current.append(item)
            continue

        key = (item.get("date"), item.get("name"))
        if key in latest_dict:
            latest_item = latest_dict[key]
            if latest_item.get("completed") is True:
                print(f"更新赛事: {item.get('name')} ({item.get('date')}) -> 已完成")
                latest_item["rank"] = item.get("rank")
                updated_current.append(latest_item)
            else:
                updated_current.append(item)
        else:
            updated_current.append(item)

    # 新增赛事：最新有但本地当前年份没有的
    new_events = []
    for key, latest_item in latest_dict.items():
        if key not in local_dict:
            print(f"新增赛事: {latest_item.get('name')} ({latest_item.get('date')})")
            new_events.append(latest_item)

    final_current = updated_current + new_events
    final_all = other_years + final_current
    final_all.sort(key=lambda x: x.get("date", ""), reverse=True)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(final_all, f, indent=2, ensure_ascii=False)

    print(f"更新完成: {summary_path}，总记录数: {len(final_all)}")


def main():
    year = datetime.now().year
    print(f"当前年份: {year}")
    for tour in ("atp", "wta"):
        update_calendar_summary(tour, year)


if __name__ == "__main__":
    main()