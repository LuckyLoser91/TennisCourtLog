"""
发球数据块回补脚本（可选，需自备 API key）

背景
----
本项目的 13 列统一格式来自 Jeff Sackmann 的 49 列原始数据集，在归一化过程中
整个发球统计块被裁掉了：

    w_ace, w_df, w_svpt, w_1stIn, w_1stWon, w_2ndWon, w_SvGms, w_bpSaved, w_bpFaced
    l_ace, l_df, l_svpt, l_1stIn, l_1stWon, l_2ndWon, l_SvGms, l_bpSaved, l_bpFaced

README 的 ToDo 第 1 条「做一些关于得分率的数据 leaderboard」正好需要这批列
（一发进球率、一发得分率、二发得分率、破发点挽救率、ACE 场均等）。而 README
「数据来源」中链接的上游仓库 JeffSackmann/tennis_atp 与 tennis_wta 目前均返回
404，所以这些列已经无法从原处重新导入。

本脚本从 Live Tennis API 的 1968–2022 历史成绩档案把这批列取回来，写成一个
**独立的 sidecar CSV**，通过本项目已有的 5 个规范列与现有数据关联：

    tourney_name, tourney_date, round, winner_name, loser_name

不修改、不覆盖 tennis_atp/ 与 tennis_wta/ 下的任何现有文件。不设置
LTAPI_KEY 时本脚本不会被任何其他模块调用，对现有流程零影响。

覆盖范围与边界（重要）
----------------------
- 该档案覆盖 1968–2022。本项目数据为 1968–2026，因此 **2023 年及以后不在本
  脚本覆盖范围内**。
- 该档案的逐场发球统计**自 1991 年起**才有记录，1991 年以前的绝大多数场次
  stats 为 null。因此本脚本默认只接受 1991–2022 的年份。
- 未能精确匹配、匹配到多条、或比分对不上的记录一律**跳过并写入 review 文件**，
  绝不猜测、绝不模糊匹配。

输入文件
--------
- ./tennis_{tour}/{tour}_matches_{year}.csv : 本项目的 13 列比赛数据（必需）

输出文件
--------
1. ./output/{tour}_serve_stats_{year}.csv : 发球数据块（主要输出，可断点续跑）
2. ./output/{tour}_serve_stats_{year}_review.csv : 需人工核对的记录
   （未匹配 / 多重匹配 / 比分不一致 / 档案未记录统计）

运行方式
--------
    export LTAPI_KEY=<你的 key>
    python updates/update_serve_stats_ltapi.py --tour atp --year 2019

    # 先小规模试跑 50 场，确认无误再跑整年
    python updates/update_serve_stats_ltapi.py --tour atp --year 2019 --limit 50

    # 不联网的纯函数自检
    python updates/update_serve_stats_ltapi.py --self-test

请求量提示
----------
档案列表接口一次最多返回 200 条，但**逐场发球统计只在单场详情接口上返回**，
因此一年 ≈ 该年场次数 次详情请求（ATP 一年约 3000 场）。脚本默认限速
1.1 秒/请求以适配 60 次/分钟的额度，并支持断点续跑：重跑时会自动跳过输出文件
中已有的场次。请按年份分批运行。

依赖：requests（本项目已在使用）+ 标准库 csv，无新增依赖。
"""

import argparse
import csv
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from scripts.config import DATA_PATHS

# ─── 常量 ─────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://api.livetennisapi.com/api/public/v1"

# 档案有逐场发球统计的起始年份，以及档案本身的结束年份
STATS_FIRST_YEAR = 1991
ARCHIVE_LAST_YEAR = 2022

PAGE_SIZE = 200          # 档案列表接口上限
DEFAULT_SLEEP = 1.1      # 秒/请求，适配 60 次/分钟
REQUEST_TIMEOUT = 30

# 本项目 13 列中用于关联的 5 列
JOIN_COLUMNS = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name"]

# 档案 stats 字段 -> Sackmann 原始列名（保持上游命名，方便后续 leaderboard 复用）
STAT_FIELD_MAP = [
    ("aces", "ace"),
    ("double_faults", "df"),
    ("serve_points", "svpt"),
    ("first_in", "1stIn"),
    ("first_won", "1stWon"),
    ("second_won", "2ndWon"),
    ("serve_games", "SvGms"),
    ("bp_saved", "bpSaved"),
    ("bp_faced", "bpFaced"),
]

STAT_COLUMNS = (
    ["minutes"]
    + [f"w_{suffix}" for _, suffix in STAT_FIELD_MAP]
    + [f"l_{suffix}" for _, suffix in STAT_FIELD_MAP]
)

OUTPUT_COLUMNS = JOIN_COLUMNS + STAT_COLUMNS
REVIEW_COLUMNS = JOIN_COLUMNS + ["reason", "detail"]


# ─── 归一化与关联键 ───────────────────────────────────────────────────────────


def norm_text(value: Optional[str]) -> str:
    """姓名/赛事名归一化：去重音无关的大小写、合并空白、去掉非字母数字字符。

    只做确定性的形态归一，不做任何模糊匹配。
    """
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^0-9a-z一-鿿]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def norm_date(value: Optional[str]) -> str:
    """日期归一化为 YYYY-MM-DD。

    本项目内同时存在三种写法，都要能对上：
      - '2020-01-06'  历史文件（1968–2024，源自 tennisabstract）
      - '2020/1/6'    update_tour_matches_uk.py 生成的文件（未补零）
      - '20200106'    Sackmann 原始格式
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""

    # 带分隔符：YYYY-M-D / YYYY/M/D，逐段补零
    parts = re.split(r"[^0-9]+", text)
    if len(parts) == 3 and len(parts[0]) == 4 and all(parts):
        year, month, day = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # 无分隔符：YYYYMMDD
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return text


def norm_round(value: Optional[str]) -> str:
    """轮次归一化。两侧使用同一套受控词表（R128..F, RR, BR, Q1..Q4, ER）。"""
    if value is None:
        return ""
    return str(value).strip().upper().replace(" ", "")


def norm_score(value: Optional[str]) -> str:
    """比分归一化，仅用于**校验**，不参与关联键。

    去掉空白与括号内抢七小分的差异之外的噪声，保留 RET / W/O / DEF 等结果词，
    因为这些词本身就是结果的一部分。
    """
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = text.replace("W/O", "WO").replace("WALKOVER", "WO")
    text = re.sub(r"[^0-9A-Z]+", "", text)
    return text


def join_key(
    tourney_name: Optional[str],
    tourney_date: Optional[str],
    round_: Optional[str],
    winner_name: Optional[str],
    loser_name: Optional[str],
) -> Tuple[str, str, str, str, str]:
    """构造五元组关联键。任一分量为空即视为不可关联（返回值含空串）。"""
    return (
        norm_text(tourney_name),
        norm_date(tourney_date),
        norm_round(round_),
        norm_text(winner_name),
        norm_text(loser_name),
    )


def key_is_complete(key: Tuple[str, ...]) -> bool:
    return all(part for part in key)


# ─── 档案记录 -> 输出行 ───────────────────────────────────────────────────────


def archive_join_key(record: Dict) -> Tuple[str, str, str, str, str]:
    """从档案的一条 ArchiveMatch 记录构造关联键。"""
    winner = record.get("winner") or {}
    loser = record.get("loser") or {}
    return join_key(
        record.get("tournament"),
        record.get("event_date"),
        record.get("round"),
        winner.get("name"),
        loser.get("name"),
    )


def extract_stats(detail: Dict) -> Optional[Dict[str, object]]:
    """把单场详情的 stats 块映射成 Sackmann 命名的列。

    档案未记录统计时 stats 为 null —— 此时返回 None，绝不用 0 或均值填充。
    只要 winner/loser 任一侧缺失就整场判为未记录，避免半条数据流入得分率计算。
    """
    stats = detail.get("stats")
    if not isinstance(stats, dict):
        return None

    winner_stats = stats.get("winner")
    loser_stats = stats.get("loser")
    if not isinstance(winner_stats, dict) or not isinstance(loser_stats, dict):
        return None

    row: Dict[str, object] = {"minutes": detail.get("minutes")}
    for side, side_stats in (("w", winner_stats), ("l", loser_stats)):
        for field, suffix in STAT_FIELD_MAP:
            row[f"{side}_{suffix}"] = side_stats.get(field)
    return row


# ─── HTTP ─────────────────────────────────────────────────────────────────────


class ArchiveClient:
    """Live Tennis API 历史档案的极简客户端。

    只读、只访问固定的 base URL；限速与 429 退避内置。
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL,
                 sleep: float = DEFAULT_SLEEP):
        self.base_url = base_url.rstrip("/")
        self.sleep = sleep
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })
        self._last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.sleep:
            time.sleep(self.sleep - elapsed)
        self._last_request = time.monotonic()

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        for attempt in range(5):
            self._throttle()
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                # 额度用尽是对方在说“慢一点”，照做，不绕过。
                wait = float(response.headers.get("Retry-After") or (5 * (attempt + 1)))
                print(f"  达到速率限制，等待 {wait:.0f}s 后重试…")
                time.sleep(wait)
                continue
            if response.status_code == 401:
                raise SystemExit("LTAPI_KEY 无效或未授权（401）。")
            if response.status_code == 403:
                raise SystemExit(
                    "当前套餐无权访问历史档案（403）。档案接口需要 BASIC 及以上，"
                    "或任一 Historical Data API 套餐。"
                )
            response.raise_for_status()
            return response.json()
        raise SystemExit("多次触发速率限制后仍未成功，请稍后再试。")

    def iter_archive_matches(self, tour: str, date_from: str, date_to: str):
        """分页拉取某年的档案列表。以 meta.has_more 为准，不靠比较条数判断。"""
        offset = 0
        while True:
            payload = self._get("/history/archive/matches", {
                "tour": tour,
                "from": date_from,
                "to": date_to,
                "limit": PAGE_SIZE,
                "offset": offset,
            })
            data = payload.get("data") or []
            for record in data:
                yield record
            meta = payload.get("meta") or {}
            if not meta.get("has_more"):
                return
            if not data:
                # has_more 为真却返回空页：宁可停下，也不空转。
                print("  警告：档案返回空页但 has_more 仍为真，提前停止分页。")
                return
            offset += len(data)

    def get_archive_match(self, archive_id: int) -> Dict:
        return self._get(f"/history/archive/matches/{archive_id}")


# ─── 主流程 ───────────────────────────────────────────────────────────────────


def read_local_matches(tour: str, year: int) -> List[Dict[str, str]]:
    path = DATA_PATHS[tour]["matches_dir"] / f"{tour}_matches_{year}.csv"
    if not path.is_file():
        raise SystemExit(f"找不到本项目的比赛文件：{path}")
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_done_keys(out_path: str) -> set:
    """读取已完成的关联键，用于断点续跑。"""
    if not os.path.isfile(out_path):
        return set()
    done = set()
    with open(out_path, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            done.add(join_key(*(row.get(column) for column in JOIN_COLUMNS)))
    return done


def build_local_index(rows: List[Dict[str, str]]):
    """把本项目的比赛按关联键建索引。

    同一键出现多次说明本地数据本身有歧义 —— 记下来，这些场次一律不回补。
    """
    index: Dict[Tuple[str, ...], Dict[str, str]] = {}
    duplicates = set()
    skipped = 0
    for row in rows:
        key = join_key(
            row.get("tourney_name"), row.get("tourney_date"), row.get("round"),
            row.get("winner_name"), row.get("loser_name"),
        )
        if not key_is_complete(key):
            skipped += 1
            continue
        if key in index:
            duplicates.add(key)
        index[key] = row
    return index, duplicates, skipped


def run(tour: str, year: int, base_url: str, sleep: float,
        limit: Optional[int], output_dir: str) -> int:
    api_key = os.environ.get("LTAPI_KEY")
    if not api_key:
        print("未设置环境变量 LTAPI_KEY，跳过（本脚本为可选功能，不影响其他流程）。")
        return 0

    if not (STATS_FIRST_YEAR <= year <= ARCHIVE_LAST_YEAR):
        raise SystemExit(
            f"年份 {year} 超出可回补范围。档案覆盖至 {ARCHIVE_LAST_YEAR} 年，"
            f"且逐场发球统计自 {STATS_FIRST_YEAR} 年起才有记录。"
        )

    local_rows = read_local_matches(tour, year)
    local_index, duplicate_keys, incomplete = build_local_index(local_rows)
    print(f"本项目 {tour}_matches_{year}.csv：{len(local_rows)} 行，"
          f"可关联 {len(local_index) - len(duplicate_keys)} 场"
          f"（重复键 {len(duplicate_keys)}，关联列缺失 {incomplete}）")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{tour}_serve_stats_{year}.csv")
    review_path = os.path.join(output_dir, f"{tour}_serve_stats_{year}_review.csv")

    done_keys = read_done_keys(out_path)
    if done_keys:
        print(f"检测到已有输出，断点续跑：已完成 {len(done_keys)} 场")

    client = ArchiveClient(api_key, base_url=base_url, sleep=sleep)

    # 第一步：拉取该年档案列表，按关联键归并。
    print(f"拉取 {year} 年档案列表…")
    archive_index: Dict[Tuple[str, ...], Dict] = {}
    archive_duplicates = set()
    archive_total = 0
    for record in client.iter_archive_matches(
        tour, f"{year}-01-01", f"{year}-12-31"
    ):
        archive_total += 1
        key = archive_join_key(record)
        if not key_is_complete(key):
            continue
        if key in archive_index:
            archive_duplicates.add(key)
        archive_index[key] = record
    print(f"档案返回 {archive_total} 场，可关联 {len(archive_index)} 场"
          f"（重复键 {len(archive_duplicates)}）")

    # 第二步：逐场取详情里的 stats。
    out_exists = os.path.isfile(out_path)
    review_rows: List[Dict[str, str]] = []
    written = 0
    processed = 0

    out_handle = open(out_path, "a", encoding="utf-8", newline="")
    writer = csv.DictWriter(out_handle, fieldnames=OUTPUT_COLUMNS)
    if not out_exists:
        writer.writeheader()

    try:
        for key, local_row in local_index.items():
            if key in done_keys:
                continue

            def review(reason: str, detail: str = "") -> None:
                review_rows.append({
                    "tourney_name": local_row.get("tourney_name", ""),
                    "tourney_date": local_row.get("tourney_date", ""),
                    "round": local_row.get("round", ""),
                    "winner_name": local_row.get("winner_name", ""),
                    "loser_name": local_row.get("loser_name", ""),
                    "reason": reason,
                    "detail": detail,
                })

            if key in duplicate_keys:
                review("本地重复键", "同一关联键对应多场本地比赛，未回补")
                continue

            record = archive_index.get(key)
            if record is None:
                review("档案未匹配", "档案中无该五元组对应的记录")
                continue
            if key in archive_duplicates:
                review("档案重复键", "档案中多条记录命中同一关联键，未回补")
                continue

            # 比分校验：两侧同源，比分应当一致；不一致说明关联不可信。
            local_score = norm_score(local_row.get("score"))
            archive_score = norm_score(record.get("score"))
            if local_score and archive_score and local_score != archive_score:
                review("比分不一致",
                       f"本地={local_row.get('score')} 档案={record.get('score')}")
                continue

            archive_id = record.get("id")
            if archive_id is None:
                review("档案缺少 id", "")
                continue

            detail = client.get_archive_match(int(archive_id))
            processed += 1
            stats = extract_stats(detail)
            if stats is None:
                review("档案未记录统计", "该场 stats 为 null（1991 年前多数如此）")
                continue

            row = {column: local_row.get(column, "") for column in JOIN_COLUMNS}
            row.update(stats)
            writer.writerow(row)
            out_handle.flush()
            written += 1

            if written % 100 == 0:
                print(f"  已写入 {written} 场…")
            if limit is not None and processed >= limit:
                print(f"已达到 --limit {limit}，停止。")
                break
    except KeyboardInterrupt:
        print("\n已中断。输出文件可直接用于下次断点续跑。")
    finally:
        out_handle.close()

    if review_rows:
        with open(review_path, "w", encoding="utf-8", newline="") as handle:
            review_writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
            review_writer.writeheader()
            review_writer.writerows(review_rows)
        print(f"需人工核对 {len(review_rows)} 条 → {review_path}")

    print(f"\n完成：新写入 {written} 场 → {out_path}")
    print("关联方式：pd.merge(matches_df, serve_df, on="
          "['tourney_name','tourney_date','round','winner_name','loser_name'], how='left')")
    return 0


# ─── 自检（不联网） ───────────────────────────────────────────────────────────


def self_test() -> int:
    """纯函数自检：归一化、关联键、stats 映射。不发起任何网络请求。

    使用按 OpenAPI 文档构造的样例数据 —— 本机没有 API key，
    这些样例不是真实响应。
    """
    failures = []

    def check(name, actual, expected):
        if actual != expected:
            failures.append(f"{name}: 期望 {expected!r}，实际 {actual!r}")

    check("norm_text 合并空白", norm_text("  Roland  Garros "), "roland garros")
    check("norm_text 去标点", norm_text("Queen's Club"), "queen s club")
    check("norm_text None", norm_text(None), "")
    check("norm_date 连字符", norm_date("2019-05-27"), "2019-05-27")
    check("norm_date 紧凑", norm_date("20190527"), "2019-05-27")
    check("norm_date 斜杠未补零", norm_date("2019/5/27"), "2019-05-27")
    check("norm_date 斜杠已补零", norm_date("2019/05/27"), "2019-05-27")
    check("norm_date 空", norm_date(""), "")
    check("norm_round 大小写", norm_round(" r16 "), "R16")
    check("norm_score 抢七", norm_score("6-4 7-6(5)"), "64765")
    check("norm_score 退赛", norm_score("6-3 RET"), "63RET")
    check("norm_score walkover", norm_score("W/O"), "WO")
    check("norm_score 空", norm_score(None), "")

    key_a = join_key("Roland Garros", "2019-05-27", "R16", "A B", "C D")
    key_b = join_key("roland  garros", "20190527", "r16", "A  B", "c d")
    check("关联键归一后一致", key_a, key_b)
    check("关联键完整性", key_is_complete(key_a), True)
    check("关联键缺失检测", key_is_complete(join_key("X", "", "F", "A", "B")), False)

    # 按 OpenAPI 的 ArchiveMatch 形状构造
    record = {
        "id": 1234,
        "tournament": "Roland Garros",
        "event_date": "2019-05-27",
        "round": "R16",
        "score": "6-4 7-6(5)",
        "winner": {"name": "A B"},
        "loser": {"name": "C D"},
    }
    check("档案关联键", archive_join_key(record), key_a)

    detail_with_stats = {
        "minutes": 122,
        "stats": {
            "winner": {"aces": 12, "double_faults": 2, "serve_points": 80,
                       "first_in": 50, "first_won": 40, "second_won": 18,
                       "serve_games": 13, "bp_saved": 3, "bp_faced": 4},
            "loser": {"aces": 5, "double_faults": 4, "serve_points": 85,
                      "first_in": 48, "first_won": 33, "second_won": 15,
                      "serve_games": 12, "bp_saved": 2, "bp_faced": 6},
        },
    }
    stats = extract_stats(detail_with_stats)
    check("stats minutes", stats["minutes"], 122)
    check("stats w_ace", stats["w_ace"], 12)
    check("stats w_1stIn", stats["w_1stIn"], 50)
    check("stats l_bpFaced", stats["l_bpFaced"], 6)
    check("stats 列齐全", sorted(stats.keys()), sorted(STAT_COLUMNS))

    check("stats 为 null", extract_stats({"minutes": 90, "stats": None}), None)
    check("stats 缺 loser 侧",
          extract_stats({"stats": {"winner": detail_with_stats["stats"]["winner"]}}),
          None)
    check("stats 字段缺失不编造",
          extract_stats({"stats": {"winner": {}, "loser": {}}})["w_ace"], None)

    if failures:
        print("自检未通过：")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("自检通过（全部纯函数，未发起网络请求）。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从 Live Tennis API 历史档案（1968–2022）回补被裁掉的发球数据块",
    )
    parser.add_argument("--tour", choices=["atp", "wta"], help="巡回赛")
    parser.add_argument("--year", type=int, help=f"年份（{STATS_FIRST_YEAR}–{ARCHIVE_LAST_YEAR}）")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少场（试跑用）")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP,
                        help=f"每次请求最小间隔秒数（默认 {DEFAULT_SLEEP}）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API 基础地址")
    parser.add_argument("--output-dir", default="output", help="输出目录（默认 output）")
    parser.add_argument("--self-test", action="store_true", help="仅运行纯函数自检")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.tour or not args.year:
        parser.error("需要同时提供 --tour 与 --year（或使用 --self-test）")
    return run(args.tour, args.year, args.base_url, args.sleep,
               args.limit, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
