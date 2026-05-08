import argparse
import glob
import json
import os
import pandas as pd
from typing import Dict, List
from get_draw_and_event import normalize_name




# 轮次排序（用于判断最佳轮次）
ROUND_ORDER = {
    "R128": 1,
    "R64": 2,
    "R32": 3,
    "R16": 4,
    "QF": 5,
    "SF": 6,
    "F": 7
}

def to_title_case(s: str) -> str:
    """转换为 Title Case 用于匹配"""
    return s.strip().title()

def load_historical_calendar(calendar_path: str) -> Dict[tuple, str]:
    """
    从 wta_calendar_champs_start_2009.json 加载每年每项赛事的级别映射。
    返回 {(year, tourney_name_title_case): level}
    """
    with open(calendar_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for entry in data:
        year = entry.get("year")
        name = entry.get("tourney_name")
        level = entry.get("tourney_level")
        if year is None or not name or not level:
            continue
        if to_title_case(name) in ['Montreal', 'Toronto']:
            name = 'Canada'
        key = (year, to_title_case(name))
        mapping[key] = level
    return mapping

def load_stats_cache(stats_cache_path) -> Dict[str, Dict]:
    """
    加载罗马战绩缓存文件
    """
    if os.path.exists(stats_cache_path):
        with open(stats_cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_stats_cache(cache: Dict[str, Dict]):
    """
    保存罗马战绩缓存文件
    """
    with open(STATS_CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"已更新罗马战绩缓存，共 {len(cache)} 名球员")

def find_tourney_stats(name: str, stats_map: Dict, not_found: List, ranking: str) -> Dict:
    """查找球员的赛事历史统计数据"""
    if name in ['Bye', 'TBD']:
        return {'best_round': '', 'W': '', 'L': '', 'winrate': '', 'titles': ''}

    if name in stats_map:
        tourney_data = stats_map[name]
        return {
            'best_round': tourney_data.get('best_round', '') or '',
            'W': tourney_data.get('W', ''),
            'L': tourney_data.get('L', ''),
            'winrate': tourney_data.get('winrate', ''),
            'titles': tourney_data.get('titles', '')
        }
    else:
        not_found.append({'name': name, 'ranking': ranking})
        return {'best_round': '', 'W': '', 'L': '', 'winrate': '', 'titles': ''}

def get_tourney_stats_for_players(
    player_names,
    matches_dir,
    historical_calendar_path,
    target_tourney,
    stats_cache_path
) -> Dict[str, Dict]:
    """
    从 tennis_wta 文件夹的历年 CSV 中提取指定球员在赛事的历史统计数据。
    支持缓存：先从缓存读取，缺失的球员再从 CSV 中获取并更新缓存。

    Args:
        player_names: 需要查询的球员姓名列表
        matches_dir: 存放 wta_matches_{year}.csv 的目录
        historical_calendar_path: 历史赛历 JSON 路径
        target_tourney: 目标赛事名称（Title Case），默认为 "Rome"

    Returns:
        {player_name: {best_round, W, L, winrate, titles}} 的字典
    """
    # 加载现有缓存
    cache = load_stats_cache(stats_cache_path)
    
    # 分离已缓存和未缓存的球员
    cached_players = {name: cache[name] for name in player_names if name in cache}
    missing_players = [name for name in player_names if name not in cache]
    
    print(f"缓存命中: {len(cached_players)} 名球员")
    print(f"需要获取: {len(missing_players)} 名球员")
    
    # 如果没有缺失的球员，直接返回缓存结果
    if not missing_players:
        return cached_players
    
    # 加载历史赛历
    hist_cal = load_historical_calendar(historical_calendar_path)
    
    # 初始化缺失球员的统计结构
    missing_stats: Dict[str, Dict] = {}
    for name in missing_players:
        missing_stats[name] = {
            "rounds_seen": set(),
            "wins": 0,
            "losses": 0,
            "has_won_final": 0
        }
    
    # 创建缺失球员名集合用于快速查找
    missing_set = set(missing_players)
    
    # 遍历历年 CSV，只处理缺失的球员
    for year in range(2009, 2027):
        file_path = os.path.join(matches_dir, f"wta_matches_{year}.csv")
        if not os.path.exists(file_path):
            print(f"警告：文件 {file_path} 不存在，跳过")
            continue
        
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            raw_tourney = row["tourney_name"]
            tourney_title = to_title_case(raw_tourney)
            if to_title_case(tourney_title) in ['Montreal', 'Toronto']:
                tourney_title = 'Canada'
            
            # 只处理目标赛事
            if tourney_title != target_tourney:
                continue
            
            # 验证该年此赛事确实是大赛级别
            actual_level = hist_cal.get((year, tourney_title))
            if actual_level not in {"Grand Slam", "WTA 1000", "WTA1000"}:
                continue
            
            winner = row["winner_name"]
            loser = row["loser_name"]
            round_val = row["round"]
            score = str(row.get("score", "")).strip()
            
            # 处理胜者（仅当在缺失球员集合中）
            if winner in missing_set:
                entry = missing_stats[winner]
                if score.upper() != "W/O":
                    entry["wins"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
                if round_val == "F":
                    entry["has_won_final"] += 1
            
            # 处理负者（仅当在缺失球员集合中）
            if loser in missing_set:
                entry = missing_stats[loser]
                if score.upper() != "W/O":
                    entry["losses"] += 1
                if round_val in ROUND_ORDER:
                    entry["rounds_seen"].add(round_val)
    
    # 转换缺失球员的统计为最终格式
    new_entries = {}
    for name, data in missing_stats.items():
        if data["has_won_final"] > 0:
            best_round = "W"
        else:
            rounds = data["rounds_seen"]
            if rounds:
                max_num = max(ROUND_ORDER[r] for r in rounds if r in ROUND_ORDER)
                best_round = next(r for r, num in ROUND_ORDER.items() if num == max_num)
            else:
                best_round = ""
        
        wins = data["wins"]
        losses = data["losses"]
        total = wins + losses
        winrate = wins / total if total > 0 else 0.0
        
        new_entries[name] = {
            "best_round": best_round,
            "W": wins,
            "L": losses,
            "winrate": round(winrate, 3),
            "titles": data["has_won_final"]
        }
    
    # 更新缓存
    cache.update(new_entries)
    save_stats_cache(cache)
    
    # 合并缓存结果和新获取的结果
    result = {**cached_players, **new_entries}
    return result

def enhance_draw(tourney_name, season, data_dir, stats_cache_path, tourney_json_path):
    """为 draw.json 添加赛事历史统计和排名数据，生成结构化的 JSON"""

    draw_json_path = f"{data_dir}/draw.json"

    # 读取原始 draw.json
    with open(draw_json_path, 'r', encoding='utf-8') as f:
        draw_data = json.load(f)


    # 获取正赛签表，收集所有球员名（用于历史统计）
    main_draw = draw_data['cupTrees'][0]
    all_player_names = set()
    for round_data in main_draw['rounds']:
        for block in round_data['blocks']:
            for player in block.get('participants', []):
                team = player.get('team', {})
                name = normalize_name(team.get('name', ''))
                if name and name not in ['Bye', 'TBD', '']:
                    if not (name.startswith('R64P') or name.startswith('R32P') or
                            name.startswith('R16P') or name.startswith('Qf') or
                            name.startswith('Wqf') or name.startswith('Wsf')):
                        all_player_names.add(name)

    print(f"共找到 {len(all_player_names)} 名球员")
    
    # 使用缓存机制获取历史统计
    stats_map = get_tourney_stats_for_players(
        player_names=list(all_player_names),
        matches_dir="tennis_wta",
        historical_calendar_path="output/wta_calendar_champs_start_2009.json",
        target_tourney=tourney_name,
        stats_cache_path=stats_cache_path
    )
    print(f"成功获取 {len(stats_map)} 名球员的{tourney_name}历史数据")

    current_round = main_draw.get('currentRound', 1)
    not_found = []  # 未找到历史数据的球员

    # 构建增强后的 rounds 结构
    enhanced_rounds = []
    for round_data in main_draw['rounds']:
        round_info = {
            'order': round_data['order'],
            'type': round_data['type'],
            'description': round_data['description'],
            'blocks': []
        }

        for block in round_data['blocks']:
            finished = block.get('finished', False)
            block_order = block.get('order', '')
            events = block.get('events', [])
            event_id = events[0] if events else ''
            participants = block.get('participants', [])
            block_id = block.get('blockId', '')

            enhanced_participants = []

            if len(participants) == 0:
                for _ in range(2):
                    enhanced_participants.append({
                        'name': 'TBD', 'shortname': 'TBD','ranking': '', 'winner': '',
                        'teamSeed': '', 'team_id': '', 'event_id': event_id,
                        'sourceBlockId': '',
                        'blockId': '',
                        'best_round': '', 'W': '', 'L': '', 'winrate': '', 'titles': ''
                    })
            elif len(participants) == 1:
                player = participants[0]
                team = player.get('team', {})
                name = normalize_name(team.get('name', ''))
                shortname = team.get('shortName', '')
                team_id = team.get('id')
                ranking = team.get('ranking', '')
                stats = find_tourney_stats(name, stats_map, not_found, ranking)

                enhanced_participants.append({
                    'name': name, 'shortname': shortname, 'ranking': ranking,
                    'winner': player.get('winner', ''),
                    'teamSeed': player.get('teamSeed', ''),
                    'team_id': team_id,
                    'event_id': event_id,
                    'sourceBlockId': player.get('sourceBlockId', ''),
                    'blockId': block_id,
                    **stats
                })
                enhanced_participants.append({
                    'name': 'Bye', 'shortname':'Bye', 'ranking': '', 'winner': '',
                    'teamSeed': '', 'team_id': '', 'event_id': event_id,
                    'sourceBlockId': '',
                    'blockId': '',
                    'best_round': '', 'W': '', 'L': '', 'winrate': '', 'titles': ''
                })
            else:
                for player in participants:
                    team = player.get('team', {})
                    name = normalize_name(team.get('name', ''))
                    shortname = team.get('shortName', '')
                    team_id = team.get('id')
                    ranking = team.get('ranking', '')
                    stats = find_tourney_stats(name, stats_map, not_found, ranking)


                    enhanced_participants.append({
                        'name': name, 'shortname': shortname, 'ranking': ranking,
                        'winner': player.get('winner', ''),
                        'teamSeed': player.get('teamSeed', ''),
                        'team_id': team_id,
                        'event_id': event_id,
                        'sourceBlockId': player.get('sourceBlockId', ''),
                        'block_id': block_id,
                        **stats
                    })

            round_info['blocks'].append({
                'finished': finished,
                'order': block_order,
                'event_id': event_id,
                'participants': enhanced_participants
            })

        enhanced_rounds.append(round_info)

    # 构建最终输出
    output = {
        'currentRound': current_round,
        'tournament': {
            'name': main_draw.get('name', ''),
            'tournament': main_draw.get('tournament', {})
        },
        'rounds': enhanced_rounds
    }

    # 保存 JSON
    with open(tourney_json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # 打印未找到历史数据的球员（仅打印有排名的）
    if len(not_found) > 0:
        print(f"\n以下球员未找到{tourney_name}赛事历史数据：")
        for player in not_found:
            if player['ranking'] != '':
                print(f"  - {player['name']} (Rank: {player['ranking']})")

    print(f"\n增强数据已保存：{tourney_json_path}")
    print(f"当前轮次: Round {current_round}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='获取网球赛事数据')
    parser.add_argument('--tourney-name', type=str, default='Rome',
                        help='赛事名称 (默认: Rome)')
    parser.add_argument('--season', type=int, default=2026,
                        help='赛季年份 (默认: 2026)')
    
    args = parser.parse_args()
    
    # 从参数生成所有需要的变量
    TOURNEY_NAME = args.tourney_name
    SEASON = args.season
    
    # 自动生成路径（组合 lowercase name 和 season）
    tourney_lower = TOURNEY_NAME.lower().replace(' ', '_')
    # map Roland Garros into roland_garros
    DATA_DIR = f"api_folder/data/{tourney_lower}_{SEASON}"
    STATS_CACHE_PATH = f"{DATA_DIR}/tournament_stats_cache.json"
    TOURNEY_JSON_PATH = f"./output/draw_{tourney_lower}_{SEASON}_with_history_stats.json"
    
    print(f"配置信息:")
    print(f"  赛事名称: {TOURNEY_NAME}")
    print(f"  赛季: {SEASON}")
    print(f"  数据目录: {DATA_DIR}")
    print(f"  缓存路径: {STATS_CACHE_PATH}")
    print(f"  输出路径: {TOURNEY_JSON_PATH}")

    enhance_draw(
        tourney_name=TOURNEY_NAME, 
        season=SEASON, 
        data_dir=DATA_DIR,
        stats_cache_path=STATS_CACHE_PATH,
        tourney_json_path=TOURNEY_JSON_PATH)