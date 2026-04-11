# tennisdata/config.py
from pathlib import Path
from typing import Optional, Tuple

def find_project_root(
    start_path: Optional[Path] = None,
    marker_dirs: Tuple[str, ...] = ("tennis_wta", "tennis_atp")
) -> Path:
    """
    向上查找项目根目录。
    
    Args:
        start_path: 起始搜索路径，如果不提供则使用当前工作目录。
        marker_dirs: 用于标识项目根目录的文件夹名。
    
    Returns:
        项目根目录的 Path 对象。
    
    Raises:
        FileNotFoundError: 如果找不到根目录。
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path
    while True:
        if all((current / d).is_dir() for d in marker_dirs):
            return current
        parent = current.parent
        if parent == current:  # 到达文件系统根目录
            raise FileNotFoundError(
                f"找不到项目根目录。标志目录: {marker_dirs}，起始路径: {start_path}"
            )
        current = parent

# 为方便其他模块使用，可以提供一个基于本模块所在目录推算根目录的方法
def get_project_root_from_this_file() -> Path:
    """基于本配置文件所在位置推算项目根目录（适用于本文件就在项目内的场景）"""
    return find_project_root(Path(__file__).resolve().parent)

# 或者直接计算一次根目录并导出为常量（如果确定本模块位于项目内）
PROJECT_ROOT = find_project_root(Path(__file__).resolve().parent)

# 比赛数据路径配置
DATA_PATHS = {
    "wta": {
        "matches_dir": PROJECT_ROOT / "tennis_wta",  # 存放年份 CSV 的目录
        "gs_matches": PROJECT_ROOT / "tennis_wta" / "wta_gs_matches.csv",
        "players": PROJECT_ROOT / "tennis_wta" / "wta_players.csv",
        "active_rank": PROJECT_ROOT / "tennis_wta" / "wta_players_active_rank.csv",
        
        "manual_mapping": PROJECT_ROOT / "tennis_wta" / "wta_manual_mapping.csv",
    },
    "atp": {
        "matches_dir": PROJECT_ROOT / "tennis_atp",
        "gs_matches": PROJECT_ROOT / "tennis_atp" / "atp_gs_matches.csv",
        "players": PROJECT_ROOT / "tennis_atp" / "atp_players.csv",
        "active_rank": PROJECT_ROOT / "tennis_atp" / "atp_players_active_rank.csv",
        
        "manual_mapping": PROJECT_ROOT / "tennis_atp" / "atp_manual_mapping.csv",
    },
}