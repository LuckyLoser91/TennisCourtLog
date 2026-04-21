# 关于数据集

## 📂 目录结构

<!-- DIR_STRUCTURE_START -->
```
TennisCourtLog/
├── scripts
│   ├── config.py  # 项目路径配置模块
│   ├── file_descriptions.json
│   ├── transfer_tennisabstract_data.py  # Tennis Abstract 数据获取
│   ├── transfer_uk_data.py  # 从 tennis-data.co.uk 数据进行统一化数据转换包括name映射
│   ├── update_data.py  # 主更新脚本：更新球员库和 GS 汇总
│   └── update_readme_tree.py  # 自动更新 README 目录树
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


## 📌 数据集内容

主要维护两个数据子集tennis_wta和tennis_atp, 包括wta_matches_year.csv，atp_matches_year.csv文件

Datasource：tennisabstract: https://github.com/JeffSackmann/tennis_wta; uk: http://tennis-data.co.uk/

数据来自以上两个网站，从中构建了统一的列，包括13列信息。其中1968-2024年的数据来自tennisabstract，感谢JeffSackmann公开的数据集。而2025年开始的数据来自uk网站，辅助实时更新该数据集。

赛事信息： 
tourney_name, tourney_level, tourney_date, surface

注：tourney_level两个数据集类型不统一的问题暂时没解决，只统一了Grand Slam

比赛信息： 
round, best_of, winner_name, loser_name, score, winner_rank, loser_rank, winner_rank_points, loser_rank_points

注：round对uk的数据进行了统一化处理包括 [R128, R64, R32, R16, QF, SF, F]

另外在维护数据中需要的几个其他文件，xxx为wta or atp

* xxx_players.csv: 历史所有球员的信息文件，列名包括player_id,name,hand,dob,ioc,height
* xxx_players_active_rank.csv：当前球员排名文件，列名包括rank,name,ioc,dob
* xxx_manual_mapping.csv：在对uk的名字缩写进行映射时的一些手动映射文件，列名包括abbreviation,full_name

# 数据更新与维护
1. 月更，更新wta tour champs
2. 季度性更新，每个大满贯过后会进行一次数据更新
   * 调用transfer_uk_data.py脚本，更新最新年份的比赛数据
3. 年更
   * 调用update_data.py脚本，更新大满贯数据和球员库数据

# 📝 数据分析

1. 大满贯冠军Leaderboard数据统计

# ToDo

1. 做一些有意思的数据分析脚本









## 📄 许可证 (License)

本项目（包括所有数据文件、脚本及相关文档）采用 [知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh) 进行许可。

这意味着您可以自由地：
- **共享** — 在任何媒介以任何形式复制、发行本作品。
- **演绎** — 修改、转换或以本作品为基础进行创作。

但必须遵守以下条件：
- **署名 (BY)** — 您必须给出适当的署名，提供指向本许可协议的链接，同时标明是否（对原始作品）作了修改[reference:5]。
- **非商业性使用 (NC)** — 您不得将本作品用于商业目的[reference:6]。
- **相同方式共享 (SA)** — 如果您再混合、转换或者基于本作品进行创作，您必须基于与原先许可协议相同的许可协议分发您贡献的作品[reference:7]。

### 致谢 (Attribution)
本项目的数据来源及整理工作由以下各方贡献：
- **历史比赛数据 (1968-2024)**：源自 [JeffSackmann / Tennis Abstract](https://github.com/JeffSackmann) 的 [tennis_wta](https://github.com/JeffSackmann/tennis_wta) 与 [tennis_atp](https://github.com/JeffSackmann/tennis_atp) 项目，采用 CC BY-NC-SA 4.0 许可。

- **最新比赛数据 (2025+)**：源自 [tennis-data.co.uk](http://tennis-data.co.uk/)。

  

