#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from tennis_api import TennisApi


BASE_DIR = Path(__file__).resolve().parent
API_CONFIG_PATH = BASE_DIR / "config" / "api_config.json"
REQUEST_CONFIG_PATH = BASE_DIR / "config" / "request_config.json"

with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
    API_CONFIG = json.load(f)

with open(REQUEST_CONFIG_PATH, "r", encoding="utf-8") as f:
    REQUEST_CONFIG = json.load(f)

CALENDAR_API = "tennisapi2"
PLAYER_INFO_API = "tennisapi2"
API_BASE_URL = API_CONFIG[CALENDAR_API]["base_url"]
API_HOST = API_CONFIG[CALENDAR_API]["api_host"]

DEFAULT_YEAR = 2025
DEFAULT_PAGE_SIZE = 200
ALLOWED_RANK_IDS = {2, 3, 4, 7}

# Rate limit: max 4 requests per second => 0.25s between requests
MIN_REQUEST_INTERVAL = 0.25
_last_request_time: Optional[float] = None

# In-memory cache for player info to avoid duplicate API calls
_player_info_cache: Dict[str, Dict[str, Any]] = {}


def _wait_for_rate_limit() -> None:
    """Ensure at least MIN_REQUEST_INTERVAL seconds between API calls."""
    global _last_request_time
    if _last_request_time is not None:
        elapsed = time.time() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def normalize_date(value: Any) -> str:
    """把 ISO 8601 的日期时间字符串转成纯 YYYY-MM-DD。"""
    if not isinstance(value, str):
        return ""
    if "T" in value:
        return value.split("T", 1)[0]
    return value


def normalize_winner(player: Any) -> Dict[str, Any]:
    """把 winner 统一成只保留 id/name/seed/countryAcr 四个字段。"""
    if not isinstance(player, dict):
        return {
            "id": None,
            "name": "",
            "seed": None,
            "countryAcr": "",
        }

    return {
        "id": player.get("id"),
        "name": player.get("name", ""),
        "seed": player.get("seed"),
        "countryAcr": player.get("countryAcr", player.get("countryArc", "")),
    }


def normalize_calendar_record(item: Dict[str, Any]) -> Dict[str, Any]:
    """整理一个 calendar 原始对象，去掉 games，写入 winner、completed 和日期格式。"""
    games = item.get("games") or []
    completed = False
    winner = {
        "id": None,
        "name": "",
        "seed": None,
        "countryAcr": "",
    }

    # 如果 games 不为空，且里面存在 player1 字段，则视为已完成赛事。
    if isinstance(games, list) and games:
        for game in games:
            if isinstance(game, dict) and "player1" in game:
                completed = True
                player1 = game.get("player1")
                winner = normalize_winner(player1)
                break

    # 复制原始字段，但去掉 games 字段，且按要求整理 date 与 winner。
    clean_item = {}
    for key, value in item.items():
        if key == "games":
            continue
        if key == "date":
            clean_item[key] = normalize_date(value)
        else:
            clean_item[key] = value

    # 只保留 winner 字段，并强制写入 key 格式
    clean_item["winner"] = winner
    clean_item["completed"] = completed

    return clean_item


def fetch_calendar_page(tour: str, year: int, page_no: int, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    """
    请求单页 calendar 数据。

    Args:
        tour: 赛事类型，atp 或 wta
        year: 年份，例如 2026
        page_no: 页码，从 1 开始
        page_size: 每页大小，默认 200

    Returns:
        返回单页 list 数据；如果响应为空列表，则返回 []
    """
    api = TennisApi()
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": API_HOST,
        "x-rapidapi-key": api.api_key,
    }

    # 读取 request_config.json 中的 endpoint 模板，保持与项目配置一致
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
    """
    只保留 rank.id 属于 2, 3, 4, 7 的 calendar 项。
    """
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


def fetch_calendar(tour: str, year: int = DEFAULT_YEAR, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    """
    循环抓取 calendar 的所有页，直到返回空 list 为止；
    返回 pageNo=1 开始累加得到的完整列表。
    """
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
    """
    根据 tour 和 player_id 请求球员详细信息。
    返回包含 birthday 和 height 的字典；若请求失败则返回空字典。
    """
    cache_key = f"{tour}:{player_id}"
    if cache_key in _player_info_cache:
        return _player_info_cache[cache_key]

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
        _player_info_cache[cache_key] = {}
        return {}

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        _player_info_cache[cache_key] = {}
        return {}

    # Extract birthday and height
    birthday_raw = data.get("birthday")
    birthday = normalize_date(birthday_raw) if birthday_raw else None

    information = data.get("information") or {}
    height = information.get("height")
    # height may be string like "174", keep as string or convert to int if possible
    if height is not None:
        try:
            height = int(height)
        except (ValueError, TypeError):
            pass

    result = {
        "birthday": birthday,
        "height": height,
    }
    _player_info_cache[cache_key] = result
    return result


def calculate_age(event_date_str: str, birthday_str: str) -> Optional[float]:
    """
    根据赛事日期和出生日期计算夺冠时年龄，保留两位小数。
    """
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
    """
    为每条已完赛记录的 winner 补充 birthday、height 和 age 字段。
    """
    enriched = []
    for item in records:
        winner = item.get("winner") or {}
        player_id = winner.get("id")

        if item.get("completed") and player_id:
            player_info = fetch_player_info(tour, player_id)
            birthday = player_info.get("birthday")
            height = player_info.get("height")
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

    return enriched


def save_calendar_file(tour: str, data: List[Dict[str, Any]], year: int) -> str:
    """
    将 atp / wta 的 calendar list 分别保存到 output/calendar/
    目录下，文件名使用 calendar_{tour}_{year}.json。
    同时会整理每条记录：date 切成 YYYY-MM-DD，删除 games，补上 winner 与 completed 字段。
    最后为已完赛记录的 winner 补充 birthday、height 和 age。
    """
    output_dir = Path("output") / "calendar"
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized = [normalize_calendar_record(item) for item in data]
    enriched = enrich_calendar_with_player_info(normalized, tour)

    output_path = output_dir / f"calendar_{tour}_{year}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"已写入: {output_path}")
    return str(output_path)


def main() -> None:
    year = DEFAULT_YEAR
    for tour in ("atp", "wta"):
        calendar_data = fetch_calendar(tour=tour, year=year)
        save_calendar_file(tour=tour, data=calendar_data, year=year)


if __name__ == "__main__":
    main()