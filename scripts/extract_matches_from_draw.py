import json
import csv
import os
import argparse

# 轮次优先级映射（越小越优）
ROUND_ORDER = ['W', 'F', 'SF', 'QF', 'R16', 'R32', 'R64', 'R128']

def get_rank(round_str):
    """返回轮次优先级索引，空白或未知轮次返回999（最低优先级）"""
    if not round_str:
        return 999
    if round_str in ROUND_ORDER:
        return ROUND_ORDER.index(round_str)
    return 999

def extract_draw_data(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rounds = data.get('rounds', [])
    rows = []
    round_stats = {}
    round_three_stats = {}
    round_over_stats = {}
    
    for round_info in rounds:
        round_desc = round_info.get('description', '')
        blocks = round_info.get('blocks', [])
        
        if round_desc not in round_stats:
            round_stats[round_desc] = {'total': 0, 'higher_wins': 0}
        if round_desc not in round_three_stats:
            round_three_stats[round_desc] = {'total': 0, 'three': 0}
        if round_desc not in round_over_stats:
            round_over_stats[round_desc] = {'total': 0, 'over': 0}
        
        for block in blocks:
            if not block.get('finished', False):
                continue
            
            participants = block.get('participants', [])
            if len(participants) < 2:
                continue
            
            p1, p2 = participants[0], participants[1]
            if p1.get('name') == 'Bye' or p2.get('name') == 'Bye':
                continue
            
            if p1.get('winner') == True:
                winner, loser = p1, p2
            elif p2.get('winner') == True:
                winner, loser = p2, p1
            else:
                continue
            
            def parse_winrate(p):
                wr = p.get('winrate', '')
                if wr == '' or wr is None:
                    return None
                try:
                    return float(wr)
                except:
                    return None
            
            wr_w = parse_winrate(winner)
            wr_l = parse_winrate(loser)
            
            higher_wins = False
            if wr_w is not None and wr_l is not None:
                round_stats[round_desc]['total'] += 1
                if wr_w > wr_l:
                    higher_wins = True
                elif wr_w < wr_l:
                    higher_wins = False
                else:
                    best_w = winner.get('best_round', '')
                    best_l = loser.get('best_round', '')
                    rank_w = get_rank(best_w)
                    rank_l = get_rank(best_l)
                    higher_wins = rank_w < rank_l
                if higher_wins:
                    round_stats[round_desc]['higher_wins'] += 1
            
            name_w = winner.get('name', '')
            name_l = loser.get('name', '')
            best_w = winner.get('best_round', '')
            best_l = loser.get('best_round', '')
            
            score = block.get('score', {})
            home = score.get('homeScore', {})
            away = score.get('awayScore', {})
            
            periods = set()
            for k in home.keys():
                if k.startswith('period') and not k.endswith('TieBreak'):
                    periods.add(k)
            for k in away.keys():
                if k.startswith('period') and not k.endswith('TieBreak'):
                    periods.add(k)
            
            sorted_periods = sorted(periods, key=lambda x: int(x.replace('period', '')))
            score_parts = []
            for p in sorted_periods:
                h = home.get(p)
                a = away.get(p)
                if h is not None and a is not None:
                    score_parts.append(f"{h}-{a}")
            score_str = ' '.join(score_parts) if score_parts else ''
            
            if len(score_parts) >= 2:
                num_sets = len(score_parts)
                total_games = 0
                for sp in score_parts:
                    parts = sp.split('-')
                    if len(parts) == 2:
                        total_games += int(parts[0]) + int(parts[1])
                
                round_three_stats[round_desc]['total'] += 1
                if num_sets == 3:
                    round_three_stats[round_desc]['three'] += 1
                
                round_over_stats[round_desc]['total'] += 1
                if total_games > 21.5:
                    round_over_stats[round_desc]['over'] += 1
            
            rows.append([
                round_desc,
                name_w,
                name_l,
                wr_w if wr_w is not None else '',
                wr_l if wr_l is not None else '',
                best_w,
                best_l,
                higher_wins,
                score_str
            ])
    
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    # 🔽 关键改动：编码改为 'utf-8-sig' 以便 Excel 正确显示中文
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            '轮次', '胜者', '负者', '胜者胜率', '负者胜率',
            '胜者最好成绩', '负者最好成绩', '胜者胜率>负者胜率', '比分'
        ])
        writer.writerows(rows)
    
    print(f"提取完成，共 {len(rows)} 场比赛，保存至 {output_file}")
    
    print("\n=== 每轮胜率统计（仅计入双方胜率均有效场次） ===")
    total_matches = 0
    total_higher_wins = 0
    for round_desc, stats in round_stats.items():
        total = stats['total']
        higher = stats['higher_wins']
        if total > 0:
            ratio = higher / total
            print(f"{round_desc}: {higher}/{total} = {ratio:.2%}")
            total_matches += total
            total_higher_wins += higher
        else:
            print(f"{round_desc}: 无有效数据")
    
    if total_matches > 0:
        overall_ratio = total_higher_wins / total_matches
        print(f"\n总体胜率统计: {total_higher_wins}/{total_matches} = {overall_ratio:.2%}")
    else:
        print("\n总体胜率统计: 无有效数据")
    
    print("\n=== 每轮三盘概率与总局数>21.5概率（所有完赛比赛） ===")
    total_three = 0
    total_over = 0
    total_all = 0
    for round_desc, stats in round_three_stats.items():
        total = stats['total']
        if total > 0:
            three = stats['three']
            over = round_over_stats[round_desc]['over']
            p_three = three / total
            p_over = over / total
            print(f"{round_desc}: 三盘 {three}/{total} = {p_three:.2%}, 总分>21.5 {over}/{total} = {p_over:.2%}")
            total_all += total
            total_three += three
            total_over += over
        else:
            print(f"{round_desc}: 无有效比赛")
    
    if total_all > 0:
        print(f"\n总体: 三盘 {total_three}/{total_all} = {total_three/total_all:.2%}, 总分>21.5 {total_over}/{total_all} = {total_over/total_all:.2%}")
    else:
        print("\n总体: 无有效比赛")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='从网球签表 JSON 提取已完成比赛数据')
    parser.add_argument('--input', required=True,
                        help='基础名称，例如 canada_2026（会拼接成 output/draw/draw_canada_2026_with_history_stats.json）')
    parser.add_argument('--output', help='输出 CSV 路径，默认 temp/draw/{input}_matches.csv')
    args = parser.parse_args()

    if '/' in args.input or '\\' in args.input:
        input_file = args.input
        base = os.path.splitext(os.path.basename(input_file))[0]
    else:
        base = args.input
        input_file = f'output/draw/draw_{base}_with_history_stats.json'

    if args.output is None:
        output_file = f'temp/draw/{base}_matches.csv'
    else:
        output_file = args.output

    if not os.path.isfile(input_file):
        print(f"错误：文件不存在 - {input_file}")
        exit(1)

    extract_draw_data(input_file, output_file)