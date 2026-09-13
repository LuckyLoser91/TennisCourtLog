from pathlib import Path
import requests
import csv
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime, timedelta


# 项目根目录（假设 tennis_api.py 在 api_folder/ 下，根目录是它的上一级）
project_root = Path(__file__).parent.parent

# 指定 .vscode 文件夹下的 .env
env_path = project_root / '.vscode' / '.env'
load_dotenv(env_path, override=True)


class TennisApi:
    """统一的网球API请求类，基于配置文件驱动"""

    # 类级别缓存：tour -> {pid_str: profile}
    _profile_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def __init__(self, api_config_path: str = None,
                 request_config_path: str = None):
        """
        初始化API客户端

        Args:
            api_config_path: API连接配置文件路径
            request_config_path: 请求模板配置文件路径
        """
        base_dir = os.path.dirname(__file__)

        if api_config_path is None:
            api_config_path = os.path.join(base_dir, 'config', 'api_config.json')
        if request_config_path is None:
            request_config_path = os.path.join(base_dir, 'config', 'request_config.json')

        with open(api_config_path, 'r', encoding='utf-8') as f:
            self.api_config = json.load(f)
        with open(request_config_path, 'r', encoding='utf-8') as f:
            self.request_config = json.load(f)

        self.api_key = os.environ.get("RAPIDAPI_KEY")
        if not self.api_key:
            raise ValueError("请设置环境变量 RAPIDAPI_KEY")

    # ------------------------------------------------------------------
    # 基础请求工具
    # ------------------------------------------------------------------
    def _get_headers(self, api_name: str) -> Dict[str, str]:
        """根据API名称构建请求头"""
        api_host = self.api_config[api_name]["api_host"]
        return {
            "x-rapidapi-host": api_host,
            "x-rapidapi-key": self.api_key,
            "Content-Type": "application/json"
        }

    def _save_to_file(self, data: Dict, save_path: str) -> None:
        """保存数据到JSON文件"""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"数据已保存到: {save_path}")

    def _build_url(self, request_name: str, **params) -> tuple:
        """
        根据请求名称和参数构建完整URL和headers

        Args:
            request_name: 请求配置中的请求名称
            **params: endpoint模板中需要的参数

        Returns:
            (完整URL, headers) 元组
        """
        request_conf = self.request_config[request_name]
        api_name = request_conf["api"]
        api_conf = self.api_config[api_name]

        endpoint = request_conf["endpoint_template"].format(**params)
        url = f"{api_conf['base_url']}/{endpoint}"
        headers = self._get_headers(api_name)

        return url, headers

    def _generic_request(self, request_name: str, save_path: Optional[str] = None,
                         **params) -> Dict:
        """
        通用请求方法

        Args:
            request_name: 请求配置中的请求名称
            save_path: JSON保存路径，为None时不保存
            **params: endpoint模板参数

        Returns:
            响应数据字典
        """
        url, headers = self._build_url(request_name, **params)
        print(f"请求 URL: {url}")

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if save_path is not None:
            self._save_to_file(data, save_path)

        return data

    # ------------------------------------------------------------------
    # player_profile.csv 缓存与球员资料
    # ------------------------------------------------------------------
    def _get_profile_path(self, tour: str) -> str:
        """
        返回项目根目录下 tennis_{tour}/player_profile.csv 的路径
        例如：/project_root/tennis_wta/player_profile.csv
        """
        return str(project_root / f"tennis_{tour}" / "player_profile.csv")

    def _load_player_profiles(self, tour: str) -> Dict[str, Dict[str, Any]]:
        """加载 CSV 到 dict（按 player_id str 索引），带类级缓存"""
        if tour in TennisApi._profile_cache:
            return TennisApi._profile_cache[tour]

        path = self._get_profile_path(tour)
        profiles: Dict[str, Dict[str, Any]] = {}

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pid = (row.get("id") or "").strip()
                    if not pid:
                        continue
                    profiles[pid] = {
                        "name": row.get("name", ""),
                        "id": pid,
                        "birthday": (row.get("birthday") or "").strip() or None,
                        "height": (row.get("height") or "").strip() or None,
                    }

        TennisApi._profile_cache[tour] = profiles
        return profiles

    def _save_player_profiles(self, tour: str, profiles: Dict[str, Dict[str, Any]]) -> None:
        """把 dict 写回 CSV（按 id 数字升序）"""
        path = self._get_profile_path(tour)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        def _sort_key(x: str):
            return int(x) if x.isdigit() else float("inf")

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "id", "birthday", "height"])
            writer.writeheader()
            for pid in sorted(profiles.keys(), key=_sort_key):
                p = profiles[pid]
                writer.writerow({
                    "name": p.get("name", ""),
                    "id": pid,
                    "birthday": p.get("birthday") or "",
                    "height": str(p["height"]) if p.get("height") is not None else "",
                })

        # 同步更新缓存
        TennisApi._profile_cache[tour] = profiles

    def _parse_player_info_response(self, api_data: Dict,
                                    fallback_name: str = "") -> Dict[str, Any]:
        """把 /player/profile 返回的 data 解析成 {name, birthday, height}"""
        data = api_data.get("data") if isinstance(api_data, dict) else None
        if not isinstance(data, dict):
            data = {}

        birthday_raw = data.get("birthday")
        birthday = None
        if isinstance(birthday_raw, str):
            birthday = birthday_raw.split("T", 1)[0] if "T" in birthday_raw else birthday_raw

        information = data.get("information") or {}
        height = information.get("height")
        if height is not None:
            try:
                height = int(height)
            except (ValueError, TypeError):
                pass

        return {
            "name": fallback_name or data.get("name", ""),
            "birthday": birthday,
            "height": height,
        }

    def get_player_profile(self, tour: str, player_id: int,
                           player_name: str = "") -> Dict[str, Any]:
        """
        获取球员资料：先查 CSV，没有就调 API 并写回 CSV。
        """
        profiles = self._load_player_profiles(tour)
        pid_str = str(player_id)

        if pid_str in profiles:
            return profiles[pid_str]

        try:
            api_data = self.request_player_info(tour=tour, player_id=player_id)
        except Exception as e:
            print(f"获取球员 {player_id} 信息失败: {e}")
            api_data = {}

        parsed = self._parse_player_info_response(api_data, fallback_name=player_name)
        profile = {
            "name": parsed["name"],
            "id": pid_str,
            "birthday": parsed["birthday"],
            "height": parsed["height"],
        }

        profiles[pid_str] = profile
        self._save_player_profiles(tour, profiles)
        return profile

    # ------------------------------------------------------------------
    # 特化请求方法
    # ------------------------------------------------------------------
    def request_draw(self, season_id: int, unique_tournament_id: int,
                     save_path: Optional[str] = None) -> Dict:
        """
        获取赛事签表（cup-trees）

        Args:
            season_id: 赛季ID
            unique_tournament_id: 赛事ID
            save_path: JSON保存路径

        Returns:
            签表数据字典
        """
        return self._generic_request(
            "request_draw",
            season_id=season_id,
            unique_tournament_id=unique_tournament_id,
            save_path=save_path
        )

    def request_event_statistics(self, event_id: int,
                                 save_path: Optional[str] = None) -> Dict:
        """
        获取比赛统计数据

        Args:
            event_id: 比赛事件ID
            save_path: JSON保存路径

        Returns:
            统计数据字典
        """
        return self._generic_request(
            "event_statistics",
            event_id=event_id,
            save_path=save_path
        )

    def request_event_detail(self, event_id: int,
                             save_path: Optional[str] = None) -> Dict:
        """
        获取比赛详细信息（event/{event_id}）
        """
        return self._generic_request(
            "event_detail",
            event_id=event_id,
            save_path=save_path
        )

    def request_player_previous_match(self, team_id: int, page: int = 0,
                                      save_path: Optional[str] = None) -> Dict:
        """
        获取球员最近的比赛记录（team/{team_id}/events/previous/{page}）

        Args:
            team_id: 球员ID
            page: 分页参数，默认为0
            save_path: JSON保存路径

        Returns:
            最近比赛数据字典
        """
        return self._generic_request(
            "player_previous_match",
            team_id=team_id,
            page=page,
            save_path=save_path
        )

    def request_player_info(self, tour: str, player_id: int,
                            save_path: Optional[str] = None) -> Dict:
        """
        获取球员详细资料（player/profile）

        Args:
            tour: "atp" 或 "wta"
            player_id: 球员 ID
            save_path: JSON 保存路径

        Returns:
            球员资料字典
        """
        return self._generic_request(
            "player_info",
            tour=tour,
            player_id=player_id,
            save_path=save_path
        )

    # ------------------------------------------------------------------
    # 排名相关
    # ------------------------------------------------------------------
    def get_monday_from_timestamp(self, timestamp: int) -> str:
        """
        根据时间戳计算所在周的周一日期

        Args:
            timestamp: Unix 时间戳（秒）

        Returns:
            格式为 YYYY-MM-DD 的周一日期字符串
        """
        date = datetime.fromtimestamp(timestamp)
        monday = date - timedelta(days=date.weekday())
        return monday.strftime("%Y-%m-%d")

    def _enrich_rank_data(self, rank_data: Dict, tour: str, top_n: int = 100) -> None:
        """
        对 rankings 返回的 data 列表，逐个 player 补充 birthday / height。
        只处理前 top_n 条（按返回顺序，通常就是排名顺序）。
        优先 CSV，缺失才调 API；一次性写回 CSV，避免频繁 IO。

        Args:
            rank_data: rankings 返回的完整字典
            tour: "atp" 或 "wta"
            top_n: 只补充前 N 名，默认 100
        """
        rank_list = rank_data.get("data", [])
        if not rank_list:
            return

        # 只取前 top_n 条
        target_list = rank_list[:top_n]

        profiles = self._load_player_profiles(tour)
        needs_save = False

        for entry in target_list:
            player = entry.get("player")
            if not isinstance(player, dict):
                continue

            pid = player.get("id")
            if pid is None:
                continue
            pid_str = str(pid)
            player_name = player.get("name", "")

            if pid_str in profiles:
                profile = profiles[pid_str]
            else:
                try:
                    api_data = self.request_player_info(tour=tour, player_id=pid)
                except Exception as e:
                    print(f"获取球员 {pid} 信息失败: {e}")
                    api_data = {}

                parsed = self._parse_player_info_response(api_data, fallback_name=player_name)
                profile = {
                    "name": parsed["name"],
                    "id": pid_str,
                    "birthday": parsed["birthday"],
                    "height": parsed["height"],
                }
                profiles[pid_str] = profile
                needs_save = True

            player["birthday"] = profile.get("birthday")
            player["height"] = profile.get("height")

        if needs_save:
            self._save_player_profiles(tour, profiles)
    def request_rank(
        self,
        tour: str = "atp",
        save_path: Optional[str] = None,
        auto_save: bool = True,
        enrich: bool = False,
        enrich_top_n: int = 100
    ) -> Dict:
        """
        获取 ATP/WTA 排名数据并自动保存。

        Args:
            tour: "atp" 或 "wta"
            save_path: 自定义保存路径（为 None 时自动生成）
            auto_save: 是否自动保存到 output/rankings_{tour}_{date}.json
            enrich: 是否补充球员的 birthday / height
            enrich_top_n: 只补充前 N 名的信息，默认 100

        Returns:
            排名数据字典
        """
        data = self._generic_request("rankings", tour=tour)

        # 只对前 enrich_top_n 名补球员信息
        if enrich:
            self._enrich_rank_data(data, tour, top_n=enrich_top_n)

        # 从返回列表里取第一条 date 作为排名更新日期
        rank_list = data.get("data", [])
        date_str = rank_list[0].get("date") if rank_list else None

        if date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            updated_at = int(dt.timestamp())
            monday = dt.date() - timedelta(days=dt.weekday())
            monday_date = monday.strftime("%Y-%m-%d")
            print(
                f"排名更新日期: {dt.strftime('%Y-%m-%d')} "
                f"(周一: {monday_date}, 时间戳: {updated_at})"
            )
        else:
            updated_at = None
            monday_date = datetime.now().strftime("%Y-%m-%d")
            print(f"未找到排名更新日期，使用当前日期: {monday_date}")

        if save_path is None and auto_save:
            save_path = f"output/rankings_{tour}_{monday_date}.json"

        if save_path:
            self._save_to_file(data, save_path)

        return data

# ----------------------------------------------------------------------
# 使用示例
# ----------------------------------------------------------------------
if __name__ == "__main__":
    tennis_api = TennisApi()

    # 示例 1：获取 ATP 排名，并补充球员生日/身高
    atp_rank = tennis_api.request_rank(tour="atp", enrich=True)
    print(f"ATP 排名条目数: {len(atp_rank.get('data', []))}")

    # 示例 2：获取 WTA 排名，并补充球员生日/身高
    wta_rank = tennis_api.request_rank(tour="wta", enrich=True)
    print(f"WTA 排名条目数: {len(wta_rank.get('data', []))}")

    # 示例 3：获取球员最近比赛（分页循环）
    # team_id = 157754
    # page = 0
    # save_dir = 'api_folder/data/player_matches/aryna_sabalenka'
    # while True:
    #     previous_matches = tennis_api.request_player_previous_match(
    #         team_id=team_id,
    #         page=page,
    #         save_path=f"{save_dir}/page_{page}.json"
    #     )
    #     if not previous_matches.get("hasNextPage", False):
    #         print("没有更多数据了，结束请求。")
    #         break
    #     page += 1