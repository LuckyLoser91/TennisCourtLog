import pandas as pd
from collections import defaultdict
import os
import re

# ====================== 配置路径 ======================
# label for wta or atp
LABEL = 'atp'
year = 2026
DATA_DIR = f'./tennis_{LABEL}'
ACTIVE_RANK_PATH = os.path.join(DATA_DIR, f'{LABEL}_players_active_rank.csv')
PLAYER_DB_PATH = os.path.join(DATA_DIR, f'{LABEL}_players.csv')
MATCHES_PATH = os.path.join(DATA_DIR, f'{LABEL}_matches_{year}.csv')
MANUAL_MAPPING_PATH = f'./tennis_{LABEL}/{LABEL}_manual_mapping.csv'

# ====================== 加载手动映射 ======================
MANUAL_MAP = {}
if os.path.exists(MANUAL_MAPPING_PATH):
    try:
        df_manual = pd.read_csv(MANUAL_MAPPING_PATH)
        if {'abbreviation', 'full_name'}.issubset(df_manual.columns):
            MANUAL_MAP = dict(zip(df_manual['abbreviation'].str.strip(),
                                  df_manual['full_name'].str.strip()))
            print(f"加载手动映射 {len(MANUAL_MAP)} 条。")
    except Exception as e:
        print(f"读取手动映射失败: {e}")

# ====================== 从全名生成缩写变体 ======================
def generate_abbr_variants(full_name: str):
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

# ====================== 解析比赛缩写 ======================
def parse_match_abbr(abbr_str: str):
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

# ====================== 读取活跃排名表并构建精确映射 ======================
print("正在加载活跃排名表...")
df_active = pd.read_csv(ACTIVE_RANK_PATH)
active_names = df_active['name'].dropna().astype(str).str.strip().tolist()

abbr_map_active = defaultdict(list)
for full in active_names:
    for last_name, initials in generate_abbr_variants(full):
        key = (last_name.lower(), initials)
        abbr_map_active[key].append(full)
for key in abbr_map_active:
    abbr_map_active[key] = list(set(abbr_map_active[key]))

print(f"活跃排名表精确映射键数量: {len(abbr_map_active)}")

# ====================== 第一轮匹配（手动 + 活跃精确） ======================
def lookup_with_active_exact(abbr_str):
    s = abbr_str.strip() if isinstance(abbr_str, str) else ''
    if not s:
        return []
    # 手动优先
    if s in MANUAL_MAP:
        return [MANUAL_MAP[s]]
    if s.endswith('.') and s[:-1] in MANUAL_MAP:
        return [MANUAL_MAP[s[:-1]]]
    # 活跃精确
    last, initials = parse_match_abbr(s)
    if last is None:
        return []
    key = (last.lower(), initials)
    return abbr_map_active.get(key, [])

print("正在处理比赛数据（第一轮：手动+活跃精确）...")
df_matches = pd.read_csv(MATCHES_PATH)

def first_pass_resolve(abbr_str):
    candidates = lookup_with_active_exact(abbr_str)
    if len(candidates) == 1:
        return candidates[0], 'unique'
    elif len(candidates) == 0:
        return abbr_str, 'not_found'
    else:
        return abbr_str, 'multiple'

df_matches['winner_full'] = df_matches['winner_name'].apply(lambda x: first_pass_resolve(x)[0])
df_matches['winner_status'] = df_matches['winner_name'].apply(lambda x: first_pass_resolve(x)[1])
df_matches['loser_full'] = df_matches['loser_name'].apply(lambda x: first_pass_resolve(x)[0])
df_matches['loser_status'] = df_matches['loser_name'].apply(lambda x: first_pass_resolve(x)[1])

# ====================== 新增：活跃表姓氏包含匹配（针对 not_found） ======================
# 提取所有状态为 not_found 的缩写
not_found_mask_winner = df_matches['winner_status'] == 'not_found'
not_found_mask_loser = df_matches['loser_status'] == 'not_found'
not_found_abbrs = set(df_matches.loc[not_found_mask_winner, 'winner_name']) | \
                  set(df_matches.loc[not_found_mask_loser, 'loser_name'])

if not_found_abbrs:
    print(f"第一轮后未找到的缩写数: {len(not_found_abbrs)}，尝试活跃表姓氏包含匹配...")
    # 构建活跃表姓氏到全名的映射（仅用于包含匹配）
    lastname_to_fullnames = defaultdict(list)
    for full in active_names:
        # 姓氏取最后一个单词（简单起见，复杂姓氏也取最后一个，包含匹配时已足够）
        parts = full.split()
        if parts:
            last_simple = parts[-1].lower()
            lastname_to_fullnames[last_simple].append(full)
    
    # 对每个 not_found 缩写尝试姓氏包含匹配
    abbr_to_full_loose = {}
    for abbr in not_found_abbrs:
        # 提取姓氏部分（缩写中最后一个空格之前的部分）
        if ' ' not in abbr:
            continue
        last_part = abbr[:abbr.rfind(' ')].strip()
        last_lower = last_part.lower()
        # 在活跃表中查找全名，要求全名包含该姓氏（作为独立单词，避免部分匹配）
        # 使用正则：姓氏前后应为单词边界或字符串边界
        pattern = r'(?:^|\s)' + re.escape(last_part) + r'(?:$|\s)'
        matches = []
        for full in active_names:
            if re.search(pattern, full, re.IGNORECASE):
                matches.append(full)
        if len(matches) == 1:
            abbr_to_full_loose[abbr] = matches[0]
    
    print(f"姓氏包含匹配成功数: {len(abbr_to_full_loose)}")
    
    # 更新匹配结果
    def apply_loose_match(row):
        if row['winner_status'] == 'not_found' and row['winner_name'] in abbr_to_full_loose:
            row['winner_full'] = abbr_to_full_loose[row['winner_name']]
            row['winner_status'] = 'unique'
        if row['loser_status'] == 'not_found' and row['loser_name'] in abbr_to_full_loose:
            row['loser_full'] = abbr_to_full_loose[row['loser_name']]
            row['loser_status'] = 'unique'
        return row
    
    df_matches = df_matches.apply(apply_loose_match, axis=1)
else:
    print("没有未找到的缩写，跳过姓氏包含匹配。")

# ====================== 第二轮：针对剩余 not_found，在历史表中精确查找 ======================
# 重新收集 still not_found 的缩写
still_not_found_abbrs = set(df_matches.loc[df_matches['winner_status'] == 'not_found', 'winner_name']) | \
                        set(df_matches.loc[df_matches['loser_status'] == 'not_found', 'loser_name'])

if still_not_found_abbrs:
    print(f"姓氏包含匹配后仍有未找到缩写数: {len(still_not_found_abbrs)}，加载历史表...")
    df_players = pd.read_csv(PLAYER_DB_PATH, low_memory=False)
    if 'name' not in df_players.columns:
        df_players['name'] = df_players['name_first'].fillna('') + ' ' + df_players['name_last'].fillna('')
        df_players['name'] = df_players['name'].str.strip()
    
    print("为历史球员表建立索引...")
    player_index = defaultdict(list)
    for full in df_players['name'].dropna().astype(str).str.strip():
        if not full:
            continue
        for last_name, initials in generate_abbr_variants(full):
            key = (last_name.lower(), initials)
            player_index[key].append(full)
    for key in player_index:
        player_index[key] = list(set(player_index[key]))
    
    abbr_to_full_history = {}
    for abbr in still_not_found_abbrs:
        last, initials = parse_match_abbr(abbr)
        if last is None:
            continue
        key = (last.lower(), initials)
        candidates = player_index.get(key, [])
        if len(candidates) == 1:
            abbr_to_full_history[abbr] = candidates[0]
    
    print(f"从历史表中找到唯一匹配的缩写数: {len(abbr_to_full_history)}")
    
    def apply_history_match(row):
        if row['winner_status'] == 'not_found' and row['winner_name'] in abbr_to_full_history:
            row['winner_full'] = abbr_to_full_history[row['winner_name']]
            row['winner_status'] = 'unique'
        if row['loser_status'] == 'not_found' and row['loser_name'] in abbr_to_full_history:
            row['loser_full'] = abbr_to_full_history[row['loser_name']]
            row['loser_status'] = 'unique'
        return row
    
    df_matches = df_matches.apply(apply_history_match, axis=1)
else:
    print("所有未找到的缩写均已通过姓氏包含匹配解决，跳过历史表。")

# ====================== 输出结果 ======================
needs_review = df_matches[
    (df_matches['winner_status'] != 'unique') |
    (df_matches['loser_status'] != 'unique')
].copy()

def get_candidates_str(abbr_str):
    s = abbr_str.strip() if isinstance(abbr_str, str) else ''
    if not s:
        return ''
    if s in MANUAL_MAP:
        return MANUAL_MAP[s]
    if s.endswith('.') and s[:-1] in MANUAL_MAP:
        return MANUAL_MAP[s[:-1]]
    last, initials = parse_match_abbr(s)
    if last is None:
        return ''
    key = (last.lower(), initials)
    cand = abbr_map_active.get(key, [])
    if cand:
        return ' | '.join(cand)
    return ''

needs_review['winner_candidates'] = needs_review['winner_name'].apply(get_candidates_str)
needs_review['loser_candidates'] = needs_review['loser_name'].apply(get_candidates_str)

review_cols = ['winner_name', 'winner_rank', 'winner_candidates', 'winner_status',
               'loser_name', 'loser_rank','loser_candidates', 'loser_status']
needs_review[review_cols].to_csv(f'{LABEL}_matches_{year}_review.csv', index=False)

# 最终文件：用全名替换缩写列
df_matches['winner_name'] = df_matches['winner_full']
df_matches['loser_name'] = df_matches['loser_full']
output_cols = [col for col in df_matches.columns 
               if col not in ['winner_full', 'loser_full', 'winner_status', 'loser_status']]
df_matches[output_cols].to_csv(f'{LABEL}_matches_{year}_clean_auto.csv', index=False)

print("\n=== 处理完成 ===")
print(f"总记录数: {len(df_matches)}")
print(f"需人工审核记录数: {len(needs_review)}")
print(f"自动匹配结果已保存至: {LABEL}_matches_{year}_clean_auto.csv")
print(f"待审核列表已保存至: {LABEL}_matches_{year}_review.csv")