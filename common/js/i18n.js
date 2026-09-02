/* ================================================================
   i18n.js — 中英文翻译字典 + 语言切换引擎
   路径：common/js/i18n.js

   使用方式：
     在每个 HTML 页面的 <head> 末尾引入：
     <script src="../common/js/i18n.js"></script>

     页面内直接使用：
     - t('key')               取翻译文本
     - t('key', arg)          带参数的函数型翻译
     - data-i18n="key"        HTML 属性自动翻译
     - applyLang('zh'/'en')   手动切换语言
     - currentLang            当前语言变量

   新建页面：
     在对应区块添加新前缀的 key，公共 key 无需重复添加
================================================================ */

const i18n = {
  en: {
    /* ── 公共 ────────────────────────────────────────────────── */
    nav_home: "HOME",
    click_to_sort: "Click headers to sort",
    last_updated: "Last updated:",
    load_fail: "Failed to load data.",
    lang_toggle: "中文",
    th_no: "#",
    th_player: "PLAYER",
    th_w: "W",
    th_l: "L",
    th_winrate: "WINRATE",
    modal_winrate: "Win rate",
    th_dob: "DOB",
    th_agg: "AGG",
    th_titles: "TITLES",
    label_tour: "TOUR:",

    /* ── gsChampions · tour_gs_champions ────────────────────── */
    gsChampions_page_title: "Grand Slam Champions · WTA · ATP · Age Cutoff",
    gsChampions_title: "🏆 Grand Slam Singles · Champions Leaderboard",
    gsChampions_champions_count: (n) => `${n} champions`,
    gsChampions_label_cutoff: "CUTOFF AGE:",
    gsChampions_opt_career: "Career (All ages)",
    gsChampions_th_first: "1ST",
    gsChampions_th_agefirst: "AGE 1ST",
    gsChampions_th_last: "LAST",
    gsChampions_th_agelast: "AGE LAST",
    gsChampions_th_span: "SPAN",
    gsChampions_th_breakdown: "BREAKDOWN",
    gsChampions_th_top8: "VS TOP 8",
    gsChampions_th_top8w: "T8 W",
    gsChampions_th_top8l: "T8 L",
    gsChampions_th_winrate: "WINRATE",
    gsChampions_th_h: "H",
    gsChampions_th_c: "C",
    gsChampions_th_g: "G",
    gsChampions_footer_1st: "1ST = year of first GS title",
    gsChampions_footer_age: "AGE 1ST / AGE LAST = age at first / last title",
    gsChampions_footer_span: "SPAN = last − first + 1",
    gsChampions_footer_slams:
      "AO = Australian Open · RG = Roland Garros · WIM = Wimbledon · USO = US Open",
    gsChampions_footer_agg: "AGG = aggregate GS win rate",
    gsChampions_footer_hcg: "H = Hard · C = Clay · G = Grass",
    gsChampions_footer_top8:
      "TOP 8 W / TOP 8 L = wins / losses vs. opponents ranked top 8 at match time",
    gsChampions_footer_titles_lbl: "Titles:",
    gsChampions_footer_wr_lbl: "AGG / Surface win rate:",
    gsChampions_no_data: "No data",

    /* ── gsAtAge · tour_gs_champions_at_age ─────────────────── */
    gsAtAge_page_title: "Grand Slam · At Age (by Birth Year)",
    gsAtAge_title: "🏆 Grand Slam · Performance at Age (based on Birth Year)",
    gsAtAge_label_age: "AGE:",
    gsAtAge_th_year: "YEAR",
    gsAtAge_th_gs_result: "GRAND SLAM RESULT",
    gsAtAge_th_cum_titles: "CUM. TITLES",
    gsAtAge_th_career: "CAREER",
    gsAtAge_no_data: "No data for this age",
    gsAtAge_player_count: (n) => `${n} players`,

    /* ── nonGsChampions · tour_non_gs_champions ─────────────── */
    nonGsChampions_page_title: "Non-GS Champions · GS Win Rate Top 100",
    nonGsChampions_title:
      "Grand Slam Singles · Non-Champions Leaderboard (Top 100 by Win%, Wins > 5)",
    nonGsChampions_label_active:
      "🎾 ACTIVE ONLY (won GS match in last 2 years)",
    nonGsChampions_th_best_result: "BEST RESULT (BY SLAM)",
    nonGsChampions_th_winrate: "WINRATE",
    nonGsChampions_th_best: "⭐ BEST",
    nonGsChampions_th_vs_top8: "vs Top 8",
    nonGsChampions_th_t8w: "T8 W",
    nonGsChampions_th_t8l: "T8 L",
    nonGsChampions_footer_best: "BEST = Career best GS result",
    nonGsChampions_footer_slams: "AO/RG/WIM/USO = Best result at each major",
    nonGsChampions_footer_agg: "AGG = aggregate GS win rate",
    nonGsChampions_footer_hcg: "H = Hard · C = Clay · G = Grass",
    nonGsChampions_footer_color: "(AGG solid · H/C/G tint)",
    nonGsChampions_footer_wr_label: "Win rate colour:",
    nonGsChampions_player_count: (n) => `${n} players`,
    nonGsChampions_no_data: "No data",

    /* ── wtaCalendar · wta_calendar_champs_start_2009 ───────── */
    wtaCalendar_page_title:
      "WTA Champions Archive · Year, Level & Tournament Filter",
    wtaCalendar_title: "🎾 WTA Champions · Singles (Since 2009)",
    wtaCalendar_label_season: "📅 Season",
    wtaCalendar_label_level: "🏆 Level",
    wtaCalendar_label_champion: "🔍 CHAMPION",
    wtaCalendar_label_tournament: "🏟️ TOURNAMENT",
    wtaCalendar_opt_all_levels: "All Levels",
    wtaCalendar_opt_all_years: "All Years",
    wtaCalendar_th_season: "Season",
    wtaCalendar_th_start_date: "Start Date",
    wtaCalendar_th_drawsize: "Drawsize",
    wtaCalendar_th_tournament: "Tournament",
    wtaCalendar_th_level: "Level",
    wtaCalendar_th_surface: "Surface",
    wtaCalendar_th_champion: "Champion",
    wtaCalendar_th_age: "Age",
    wtaCalendar_record_count: (n) => `${n} tournaments`,
    wtaCalendar_champ_count: (n) => `${n} champions`,
    wtaCalendar_no_data: "🎯 No champion records match the filters",

    /* ── calendarCurrentSeason · calendar_current_season ───────── */
    calendarPage_title: "Calendar · WTA & ATP (Since 2009)",
    calendar_label_tour: "🏟️ Tour",
    calendar_label_season: "📅 Season",
    calendar_label_level: "🏆 Level",
    calendar_label_champion: "🔍 CHAMPION",
    calendar_label_tournament: "🏟️ EVENT",
    calendar_th_season: "Season",
    calendar_th_start_date: "Start Date",
    calendar_th_tournament: "Tournament",
    calendar_th_level: "Level",
    calendar_th_court: "Court",
    calendar_th_champion: "Champion",
    calendar_opt_all_levels: "All Levels",
    calendar_record_count: (n) => `${n} tournaments`,
    calendar_no_data: "🎯 No calendar records match the filters",
    calendar_last_updated: "Last updated:",
    calendar_th_birthday: "Birthday",
    calendar_th_age: "Age",
    calendar_th_height: "Height",
    calendar_opt_all_years: "All Years",
    calendar_label_show_uncompleted: "Show uncompleted",
    calendar_no_data: "🎯 No calendar records match the filters",
    calendar_opt_all_levels: "All Levels",
    

    /* ── top100Surface · wta_top100_surface ─────────────────── */
    top100Surface_page_title: "WTA Top 100 · Surface Win Rate & Titles",
    top100Surface_title: "🎾 WTA Top 100 · Surface Win Rate & Titles",
    top100Surface_player_count: (n) => `${n} players`,
    top100Surface_th_winrate: "WIN RATE",
    top100Surface_th_hard: "HARD",
    top100Surface_th_clay: "CLAY",
    top100Surface_th_grass: "GRASS",
    top100Surface_th_breakdown: "TITLES BREAKDOWN",
    top100Surface_th_hard_titles: "HARD TITLES",
    top100Surface_th_clay_titles: "CLAY TITLES",
    top100Surface_th_grass_titles: "GRASS TITLES",
    top100Surface_footer_agg:
      "AGG = overall win rate (2009–present, W/O excluded)",
    top100Surface_footer_hcg: "H = Hard · C = Clay · G = Grass",
    top100Surface_footer_titles:
      "Titles: GS = Grand Slam · 1000 = WTA 1000 · 500 = WTA 500 · 250 = WTA 250 · Finals = WTA Finals · Elite = Elite Trophy (small year-end)",
    top100Surface_footer_wr_lbl: "Win rate:",
    top100Surface_footer_titles_lbl: "Titles:",
    top100Surface_no_data: "No data",
    top100Surface_th_vstop8: "VS Top8",
    top100Surface_label_data: "DATA:",
    top100Surface_opt_career: "Career",
    top100Surface_opt_season: "Season",


    /* ── bigTournament · big_tournament_result_topn ─────────── */
    bigTournament_page_title: "WTA Top 100 · Big Tournament Stats",
    bigTournament_title: "📊 WTA Top 100 · Elite Event History",
    bigTournament_label_view: "View mode",
    bigTournament_opt_by_tourney: "🏟️ By Tournament",
    bigTournament_opt_by_player: "🎾 By Player",
    bigTournament_label_player: "Player",
    bigTournament_label_tournament: "Tournament",
    bigTournament_th_tournament: "Tournament",
    bigTournament_th_level: "Level",
    bigTournament_th_surface: "Surface",
    bigTournament_th_best_round: "Best Round",
    bigTournament_th_win_pct: "Win%",
    bigTournament_no_players: "No Top 100 players have competed in this event.",
    bigTournament_modal_title_suffix: "Tournament History",
    bigTournament_modal_close: "Close",
    bigTournament_modal_round: "RD",
    bigTournament_modal_winner: "Winner",
    bigTournament_modal_loser: "Loser",
    bigTournament_modal_score: "Score",
    bigTournament_modal_no_data: "No match data found.",
    bigTournament_modal_loading: "Loading...",
    bigTournament_modal_matches: "matches",
    bigTournament_dblclick_hint: "Double-click row for history",
    bigTournament_modal_result: "W/L",
    bigTournament_modal_opponent: "Opponent",

    /* ── no1Club · wta_no1_club ─────────────────────────────── */
    no1Club_title: "👑 WTA & ATP World No.1 Club · Historical Leaderboard",
  no1Club_page_title: "WTA & ATP World No.1 Club · Historical Leaderboard",
    no1Club_player_count: (n) => `${n} players`,
    no1Club_th_group_no1: "NO.1",
    no1Club_th_group_titles: "TITLES",
    no1Club_th_group_winrate: "WIN RATE",
    no1Club_th_first_date: "1ST DATE",
    no1Club_th_weeks: "WEEKS",
    no1Club_th_consec: "CONSEC.",
    no1Club_th_gs: "GS",
    no1Club_th_1000: "Master 1000",
    no1Club_th_overall: "OVERALL",
    no1Club_th_hard: "H",
    no1Club_th_clay: "C",
    no1Club_th_grass: "G",
    no1Club_footer_wr_lbl: "Win rate:",
    no1Club_footer_cols: "1ST YR = year of first reaching No.1  ·  CONSEC. = longest consecutive weeks  ·  H = Hard  ·  C = Clay  ·  G = Grass",
    no1Club_footer_gs_note: "GS counted from 1968",
    no1Club_footer_1000_note: "WTA 1000 counted from 1990",
    no1Club_footer_active: "Active player",
    no1Club_no_data: "No data",
    no1Club_th_age: "AGE",
    no1Club_th_1st_date: "1ST DATE",
    no1Club_th_1st_age: "1ST AGE",
    no1Club_th_last_date: "LAST DATE",
    no1Club_th_last_age: "LAST AGE",

    /* ── draw · draw ────────────────────────────────────────── */
    draw_tab_hist:           "Tournament history",
    draw_tab_season:         "Season",
    draw_hist_suffix:        "History",
    draw_hist_matches:       "matches",
    draw_hist_winrate:       "Win rate",
    draw_hist_win:           "W",
    draw_hist_loss:          "L",
    draw_hist_round:         "RD",
    draw_hist_result:        "W/L",
    draw_hist_opponent:      "Opponent",
    draw_hist_score:         "Score",
    draw_hist_close:         "Close",
    draw_hist_loading:       "Loading...",
    draw_hist_no_data:       "No match data found.",
    draw_season_tournament:  "Tournament",
    draw_season_no_data:     "No match data found for this season.",
    draw_season_loading:     "Loading...",
    draw_search_placeholder: "Search a player...",
    draw_interaction_hint:   "Click avatar for history · Click score for match stats",
    draw_dblclick_hint:      "Double-click for history",
    draw_failed_load:        "Failed to load draw",
    draw_could_not_load:     "Could not load",
    draw_last_updated:       "Last updated",
    draw_view_match_stats:   "Click score for match stats →",

    /* ── stats modal ── */
    stats_score:             "SCORE",
    stats_fg_title:          "FOREHAND/BACKHAND (TOTAL)",
    stats_svc_title:         "SERVICE",
    stats_ret_title:         "RETURN",
    stats_pts_title:         "POINTS",
    stats_winners:           "Winners",
    stats_forced_errors:     "Forced Errors",
    stats_unforced_errors:   "Unforced Errors",
    stats_aces:              "Aces",
    stats_double_faults:     "Double Faults",
    stats_1st_serve_in:      "1st Serve In",
    stats_1st_serve_won:     "1st Serve Won",
    stats_2nd_serve_won:     "2nd Serve Won",
    stats_bp_saved:          "Break Points Saved",
    stats_svc_games_won:     "Service Games Won",
    stats_1st_return_won:    "1st Return Won",
    stats_2nd_return_won:    "2nd Return Won",
    stats_bp_converted:      "Break Points Converted",
    stats_total_points:      "Total Points",
    stats_serve_pts_won:     "Serve Point Won",
    stats_return_pts_won:    "Return Point Won",
    stats_dominance:         "Dominance Ratio",
  },

  zh: {
    /* ── 公共 ────────────────────────────────────────────────── */
    nav_home: "首页",
    click_to_sort: "点击列标题排序",
    last_updated: "最近更新：",
    load_fail: "数据加载失败。",
    lang_toggle: "English",
    th_no: "#",
    th_player: "球员",
    th_w: "胜",
    th_l: "负",
    th_winrate: "胜率",
    modal_winrate: "胜率",
    th_dob: "生日",
    th_agg: "综合",
    th_titles: "冠军数",
    label_tour: "巡回赛：",

    /* ── gsChampions · tour_gs_champions ────────────────────── */
    gsChampions_page_title: "大满贯冠军 · WTA · ATP · 年龄截止",
    gsChampions_title: "🏆 大满贯单打 · 冠军排行榜",
    gsChampions_champions_count: (n) => `${n} 位冠军`,
    gsChampions_label_cutoff: "年龄截止：",
    gsChampions_opt_career: "全职业生涯",
    gsChampions_th_first: "首冠年",
    gsChampions_th_agefirst: "首冠年龄",
    gsChampions_th_last: "末冠年",
    gsChampions_th_agelast: "末冠年龄",
    gsChampions_th_span: "跨度",
    gsChampions_th_breakdown: "明细",
    gsChampions_th_top8: "对阵 TOP 8",
    gsChampions_th_top8w: "T8 胜",
    gsChampions_th_top8l: "T8 负",
    gsChampions_th_winrate: "胜率",
    gsChampions_th_h: "硬",
    gsChampions_th_c: "红土",
    gsChampions_th_g: "草",
    gsChampions_footer_1st: "首冠年 = 首个大满贯冠军年份",
    gsChampions_footer_age:
      "首冠年龄 / 末冠年龄 = 获得首个 / 最后一个冠军时的年龄",
    gsChampions_footer_span: "跨度 = 末冠年 − 首冠年 + 1",
    gsChampions_footer_slams:
      "AO = 澳大利亚网球公开赛 · RG = 法国网球公开赛 · WIM = 温布尔登 · USO = 美国网球公开赛",
    gsChampions_footer_agg: "综合 = 大满贯综合胜率",
    gsChampions_footer_hcg: "硬 = 硬地 · 红土 = 红土 · 草 = 草地",
    gsChampions_footer_top8:
      "TOP 8 胜 / TOP 8 负 = 对阵当时排名前 8 的对手的胜 / 负场数",
    gsChampions_footer_titles_lbl: "冠军数：",
    gsChampions_footer_wr_lbl: "综合 / 场地胜率：",
    gsChampions_no_data: "暂无数据",

    /* ── gsAtAge · tour_gs_champions_at_age ─────────────────── */
    gsAtAge_page_title: "大满贯 · 指定年龄（按出生年份）",
    gsAtAge_title: "🏆 大满贯 · 指定年龄表现（按出生年份）",
    gsAtAge_label_age: "年龄：",
    gsAtAge_th_year: "年份",
    gsAtAge_th_gs_result: "大满贯成绩",
    gsAtAge_th_cum_titles: "累计冠军",
    gsAtAge_th_career: "生涯冠军",
    gsAtAge_no_data: "该年龄暂无数据",
    gsAtAge_player_count: (n) => `${n} 位球员`,

    /* ── nonGsChampions · tour_non_gs_champions ─────────────── */
    nonGsChampions_page_title: "非大满贯冠军 · 大满贯胜率 Top 100",
    nonGsChampions_title: "大满贯单打 · 非冠军排行榜（胜率 Top 100，胜场 > 5）",
    nonGsChampions_label_active: "🎾 仅现役（近 2 年内有大满贯胜场）",
    nonGsChampions_th_best_result: "最佳成绩（按大满贯）",
    nonGsChampions_th_winrate: "胜率",
    nonGsChampions_th_best: "⭐ 最佳",
    nonGsChampions_th_vs_top8: "对阵Top8",
    nonGsChampions_th_t8w: "T8 胜",
    nonGsChampions_th_t8l: "T8 负",
    nonGsChampions_footer_best: "最佳 = 职业生涯最佳大满贯成绩",
    nonGsChampions_footer_slams: "AO/RG/WIM/USO = 各大满贯最佳成绩",
    nonGsChampions_footer_agg: "综合 = 大满贯综合胜率",
    nonGsChampions_footer_hcg: "硬 = 硬地 · 红土 = 红土 · 草 = 草地",
    nonGsChampions_footer_color: "（综合实色 · 场地浅色）",
    nonGsChampions_footer_wr_label: "胜率颜色：",
    nonGsChampions_player_count: (n) => `${n} 位球员`,
    nonGsChampions_no_data: "暂无数据",

    /* ── wtaCalendar · wta_calendar_champs_start_2009 ───────── */
    wtaCalendar_page_title: "WTA 冠军存档 · 年份、级别与赛事筛选",
    wtaCalendar_title: "🎾 WTA 冠军 · 单打（2009 年至今）",
    wtaCalendar_label_season: "📅 赛季",
    wtaCalendar_label_level: "🏆 级别",
    wtaCalendar_label_champion: "🔍 冠军",
    wtaCalendar_label_tournament: "🏟️ 赛事",
    wtaCalendar_opt_all_levels: "全部级别",
    wtaCalendar_opt_all_years: "全部年份",
    wtaCalendar_th_season: "赛季",
    wtaCalendar_th_start_date: "开赛日期",
    wtaCalendar_th_drawsize: "签表规模",
    wtaCalendar_th_tournament: "赛事",
    wtaCalendar_th_level: "级别",
    wtaCalendar_th_surface: "场地",
    wtaCalendar_th_champion: "冠军",
    wtaCalendar_th_age: "年龄",
    wtaCalendar_record_count: (n) => `${n} 站赛事`,
    wtaCalendar_champ_count: (n) => `${n} 位冠军`,
    wtaCalendar_no_data: "🎯 没有符合筛选条件的冠军记录",
    /* ── calendarCurrentSeason · calendar_current_season ───────── */
    calendarPage_title: "赛程日历 · WTA & ATP (自2009年起)",
    calendar_label_tour: "🏟️ 巡回赛",
    calendar_label_season: "📅 赛季",
    calendar_label_level: "🏆 级别",
    calendar_label_champion: "🔍 冠军",
    calendar_label_tournament: "🏟️ 赛事",
    calendar_th_season: "赛季",
    calendar_th_start_date: "开赛日期",
    calendar_th_tournament: "赛事名",
    calendar_th_level: "级别",
    calendar_th_court: "场地",
    calendar_th_champion: "冠军",
    calendar_opt_all_levels: "全部级别",
    calendar_record_count: (n) => `${n} 个赛事`,
    calendar_no_data: "🎯 没有符合条件的赛程记录",
    calendar_last_updated: "更新时间:",
    calendar_th_birthday: "生日",
    calendar_th_age: "夺冠年龄",
    calendar_th_height: "身高",
    calendar_opt_all_years: "全部赛季",
    calendar_label_show_uncompleted: "显示未完成赛事",
    calendar_no_data: "🎯 没有符合条件的赛事记录",
    calendar_opt_all_levels: "所有级别",
    /* ── top100Surface · wta_top100_surface ─────────────────── */
    top100Surface_page_title: "WTA Top 100 · 场地胜率与冠军数",
    top100Surface_title: "🎾 WTA Top 100 · 场地胜率与冠军数",
    top100Surface_player_count: (n) => `${n} 位球员`,
    top100Surface_th_winrate: "胜率",
    top100Surface_th_hard: "硬地",
    top100Surface_th_clay: "红土",
    top100Surface_th_grass: "草地",
    top100Surface_th_breakdown: "冠军明细",
    top100Surface_th_hard_titles: "硬地冠军",
    top100Surface_th_clay_titles: "红土冠军",
    top100Surface_th_grass_titles: "草地冠军",
    top100Surface_footer_agg: "综合 = 2009年至今综合胜率（W/O不计）",
    top100Surface_footer_hcg: "硬地 · 红土 · 草地",
    top100Surface_footer_titles:
      "冠军明细：GS = 大满贯 · 1000 = WTA 1000 · 500 = WTA 500 · 250 = WTA 250 · Finals = 年终总决赛 · Elite = 小年终精英赛",
    top100Surface_footer_wr_lbl: "胜率：",
    top100Surface_footer_titles_lbl: "冠军数：",
    top100Surface_no_data: "暂无数据",
    top100Surface_th_vstop8: "对阵Top8",
    top100Surface_label_data: "数据：",
    top100Surface_opt_career: "生涯",
    top100Surface_opt_season: "赛季",

    /* ── bigTournament · big_tournament_result_topn ─────────── */
    bigTournament_page_title: "WTA Top 100 · 大赛统计",
    bigTournament_title: "📊 WTA Top 100 · 精英赛历史成绩",
    bigTournament_label_view: "视图",
    bigTournament_opt_by_tourney: "🏟️ 按赛事",
    bigTournament_opt_by_player: "🎾 按球员",
    bigTournament_label_player: "球员",
    bigTournament_label_tournament: "赛事",
    bigTournament_th_tournament: "赛事",
    bigTournament_th_level: "级别",
    bigTournament_th_surface: "场地",
    bigTournament_th_best_round: "最佳轮次",
    bigTournament_th_win_pct: "胜率",
    bigTournament_no_players: "暂无 Top 100 球员参加过本赛事。",
    bigTournament_modal_title_suffix: "历史成绩",
    bigTournament_modal_close: "关闭",
    bigTournament_modal_round: "轮次",
    bigTournament_modal_winner: "胜者",
    bigTournament_modal_loser: "负者",
    bigTournament_modal_score: "比分",
    bigTournament_modal_no_data: "未找到比赛数据。",
    bigTournament_modal_loading: "加载中...",
    bigTournament_modal_matches: "场比赛",
    bigTournament_dblclick_hint: "双击行查看历史",
    bigTournament_modal_result: "胜负",
    bigTournament_modal_opponent: "对手",

     /* ── no1Club · wta_no1_club ─────────────────────────────── */
    no1Club_title: "👑 WTA & ATP 世界第一俱乐部 · 历史排行榜",
no1Club_page_title: "WTA & ATP 世界第一俱乐部 · 历史排行榜",
    no1Club_player_count: (n) => `${n} 位球员`,
    no1Club_th_group_no1: "世界第一",
    no1Club_th_group_titles: "冠军数",
    no1Club_th_group_winrate: "胜率",
    no1Club_th_first_date: "首次登顶",
    no1Club_th_weeks: "总周数",
    no1Club_th_consec: "最长连续",
    no1Club_th_gs: "大满贯",
    no1Club_th_1000: "1000赛",
    no1Club_th_overall: "综合",
    no1Club_th_hard: "硬",
    no1Club_th_clay: "红",
    no1Club_th_grass: "草",
    no1Club_footer_wr_lbl: "胜率：",
    no1Club_footer_cols: "首次登顶 = 首次成为世界第一的年份  ·  最长连续 = 最长连续周数  ·  硬 = 硬地  ·  红 = 红土  ·  草 = 草地",
    no1Club_footer_gs_note: "大满贯从 1968 年起统计",
    no1Club_footer_1000_note: "WTA 千赛从 1990 年起统计",
    no1Club_footer_active: "现役球员",
    no1Club_no_data: "暂无数据",
    no1Club_th_age: "登顶年龄",
    no1Club_th_1st_date: "首次登顶",
    no1Club_th_1st_age: "首次年龄",
    no1Club_th_last_date: "最后登顶",
    no1Club_th_last_age: "最后年龄",

    /* ── draw · draw ────────────────────────────────────────── */
    draw_tab_hist:           "赛事历史",
    draw_tab_season:         "本赛季",
    draw_hist_suffix:        "历史成绩",
    draw_hist_matches:       "场比赛",
    draw_hist_winrate:       "胜率",
    draw_hist_win:           "胜",
    draw_hist_loss:          "负",
    draw_hist_round:         "轮次",
    draw_hist_result:        "胜负",
    draw_hist_opponent:      "对手",
    draw_hist_score:         "比分",
    draw_hist_close:         "关闭",
    draw_hist_loading:       "加载中...",
    draw_hist_no_data:       "未找到比赛数据。",
    draw_season_tournament:  "赛事",
    draw_season_no_data:     "未找到本赛季比赛数据。",
    draw_season_loading:     "加载中...",
    draw_search_placeholder: "搜索球员...",
    draw_interaction_hint:   "单击头像查看历史成绩 · 单击比分查看比赛数据",
    draw_dblclick_hint:      "单击查看历史",
    draw_failed_load:        "签表加载失败",
    draw_could_not_load:     "无法加载",
    draw_last_updated:       "更新时间",
    draw_view_match_stats:   "单击比分查看比赛数据",

    /* ── stats modal ── */
    stats_score:             "比分",
    stats_fg_title:          "正手/反手（合计）",
    stats_svc_title:         "发球",
    stats_ret_title:         "接发球",
    stats_pts_title:         "得分",
    stats_winners:           "制胜分",
    stats_forced_errors:     "被迫失误",
    stats_unforced_errors:   "主动失误",
    stats_aces:              "Aces",
    stats_double_faults:     "双误",
    stats_1st_serve_in:      "一发进球率",
    stats_1st_serve_won:     "一发得分率",
    stats_2nd_serve_won:     "二发得分率",
    stats_bp_saved:          "破发点挽回率",
    stats_svc_games_won:     "保发局率",
    stats_1st_return_won:    "接一发得分率",
    stats_2nd_return_won:    "接二发得分率",
    stats_bp_converted:      "破发成功率",
    stats_total_points:      "总得分",
    stats_serve_pts_won:     "发球得分率",
    stats_return_pts_won:    "接发得分率",
    stats_dominance:         "统治力指数",
  },
};

/* ================================================================
   语言切换引擎
================================================================ */

let currentLang =
  localStorage.getItem("lang") ||
  (navigator.language.startsWith("zh") ? "zh" : "en");

function t(key, ...args) {
  const val = i18n[currentLang]?.[key] ?? i18n["en"][key];
  return typeof val === "function" ? val(...args) : (val ?? key);
}

function applyLang(lang) {
  currentLang = lang;
  localStorage.setItem("lang", lang);
  document.documentElement.lang = lang;
  if (i18n[lang].page_title) document.title = i18n[lang].page_title;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = i18n[lang][key];
    if (val !== undefined && typeof val !== "function") el.textContent = val;
  });

  // 处理 data-i18n-opt（<option> 的文本）
  document.querySelectorAll("[data-i18n-opt]").forEach((el) => {
    const key = el.getAttribute("data-i18n-opt");
    const val = i18n[lang][key];
    if (val !== undefined && typeof val !== "function") el.textContent = val;
  });

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.textContent = i18n[lang].lang_toggle;
  });

  document.dispatchEvent(new CustomEvent("langchange", { detail: lang }));
}

document.addEventListener("DOMContentLoaded", () => applyLang(currentLang));
