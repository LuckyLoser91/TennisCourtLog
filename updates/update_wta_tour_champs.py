"""
WTA 赛事日历 JSON 更新脚本

功能：更新指定年份的 WTA 赛事日历数据到 JSON 文件中

输入文件：
- ./output/wta_calendar_champs_start_2009.json : 历史日历 JSON 文件
  格式：包含 year, tourney_start_date, tourney_end_date, tourney_name,
        tourney_id, tourney_level, surface, drawsize, winner, ioc, dob, seed 等字段

输出文件：
- 同一 JSON 文件（原地更新）
  - 删除目标年份的旧数据
  - 追加该年份的最新赛事日历数据（从 WTA API 获取）
  - 按 tourney_start_date 降序排列
  - 自动计算并添加 winner_age 字段

运行方式：
    scraper = WTAScraper(year=2026, output_dir='./output', only_fetch_gs=False)
    scraper.update_calendar(filepath='./output/wta_calendar_champs_start_2009.json')

注意：
- API 地址：https://api.wtatennis.com
"""

from datetime import datetime

import requests
import pandas as pd
import numpy as np
import time
from pathlib import Path
from typing import Optional
from unidecode import unidecode
import json, csv


ROUND_LABELS = {
    4: ['R128', 'R64', 'R32', 'R16'],
    3: ['R64', 'R32', 'R16'],
    2: ['R32', 'R16'],
}


class WTAScraper:
    def __init__(self, year: int = 2026, output_dir: str = './scrape', only_fetch_gs=True):
        self.year = year
        self.only_fetch_gs = only_fetch_gs
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.calendar_path = self.output_dir / f'wta_{year}_calendar.csv'
        self.matches_path = self.output_dir / f'wta_{year}_matches.csv'

    # ── 网络请求 ─────────────────────────────────────────────

    def _get(self, url: str) -> Optional[dict]:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"   ❌ 请求失败 {url}: {e}")
            return None

    # ── 日历 ─────────────────────────────────────────────────

    def fetch_calendar(self) -> pd.DataFrame:
        """从 WTA API 获取年度赛事日历，直接覆盖保存。"""
            #  https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100&excludeLevels=%2C+250k%2C+WTA+125k+Series%2C+125K%2C+WTA+125%2C+ITF&from=2026-01-01&to=2026-12-31
        url = (
            f"https://api.wtatennis.com/tennis/tournaments/"
            f"?page=0&pageSize=100"
            f"&excludeLevels=%2C+250k%2C+WTA+125k+Series%2C+125K%2C+WTA+125%2C+ITF"
            f"&from={self.year}-01-01&to={self.year}-12-31"
        )
        data = self._get(url)
        if not data:
            raise RuntimeError("无法获取日历数据")

        rows = []
        for t in data['content']:
            winner = ''
            try:
                singles = (t.get('winners') or [{}])[0].get('singles') or {}
                winner = (singles.get('player') or {}).get('fullName', '')
            except Exception:
                pass
            # 只爬取 Grand Slam
            if self.only_fetch_gs:
                if t['tournamentGroup']['level'] != 'Grand Slam':
                    continue
            rows.append({
                'year': t['year'],
                'tourney_start_date': t['startDate'],
                'tourney_end_date': t['endDate'],
                'tourney_name': t['tournamentGroup']['name'].title(),
                'tourney_id': t['tournamentGroup']['id'],
                'tourney_level': t['tournamentGroup']['level'],
                'surface': t['surface'],
                'inOutdoor': t['inOutdoor'],
                'drawsize': t['singlesDrawSize'],
                'winner': winner,
                'ioc': (singles.get('player') or {}).get('countryCode', ''),
                'dob': (singles.get('player') or {}).get('dateOfBirth', ''),
                'seed': singles.get('seed', '')
            })
        
        return rows


    # ── 比赛数据 ──────────────────────────────────────────────

    def _parse_matches(self, data):
        """解析单站赛事 JSON，返回原始比赛记录列表。"""
        tourney_name = data['tournament']['tournamentGroup']['name'].title()
        tourney_level = data['tournament']['tournamentGroup']['level']
        surface = data['tournament']['surface']
        records = []
        for m in data['matches']:
            if m.get('DrawMatchType') != 'S' or m.get('DrawLevelType') != 'M':
                continue
            records.append({
                'tourney_name': tourney_name,
                'tourney_level': tourney_level,
                'tourney_date': m['MatchTimeStamp'].split('T')[0],
                'surface': surface,
                'round_id': m['RoundID'],
                'best_of': 3,
                'playerA': f"{m['PlayerNameFirstA']} {m['PlayerNameLastA']}",
                'playerB': f"{m['PlayerNameFirstB']} {m['PlayerNameLastB']}",
                'score_original': m.get('ScoreString'),
                'result_string': m.get('ResultString'),
                'winner': int(m['Winner']),
                'scoreset1A': m.get('ScoreSet1A'), 'scoreset1B': m.get('ScoreSet1B'),
                'scoreset2A': m.get('ScoreSet2A'), 'scoreset2B': m.get('ScoreSet2B'),
                'scoreset3A': m.get('ScoreSet3A'), 'scoreset3B': m.get('ScoreSet3B'),
                'seedA': m.get('SeedA'),
                'seedB': m.get('SeedB'),
            })
        return records

    def _build_round_map(self, df: pd.DataFrame) -> dict:
        """根据每个赛事出现的数字 round_id 数量，生成轮次名称映射。"""
        round_maps = {}
        digit_df = df[df['round_id'].astype(str).str.isdigit()].copy()
        for tourney, sub in digit_df.groupby('tourney_name'):
            unique_ids = sorted(sub['round_id'].unique())
            n = len(unique_ids)
            labels = ROUND_LABELS.get(n, [f'R{i+1}' for i in range(n)])
            if n not in ROUND_LABELS:
                print(f"⚠️ {tourney} 数字轮次数={n}，使用默认标签")
            round_maps[tourney] = {int(uid): label for uid, label in zip(unique_ids, labels)}
        return round_maps

    def _map_round(self, tourney_name: str, round_id, round_maps: dict) -> Optional[str]:
        if pd.isna(round_id):
            return None
        s = str(round_id).strip().upper()
        if s in ('Q', 'S', 'F'):
            return {'Q': 'QF', 'S': 'SF', 'F': 'F'}[s]
        try:
            return round_maps.get(tourney_name, {}).get(int(s))
        except ValueError:
            return None

    def _extract_seed(self, val) -> Optional[int]:
        if pd.notna(val):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                pass
        return None

    def _build_score(self, row: pd.Series) -> Optional[str]:
        try:
            w = int(row['winner'])
        except (ValueError, TypeError):
            return None

        def sets():
            parts = []
            for i in range(1, 4):
                a, b = row.get(f'scoreset{i}A'), row.get(f'scoreset{i}B')
                if pd.notna(a) and pd.notna(b) and str(a).strip() != '' and str(b).strip() != '':
                    av, bv = int(a), int(b)
                    parts.append(f"{av}-{bv}" if w in (2, 4) else f"{bv}-{av}")
                else:
                    break
            return parts

        if w in (2, 3):
            parts = sets()
            return ' '.join(parts) if parts else None
        elif w in (4, 5):
            parts = [p for p in sets() if p != '0-0']
            base = ' '.join(parts)
            return f"{base} RET" if base else "RET"
        elif w in (6, 7):
            return "W/O"
        return None

    def _process_raw(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """将原始爬取数据处理为最终字段格式。"""
        round_maps = self._build_round_map(raw_df)
        results = []
        for _, row in raw_df.iterrows():
            try:
                w = int(row['winner'])
            except (ValueError, TypeError):
                continue
            if w in (2, 4, 6):
                winner_name, loser_name = row['playerA'], row['playerB']
                winner_seed, loser_seed = self._extract_seed(row['seedA']), self._extract_seed(row['seedB'])
            elif w in (3, 5, 7):
                winner_name, loser_name = row['playerB'], row['playerA']
                winner_seed, loser_seed = self._extract_seed(row['seedB']), self._extract_seed(row['seedA'])
            else:
                continue
            results.append({
                'tourney_name': unidecode(row['tourney_name']),
                'tourney_level': row['tourney_level'],
                'tourney_date': row['tourney_date'],
                'surface': row['surface'],
                'round': self._map_round(row['tourney_name'], row['round_id'], round_maps),
                'best_of': row['best_of'],
                'winner_name': winner_name,
                'loser_name': loser_name,
                'score': self._build_score(row),
                'winner_seed': winner_seed,
                'loser_seed': loser_seed,
            })
        return pd.DataFrame(results)

    # ── 增量更新 ──────────────────────────────────────────────

    def _get_already_scraped(self) -> set:
        """读取已有 matches 文件，返回已爬取的 tourney_name 集合。"""
        if not self.matches_path.exists():
            return set()
        df = pd.read_csv(self.matches_path)
        return set(df['tourney_name'].unique())

    def update_matches(self, calendar_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        增量更新比赛数据。
        - 只爬取 winner 不为空（赛事已结束）且尚未爬取过的赛事。
        - 将新数据追加到已有 matches 文件。
        """
        if calendar_df is None:
            if not self.calendar_path.exists():
                raise FileNotFoundError("未找到日历文件，请先运行 fetch_calendar()")
            calendar_df = pd.read_csv(self.calendar_path)

        finished = calendar_df[(calendar_df['winner'].notna()) & (calendar_df['winner'] != '')].copy()
        already_done = self._get_already_scraped()
        to_scrape = finished[~finished['tourney_name'].isin(already_done)]

        if to_scrape.empty:
            print("✅ 没有需要更新的赛事。")
            return pd.read_csv(self.matches_path) if self.matches_path.exists() else pd.DataFrame()

        print(f"共 {len(to_scrape)} 个新赛事需要爬取...")
        all_raw = []
        for _, cal_row in to_scrape.iterrows():
            tid = cal_row['tourney_id']
            drawsize = cal_row['drawsize']
            print(f"⏳ 爬取赛事：{cal_row['tourney_name']} (ID: {tid}) (Drawsize: {drawsize})")
            data = self._get(f'https://api.wtatennis.com/tennis/tournaments/{tid}/{self.year}/matches')
            if data:
                records = self._parse_matches(data)
                all_raw.extend(records)
                print(f"   ✓ 获取 {len(records)} 场比赛")
                # if drawsize - 1 != len(records):  给出警告，缺少一些比赛
                if (drawsize - 1) != len(records):
                    print(f" ⚠️ 期望有 {drawsize - 1} 场比赛，缺少 {drawsize -1 -len(records)} 场")
            time.sleep(3)

        if not all_raw:
            print("⚠️ 未获取到新比赛数据。")
            return pd.read_csv(self.matches_path) if self.matches_path.exists() else pd.DataFrame()

        new_df = self._process_raw(pd.DataFrame(all_raw))

        if self.matches_path.exists():
            existing_df = pd.read_csv(self.matches_path)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined = new_df

        combined.to_csv(self.matches_path, index=False, encoding='utf-8-sig')
        print(f"🎉 matches 已更新：{self.matches_path}（新增 {len(new_df)} 场，共 {len(combined)} 场）")
        return combined
    
    def get_winner_age(self, rows):
        for row in rows:
            if row["winner"] != "":
                # 利用dob和tourney_end_date计算winner_age
                dob = datetime.strptime(row["dob"], "%Y-%m-%d")
                tourney_end_date = datetime.strptime(row["tourney_end_date"], "%Y-%m-%d")
                winner_age = (tourney_end_date - dob).days / 365.25
                row["winner_age"] = round(winner_age, 2)
        return rows


    def update_calendar(self, filepath='./output/wta_calendar_champs_start_2009.json'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            print(f"成功读取日历文件：{filepath}（{len(all_data)} 个赛事）")

        except Exception as e:
            print(f"⚠️ 日历读取失败：{e}")
            return
        # 删除目标年份记录
        original_count = len(all_data)
        filtered_data = [record for record in all_data if str(self.year) != str(record['year'])]
        remove_count = original_count - len(filtered_data)
        print(f"✅ 删除目标年份{self.year}记录：{remove_count} 个赛事")
        # 拼接新数据
        new_rows = self.fetch_calendar()
        new_rows = self.get_winner_age(new_rows)
        filtered_data.extend(new_rows)
        print(f"添加新年份{self.year}记录：{len(new_rows)} 个赛事")
        # 写回文件
        filtered_data.sort(key=lambda x: datetime.strptime(x['tourney_start_date'], '%Y-%m-%d'), reverse=True)
        with open(filepath,'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 日历已更新：{filepath}（{len(filtered_data)} 个赛事）")
    
        


    # ── 主入口 ────────────────────────────────────────────────

    def run(self):
        """完整流程：更新日历 → 增量爬取比赛数据。"""
        print(f"=== WTA {self.year} 数据更新 ===")
        cal_df = self.fetch_calendar()
        cal_df.to_csv(self.calendar_path, index=False, encoding='utf-8-sig')
        print(f"✅ 日历已保存：{self.calendar_path}（{len(cal_df)} 个赛事）")
        self.update_matches(cal_df)
        print("=== 完成 ===")



def get_col_winner_age(file_path='./scrape/wta_calendar_start_2009.csv'):
    df = pd.read_csv(file_path)
    # use 'dob' - 'tourney_end_date, datetime，注意可能会有nan的情况就不处理
    # 得到天数转换为年，保留一位小数
    # 把str转换为datetime格式
    df['tourney_end_date'] = pd.to_datetime(df['tourney_end_date'])
    df['dob'] = pd.to_datetime(df['dob'])
    df['winner_age'] = (df['tourney_end_date'] - df['dob']).dt.days / 365
    # 保留两位小数
    df['winner_age'] = df['winner_age'].round(2)
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

    # replace seed 0 into 非种子标记
    df['seed'] = df['seed'].replace(0, 'Non-seed')
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def csv_to_json(csv_file_path, json_file_path):
    data = []
    # load csv_file_path data and sort by tourney_end_date(dscending)
    csv_data = pd.read_csv(csv_file_path)
    # tourney_start_date dtype: datetime
    csv_data['tourney_start_date'] = pd.to_datetime(csv_data['tourney_start_date'], format="%Y-%m-%d")
    csv_data = csv_data.sort_values(by='tourney_start_date', ascending=False)
    csv_data.to_csv(csv_file_path, index=False, encoding='utf-8-sig')


    with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
        # 自动将第一行作为字典的键
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            data.append(row)
    
    with open(json_file_path, mode='w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)
    
    print(f"转换完成！共 {len(data)} 条记录。")


if __name__ == '__main__':
    file_path='./output/wta_calendar_champs_start_2009.json'
    # 使用示例（请将文件路径替换为你的实际路径）
    scraper = WTAScraper(year=2026, output_dir='./output', only_fetch_gs=False)
    scraper.update_calendar(filepath=file_path)

    # # scrape 1968-2026 grand slam
    # all_gs_calendar = pd.DataFrame()
    # for year in range(1968, 2027):
    #     scraper = WTAScraper(year=year, output_dir='./scrape', only_fetch_gs=True)
    #     cal_df = scraper.fetch_calendar()
    #     all_gs_calendar = pd.concat([all_gs_calendar, cal_df], ignore_index=True)

    # all_gs_calendar.to_csv('./scrape/wta_all_gs_calendar.csv', index=False, encoding='utf-8-sig')



    # merge_calendar() 
    # get_col_winner_age()

