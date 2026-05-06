"""
通过指定的tournament id，从tennis api(rapidapi)获取比赛信息csv文件
"""
import json
import os
import requests
import pandas as pd
from datetime import datetime,timedelta

CALENDAR_2026_JSON = "output/calendar-2026.json"


def get_tournament_info(tourney_name):
    """
    tourney_name: Madrid
    返回信息：dict{tourney_name,tourney_level,surface}
    """
    BEST_OF = 3
    tourney_info = {}
    with open(CALENDAR_2026_JSON, 'r', encoding='utf-8') as f:
        calendar_data = json.load(f).get("content")
        for item in calendar_data:
            if item.get("tournamentGroup").get("name").strip().title() == tourney_name.title():
                tourney_info['tourney_name'] = tourney_name
                tourney_info['tourney_level'] = item.get("tournamentGroup").get("level")
                tourney_info['surface'] = item.get("surface")
                tourney_info['best_of'] = BEST_OF
                tourney_info['drawsize'] = item.get("singlesDrawSize")
                tourney_info['startDate'] = item.get("startDate")

                return tourney_info

def requests_api(endpoint, params=None):
    print(f"requesting {endpoint}...")
    base_url = "https://tennis-api-atp-wta-itf.p.rapidapi.com"
    headers = {
        "X-RapidAPI-Key": "4ed1cf9ed3mshf45a50f4cdfa8cfp1d01d3jsn535453c7db68",
        "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com"
    }
    response = requests.get(f"{base_url}{endpoint}", headers=headers,params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: {response.status_code}")
        return None


def get_tournament_result(tourney_id, tourney_name,tour):
    """api tourney_id"""
    save_file_path = f"scrape_json/tourney_result_{tourney_name}_{tourney_id}.json"
    
    
    endpoint = f"/tennis/v2/{tour}/tournament/results/{tourney_id}"
    data = requests_api(endpoint)
    tourney_results = data['data']['singles']
    # save this tourney_results into a json
    with open(save_file_path, 'w', encoding='utf-8') as f:
        json.dump(tourney_results, f)
    
    return tourney_results

def map_tennisapi_round(round_column, drawsize):
    """目前只map普通的"""
    # 查看这个col有多少unique的值
    # 2^total_round <= drawsize,次方
    total_round = 3
    while 2**total_round < drawsize:
        total_round += 1

    if total_round == 5:
        map_dict = {
            4: 'R32',# First Round
            5: 'R16', # Second Round
            9: 'QF', # Quarterfinals
            10: 'SF', # Semifinals
            12: 'F'
            }
    elif total_round == 6:
        map_dict = {
            4: 'R64',# First Round
            5: 'R32', # Second Round
            6: 'R16', # Third Round
            9: 'QF', # Quarterfinals
            10: 'SF', # Semifinals
            12: 'F'
            }
    elif total_round == 7:
        map_dict = {
            4: 'R128',# First Round
            5: 'R64', # Second Round
            6: 'R32', # Third Round
            7: 'R16', # Fourth Round
            9: 'QF', # Quarterfinals
            10: 'SF', # Semifinals
            12: 'F'
            }
    else:
        print(f'Round Totla is {total_round}')
        import sys
        sys.exit()
    
    round_map = round_column.map(map_dict)
    # 统计每个round的次数
    round_count = {}
    for round in round_map:
        if round in round_count:
            round_count[round] += 1
        else:
            round_count[round] = 1
    
    # 需要检查是否有W/O情况
    for round in round_count:
        if 'R' in round:
            # 提取round里的数字
            round_num = int(round.split('R')[1])
            if round_count[round] != (round_num//2):
                # 警告
                print(f'Round {round} has {round_count[round]} matches, but should have {round_num//2}，可能有W/O情况')
        else:
            if round == 'QF':
                if round_count[round] != 4:
                    print(f'Round {round} has {round_count[round]} matches, but should have 8')
            elif round == 'SF':
                if round_count[round] != 2:
                    print(f'Round {round} has {round_count[round]} matches, but should have 2')
            elif round == 'F':
                if round_count[round] != 1:
                    print(f'Round {round} has {round_count[round]} matches, but should have 1')

    return round_map
    

def get_matches(tourney_info,tourney_results):
    col_names = ['tourney_name', 'tourney_level', 'tourney_date', 'surface', 'round', 'best_of', 'winner_name', 'loser_name', 'score']

    rows = []
    for match in tourney_results:
        round = match.get("roundId") #todo:map roundId
        winner_name = match.get("player1").get("name")
        winner_id = match.get("player1").get("id")
        loser_name = match.get("player2").get("name")
        loser_id = match.get("player2").get("id")
        score = match.get("result")
        tourney_date = match.get("date").split('T')[0]
        row = {
            'tourney_name': tourney_info['tourney_name'],
            'tournyey_level': tourney_info['tourney_level'],
            'tourney_date': tourney_date,
            'surface': tourney_info['surface'],
            'round': round,
            'best_of': tourney_info['best_of'],
            'winner_name': winner_name,
            'winner_id': winner_id,
            'loser_name': loser_name,
            'loser_id': loser_id,
            'score': score
        }
        rows.append(row)

    matches_df = pd.DataFrame(rows)
    matches_df['round'] = map_tennisapi_round(matches_df['round'],tourney_info['drawsize'])
    # save this into a csv file
    matches_df.to_csv(f'scrape_json/{tourney_info["tourney_name"]}_{tour}.csv', index=False)
    return matches_df

def get_live_rank(tourney_startDate, tour):
    date_obj = datetime.strptime(tourney_startDate, '%Y-%m-%d')
    monday_obj = date_obj - timedelta(days=date_obj.weekday())
    monday_str = monday_obj.strftime('%Y-%m-%d')
    
    save_file_path = f"api_folder/TennisAPI-ATP-WTA-ITF/data/live_rank_{tour}_{monday_str}.json"

    # 先检查该文件是否存在
    if os.path.exists(save_file_path):
        with open(save_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"load data from {save_file_path}")
            return data
    print(f"正从API获取数据...")

    endpoint = f'/tennis/v2/{tour}/ranking/singles'
    params = {
        'filter': f'RankingDate:{monday_str}',
        "pageSize": 900,
        'pageNo': 1
    }
    data = requests_api(endpoint, params)

    with open(save_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    print(f"save data to {save_file_path}")

    return data

def main(tourney_name, tourney_id, tour):
    
    tourney_info = get_tournament_info(tourney_name)
    print(tourney_info)
    tourney_results = get_tournament_result(tourney_id, tourney_name, tour)
    # pring the list length
    print(f"Tournament Matches Length: {len(tourney_results)}")
    matches_df = get_matches(tourney_info,tourney_results)
    rank_data = get_live_rank(tourney_info['startDate'], tour)

    player_rank_map = {}
    player_point_map = {}
    for item in rank_data['data']:
        player_id = item['player']['id']
        player_rank_map[player_id] = item['position']
        if tour == 'wta':
            player_point_map[player_id] = item['point'] // 100
        if tour == 'atp':
            player_point_map[player_id] = item['point']
    
    matches_df['winner_rank'] = matches_df['winner_id'].map(player_rank_map)
    matches_df['loser_rank'] = matches_df['loser_id'].map(player_rank_map)
    matches_df['winner_rank_points'] = matches_df['winner_id'].map(player_point_map)
    matches_df['loser_rank_points'] = matches_df['loser_id'].map(player_point_map)
    # 7. 检查未匹配到的球员（如果有的话）
    unmatched_winners = matches_df[matches_df['winner_rank'].isna()]['winner_id'].unique()
    unmatched_losers = matches_df[matches_df['loser_rank'].isna()]['loser_id'].unique()
    all_unmatched = set(unmatched_winners) | set(unmatched_losers)

    if all_unmatched:
        print(f"\n警告：以下 {len(all_unmatched)} 个球员ID在 live_rank 中未找到：")
        for pid in all_unmatched:
            print(f"  - ID: {pid}")
    else:
        print("\n✓ 所有球员ID都已成功匹配！")
    matches_df = matches_df.drop(columns=['winner_id', 'loser_id'])
    # 修改tourney_level，去掉字符串里的空格
    matches_df['tournyey_level'] = matches_df['tournyey_level'].str.replace(' ', '')
    # 修改tourney_date，改日期格式为yyyy/mm/dd
    matches_df['tourney_date'] = pd.to_datetime(matches_df['tourney_date']).dt.strftime('%Y/%m/%d')
    # 修改winner_name,loser_name里的Cori Gauff改为Coco Gauff
    matches_df['winner_name'] = matches_df['winner_name'].str.replace('Cori', 'Coco')
    matches_df['loser_name'] = matches_df['loser_name'].str.replace('Cori', 'Coco')

    matches_df.to_csv(f'scrape_json/{tourney_info["tourney_name"]}_{tour}.csv', index=False)
    print(f"save data to scrape_json/{tourney_info['tourney_name']}_{tour}.csv")
    

if __name__ == '__main__':
    # ############################################
    # # 获取tourament的赛事csv文件
    # ############################################
    # tourney_name = "Madrid"
    # tourney_id = 16721
    # tour='wta'
    # main(tourney_name, tourney_id, tour)

    # 获取live_rank的json文件
    tour='wta'
    tourney_startDate = '2025-05-26'
    get_live_rank(tourney_startDate, tour)




        


