#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 获取签表+增强
#     python fetch_and_enhance_draw.py \
#     --tourney-name Wimbledon \
#     --season 2026 \
#     --tournament-id 2600 \
#     --season-id 85945
# 仅增强
#     python fetch_and_enhance_draw.py \
#     --tourney-name Wimbledon \
#     --season 2026 \
#     --skip-download

import argparse
import glob
import json
import os
import time
import unicodedata
from pathlib import Path
from typing import Dict, List

import pandas as pd
from tennis_api import TennisApi

# ---------- 轮次排序（用于判断最佳轮次） ----------
ROUND_ORDER = {
    "R128": 1,
    "R64": 2,
    "R32": 3,
    "R16": 4,
    "QF": 5,
    "SF": 6,
    "F": 7
}

# ---------- 名字修正映射 ----------
NAME_CORRECTIONS = {
    "Catherine McNally": "Caty McNally",
    "Elena-Gabriela Ruse": "Elena Gabriela Ruse",
    # 可继续添加
}

# ---------- 工具函数 ----------
def normalize_name(name: str) -> str:
    """格式化球员姓名：去除变音符号、去除多余空格、转 Title Case"""
    if not name:
        return ""
    name = ' '.join(name.split()).strip().title()
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    return name

def correct_player_names(draw_file_path: str) -> int:
    """修正 draw.json 中的球员名字"""
    with open(draw_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified_count = 0
    for cup_tree in data.get('cupTrees', []):
        for round_data in cup_tree.get('rounds', []):
            for block in round_data.get('blocks', []):
                for participant in block.get('participants', []):
                    team = participant.get('team', {})
                    name = team.get('name', '')
                    if name in NAME_CORRECTIONS:
                        old = name
                        new = NAME_CORRECTIONS[name]
                        team['name'] = new
                        modified_count += 1
                        print(f"  名字已修正: {old} -> {new}")
                # 处理 finalMatchCupBlock
                if 'finalMatchCupBlock' in round_data:
                    final_block = round_data['finalMatchCupBlock']
                    for participant in final_block.get('participants', []):
                        team = participant.get('team', {})
                        name = team.get('name', '')
                        if name in NAME_CORRECTIONS:
                            old = name
                            new = NAME_CORRECTIONS[name]
                            team['name'] = new
                            modified_count += 1
                            print(f"  名字已修正: {old} -> {new}")

    if modified_count > 0:
        with open(draw_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"共修正 {modified_count} 处名字，文件已更新")
    else:
        print("未发现需要修正的名字")
    return modified_count

# ---------- 获取已完成比赛的 statistics 和 detail ----------
def fetch_completed_events(data_dir: str):
    """从 draw.json 中提取已完成比赛的 event_id，并下载 statistics 和 detail"""
    draw_json_path = os.path.join(data_dir, "draw.json")
    if not os.path.exists(draw_json_path):
        print(f"错误：{draw_json_path} 不存在，请先获取签表")
        return

    with open(draw_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    unique_ids = set()
    main_draw = data['cupTrees'][0]
    for round_data in main_draw.get('rounds', []):
        for block in round_data.get('blocks', []):
            if block.get('finished') != True:
                continue
            events = block.get('events', [])
            for eid in events:
                unique_ids.add(eid)

    unique_ids = sorted(unique_ids)
    print(f"共找到 {len(unique_ids)} 个已完成比赛的事件 ID")
    if not unique_ids:
        print("未找到已完成比赛，跳过下载")
        return

    api = TennisApi()
    for eid in unique_ids:
        try:
            eid_int = int(eid)
        except ValueError:
            print(f"警告：event_id '{eid}' 无法转为整数，跳过")
            continue

        stats_path = os.path.join(data_dir, f"event_statistics_{eid_int}.json")
        if not os.path.exists(stats_path):
            try:
                print(f"-------------处理 event_id: {eid_int}------------")
                api.request_event_statistics(event_id=eid_int, save_path=stats_path)
                time.sleep(0.2)
            except Exception as e:
                print(f"  statistics 请求失败: {e}")

        detail_path = os.path.join(data_dir, f"event_detail_{eid_int}.json")
        if not os.path.exists(detail_path):
            try:
                api.request_event_detail(event_id=eid_int, save_path=detail_path)
                time.sleep(0.2)
            except Exception as e:
                print(f"  detail 请求失败: {e}")

# ---------- 加载历史比赛数据 ----------
def load_tennis_dataframe(matches_dir: str = "tennis_wta", start_year: int = 2009) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(matches_dir, "wta_matches_*.csv")))
    if not files:
        print(f"警告：在 {matches_dir} 中未找到任何 CSV 文件")
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            year = int(os.path.basename(f).replace("wta_matches_", "").replace(".csv", ""))
            if year < start_year:
                continue
            df = pd.read_csv(f, dtype=str)
            dfs.append(df)
        except Exception as e:
            print(f"警告：无法读取 {f}，跳过 ({e})")
            continue
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

# ---------- H2H 查询 ----------
def get_h2h_from_df(df: pd.DataFrame, player1: str, player2: str) -> Dict[str, int]:
    p1 = normalize_name(player1)
    p2 = normalize_name(player2)
    mask = ((df['winner_name'] == p1) & (df['loser_name'] == p2)) | \
           ((df['winner_name'] == p2) & (df['loser_name'] == p1))
    matches = df[mask]
    wins_p1 = len(matches[matches['winner_name'] == p1])
    wins_p2 = len(matches[matches['winner_name'] == p2])
    return {"player1_wins": wins_p1, "player2_wins": wins_p2}

# ---------- 历史战绩缓存 ----------
def load_stats_cache(cache_path: str) -> Dict:
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_stats_cache(cache: Dict, cache_path: str):
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"已更新历史战绩缓存，共 {len(cache)} 名球员")

def get_tourney_stats_for_players(
    df: pd.DataFrame,
    player_names: List[str],
    target_tourney: str,
    stats_cache_path: str
) -> Dict[str, Dict]:
    cache = load_stats_cache(stats_cache_path)
    cached_players = {name: cache[name] for name in player_names if name in cache}
    missing_players = [name for name in player_names if name not in cache]

    print(f"缓存命中: {len(cached_players)} 名球员")
    print(f"需要计算: {len(missing_players)} 名球员")

    if not missing_players:
        return cached_players

    df_target = df[df['tourney_name'] == target_tourney].copy()
    missing_stats = {name: {"rounds_seen": set(), "wins": 0, "losses": 0, "has_won_final": 0}
                     for name in missing_players}
    missing_set = set(missing_players)

    for _, row in df_target.iterrows():
        winner = row["winner_name"]
        loser = row["loser_name"]
        round_val = row["round"]
        score = str(row.get("score", "")).strip()

        if winner in missing_set:
            entry = missing_stats[winner]
            if score.upper() != "W/O":
                entry["wins"] += 1
            if round_val in ROUND_ORDER:
                entry["rounds_seen"].add(round_val)
            if round_val == "F":
                entry["has_won_final"] += 1

        if loser in missing_set:
            entry = missing_stats[loser]
            if score.upper() != "W/O":
                entry["losses"] += 1
            if round_val in ROUND_ORDER:
                entry["rounds_seen"].add(round_val)
            

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

    cache.update(new_entries)
    save_stats_cache(cache, stats_cache_path)
    return {**cached_players, **new_entries}

# ---------- 读取比赛详情中的比分 ----------
def get_match_score(data_dir: str, event_id: str) -> Dict:
    if not event_id:
        return {}
    detail_path = os.path.join(data_dir, f"event_detail_{event_id}.json")
    if not os.path.exists(detail_path):
        return {}
    try:
        with open(detail_path, 'r', encoding='utf-8') as f:
            event_data = json.load(f)
        event = event_data.get('event', {})
        home_score = event.get('homeScore', {})
        away_score = event.get('awayScore', {})
        home_periods = {k: v for k, v in home_score.items() if k.startswith('period')}
        away_periods = {k: v for k, v in away_score.items() if k.startswith('period')}
        return {
            'homeScore': home_periods,
            'awayScore': away_periods
        }
    except Exception as e:
        print(f"警告：无法读取比赛详情文件 {detail_path}: {e}")
        return {}

# ---------- 获取单名球员的历史数据 ----------
def find_tourney_stats(name: str, stats_map: Dict, not_found: List, ranking: str) -> Dict:
    if name in ['Bye', 'TBD', '']:
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

# ---------- 核心增强函数 ----------
def enhance_draw(tourney_name: str, season: int, data_dir: str,
                 stats_cache_path: str, output_json_path: str):
    draw_json_path = os.path.join(data_dir, "draw.json")
    if not os.path.exists(draw_json_path):
        print(f"错误：{draw_json_path} 不存在，请先获取签表")
        return

    with open(draw_json_path, 'r', encoding='utf-8') as f:
        draw_data = json.load(f)

    main_draw = draw_data['cupTrees'][0]

    # 收集所有参赛球员（从第一轮提取）
    all_player_names = set()
    player_seed_map = {}
    round_1 = main_draw['rounds'][0] if main_draw['rounds'] else None
    if round_1:
        for block in round_1['blocks']:
            for player in block.get('participants', []):
                team = player.get('team', {})
                name = normalize_name(team.get('name', ''))
                if not name or name in ['Bye', 'TBD', '']:
                    continue
                all_player_names.add(name)
                team_seed = player.get('teamSeed', '')
                if team_seed:
                    player_seed_map[name] = team_seed

    print(f"共找到 {len(all_player_names)} 名球员，其中 {len(player_seed_map)} 名有种子信息")

    # 加载历史数据
    print("正在加载历史比赛数据（用于历史统计和H2H）...")
    matches_df = load_tennis_dataframe("tennis_wta", start_year=2009)
    print(f"加载完成，共 {len(matches_df)} 场比赛记录")

    # 计算历史战绩
    stats_map = get_tourney_stats_for_players(
        df=matches_df,
        player_names=list(all_player_names),
        target_tourney=tourney_name,
        stats_cache_path=stats_cache_path
    )
    print(f"成功获取 {len(stats_map)} 名球员的 {tourney_name} 历史数据")

    current_round = main_draw.get('currentRound', 1)
    not_found = []

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
            result = block.get('result', '')
            block_order = block.get('order', '')
            events = block.get('events', [])
            event_id = events[0] if events else ''
            participants = block.get('participants', [])
            block_id = block.get('blockId', '')

            enhanced_participants = []

            # 处理 participants
            if len(participants) == 0:
                for _ in range(2):
                    enhanced_participants.append({
                        'name': 'TBD', 'shortname': 'TBD', 'ranking': '', 'winner': '',
                        'teamSeed': '', 'team_id': '', 'event_id': event_id,
                        'sourceBlockId': '', 'blockId': block_id,
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
                team_seed = player_seed_map.get(name, player.get('teamSeed', ''))
                enhanced_participants.append({
                    'name': name, 'shortname': shortname, 'ranking': ranking,
                    'winner': player.get('winner', ''),
                    'teamSeed': team_seed,
                    'team_id': team_id,
                    'event_id': event_id,
                    'sourceBlockId': player.get('sourceBlockId', ''),
                    'blockId': block_id,
                    **stats
                })
                enhanced_participants.append({
                    'name': 'Bye', 'shortname': 'Bye', 'ranking': '', 'winner': '',
                    'teamSeed': '', 'team_id': '', 'event_id': event_id,
                    'sourceBlockId': '', 'blockId': '',
                    'best_round': '', 'W': '', 'L': '', 'winrate': '', 'titles': ''
                })
            else:  # len == 2
                for player in participants:
                    team = player.get('team', {})
                    name = normalize_name(team.get('name', ''))
                    shortname = team.get('shortName', '')
                    team_id = team.get('id')
                    ranking = team.get('ranking', '')
                    stats = find_tourney_stats(name, stats_map, not_found, ranking)
                    team_seed = player_seed_map.get(name, player.get('teamSeed', ''))
                    enhanced_participants.append({
                        'name': name, 'shortname': shortname, 'ranking': ranking,
                        'winner': player.get('winner', ''),
                        'teamSeed': team_seed,
                        'team_id': team_id,
                        'event_id': event_id,
                        'sourceBlockId': player.get('sourceBlockId', ''),
                        'blockId': block_id,
                        **stats
                    })

            # 构建 block_info
            block_info = {
                'finished': finished,
                'result': result,
                'order': block_order,
                'event_id': event_id,
                'participants': enhanced_participants
            }

            # H2H（不要求 finished）
            if len(enhanced_participants) == 2:
                p1 = enhanced_participants[0].get('name', '')
                p2 = enhanced_participants[1].get('name', '')
                if p1 and p2 and p1 not in ['Bye', 'TBD'] and p2 not in ['Bye', 'TBD']:
                    h2h = get_h2h_from_df(matches_df, p1, p2)
                    block_info['h2h'] = h2h

            # 比分（仅 finished）
            if finished and len(enhanced_participants) == 2 and event_id:
                score = get_match_score(data_dir, event_id)
                if score:
                    block_info['score'] = score

            round_info['blocks'].append(block_info)

        enhanced_rounds.append(round_info)

    # 输出增强 JSON
    output = {
        'last_updated': int(time.time()),
        'currentRound': current_round,
        'tournament': {
            'name': main_draw.get('name', ''),
            'tournament': main_draw.get('tournament', {})
        },
        'rounds': enhanced_rounds
    }

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    if not_found:
        print(f"\n以下球员未找到 {tourney_name} 赛事历史数据：")
        for player in not_found:
            # player['name'] not 包含R64，R32，R16，Qf，Wqf，Wsf等信息
            if any(round_str in player['name'] for round_str in ['R64', 'R32', 'R16', 'Qf', 'Wqf', 'Wsf']):
                continue
            ranking_info = f" (Rank: {player['ranking']})" if player['ranking'] else ""
            print(f"  - {player['name']}{ranking_info}")

    print(f"\n增强数据已保存：{output_json_path}")
    print(f"当前轮次: Round {current_round}")

# ---------- 主流程 ----------
def main():
    parser = argparse.ArgumentParser(description="获取并增强网球赛事签表数据")
    parser.add_argument('--tourney-name', type=str, default='Wimbledon',
                        help='赛事名称（用于历史数据查询）')
    parser.add_argument('--season', type=int, default=2026,
                        help='赛季年份')
    parser.add_argument('--tournament-id', type=int, default=2600,
                        help='API 赛事ID（默认 2600，对应 Roland Garros）')
    parser.add_argument('--season-id', type=int, default=85945,
                        help='API 赛季ID（默认 85945）')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='数据目录（默认自动生成）')
    parser.add_argument('--output', type=str, default=None,
                        help='增强 JSON 输出路径（默认自动生成）')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过 API 下载，仅做增强（需已有 draw.json 和 detail 文件）')
    args = parser.parse_args()

    # 自动构建目录和输出路径
    tourney_lower = args.tourney_name.lower().replace(' ', '_')
    if args.tourney_name.lower() == 'roland garros':
        tourney_lower = 'roland_garros'

    if args.data_dir is None:
        data_dir = f"api_folder/data/{tourney_lower}_{args.season}"
    else:
        data_dir = args.data_dir

    if args.output is None:
        output_json = f"./output/draw/draw_{tourney_lower}_{args.season}_with_history_stats.json"
    else:
        output_json = args.output

    stats_cache_path = os.path.join(data_dir, "tournament_stats_cache.json")

    print("配置信息:")
    print(f"  赛事名称: {args.tourney_name}")
    print(f"  赛季: {args.season}")
    print(f"  数据目录: {data_dir}")
    print(f"  缓存路径: {stats_cache_path}")
    print(f"  输出路径: {output_json}")

    # 步骤1：获取签表数据（除非跳过下载）
    if not args.skip_download:
        print("\n===== 步骤1：获取签表数据 =====")
        api = TennisApi()
        draw_json_path = os.path.join(data_dir, "draw.json")
        api.request_draw(
            season_id=args.season_id,
            unique_tournament_id=args.tournament_id,
            save_path=draw_json_path
        )
        correct_player_names(draw_json_path)

        # 步骤2：下载已完成比赛的 statistics 和 detail
        print("\n===== 步骤2：下载已完成比赛详情 =====")
        fetch_completed_events(data_dir)
    else:
        print("\n跳过 API 下载，仅做增强")

    # 步骤3：增强签表
    print("\n===== 步骤3：增强签表（历史战绩 + H2H + 比分） =====")
    enhance_draw(
        tourney_name=args.tourney_name,
        season=args.season,
        data_dir=data_dir,
        stats_cache_path=stats_cache_path,
        output_json_path=output_json
    )

    print("\n全部完成！")

if __name__ == "__main__":
    main()