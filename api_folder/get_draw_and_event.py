import json
import csv
import os
import unicodedata
import pandas as pd
from typing import Dict, List, Set, Optional
from tennis_api import TennisApi
import time



def correct_player_names(draw_file_path: str):
    """
    修正 draw.json 中的球员名字
    
    Args:
        draw_file_path: draw.json 文件路径
    """
    # 名字更正映射表
    NAME_CORRECTIONS = {
        "Catherine McNally": "Caty McNally",
        "Catherine Mcnally": "Caty McNally",
        # 可以在这里添加更多需要更正的名字
    }

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
                        old_name = name
                        new_name = NAME_CORRECTIONS[name]
                        team['name'] = new_name
                        modified_count += 1
                        print(f"  名字已修正: {old_name} -> {new_name}")

                # 同时处理 finalMatchCupBlock 中的 participants
                if 'finalMatchCupBlock' in round_data:
                    final_block = round_data['finalMatchCupBlock']
                    for participant in final_block.get('participants', []):
                        team = participant.get('team', {})
                        name = team.get('name', '')
                        
                        if name in NAME_CORRECTIONS:
                            old_name = name
                            new_name = NAME_CORRECTIONS[name]
                            team['name'] = new_name
                            modified_count += 1
                            print(f"  名字已修正: {old_name} -> {new_name}")

    if modified_count > 0:
        with open(draw_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"共修正 {modified_count} 处名字，文件已更新")
    else:
        print("未发现需要修正的名字")

    return modified_count

def normalize_name(name: str) -> str:
    """格式化球员姓名：去除变音符号、去除多余空格、转 Title Case"""
    name = ' '.join(name.split()).strip().title()
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    return name


def parse_draw_to_csv(draw_file_path: str, output_dir: str):
    """
    解析 draw.json 文件，提取正赛签表数据并保存为 CSV

    Args:
        draw_file_path: draw.json 文件路径
        output_dir: 输出目录路径
    """
    with open(draw_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    main_draw = data['cupTrees'][0]
    csv_rows = []

    for round_data in main_draw['rounds']:
        round_description = round_data['description']

        for block in round_data['blocks']:
            finished = block.get('finished', False)
            block_order = block.get('order', '')
            participants = block.get('participants', [])

            events = block.get('events', [])
            event_id = events[0] if events else ''

            if len(participants) == 0:
                csv_rows.append({
                    'finished': finished, 'round': round_description,
                    'block_order': block_order, 'name': 'TBD','shortname': 'TBD',
                    'ranking': '', 'winner': '', 'teamSeed': '',
                    'team_id': '', 'event_id': event_id
                })
                csv_rows.append({
                    'finished': finished, 'round': round_description,
                    'block_order': block_order, 'name': 'TBD','shortname': 'TBD',
                    'ranking': '', 'winner': '', 'teamSeed': '',
                    'team_id': '', 'event_id': event_id
                })
            elif len(participants) == 1:
                player = participants[0]
                team = player.get('team', {})
                csv_rows.append({
                    'finished': finished, 'round': round_description,
                    'block_order': block_order,
                    'name': normalize_name(team.get('name', '')),
                    'shortname': team.get('shortName', ''),
                    'ranking': team.get('ranking', ''),
                    'winner': player.get('winner', ''),
                    'teamSeed': player.get('teamSeed', ''),
                    'team_id': team.get('id', ''),
                    'event_id': event_id
                })
                csv_rows.append({
                    'finished': finished, 'round': round_description,
                    'block_order': block_order, 'name': 'Bye','shortname':'Bye',
                    'ranking': '', 'winner': '', 'teamSeed': '',
                    'team_id': '', 'event_id': event_id
                })
            else:
                for player in participants:
                    team = player.get('team', {})
                    csv_rows.append({
                        'finished': finished, 'round': round_description,
                        'block_order': block_order,
                        'name': normalize_name(team.get('name', '')),
                        'shortname': team.get('shortName', ''),
                        'ranking': team.get('ranking', ''),
                        'winner': player.get('winner', ''),
                        'teamSeed': player.get('teamSeed', ''),
                        'team_id': team.get('id', ''),
                        'event_id': event_id
                    })

    os.makedirs(output_dir, exist_ok=True)
    csv_file_path = os.path.join(output_dir, 'draw.csv')
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['finished', 'round', 'block_order', 'name', 'shortname', 'ranking', 'winner', 'teamSeed', 'team_id', 'event_id']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"CSV 文件已保存到: {csv_file_path}")
    print(f"共提取 {len(csv_rows)} 行数据")





def fetch_completed_events_from_json():
    """直接从 draw.json 中提取正赛已完成比赛的 event_id，并获取 statistics 和 detail 数据"""
    draw_json_path = "api_folder/data/rome_2026/draw.json"
    output_dir = "api_folder/data/rome_2026"
    os.makedirs(output_dir, exist_ok=True)

    # 读取 draw.json
    with open(draw_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集所有已完成比赛的 event_id
    unique_ids = set()

    # 只处理 cupTrees 中的第一个元素（正赛）
    main_draw = data['cupTrees'][0]
    
    for round_data in main_draw.get('rounds', []):
        for block in round_data.get('blocks', []):
            # 只处理已完成的比赛
            if block.get('finished') != True:
                continue
            
            # 获取 event_id
            events = block.get('events', [])
            if events:
                for event_id in events:
                    unique_ids.add(event_id)

    unique_ids = sorted(unique_ids)
    print(f"共找到 {len(unique_ids)} 个已完成比赛的事件 ID")
    
    if len(unique_ids) > 0:
        print(f"事件 ID: {unique_ids}")
    else:
        print("未找到已完成比赛的事件 ID")
        return

    api = TennisApi()

    for eid in unique_ids:
        try:
            eid_int = int(eid)
        except ValueError:
            print(f"警告：event_id '{eid}' 无法转为整数，跳过")
            continue

        # 1. 获取 statistics（如果文件已存在则跳过）
        stats_path = os.path.join(output_dir, f"event_statistics_{eid_int}.json")
        if not os.path.exists(stats_path):

            try:
                api.request_event_statistics(event_id=eid_int, save_path=stats_path)

            except Exception as e:
                print(f"  statistics 请求失败: {e}")
        else:
            print(f"  statistics 已存在，跳过: {stats_path}")

        # 2. 获取 detail（如果文件已存在则跳过）
        detail_path = os.path.join(output_dir, f"event_detail_{eid_int}.json")
        if not os.path.exists(detail_path):

            try:
                api.request_event_detail(event_id=eid_int, save_path=detail_path)

            except Exception as e:
                print(f"  detail 请求失败: {e}")
        else:
            print(f"  detail 已存在，跳过: {detail_path}")
        time.sleep(0.2)

if __name__ == "__main__":
    # 第一步：获取签表数据
    tennis_api = TennisApi()

    draw_data = tennis_api.request_draw(
        season_id=85600, 
        unique_tournament_id=2569, 
        save_path="api_folder/data/rome_2026/draw.json"
    )

    correct_player_names("api_folder/data/rome_2026/draw.json")
    # 第二步：解析 draw.json 生成 CSV
    parse_draw_to_csv(
        draw_file_path="api_folder/data/rome_2026/draw.json",
        output_dir="api_folder/data/rome_2026/"
    )


    # 第四步： 抓取已完成比赛的 statistics 和 detail
    fetch_completed_events_from_json()