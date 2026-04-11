import pandas as pd
import os
from scripts.config import DATA_PATHS

def load_existing_names(players_file):
    """
    读取 players.csv，返回 (现有姓名集合, 最大 player_id)
    使用 pandas 提高代码简洁性。
    """
    if not players_file.exists():
        print(f"⚠️ 警告：{players_file} 不存在，将创建新文件。")
        return set(), 0

    df = pd.read_csv(players_file)
    
    # 获取所有不重复的姓名
    names = set(df['name'].dropna().unique())
    
    # 获取最大 ID，若 DataFrame 为空则返回 0
    max_id = df['player_id'].max() if not df.empty else 0
    # 注意：max() 可能返回 float 类型，转换为 int（若全为空则返回 nan，需处理）
    max_id = int(max_id) if pd.notna(max_id) else 0

    return names, max_id


def load_active_players(active_file):
    """
    读取 active_rank.csv，返回球员列表（按原始顺序）。
    使用 pandas 读取并过滤。
    """
    if not active_file.exists():
        print(f"❌ 错误：活跃排名文件 {active_file} 不存在，跳过。")
        return []

    df = pd.read_csv(active_file)

    # 过滤姓名为空的行
    df = df[df['name'].notna()]
    if df.empty:
        print("  ⚠️ 活跃排名表中无有效球员。")
        return []

    # 选择需要的列，并转换为字典列表（保持原始顺序）
    # 使用 .fillna('') 处理 NaN 值，再去除字符串空格
    players = []
    for _, row in df.iterrows():
        players.append({
            'name': str(row['name']).strip(),
            'ioc': str(row['ioc']).strip() if pd.notna(row['ioc']) else '',
            'dob': str(row['dob']).strip() if pd.notna(row['dob']) else '',
        })
    return players


def append_new_players(players_file, existing_names, max_id, active_players):
    """将新球员追加写入 players.csv"""
    fieldnames = ['player_id', 'name', 'hand', 'dob', 'ioc', 'height']
    new_id = max_id + 1
    new_rows = []

    for p in active_players:
        if p['name'] not in existing_names:
            new_row = {
                'player_id': new_id,
                'name': p['name'],
                'hand': '',          # 留空，后续可手动补充
                'dob': p['dob'],
                'ioc': p['ioc'],
                'height': '',        # 留空
            }
            new_rows.append(new_row)
            existing_names.add(p['name'])   # 防止同一批里重复添加
            print(f"  ➕ 新增球员: {p['name']} (ID: {new_id})")
            new_id += 1

    if not new_rows:
        print("  ✅ 没有发现新球员，无需更新。")
        return

    file_exists = players_file.exists()
    with open(players_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"  📝 已添加 {len(new_rows)} 名新球员到 {players_file.name}")


def update_player_from_active_rank(tour='wta'):
    """
    根据活跃排名表更新指定巡回赛的历史球员库。
    
    Args:
        tour (str): 'wta' 或 'atp'，默认为 'wta'。
    """

    config = DATA_PATHS[tour]
    players_file = config['players']
    active_file = config['active_rank']

    print(f"\n🔄 正在处理 {tour.upper()} 数据...")
    existing_names, max_id = load_existing_names(players_file)
    active_players = load_active_players(active_file)

    if active_players:
        append_new_players(players_file, existing_names, max_id, active_players)
    else:
        print("  ⏭️  跳过（无活跃数据）")


def update_gs_matches(years=range(1968, 2027), tour='wta'):
    matches_dir = DATA_PATHS[tour]['matches_dir']
    save_path = os.path.join(DATA_PATHS[tour]['matches_dir'], f'{tour}_gs_matches.csv')
    # check if the file exists
    if os.path.exists(save_path):
        # update_gs_matches
        gs_matches = pd.read_csv(save_path)
    else:
        # set a empty dataframe
        gs_matches = pd.DataFrame()  
    for year in years:
        match_path = os.path.join(matches_dir, f'{tour}_matches_{year}.csv')
        cur_matches = pd.read_csv(match_path)
        cur_gs_matches = cur_matches[cur_matches['tourney_level'] == 'Grand Slam']
        # 对cur_gs_matches新建一个首列year，保证是首列，值全为year
        cur_gs_matches.insert(0, 'year', year)
        gs_matches = pd.concat([gs_matches, cur_gs_matches])

    
    gs_matches.to_csv(save_path, index=False)


if __name__ == '__main__':
    # update_gs_matches(years=range(1968, 2027), tour='wta')
    # update_gs_matches(years=range(1968, 2027), tour='atp')
    update_player_from_active_rank(tour='wta')
    update_player_from_active_rank(tour='atp')
    
    
    
    

    


