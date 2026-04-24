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

export function titlesBg_cur(titles) {
    // if (titles >= 1) return '#83c14d';
    return 'transparent';
  }
  
export function titlesFc_cur(titles) {
    return titles >= 1 ? '#f5c842' : '#e5e5e5';
  }

export function titlesBg(titles) {
    if (titles >= 10) return '#B8860B';
    if (titles >= 5) return '#2E8B57';
    if (titles >= 2) return '#4682B4';
    return 'transparent';
  }
  
export function titlesFc(titles) {
    return titles >= 2 ? '#111111' : '#e5e5e5';
  }

export function getFlagImg(ioc) {
  const iso2 = IOC_TO_ISO2[ioc];
  
  if (!iso2) {
    if (!missingIOCSet.has(ioc)) {
      missingIOCSet.add(ioc);
      console.warn(
        `%c[FLAG MISSING] %cUnknown IOC: "${ioc}"%c\n👉 Please add it to IOC_TO_ISO2 map in utils.js`,
        'color: #f5c842; font-weight: bold;',
        'color: #ff6b6b; font-weight: bold;',
        'color: inherit;'
      );
    }
    return `<span title="Unknown IOC: ${ioc}" style="margin-right:6px; opacity:0.7;">🏳️</span>`;
  }
  
  const iso2Lower = iso2.toLowerCase();
  return `<img src="https://flagcdn.com/16x12/${iso2Lower}.png" width="16" height="12" alt="${iso2}" title="${iso2}" style="vertical-align:middle; margin-right:6px; border-radius:1px;">`;
}

export function fmtWinrate(val) {
  return val === null || val === undefined ? "—" : val + "%";
}

export function fmtAge(age) {
  return age === null || age === undefined ? "—" : age.toFixed(1);
}

export function fmtRound(round) {
  if (!round) return '<span class="result-other">—</span>';
  const upper = round.toUpperCase();
  if (upper === "W") return '<span class="slam-cell result-W">W</span>';
  if (upper === "F") return '<span class="slam-cell result-F">F</span>';
  if (upper === "SF") return '<span class="slam-cell result-SF">SF</span>';
  if (upper === "QF") return '<span class="slam-cell result-QF">QF</span>';
  return `<span class="result-other">${round}</span>`;
}

export function fmtBestRound(round, titles) {
  if (!round) return '<span class="result-other">—</span>';
  const upper = round.toUpperCase();
  if (upper === "W") {
    const t = titles || 1;
    return `<span class="slam-cell result-W">W×${t}</span>`;
  }
  // 其余情况直接复用原有的 fmtRound
  return fmtRound(round);
}

// 开发辅助：将缺失集合暴露到全局（可选）
if (typeof window !== 'undefined') {
  window.__missingIOCs = missingIOCSet;
}

