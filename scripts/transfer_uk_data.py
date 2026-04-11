import pandas as pd
import numpy as np
import os
import re
from pathlib import Path
from config import PROJECT_ROOT, DATA_PATHS

def make_round_mapper(id_column='WTA'):
    def mapper(row, round_counts):
        r = row['Round']
        total = round_counts[row[id_column]]
        if 'Quarter' in r:
            return 'QF'
        if 'Semi' in r:
            return 'SF'
        if 'Final' in r:
            return 'F'
        if 'Robin' in r:
            return 'RR'

        num = re.search(r'(\d+)', str(r)) # get the num
        if num:
            n = int(num.group(1))
            if total == 7:
                map_num_dir = {1: 'R128', 2: 'R64', 3: 'R32', 4:'R16'}
                return map_num_dir.get(n)
            elif total == 6:
                map_num_dir = {1: 'R64', 2: 'R32', 3: 'R16'}
                return map_num_dir.get(n)
            elif total == 5:
                map_num_dir = {1: 'R32', 2: 'R16'}
                return map_num_dir.get(n)
    return mapper


def build_score(row):
    comment = str(row.get('Comment', '')).strip().lower()
    if 'walkover' in comment:
        return 'W/O'
    
    best_of = row['Best of']
    max_set = int(best_of)

    sets = []
    for i in range(1, max_set + 1):
        w = row[f'W{i}']
        l = row[f'L{i}']
        if pd.isna(w) or pd.isna(l):
            break
        w_int = int(w)
        l_int = int(l)
        sets.append(f'{w_int}-{l_int}')
    score_str = ' '.join(sets)
    # 处理Retired情况
    if 'ret' in comment:
        score_str += ' RET' if score_str else 'RET'

    return score_str


def transfer_atp(uk_data_dir='../data/tennis_betting/tennis_atp', years=range(2025, 2027), out_data_dir='./tennis_atp'):
    for year in years:
        file_path = os.path.join(uk_data_dir, f'{year}.xlsx')
        df = pd.read_excel(file_path)

        ###########
        # 1. tourney cols
        ###########
        tourney_cols = ['tourney_name', 'tourney_level', 'tourney_date', 'surface']
        df['tourney_level'] = df['Series']
        df['tourney_name'] = np.where(df['Series'] != 'Grand Slam', df['Location'], df['Tournament'])
        df['tourney_name'] = df['tourney_name'].replace({'French Open': 'Roland Garros', 'US Open': 'Us Open'})
        
        df['tourney_date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d')
        df['surface'] = df['Surface']

        ###########
        # 2. match cols
        ###########
        match_info_cols = ['round', 'best_of', 'winner_name', 'loser_name', 'score', 'winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']

        round_counts_atp = df.groupby('ATP')['Round'].nunique()
        mapper = make_round_mapper('ATP')
        df['round'] = df.apply(lambda row: mapper(row, round_counts_atp), axis=1)
        
        df['best_of'] = df['Best of']
        df['winner_name'] = df['Winner']
        df['loser_name'] = df['Loser']
        # score map
        df['score'] = df.apply(build_score, axis=1)

        df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']] = df[['WRank', 'LRank', 'WPts', 'LPts']].astype('Int64')
        new_df = df[tourney_cols + match_info_cols].copy()
        # todo: name map from Lastname F. into Firstname Lastname
        for col in ['winner_name', 'loser_name']:
            new_df[col] = new_df[col].str.strip().str.title()

        #############
        # 3. save file
        #############
        if not os.path.exists(out_data_dir):
            os.makedirs(out_data_dir)
        new_df.to_csv(os.path.join(out_data_dir, f'atp_matches_{year}.csv'), index=False)


def transfer_wta(uk_data_dir='../data/tennis_betting/tennis_atp', years=range(2025, 2027), out_data_dir='./tennis_atp'):
    for year in years:
        file_path = os.path.join(uk_data_dir, f'{year}.xlsx')
        df = pd.read_excel(file_path)

        ###########
        # 1. tourney cols
        ###########
        tourney_cols = ['tourney_name', 'tourney_level', 'tourney_date', 'surface']
        df['tourney_level'] = df['Tier']
        df['tourney_name'] = np.where(df['Tier'] != 'Grand Slam', df['Location'], df['Tournament'])
        df['tourney_name'] = df['tourney_name'].replace({'French Open': 'Roland Garros', 'US Open': 'Us Open'})
        
        df['tourney_date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d')
        df['surface'] = df['Surface']

        ###########
        # 2. match cols
        ###########
        match_info_cols = ['round', 'best_of', 'winner_name', 'loser_name', 'score', 'winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']

        round_counts_wta = df.groupby('WTA')['Round'].nunique()
        mapper = make_round_mapper('WTA')
        df['round'] = df.apply(lambda row: mapper(row, round_counts_wta), axis=1)
        
        df['best_of'] = df['Best of']
        df['winner_name'] = df['Winner']
        df['loser_name'] = df['Loser']
        # score map
        df['score'] = df.apply(build_score, axis=1)

        df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']] = df[['WRank', 'LRank', 'WPts', 'LPts']].astype('Int64')
        new_df = df[tourney_cols + match_info_cols].copy()
        # todo: name map from Lastname F. into Firstname Lastname
        for col in ['winner_name', 'loser_name']:
            new_df[col] = new_df[col].str.strip().str.title()

        #############
        # 3. save file
        #############
        if not os.path.exists(out_data_dir):
            os.makedirs(out_data_dir)
        new_df.to_csv(os.path.join(out_data_dir, f'wta_matches_{year}.csv'), index=False)

if __name__ == '__main__':
    
    # 简单的从uk网站获取的数据进行数据提取
    transfer_atp(uk_data_dir='../data/tennis_betting/tennis_atp', years=range(2026, 2027), out_data_dir=DATA_PATHS['atp']['matches_dir'])
    transfer_wta(uk_data_dir='../data/tennis_betting/tennis_atp', years=range(2026, 2027), out_data_dir=DATA_PATHS['wta']['matches_dir'])

        



    







    
