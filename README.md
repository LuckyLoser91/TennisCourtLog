# 关于数据集

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

1. 季度性更新，每个大满贯过后会进行一次数据更新
   * 从uk的网站下载实时数据，并利用transfer_uk_data.py对源数据进行预处理，提取13列信息。
   * 由于uk的网站上的数据的winner_name, loser_name没有全名，所以利用map_name.py对预处理的数据进行name mapping，这里需要用到xxx_player_active_rank.csv，xxx_players.csv, xxx_manual_mapping.csv这三个文件。这里可能有些没有映射成功的需要手动映射处理
2. 年更
   * 利用xxx_players_active_rank.csv年度更新历史球员信息文件
   * 更新xxx_players_active_rank.csv

# ToDo

1. 制作一个所有大满贯的数据集









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

  

