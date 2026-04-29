import os
import json
import requests
from datetime import datetime, timedelta


def get_monday_date(date: datetime = None) -> str:
    """
    获取给定日期所属周的周一日期。
    
    Args:
        date: 目标日期（默认为今天）
    
    Returns:
        格式为 YYYY-MM-DD 的周一日期字符串
    """
    if date is None:
        date = datetime.now()
    # datetime.weekday() 返回 0-6，0 表示周一
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def fetch_live_rank_topn(save_dir: str = "tennis_wta", topn=100) -> dict:
    """
    获取 WTA 单打 Live Rank 前 topn 名球员数据。
    
    逻辑：
    1. 计算当前周一的日期
    2. 检查 save_dir 下是否存在 live-rank-topn-{周一日}.json
    3. 如果文件存在且日期匹配，直接加载返回
    4. 如果存在但日期不匹配，删除旧文件并重新获取
    5. 如果不存在，从 WTA API 获取并保存
    
    Args:
        save_dir: 保存文件的目录（默认为 tennis_wta）
    
    Returns:
        解析后的 JSON 数据（list 或 dict，取决于 API 返回）
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 计算当前周的周一日期
    monday_date = get_monday_date()
    target_filename = f"live-rank-top{topn}-{monday_date}.json"
    target_path = os.path.join(save_dir, target_filename)
    
    # 检查是否已存在符合条件的文件
    if os.path.exists(target_path):
        print(f"✓ 找到缓存文件: {target_path}")
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # 清理旧的排名文件（如果存在但日期不匹配）
    for filename in os.listdir(save_dir):
        if filename.startswith(f"live-rank-top{topn}-") and filename.endswith(".json"):
            old_path = os.path.join(save_dir, filename)
            print(f"✗ 删除旧文件: {old_path}")
            os.remove(old_path)
    
    # 从 API 获取新数据
    api_url = f"https://api.wtatennis.com/tennis/players/ranked?metric=SINGLES&type=rankSingles&sort=asc&at={monday_date}&pageSize={topn}"
    print(f"↓ 正在从 API 获取数据: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")
    
    # 保存到文件
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存: {target_path}")
    
    return data

def fetch_calendar(year: int = None, save_dir: str = "tennis_wta") -> dict:
    """
    获取指定年份的 WTA 赛事日历数据（过滤掉低级别赛事）。
    
    逻辑：
    1. 确定目标年份（默认当前年份）
    2. 检查 save_dir 下是否存在 calendar-{year}.json
    3. 如果文件存在，直接加载返回
    4. 如果不存在，从 WTA API 获取并保存
    
    Args:
        year: 目标年份（默认为当前年份）
        save_dir: 保存文件的目录（默认为 tennis_wta）
    
    Returns:
        解析后的 JSON 数据（包含赛事列表）
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 确定年份
    if year is None:
        year = datetime.now().year
    
    target_filename = f"calendar-{year}.json"
    target_path = os.path.join(save_dir, target_filename)
    
    # 检查是否已存在缓存文件
    if os.path.exists(target_path):
        print(f"✓ 找到缓存文件: {target_path}")
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # 构建 API URL（排除低级别赛事）
    exclude_levels = "250k,WTA 125k Series,125K,ITF,WTA 125"
    api_url = (
        f"https://api.wtatennis.com/tennis/tournaments/"
        f"?page=0&pageSize=100&excludeLevels={requests.utils.quote(exclude_levels)}"
        f"&from={year}-01-01&to={year}-12-31"
    )
    print(f"↓ 正在从 API 获取数据: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API 请求失败: {e}")
    
    # 保存到文件
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存: {target_path}")
    
    return data


# 使用示例
if __name__ == "__main__":
    calendar_data = fetch_calendar(year=2026, save_dir="./scrape/temp_output")
    print(f"获取到 {len(calendar_data.get('items', calendar_data['content']))} 个赛事")

