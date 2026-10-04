# TennisCourtLog

**TennisCourtLog** 是一个网球数据统计网站：[tennis-leaderboard.cc.cd](https://www.tennis-leaderboard.cc.cd)

网站基于 Jeff Sackmann 风格的历史比赛数据构建，覆盖 **WTA 与 ATP** 两大巡回赛，时间跨度 **1968–2026**，提供各类可交互的排行榜、球员数据统计与单场赛事签表可视化，并支持中英双语。

## 📌 网站功能概览

- **冠军类统计**：大满贯冠军榜、非大满贯冠军榜、大满贯冠军同龄对比等
- **巡回赛排名类**：历史 No.1 球员榜（在位周数、连续在位周数、大满贯/WTA1000 头衔、各表面胜率等）、Top100 球员各类数据统计
- **单场赛事可视化**：赛事签表（Draw）页面，支持球员赛事历史与赛季战绩的分栏查看
- **双语支持**：全站中/英文切换，i18n 统一管理

## 🛠 技术架构

- **部署**：全站统一部署在 **Vercel**（静态页面与动态 API 均在其上运行）
- **前端**：原生 JavaScript，共享基础设施统一维护：
  - `utils.js`：通用格式化与颜色/样式工具函数
  - `styles.css`：统一的样式类（如结果标签 `result-W`/`result-F` 等）
  - `i18n.js`：多语言文案，按模块分前缀管理（如 `draw_` 前缀用于签表页，`stats_` 前缀用于统计页）
- **后端**：`api/` 目录下的 Python 脚本，负责数据处理与页面数据生成，默认基于全量历史 CSV（`wta_matches_*.csv` / `atp_matches_*.csv`，1968–2026）扫描计算
- **本地开发**：`mock_server.py` 用于本地静态文件服务与 API 代理，方便在不推送代码的情况下预览改动
- **自动化更新**：通过 GitHub Actions 定时任务（每周一 UTC 20:00 / 北京时间 4:00，亦支持手动触发）自动执行 `updates/` 目录下的脚本，依次完成 WTA 赛事日历更新、WTA & ATP 最新比赛数据抓取、Top N 球员大赛数据统计、Top100 场地表现数据更新、WTA 世界第一球员数据更新，并在数据有变化时自动提交推送

## 📂 目录结构

<!-- DIR_STRUCTURE_START -->
```
TennisCourtLog/
├── tennis_atp
│   ├── atp_gs_matches.csv  # ATP 大满贯汇总
│   ├── atp_manual_mapping.csv  # ATP 手动姓名缩写映射表
│   ├── atp_matches_1968.csv  # ATP 历年比赛记录
│   ├── ...
│   ├── atp_matches_2026.csv  # ATP 历年比赛记录
│   ├── atp_players.csv  # ATP 历史球员档案
│   └── atp_players_active_rank.csv  # ATP 现役排名
├── tennis_wta
│   ├── wta_gs_matches.csv  # WTA 大满贯汇总
│   ├── wta_manual_mapping.csv  # WTA 手动姓名缩写映射表
│   ├── wta_matches_1968.csv  # WTA 历年比赛记录
│   ├── ...
│   ├── wta_matches_2026.csv  # WTA 历年比赛记录
│   ├── wta_players.csv  # WTA 历史球员档案
│   └── wta_players_active_rank.csv  # WTA 现役排名
├── LICENSE  # 项目许可证 (CC BY-NC-SA 4.0)
└── README.md  # 项目说明文档
```
<!-- DIR_STRUCTURE_END -->

## 📊 数据集说明

主要维护两个数据子集 tennis_wta 和 tennis_atp，包括 wta_matches_year.csv，atp_matches_year.csv 文件。

数据来源：[tennisabstract (JeffSackmann)](https://github.com/JeffSackmann/tennis_wta)；[tennis-data.co.uk](http://tennis-data.co.uk/)

数据来自以上两个网站，从中构建了统一的列，包括 13 列信息。其中 1968-2024 年的数据来自 tennisabstract，感谢 JeffSackmann 公开的数据集；而 2025 年开始的数据来自 uk 网站，辅助实时更新该数据集。

**赛事信息：**
`tourney_name`, `tourney_level`, `tourney_date`, `surface`

> 注：`tourney_level` 两个数据集类型不统一的问题暂时没解决，只统一了 Grand Slam

**比赛信息：**
`round`, `best_of`, `winner_name`, `loser_name`, `score`, `winner_rank`, `loser_rank`, `winner_rank_points`, `loser_rank_points`

> 注：`round` 对 uk 的数据进行了统一化处理，包括 `[R128, R64, R32, R16, QF, SF, F]`

另外在维护数据中需要的几个其他文件，`xxx` 为 wta 或 atp：

- `xxx_players.csv`：历史所有球员的信息文件，列名包括 `player_id, name, hand, dob, ioc, height`
- `xxx_players_active_rank.csv`：当前球员排名文件，列名包括 `rank, name, ioc, dob`
- `xxx_manual_mapping.csv`：对 uk 的名字缩写进行映射时的一些手动映射文件，列名包括 `abbreviation, full_name`

### 数据更新与维护

1. **月更**：wta/atp tour-related 数据
2. **大满贯周期更新**：gs-related 数据

## 📝 ToDo

1. 做一些关于得分率的数据 leaderboard

> 关于第 1 条：得分率需要的发球统计列（`w_ace`、`w_svpt`、`w_1stIn`、`w_1stWon`、
> `w_2ndWon`、`w_bpSaved`、`w_bpFaced` 及 `l_` 对应列）不在本项目的 13 列统一格式中，
> 也无法从 `score` 推导（`score` 只有每盘局分，没有分数）。
> 可选脚本 `updates/update_serve_stats_ltapi.py` 可以把 **1991–2022** 这段的这批列取回来，
> 写成 `output/{tour}_serve_stats_{year}.csv` sidecar 文件，用
> `tourney_name / tourney_date / round / winner_name / loser_name` 五列与现有数据关联。
> 该脚本需自备 Live Tennis API 的 key（环境变量 `LTAPI_KEY`），不设置时不做任何事，
> 也不修改 `tennis_atp/`、`tennis_wta/` 下的任何现有文件。用法见脚本开头的说明。

## 📄 许可证 (License)

本项目（包括所有数据文件、脚本及相关文档）采用 [知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh) 进行许可。

这意味着您可以自由地：
- **共享** — 在任何媒介以任何形式复制、发行本作品
- **演绎** — 修改、转换或以本作品为基础进行创作

但必须遵守以下条件：
- **署名 (BY)** — 您必须给出适当的署名，提供指向本许可协议的链接，同时标明是否（对原始作品）作了修改
- **非商业性使用 (NC)** — 您不得将本作品用于商业目的
- **相同方式共享 (SA)** — 如果您再混合、转换或者基于本作品进行创作，您必须基于与原先许可协议相同的许可协议分发您贡献的作品

### 致谢 (Attribution)

本项目的数据来源及整理工作由以下各方贡献：
- **历史比赛数据 (1968-2024)**：源自 [JeffSackmann / Tennis Abstract](https://github.com/JeffSackmann) 的 [tennis_wta](https://github.com/JeffSackmann/tennis_wta) 与 [tennis_atp](https://github.com/JeffSackmann/tennis_atp) 项目，采用 CC BY-NC-SA 4.0 许可
- **最新比赛数据 (2025+)**：源自 [tennis-data.co.uk](http://tennis-data.co.uk/)
