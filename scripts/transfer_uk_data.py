import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
import re
from pathlib import Path
from collections import defaultdict
from typing import Tuple, List, Optional, Dict, Set
from scripts.config import DATA_PATHS


class PlayerNameMapper:
    """
    网球运动员名称缩写到全名的映射器。
    
    支持多阶段匹配：
    1. 手动映射表
    2. 活跃排名表精确匹配（姓氏 + 首字母缩写）
    3. 活跃排名表姓氏包含匹配（宽松匹配）
    4. 历史球员表精确匹配（可选）
    """
    
    def __init__(self, label: str = 'atp', year: int = 2026):
        """
        初始化映射器，加载所需数据文件。
        
        Args:
            label: 'atp' 或 'wta'
            year: 年份，用于定位比赛数据（仅影响路径中的文件名）
        """
        self.label = label
        self.year = year
        self.data_dir = DATA_PATHS[label]['matches_dir']
        
        # 加载手动映射表
        self.manual_map: Dict[str, str] = self._load_manual_mapping()
        
        # 加载活跃排名表并构建精确映射索引
        self.active_names: List[str] = []
        self.abbr_map_active: Dict[Tuple[str, Tuple[str, ...]], List[str]] = defaultdict(list)
        self.lastname_to_fullnames: Dict[str, List[str]] = defaultdict(list)
        self._load_active_rank()
        
        # 历史球员表延迟加载（仅在需要时加载）
        self.history_loaded = False
        self.history_index: Dict[Tuple[str, Tuple[str, ...]], List[str]] = defaultdict(list)
        self.history_names: List[str] = []
    
    # -------------------- 内部数据加载 --------------------
    def _load_manual_mapping(self) -> Dict[str, str]:
        """加载手动映射文件 (abbreviation -> full_name)"""
        manual_path = os.path.join(self.data_dir, f'{self.label}_manual_mapping.csv')
        manual_map = {}
        if os.path.exists(manual_path):
            try:
                df_manual = pd.read_csv(manual_path)
                if {'abbreviation', 'full_name'}.issubset(df_manual.columns):
                    manual_map = dict(zip(
                        df_manual['abbreviation'].str.strip(),
                        df_manual['full_name'].str.strip()
                    ))
                    print(f"加载手动映射 {len(manual_map)} 条。")
            except Exception as e:
                print(f"读取手动映射失败: {e}")
        return manual_map
    
    def _load_active_rank(self):
        """加载活跃排名表，构建精确匹配索引和姓氏包含索引"""
        active_path = os.path.join(self.data_dir, f'{self.label}_players_active_rank.csv')
        print("正在加载活跃排名表...")
        df_active = pd.read_csv(active_path)
        self.active_names = df_active['name'].dropna().astype(str).str.strip().tolist()
        
        # 构建精确匹配索引
        for full in self.active_names:
            for last_name, initials in self._generate_abbr_variants(full):
                key = (last_name.lower(), initials)
                self.abbr_map_active[key].append(full)
        
        # 去重
        for key in self.abbr_map_active:
            self.abbr_map_active[key] = list(set(self.abbr_map_active[key]))
        
        # 构建姓氏包含匹配索引（用于第二阶段宽松匹配）
        for full in self.active_names:
            parts = full.split()
            if parts:
                last_simple = parts[-1].lower()
                self.lastname_to_fullnames[last_simple].append(full)
        
        print(f"活跃排名表精确映射键数量: {len(self.abbr_map_active)}")
    
    def _load_history_if_needed(self):
        """按需加载历史球员表并构建索引"""
        if self.history_loaded:
            return
        history_path = os.path.join(self.data_dir, f'{self.label}_players.csv')
        print("正在加载历史球员表...")
        df_players = pd.read_csv(history_path, low_memory=False)
        
        # 确保有 'name' 列
        if 'name' not in df_players.columns:
            df_players['name'] = df_players['name_first'].fillna('') + ' ' + df_players['name_last'].fillna('')
            df_players['name'] = df_players['name'].str.strip()
        
        self.history_names = df_players['name'].dropna().astype(str).str.strip().tolist()
        
        print("为历史球员表建立索引...")
        for full in self.history_names:
            if not full:
                continue
            for last_name, initials in self._generate_abbr_variants(full):
                key = (last_name.lower(), initials)
                self.history_index[key].append(full)
        
        for key in self.history_index:
            self.history_index[key] = list(set(self.history_index[key]))
        
        self.history_loaded = True
        print(f"历史表索引键数量: {len(self.history_index)}")
    
    # -------------------- 辅助解析函数 --------------------
    @staticmethod
    def _generate_abbr_variants(full_name: str) -> List[Tuple[str, Tuple[str, ...]]]:
        """
        根据全名生成可能的缩写变体。
        
        例如: "Novak Djokovic" -> ("Djokovic", ("N",))
              "Rafael Nadal Parera" -> ("Parera", ("R", "N")) 和 ("Nadal Parera", ("R",))
        
        Returns:
            List of (last_name_part, tuple_of_initials)
        """
        parts = full_name.split()
        n = len(parts)
        variants = []
        for last_len in range(1, min(4, n)):
            last_name = ' '.join(parts[-last_len:])
            first_parts = parts[:-last_len]
            if not first_parts:
                continue
            initials = tuple(w[0].upper() for w in first_parts)
            variants.append((last_name, initials))
        return variants
    
    @staticmethod
    def _parse_match_abbr(abbr_str: str) -> Tuple[Optional[str], Optional[Tuple[str, ...]]]:
        """
        解析比赛数据中的缩写格式。
        
        格式: "Djokovic N." 或 "Nadal Parera R."
        返回: (姓氏部分, 首字母元组)
        """
        if pd.isna(abbr_str) or not isinstance(abbr_str, str):
            return None, None
        s = abbr_str.strip()
        if ' ' not in s:
            return None, None
        last_space_idx = s.rfind(' ')
        last_part = s[:last_space_idx].strip()
        initials_str = s[last_space_idx+1:].strip()
        initials = tuple(c for c in initials_str if c.isupper())
        return last_part, initials
    
    # -------------------- 核心映射方法 --------------------
    def map_name(self, abbr: str, use_history: bool = True) -> Tuple[str, str]:
        """
        将缩写映射为完整姓名。
        
        Args:
            abbr: 缩写字符串
            use_history: 是否在活跃表匹配失败后使用历史表
            
        Returns:
            (full_name, status)
            status: 'unique' - 唯一匹配成功
                    'multiple' - 有多个候选（返回原缩写）
                    'not_found' - 未找到任何候选（返回原缩写）
        """
        if pd.isna(abbr) or not isinstance(abbr, str):
            return abbr if not pd.isna(abbr) else '', 'not_found'
        
        abbr_clean = abbr.strip()
        if not abbr_clean:
            return abbr_clean, 'not_found'
        
        # 1. 手动映射优先
        if abbr_clean in self.manual_map:
            return self.manual_map[abbr_clean], 'unique'
        if abbr_clean.endswith('.') and abbr_clean[:-1] in self.manual_map:
            return self.manual_map[abbr_clean[:-1]], 'unique'
        
        # 2. 活跃表精确匹配
        last, initials = self._parse_match_abbr(abbr_clean)
        if last is not None:
            key = (last.lower(), initials)
            candidates = self.abbr_map_active.get(key, [])
            if len(candidates) == 1:
                return candidates[0], 'unique'
            elif len(candidates) > 1:
                return abbr_clean, 'multiple'
        
        # 3. 活跃表姓氏包含匹配（宽松匹配）
        # 仅当精确匹配未找到任何候选时尝试
        if last is not None:
            last_lower = last.lower()
            # 使用正则确保姓氏作为独立单词出现
            pattern = r'(?:^|\s)' + re.escape(last) + r'(?:$|\s)'
            matches = []
            for full in self.active_names:
                if re.search(pattern, full, re.IGNORECASE):
                    matches.append(full)
            if len(matches) == 1:
                return matches[0], 'unique'
        
        # 4. 历史表精确匹配（如果启用且仍未找到）
        if use_history and last is not None:
            self._load_history_if_needed()
            key = (last.lower(), initials)
            candidates = self.history_index.get(key, [])
            if len(candidates) == 1:
                return candidates[0], 'unique'
        
        # 所有方法均失败
        return abbr_clean, 'not_found'
    
    def get_candidates(self, abbr: str) -> List[str]:
        """
        获取给定缩写在活跃表中的所有候选全名（用于审核）。
        """
        if pd.isna(abbr) or not isinstance(abbr, str):
            return []
        abbr_clean = abbr.strip()
        if abbr_clean in self.manual_map:
            return [self.manual_map[abbr_clean]]
        if abbr_clean.endswith('.') and abbr_clean[:-1] in self.manual_map:
            return [self.manual_map[abbr_clean[:-1]]]
        
        last, initials = self._parse_match_abbr(abbr_clean)
        if last is None:
            return []
        key = (last.lower(), initials)
        return self.abbr_map_active.get(key, [])
    
    # -------------------- 批量处理方法 --------------------
    def map_dataframe(self, df: pd.DataFrame, 
                      winner_col: str = 'winner_name',
                      loser_col: str = 'loser_name',
                      use_history: bool = True) -> pd.DataFrame:
        """
        批量处理比赛DataFrame中的两列球员名。
        
        Args:
            df: 包含 winner_name 和 loser_name 列的DataFrame
            winner_col: 胜者列名
            loser_col: 负者列名
            use_history: 是否使用历史表兜底
            
        Returns:
            添加了 _full 和 _status 列的新DataFrame
        """
        # 为胜者映射
        winner_results = df[winner_col].apply(lambda x: self.map_name(x, use_history))
        df['winner_full'] = winner_results.apply(lambda x: x[0])
        df['winner_status'] = winner_results.apply(lambda x: x[1])
        
        # 为负者映射
        loser_results = df[loser_col].apply(lambda x: self.map_name(x, use_history))
        df['loser_full'] = loser_results.apply(lambda x: x[0])
        df['loser_status'] = loser_results.apply(lambda x: x[1])
        
        return df



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

def get_uk_data(uk_data_dir='../data/tennis_betting', tour='wta', year=2026):

    file_path = os.path.join(uk_data_dir, f'{tour}_matches_{year}.xlsx')
    df = pd.read_excel(file_path)
    if tour == 'atp':
        tourney_col = 'Series'
    elif tour == 'wta':
        tourney_col = 'Tier'

    ###########
    # 1. tourney cols
    ###########
    tourney_cols = ['tourney_name', 'tourney_level', 'tourney_date', 'surface']
    df['tourney_level'] = df[tourney_col]
    df['tourney_name'] = np.where(df[tourney_col] != 'Grand Slam', df['Location'], df['Tournament'])
    df['tourney_name'] = df['tourney_name'].replace({'French Open': 'Roland Garros', 'US Open': 'Us Open'})
    df['tourney_date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d')
    df['surface'] = df['Surface']

    ###########
    # 2. match cols
    ###########
    match_info_cols = ['round', 'best_of', 'winner_name', 'loser_name', 'score', 'winner_rank', 'loser_rank', 'winner_rank_points', 'loser_rank_points']

    round_counts_atp = df.groupby(tour.upper())['Round'].nunique()
    mapper = make_round_mapper(tour.upper())
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

    return new_df

def map_uk_data_name(uk_data_dir, tour, year, use_history=False):
    print('='*30)
    print(f"Loading {tour} {year} data...")
    matches = get_uk_data(uk_data_dir=uk_data_dir, tour=tour, year=year)
    # mapping the name abbr into full
    mapper = PlayerNameMapper(label=tour, year=year)
    matches = mapper.map_dataframe(matches, use_history=use_history)
    #########################################################################
    # 整理需要人工审核的数据表
    #########################################################################
    needs_review = matches[
        (matches['winner_status'] != 'unique') |
        (matches['loser_status'] != 'unique')
    ].copy()
    # 添加候选信息列
    needs_review['winner_candidates'] = needs_review['winner_name'].apply(
        lambda x: ' | '.join(mapper.get_candidates(x))
    )
    needs_review['loser_candidates'] = needs_review['loser_name'].apply(
        lambda x: ' | '.join(mapper.get_candidates(x))
    )
    # 输出审核文件
    review_cols = ['winner_name', 'winner_rank', 'winner_candidates', 'winner_status',
                   'loser_name', 'loser_rank', 'loser_candidates', 'loser_status']
    review_path = f'{tour}_matches_{year}_review.csv'
    needs_review[review_cols].to_csv(review_path, index=False)
    #########################################################################
    # 输出清洗后的比赛数据（用全名替换缩写）
    #########################################################################
    matches['winner_name'] = matches['winner_full']
    matches['loser_name'] = matches['loser_full']
    output_cols = [col for col in matches.columns 
                   if col not in ['winner_full', 'loser_full', 'winner_status', 'loser_status']]
    clean_path = f'{tour}_matches_{year}_clean_auto.csv'
    matches[output_cols].to_csv(clean_path, index=False)
    
    print("\n=== 处理完成 ===")
    print(f"总记录数: {len(matches)}")
    print(f"需人工审核记录数: {len(needs_review)}")
    print(f"自动匹配结果已保存至: {clean_path}")
    print(f"待审核列表已保存至: {review_path}")
    

    

if __name__ == '__main__':
    map_uk_data_name(uk_data_dir ='./scrape', tour='wta', year=2026, use_history=True)
    map_uk_data_name(uk_data_dir ='./scrape', tour='atp', year=2026, use_history=True)
    
    




        



    







    
