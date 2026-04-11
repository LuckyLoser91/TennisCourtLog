#!/usr/bin/env python3
"""
update_readme_tree.py

自动更新 README.md 中的目录树，并在文件和目录后附加简介（从 file_descriptions.json 读取）。
支持通配符模式（如 'tennis_atp/atp_matches_*.csv'）匹配多个文件。

要求：
    - README.md 中包含标记：
        <!-- DIR_STRUCTURE_START -->
        <!-- DIR_STRUCTURE_END -->
    - 同目录下 file_descriptions.json 提供描述映射。
"""

import os
import re
import json
import fnmatch
from pathlib import Path

# ----------------------------------------------------------------------
# 路径配置
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_PATH = PROJECT_ROOT / "README.md"
DESCRIPTIONS_FILE = Path(__file__).parent / "file_descriptions.json"

# 忽略的目录/文件名称
IGNORE_PATTERNS = {
    "__pycache__", ".git", ".idea", ".vscode",
    "venv", "env", ".env", "*.pyc", ".DS_Store", "*.log"
}

# ----------------------------------------------------------------------
# 描述加载与匹配
# ----------------------------------------------------------------------
_descriptions = None

def load_descriptions():
    """加载文件描述 JSON，并缓存"""
    global _descriptions
    if _descriptions is not None:
        return _descriptions
    if not DESCRIPTIONS_FILE.exists():
        print(f"⚠️ 描述文件不存在: {DESCRIPTIONS_FILE}，将不显示注释。")
        _descriptions = {}
        return _descriptions
    with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
        _descriptions = json.load(f)
    return _descriptions

def get_description(rel_path: str) -> str:
    """
    根据相对路径获取描述。
    先精确匹配，再尝试通配符模式匹配。
    返回描述字符串，若没有则返回空字符串。
    """
    descriptions = load_descriptions()
    if not descriptions:
        return ""

    # 统一路径分隔符为正斜杠
    rel_path = rel_path.replace('\\', '/')

    # 1. 精确匹配
    if rel_path in descriptions:
        return descriptions[rel_path]

    # 2. 通配符匹配
    for pattern, desc in descriptions.items():
        if '*' in pattern or '?' in pattern:
            if fnmatch.fnmatch(rel_path, pattern):
                return desc

    return ""

# ----------------------------------------------------------------------
# 目录树生成（带注释）
# ----------------------------------------------------------------------
def should_ignore(name: str, is_dir: bool = False) -> bool:
    if name in IGNORE_PATTERNS:
        return True
    if name.startswith("."):
        return True
    return False

def compress_file_sequence(files):
    """压缩连续年份文件序列，返回列表，元素为文件名或 '...'"""
    if len(files) < 4:
        return [f.name for f in files]

    files_sorted = sorted(files, key=lambda p: p.name)
    result = []
    i = 0
    n = len(files_sorted)

    while i < n:
        pattern = r"^(.+)_(\d{4})(\..+)$"
        match = re.match(pattern, files_sorted[i].name)
        if not match:
            result.append(files_sorted[i].name)
            i += 1
            continue

        prefix, year_str, ext = match.groups()
        start_year = int(year_str)
        j = i + 1
        while j < n:
            next_match = re.match(pattern, files_sorted[j].name)
            if not next_match:
                break
            n_prefix, n_year_str, n_ext = next_match.groups()
            if n_prefix != prefix or n_ext != ext:
                break
            if int(n_year_str) == start_year + (j - i):
                j += 1
            else:
                break

        seq_len = j - i
        if seq_len >= 3:
            result.append(files_sorted[i].name)
            result.append("...")
            result.append(files_sorted[j-1].name)
            i = j
        else:
            for k in range(i, j):
                result.append(files_sorted[k].name)
            i = j

    return result

def generate_tree(start_path: Path, prefix: str = "", base_path: Path = None) -> list:
    """
    递归生成目录树，返回字符串列表。
    base_path 用于计算相对路径以查找描述。
    """
    if base_path is None:
        base_path = PROJECT_ROOT

    lines = []
    try:
        items = sorted(start_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return lines

    filtered_items = [
        item for item in items
        if not should_ignore(item.name, item.is_dir())
    ]

    dirs = [item for item in filtered_items if item.is_dir()]
    files = [item for item in filtered_items if item.is_file()]

    # 处理目录
    for i, d in enumerate(dirs):
        is_last = (i == len(dirs) - 1 and len(files) == 0)
        connector = "└── " if is_last else "├── "

        rel_path = str(d.relative_to(base_path)).replace('\\', '/')
        desc = get_description(rel_path)
        line = f"{prefix}{connector}{d.name}"
        if desc:
            line += f"  # {desc}"
        lines.append(line)

        extension = "    " if is_last else "│   "
        lines.extend(generate_tree(d, prefix + extension, base_path))

    # 处理文件（先压缩序列）
    compressed_names = compress_file_sequence(files)
    for i, name in enumerate(compressed_names):
        is_last = (i == len(compressed_names) - 1)
        connector = "└── " if is_last else "├── "

        if name == "...":
            lines.append(f"{prefix}{connector}...")
        else:
            # 找到对应的完整路径对象以计算相对路径
            file_obj = next((f for f in files if f.name == name), None)
            rel_path = str(file_obj.relative_to(base_path)).replace('\\', '/') if file_obj else ""
            desc = get_description(rel_path) if rel_path else ""
            line = f"{prefix}{connector}{name}"
            if desc:
                line += f"  # {desc}"
            lines.append(line)

    return lines

def build_directory_tree():
    """生成完整目录树文本"""
    tree_lines = [PROJECT_ROOT.name + "/"]
    tree_lines.extend(generate_tree(PROJECT_ROOT))
    return "\n".join(tree_lines)

# ----------------------------------------------------------------------
# 更新 README
# ----------------------------------------------------------------------
def update_readme():
    if not README_PATH.exists():
        print(f"❌ README.md 不存在于 {README_PATH}")
        return

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "<!-- DIR_STRUCTURE_START -->"
    end_marker = "<!-- DIR_STRUCTURE_END -->"

    if start_marker not in content or end_marker not in content:
        print("⚠️ 未找到目录树标记，请在 README.md 中添加：")
        print(f"    {start_marker}")
        print(f"    {end_marker}")
        return

    new_tree = build_directory_tree()
    replacement = f"{start_marker}\n```\n{new_tree}\n```\n{end_marker}"

    pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✅ README.md 目录树已更新（含文件注释）。")

if __name__ == "__main__":
    update_readme()