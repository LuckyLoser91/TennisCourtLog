import pandas as pd
import os


def transfer_atp(ta_data_dir='../data/tennis_abstract/tennis_atp/', years=range(1968, 2025), out_data_dir='./tennis_atp/'):
    for year in years:
        df = pd.read_csv(os.path.join(ta_data_dir,f'atp_matches_{year}.csv'), encoding='gbk')
        # transfer the data to the new dataframe

        # 1. tourney cols: tourney_name, tourney_level, tourney_date, surface
        tourney_cols = ['tourney_name', 'tourney_level', 'tourney_date', 'surface']
        # map the tourney_level, G -> Grand Slam; M -> Masters 1000;
        df['tourney_level'] = df['tourney_level'].replace({'G': 'Grand Slam', 'M': 'Masters 1000'})
        # set the tourney_date datatype
        df['tourney_date'] = pd.to_datetime(df['tourney_date'], format='%Y%m%d')

        # 2. match info cols: round, best_of, winner_name, loser_name, score, winner_rank, loser_rank, winner_rank_points, loser_rank_points
        match_info_cols = ['round', 'best_of', 'winner_name', 'loser_name', 'score', 'winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']
        # get the new df just keeping the above cols
        new_df = df[tourney_cols + match_info_cols].copy()
        # set the rank and points into int type and keep the NA
        new_df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']] = new_df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']].astype('Int64')
        for col in ['winner_name', 'loser_name']:
            new_df[col] = new_df[col].str.strip().str.title()

        #########################################
        # save the new df to the new dir
        # check if the dir exists
        #############################################
        if not os.path.exists(out_data_dir):
            os.makedirs(out_data_dir)
        new_df.to_csv(os.path.join(out_data_dir, f'atp_matches_{year}.csv'), index=False)

def transfer_wta(ta_data_dir='../data/tennis_abstract/tennis_wta/', years=range(1968, 2025), out_data_dir='./tennis_wta/'):
    for year in years:
        df = pd.read_csv(os.path.join(ta_data_dir,f'wta_matches_{year}.csv'), encoding='gbk')
        # transfer the data to the new dataframe
        # 1. tourney cols: tourney_name, tourney_level, tourney_date, surface
        tourney_cols = ['tourney_name', 'tourney_level', 'tourney_date', 'surface']
        # replace the tourney_level, G -> Grand Slam;
        df['tourney_level'] = df['tourney_level'].replace({'G': 'Grand Slam'})
        # set the tourney_date datatype
        df['tourney_date'] = pd.to_datetime(df['tourney_date'], format='%Y%m%d')
        # 2. match info cols: round, best_of, winner_name, loser_name, score, winner_rank, loser_rank, winner_rank_points, loser_rank_points
        match_info_cols = ['round', 'best_of', 'winner_name', 'loser_name', 'score', 'winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']
        # get the new df just keeping the above cols
        new_df = df[tourney_cols + match_info_cols].copy()
        # set the rank and points into int type and keep the NA
        new_df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']] = new_df[['winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']].astype('Int64')
        for col in ['winner_name', 'loser_name']:
            new_df[col] = new_df[col].str.strip().str.title()

        #########################################
        # save the new df to the new dir
        # check if the dir exists
        #############################################
        if not os.path.exists(out_data_dir):
            os.makedirs(out_data_dir)
        new_df.to_csv(os.path.join(out_data_dir, f'wta_matches_{year}.csv'), index=False)




if __name__ == '__main__':
    transfer_atp()
    transfer_wta()

    