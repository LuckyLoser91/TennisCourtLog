import pandas as pd
import json
from pathlib import Path

# 设置数据目录
DATA_DIR = Path("api_folder/data/roland_garros_2026")

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 读取JSON数据
def load_player_stats(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    return stats

# 转换draw文件（简化版，player1为高排名球员，player2为低排名球员）
def convert_to_simple_format(draw_csv_path, stats_json_path, output_csv_path):
    df = pd.read_csv(draw_csv_path)
    stats = load_player_stats(stats_json_path)
    
    matches = []
    grouped = df.groupby(['round', 'block_order'])
    
    for (round_name, block_order), group in grouped:
        if len(group) >= 2:
            player_row1 = group.iloc[0]
            player_row2 = group.iloc[1]
            
            player1_name = player_row1['name']
            player2_name = player_row2['name']
            
            # 跳过Bye
            if player1_name == 'Bye' or player2_name == 'Bye':
                continue
            
            # 获取排名
            try:
                rank1 = float(player_row1['ranking']) if pd.notna(player_row1['ranking']) else float('inf')
            except (ValueError, TypeError):
                rank1 = float('inf')
            
            try:
                rank2 = float(player_row2['ranking']) if pd.notna(player_row2['ranking']) else float('inf')
            except (ValueError, TypeError):
                rank2 = float('inf')
            
            # 决定哪个是排名更高的球员（ranking数值更小）
            if rank1 <= rank2:
                high_rank_row = player_row1
                low_rank_row = player_row2
            else:
                high_rank_row = player_row2
                low_rank_row = player_row1
            
            # 获取统计信息
            high_rank_stats = stats.get(high_rank_row['name'], {})
            low_rank_stats = stats.get(low_rank_row['name'], {})
            
            match_record = {
                'round': round_name,
                'block': block_order,
                'player1': high_rank_row['name'],  # 高排名球员
                'player1_ranking': high_rank_row['ranking'],
                'player1_seed': high_rank_row['teamSeed'] if pd.notna(high_rank_row['teamSeed']) else '',
                'player1_winner': high_rank_row['winner'],
                'player1_W': high_rank_stats.get('W', 0),
                'player1_L': high_rank_stats.get('L', 0),
                'player1_winrate': high_rank_stats.get('winrate', 0.0),
                'player1_best_round': high_rank_stats.get('best_round', ''),
                'player2': low_rank_row['name'],   # 低排名球员
                'player2_ranking': low_rank_row['ranking'],
                'player2_seed': low_rank_row['teamSeed'] if pd.notna(low_rank_row['teamSeed']) else '',
                'player2_winner': low_rank_row['winner'],
                'player2_W': low_rank_stats.get('W', 0),
                'player2_L': low_rank_stats.get('L', 0),
                'player2_winrate': low_rank_stats.get('winrate', 0.0),
                'player2_best_round': low_rank_stats.get('best_round', ''),
            }
            matches.append(match_record)
    
    result_df = pd.DataFrame(matches)
    result_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    
    print(f"转换完成！共处理 {len(matches)} 场比赛")
    print(f"输出文件: {output_csv_path}")
    
    return result_df

if __name__ == "__main__":
    # 文件路径（所有文件都在 ./data/roland_garros_2026 目录下）
    draw_file = DATA_DIR / "draw.csv"
    stats_file = DATA_DIR / "tournament_stats_cache.json"
    output_simple_file = DATA_DIR / "matches_simple.csv"
    
    # 检查文件是否存在
    if not draw_file.exists():
        print(f"错误: 找不到文件 {draw_file}")
        print(f"请确保文件在目录: {DATA_DIR.absolute()}")
        exit(1)
    
    if not stats_file.exists():
        print(f"错误: 找不到文件 {stats_file}")
        print(f"请确保文件在目录: {DATA_DIR.absolute()}")
        exit(1)
    
    # 显示当前工作目录和文件路径
    print(f"当前工作目录: {Path.cwd()}")
    print(f"数据目录: {DATA_DIR.absolute()}")
    print(f"输入文件:")
    print(f"  - {draw_file}")
    print(f"  - {stats_file}")
    print(f"输出文件:")
    print(f"  - {output_simple_file}")
    print("-" * 50)
    
    # 执行转换
    print("正在转换（player1 = 高排名球员, player2 = 低排名球员）...")
    df_simple = convert_to_simple_format(draw_file, stats_file, output_simple_file)
    
    # 显示统计信息
    print(f"\n各轮次比赛数量:")
    print(df_simple['round'].value_counts())
    
    # 验证排名顺序
    print("\n排名顺序验证（高排名在前）:")
    sample_matches = df_simple.head(5)
    for idx, row in sample_matches.iterrows():
        print(f"{row['round']} - {row['player1']} (排名:{row['player1_ranking']}, 种子:{row['player1_seed']}) vs {row['player2']} (排名:{row['player2_ranking']}, 种子:{row['player2_seed']})")