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

def extract_all_matches(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rounds = data.get('rounds', [])
    rows = []  # CSV 行数据

    # 统计用字典
    round_stats = {}          # 胜率统计
    round_three_stats = {}    # 三盘概率
    round_over_stats = {}     # 总局数 > 21.5 概率

    for round_info in rounds:
        round_desc = round_info.get('description', '')
        blocks = round_info.get('blocks', [])

        # 初始化统计字典
        if round_desc not in round_stats:
            round_stats[round_desc] = {'total': 0, 'higher_wins': 0}
        if round_desc not in round_three_stats:
            round_three_stats[round_desc] = {'total': 0, 'three': 0}
        if round_desc not in round_over_stats:
            round_over_stats[round_desc] = {'total': 0, 'over': 0}

        for block in blocks:
            participants = block.get('participants', [])
            if len(participants) < 2:
                continue

            p1, p2 = participants[0], participants[1]
            if p1.get('name') == 'Bye' or p2.get('name') == 'Bye':
                continue

            name1 = p1.get('name', '')
            name2 = p2.get('name', '')
            wr1_raw = p1.get('winrate', '')
            wr2_raw = p2.get('winrate', '')
            best1 = p1.get('best_round', '')
            best2 = p2.get('best_round', '')

            # 转换胜率为浮点数
            try:
                wr1 = float(wr1_raw) if wr1_raw != '' and wr1_raw is not None else None
            except:
                wr1 = None
            try:
                wr2 = float(wr2_raw) if wr2_raw != '' and wr2_raw is not None else None
            except:
                wr2 = None

            diff_abs = None
            if wr1 is not None and wr2 is not None:
                diff_abs = abs(wr1 - wr2)

            finished = block.get('finished', False)
            status = '已完成' if finished else '未完成'

            # ---------- 判断爆冷标签 ----------
            label = ''
            winner = None
            loser = None
            if not finished:
                label = '未完成'
            else:
                # 确定胜者和负者
                if p1.get('winner') == True:
                    winner, loser = p1, p2
                elif p2.get('winner') == True:
                    winner, loser = p2, p1
                else:
                    label = '未知'   # 无胜者（异常）

                if label == '':
                    wr_winner_raw = winner.get('winrate', '')
                    wr_loser_raw = loser.get('winrate', '')
                    try:
                        wr_winner = float(wr_winner_raw) if wr_winner_raw != '' and wr_winner_raw is not None else None
                    except:
                        wr_winner = None
                    try:
                        wr_loser = float(wr_loser_raw) if wr_loser_raw != '' and wr_loser_raw is not None else None
                    except:
                        wr_loser = None

                    if wr_winner is None or wr_loser is None:
                        label = '未知'
                    elif wr_winner < wr_loser:
                        label = '爆冷'
                    else:
                        label = '正常'   # 包括胜者胜率 ≥ 负者胜率

            # ---------- 解析比分 ----------
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

            # ---------- 统计逻辑（仅针对已完成且胜负有效的比赛） ----------
            if finished and winner is not None and loser is not None:
                # 胜率统计
                wr_w = None
                wr_l = None
                try:
                    wr_w = float(winner.get('winrate', '')) if winner.get('winrate', '') != '' and winner.get('winrate', '') is not None else None
                except:
                    pass
                try:
                    wr_l = float(loser.get('winrate', '')) if loser.get('winrate', '') != '' and loser.get('winrate', '') is not None else None
                except:
                    pass

                higher_wins = False
                if wr_w is not None and wr_l is not None:
                    round_stats[round_desc]['total'] += 1
                    if wr_w > wr_l:
                        higher_wins = True
                    elif wr_w < wr_l:
                        higher_wins = False
                    else:
                        # 胜率相等，比较 best_round
                        best_w = winner.get('best_round', '')
                        best_l = loser.get('best_round', '')
                        rank_w = get_rank(best_w)
                        rank_l = get_rank(best_l)
                        higher_wins = rank_w < rank_l
                    if higher_wins:
                        round_stats[round_desc]['higher_wins'] += 1

                # 三盘和总分统计（只统计有至少两盘比分的比赛）
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

            # 添加到 CSV 行
            rows.append([
                round_desc,
                name1, wr1_raw, best1,
                name2, wr2_raw, best2,
                f"{diff_abs:.2f}" if diff_abs is not None else '',
                status,
                score_str,
                label
            ])

    # 写入 CSV
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            '轮次',
            '选手1', '胜率1', '最好成绩1',
            '选手2', '胜率2', '最好成绩2',
            '胜率差绝对值',
            '状态', '比分',
            '爆冷标签'
        ])
        writer.writerows(rows)

    print(f"提取完成，共 {len(rows)} 场比赛（含未完成），保存至 {output_file}")

    # ========== 打印统计信息（来自 extract_matches_from_draw.py） ==========
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
    parser = argparse.ArgumentParser(description='提取网球签表所有比赛（含未完成）并打印统计信息')
    parser.add_argument('--input', required=True,
                        help='基础名称，例如 canada_2026（会拼接成 output/draw/draw_canada_2026_with_history_stats.json）')
    parser.add_argument('--output', help='输出 CSV 路径，默认 temp/draw/{input}_all_matches.csv')
    args = parser.parse_args()

    if '/' in args.input or '\\' in args.input:
        input_file = args.input
        base = os.path.splitext(os.path.basename(input_file))[0]
    else:
        base = args.input
        input_file = f'output/draw/draw_{base}_with_history_stats.json'

    if args.output is None:
        output_file = f'temp/draw/{base}_all_matches.csv'
    else:
        output_file = args.output

    if not os.path.isfile(input_file):
        print(f"错误：文件不存在 - {input_file}")
        exit(1)

    extract_all_matches(input_file, output_file)