from pathlib import Path
import requests
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime, timedelta


# 获取项目根目录（TennisCourtLog/）
project_root = Path(__file__).parent.parent

# 指定 .vscode 文件夹下的 .env
env_path = project_root / '.vscode' / '.env'
load_dotenv(env_path, override=True)


class TennisApi:
    """统一的网球API请求类，基于配置文件驱动"""
    
    def __init__(self, api_config_path: str = None, 
                 request_config_path: str = None):
        """
        初始化API客户端
        
        Args:
            api_config_path: API连接配置文件路径
            request_config_path: 请求模板配置文件路径
        """
        # 默认路径指向 config 子目录
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
        
        # 用传入参数填充endpoint模板
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
    
    # ========== 特化请求方法 ==========
    
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

    def request_rank(
        self,
        save_path: Optional[str] = None,
        auto_save: bool = True
    ) -> Dict:
        """
        获取 WTA 实时排名数据并自动保存到 data/rankings/ 目录
        
        Args:
            save_path: 自定义保存路径（为 None 时自动生成）
            auto_save: 是否自动保存到默认路径（data/rankings/）
        
        Returns:
            排名数据字典
        """
        data = self._generic_request("rankings_wta")
        
        # 提取更新时间戳并计算周一日期
        updated_at = data.get("updatedAtTimestamp")
        if updated_at:
            monday_date = self.get_monday_from_timestamp(updated_at)
            print(f"排名更新日期: {datetime.fromtimestamp(updated_at).strftime('%Y-%m-%d')} (周一: {monday_date})")
        else:
            monday_date = datetime.now().strftime("%Y-%m-%d")
            print(f"未找到更新时间戳，使用当前日期: {monday_date}")
        
        # 自动保存
        if save_path is None and auto_save:
            os.makedirs("api_folder/data", exist_ok=True)
            save_path = f"api_folder/data/wta_rank_{monday_date}.json"
        
        if save_path:
            self._save_to_file(data, save_path)
        
        return data

    def request_event_detail(self, event_id: int, save_path: Optional[str] = None) -> Dict:
        """
        获取比赛详细信息（event/{event_id}）
        """
        return self._generic_request(
            "event_detail",
            event_id=event_id,
            save_path=save_path
        )
    
    def request_player_previous_match(self, team_id: int, page: int = 0, save_path: Optional[str] = None) -> Dict:
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
        
        

# 使用示例
if __name__ == "__main__":
    tennis_api = TennisApi()
    
    # 初始页数为0，循环请求直到没有更多数据，判断是否有数据根据返回的hasNextPage字段
    team_id = 157754
    page = 0
    save_dir = 'api_folder/data/player_matches/aryna_sabalenka'
    while True:
        previous_matches = tennis_api.request_player_previous_match(
            team_id=team_id,
            page=page,
            save_path=f"{save_dir}/page_{page}.json"
        )
        if not previous_matches.get("hasNextPage", False):
            print("没有更多数据了，结束请求。")
            break
        page += 1


    
    # # 获取签表数据
    # draw_data = tennis_api.request_draw(
    #     season_id=85600, 
    #     unique_tournament_id=2569, 
    #     save_path="api_folder/data/rome_2026/draw.json"
    # )
    
    # # 获取比赛统计数据
    # event_id=16124718
    # stats_data = tennis_api.request_event_statistics(
    #     event_id=event_id,
    #     save_path=f"api_folder/data/rome_2026/event_{event_id}_stats.json"
    # )

    # # 获取 WTA 排名数据
    # rank_data = tennis_api.request_rank()