export const IOC_TO_ISO2 = {
    "ARG": "AR", "AUS": "AU", "AUT": "AT", "BEL": "BE", "BLR": "BY",
    "BRA": "BR", "BUL": "BG", "CAN": "CA", "CHI": "CL", "CHN": "CN",
    "COL": "CO", "CRO": "HR", "CYP": "CY", "CZE": "CZ", "DEN": "DK",
    "ECU": "EC", "EGY": "EG", "ESP": "ES", "EST": "EE", "FIN": "FI",
    "FRA": "FR", "GBR": "GB", "GER": "DE", "GRE": "GR", "HUN": "HU",
    "IND": "IN", "IRL": "IE", "ISR": "IL", "ITA": "IT", "JPN": "JP",
    "KAZ": "KZ", "KOR": "KR", "LAT": "LV", "LTU": "LT", "LUX": "LU",
    "MAR": "MA", "MEX": "MX", "MDA": "MD", "MNE": "ME", "NED": "NL",
    "NZL": "NZ", "NOR": "NO", "PER": "PE", "POL": "PL", "POR": "PT",
    "ROU": "RO", "RSA": "ZA", "RUS": "RU", "SRB": "RS", "SVK": "SK",
    "SLO": "SI", "SWE": "SE", "SUI": "CH", "THA": "TH", "TUN": "TN",
    "TUR": "TR", "UKR": "UA", "URU": "UY", "USA": "US", "UZB": "UZ",
    "VEN": "VE", "ZIM": "ZW", "FRG": "DE", "URS": "RU", "INA": "ID",
    "TPE": "TW", "PUR": "PR", "PHI": "PH"
};

const missingIOCSet = new Set();

/* ================================================================ */
/*  Titles 配色 — 青碧四档                                            */
/*  1冠  浅薄荷绿  #d1fae5 / #065f46                                  */
/*  ≥2   中薄荷    #6ee7b7 / #064e3b                                  */
/*  ≥5   深青碧    #0f766e / #ccfbf1                                  */
/*  ≥10  墨绿      #134e4a / #f0fdfa                                  */
/* ================================================================ */

/** 当前格（截止年龄）用：无特殊着色，用黄字标注有冠军 */
export function titlesBg_cur(titles) {
    return 'transparent';
}
export function titlesFc_cur(titles) {
    return titles >= 1 ? '#b45309' : '#44403c';
}

/** 职业生涯总冠军数背景色（返回 inline style 用的颜色字符串） */
export function titlesBg(titles) {
    if (titles >= 10) return '#134e4a';
    if (titles >= 5)  return '#0f766e';
    if (titles >= 2)  return '#6ee7b7';
    if (titles >= 1)  return '#d1fae5';
    return 'transparent';
}

/** 职业生涯总冠军数文字色 */
export function titlesFc(titles) {
    if (titles >= 10) return '#f0fdfa';
    if (titles >= 5)  return '#ccfbf1';
    if (titles >= 2)  return '#064e3b';
    if (titles >= 1)  return '#065f46';
    return '#44403c';
}

/* ================================================================ */
/*  Winrate 配色 — 琥珀棕渐变                                         */
/*  ≥90%  深棕红   #7c2d12 / #fed7aa                                  */
/*  ≥85%  深琥珀   #b45309 / #fef3c7                                  */
/*  ≥80%  琥珀     #f59e0b / #fff                                     */
/*  ≥75%  金黄     #fde68a / #78350f                                  */
/*  ≥70%  浅黄     #fef9c3 / #713f12                                  */
/*  <70%  无色      — / #6b7280                                       */
/* ================================================================ */

/** AGG 综合胜率 — 实心深色块 */
export function aggBg(pct) {
    if (pct == null) return 'transparent';
    if (pct >= 90) return '#7c2d12';
    if (pct >= 85) return '#b45309';
    if (pct >= 80) return '#f59e0b';
    if (pct >= 75) return '#fde68a';
    if (pct >= 70) return '#fef9c3';
    return 'transparent';
}
export function aggColor(pct) {
    if (pct == null) return '#6b7280';
    if (pct >= 85) return '#fef3c7';
    if (pct >= 80) return '#ffffff';
    if (pct >= 75) return '#78350f';
    if (pct >= 70) return '#713f12';
    return '#6b7280';
}

/** 场地胜率 — 浅色 tint，主副层次 */
export function surfBg(pct) {
    if (pct == null) return 'transparent';
    if (pct >= 90) return '#ffedd5';
    if (pct >= 85) return '#ffedd5';
    if (pct >= 80) return '#fef3c7';
    if (pct >= 75) return '#fef9c3';
    if (pct >= 70) return '#fffbeb';
    return 'transparent';
}
export function surfColor(pct) {
    if (pct == null) return '#6b7280';
    if (pct >= 90) return '#7c2d12';
    if (pct >= 85) return '#9a3412';
    if (pct >= 80) return '#b45309';
    if (pct >= 75) return '#92400e';
    if (pct >= 70) return '#a16207';
    return '#6b7280';
}

/* ================================================================ */
/*  国旗图片                                                          */
/* ================================================================ */
export function getFlagImg(ioc) {
    const iso2 = IOC_TO_ISO2[ioc];
    if (!iso2) {
        if (!missingIOCSet.has(ioc)) {
            missingIOCSet.add(ioc);
            console.warn(
                `%c[FLAG MISSING] %cUnknown IOC: "${ioc}"%c\n👉 Please add it to IOC_TO_ISO2 map in utils.js`,
                'color: #b45309; font-weight: bold;',
                'color: #b91c1c; font-weight: bold;',
                'color: inherit;'
            );
        }
        return `<span title="Unknown IOC: ${ioc}" style="margin-right:6px; opacity:0.5;">🏳️</span>`;
    }
    const iso2Lower = iso2.toLowerCase();
    return `<img src="https://flagcdn.com/16x12/${iso2Lower}.png" width="16" height="12" alt="${iso2}" title="${iso2}" style="vertical-align:middle; margin-right:6px; border-radius:1px;">`;
}

/* ================================================================ */
/*  格式化函数                                                        */
/* ================================================================ */
export function fmtWinrate(val) {
    return val === null || val === undefined ? '—' : val + '%';
}

export function fmtAge(age) {
    return age === null || age === undefined ? '—' : age.toFixed(1);
}

export function fmtRound(round) {
    if (!round) return '<span class="result-other">—</span>';
    const upper = round.toUpperCase();
    if (upper === 'W')  return '<span class="slam-cell result-W">W</span>';
    if (upper === 'F')  return '<span class="slam-cell result-F">F</span>';
    if (upper === 'SF') return '<span class="slam-cell result-SF">SF</span>';
    if (upper === 'QF') return '<span class="slam-cell result-QF">QF</span>';
    return `<span class="result-other">${round}</span>`;
}

export function fmtBestRound(round, titles) {
    if (!round) return '<span class="result-other">—</span>';
    const upper = round.toUpperCase();
    if (upper === 'W') {
        const t = titles || 1;
        return `<span class="slam-cell result-W">W×${t}</span>`;
    }
    return fmtRound(round);
}

// 开发辅助：缺失 IOC 集合暴露到全局
if (typeof window !== 'undefined') {
    window.__missingIOCs = missingIOCSet;
}