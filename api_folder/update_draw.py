import argparse
import glob
import json
import os
import time
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
    """保留但不再使用（为了兼容性）"""
    with open(calendar_path, "r", encoding="utf-8") as f:
        total_json_data = json.load(f)
        data = total_json_data.get("data", [])
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
    if os.path.exists(stats_cache_path):
        with open(stats_cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_stats_cache(cache: Dict[str, Dict], stats_cache_path: str):
    with open(stats_cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"已更新罗马战绩缓存，共 {len(cache)} 名球员")

def get_match_score(data_dir: str, event_id: str) -> Dict:
    if not event_id:
        return {}
    event_detail_path = os.path.join(data_dir, f"event_detail_{event_id}.json")
    if not os.path.exists(event_detail_path):
        return {}
    try:
        with open(event_detail_path, 'r', encoding='utf-8') as f:
            event_data = json.load(f)
        event = event_data.get('event', {})
        home_score = event.get('homeScore', {})
        away_score = event.get('awayScore', {})
        home_periods = {}
        away_periods = {}
        for key, value in home_score.items():
            if key.startswith('period'):
                home_periods[key] = value
        for key, value in away_score.items():
            if key.startswith('period'):
                away_periods[key] = value
        return {
            'homeScore': home_periods,
            'awayScore': away_periods
        }
    except Exception as e:
        print(f"警告：无法读取比赛详情文件 {event_detail_path}: {e}")
        return {}

def find_tourney_stats(name: str, stats_map: Dict, not_found: List, ranking: str) -> Dict:
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

# ========== 加载所有比赛数据 ==========
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

# ========== H2H 查询 ==========
def get_h2h_from_df(df: pd.DataFrame, player1: str, player2: str) -> Dict[str, int]:
    p1 = normalize_name(player1)
    p2 = normalize_name(player2)
    mask = ((df['winner_name'] == p1) & (df['loser_name'] == p2)) | \
           ((df['winner_name'] == p2) & (df['loser_name'] == p1))
    matches = df[mask]
    wins_p1 = len(matches[matches['winner_name'] == p1])
    wins_p2 = len(matches[matches['winner_name'] == p2])
    return {"player1_wins": wins_p1, "player2_wins": wins_p2}

# ========== 历史统计（无级别过滤） ==========
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
            if round_val == "F":
                entry["has_won_final"] += 1
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

# ========== 核心函数 ==========
def enhance_draw(tourney_name, season, data_dir, stats_cache_path, tourney_json_path):
    draw_json_path = f"{data_dir}/draw.json"
    with open(draw_json_path, 'r', encoding='utf-8') as f:
        draw_data = json.load(f)
    main_draw = draw_data['cupTrees'][0]
    
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
    
    print("正在加载比赛数据框（用于历史统计和H2H）...")
    matches_df = load_tennis_dataframe("tennis_wta", start_year=2009)
    print(f"加载完成，共 {len(matches_df)} 场比赛记录")
    
    stats_map = get_tourney_stats_for_players(
        df=matches_df,
        player_names=list(all_player_names),
        target_tourney=tourney_name,
        stats_cache_path=stats_cache_path
    )
    print(f"成功获取 {len(stats_map)} 名球员的{tourney_name}历史数据")
    
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
            # ---------- 处理 participants ----------
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
                    'name': 'Bye', 'shortname':'Bye', 'ranking': '', 'winner': '',
                    'teamSeed': '', 'team_id': '', 'event_id': event_id,
                    'sourceBlockId': '',
                    'blockId': '',
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
                        'block_id': block_id,
                        **stats
                    })
            # ---------- 构建 block_info ----------
            block_info = {
                'finished': finished,
                'result': result,
                'order': block_order,
                'event_id': event_id,
                'participants': enhanced_participants
            }
            # ---------- H2H：不要求 finished ----------
            if len(enhanced_participants) == 2:
                p1 = enhanced_participants[0].get('name', '')
                p2 = enhanced_participants[1].get('name', '')
                if p1 and p2 and p1 not in ['Bye', 'TBD'] and p2 not in ['Bye', 'TBD']:
                    h2h = get_h2h_from_df(matches_df, p1, p2)
                    block_info['h2h'] = h2h
            # ---------- 比分（仅 finished） ----------
            if finished and len(enhanced_participants) == 2 and event_id:
                block_score = get_match_score(data_dir, event_id)
                if block_score:
                    block_info['score'] = block_score
            round_info['blocks'].append(block_info)
        enhanced_rounds.append(round_info)
    
    output = {
        'last_updated': int(time.time()),
        'currentRound': current_round,
        'tournament': {
            'name': main_draw.get('name', ''),
            'tournament': main_draw.get('tournament', {})
        },
        'rounds': enhanced_rounds
    }
    with open(tourney_json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    if len(not_found) > 0:
        print(f"\n以下球员未找到{tourney_name}赛事历史数据：")
        for player in not_found:
            if player['ranking'] != '':
                print(f"  - {player['name']} (Rank: {player['ranking']})")
    print(f"\n增强数据已保存：{tourney_json_path}")
    print(f"当前轮次: Round {current_round}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='获取网球赛事数据')
    parser.add_argument('--tourney-name', type=str, default='Wimbledon',
                        help='赛事名称 (默认: Wimbledon)')
    parser.add_argument('--season', type=int, default=2026,
                        help='赛季年份 (默认: 2026)')
    args = parser.parse_args()
    TOURNEY_NAME = args.tourney_name
    SEASON = args.season
    tourney_lower = TOURNEY_NAME.lower().replace(' ', '_')
    if TOURNEY_NAME.lower() == 'roland garros':
        tourney_lower = 'roland_garros'
    DATA_DIR = f"api_folder/data/{tourney_lower}_{SEASON}"
    STATS_CACHE_PATH = f"{DATA_DIR}/tournament_stats_cache.json"
    TOURNEY_JSON_PATH = f"./output/draw/draw_{tourney_lower}_{SEASON}_with_history_stats.json"
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
        tourney_json_path=TOURNEY_JSON_PATH
    )