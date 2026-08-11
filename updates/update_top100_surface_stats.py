"""
build_top100_surface_stats.py

Generates output/wta_top100_surface_stats.json from:
  - output/live-rank-top100-*.json              (Top 100 player list)
  - output/wta_calendar_champs_start_2009.json  (titles data)
  - tennis_wta/wta_matches_YYYY.csv             (match results 2009–current)

Run from the repo root:
  python build_top100_surface_stats.py
"""

import csv
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

OUTPUT_DIR  = "output"
MATCHES_DIR = "tennis_wta"
START_YEAR  = 2009

# Normalise tourney_level in champs JSON
CHAMPS_LEVEL_MAP = {
    "Grand Slam":    "grandSlam",
    "WTA 1000":      "wta1000",
    "WTA 500":       "wta500",
    "WTA 250":       "wta250",
    "Premier":       "wta500",       # legacy
    "International": "wta250",       # legacy
    "Finals":        "finals",       # split further below by tourney_name
    # ITF → omitted intentionally
}

# Normalise tourney_level in match CSVs
CSV_LEVEL_MAP = {
    "Grand Slam":         "grandSlam",
    "WTA1000":            "wta1000",
    "WTA500":             "wta500",
    "WTA250":             "wta250",
    "Premier Mandatory":  "wta1000",
    "Premier 5":          "wta1000",
    "Premier":            "wta500",
    "International":      "wta250",
}

VALID_SURFACES = {"Hard", "Clay", "Grass", "Carpet"}  # Carpet kept for champs data parsing
OUTPUT_SURFACES = ("Hard", "Clay", "Grass")  # Carpet excluded from surface stats output

# rank fullName  →  name used in CSV / champs
NAME_ALIASES = {
    # "Elena-Gabriela Ruse": "Elena Gabriela Ruse",
}

# Title category keys (used in both overall titles and per-surface titles)
TITLE_KEYS = ["grandSlam", "wta1000", "wta500", "wta250", "finals", "yearEndFinals"]

def empty_title_counts():
    return {k: 0 for k in TITLE_KEYS}

def empty_surface_record():
    return {
        "w": 0, "l": 0, "total": 0, "pct": None,
        "titles": empty_title_counts(),
    }

# ─── Helpers ──────────────────────────────────────────────────────────────────

def canonical(name):
    return NAME_ALIASES.get(name, name)

def find_rank_file():
    pattern = os.path.join(OUTPUT_DIR, "live-rank-top100*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No rank file found: {pattern}")
    return files[-1]

def load_top100(rank_file):
    with open(rank_file, encoding="utf-8") as f:
        data = json.load(f)
    return [{
        "rank":          e["ranking"],
        "fullName":      e["player"]["fullName"],
        "canonicalName": canonical(e["player"]["fullName"]),
        "countryCode":   e["player"]["countryCode"],
        "dateOfBirth":   e["player"]["dateOfBirth"],
        "points":        e["points"],
    } for e in data]

# ─── Titles ───────────────────────────────────────────────────────────────────

def load_titles(champs_file, player_set, year=None):
    """
    Returns two dicts, both keyed by canonicalName:
      overall_titles[name]  → {grandSlam, wta1000, wta500, wta250, finals, yearEndFinals, total}
      surface_titles[name][surface] → {grandSlam, wta1000, wta500, wta250, finals, yearEndFinals}
    If year is provided, only entries matching that year are included.
    """
    with open(champs_file, encoding="utf-8") as f:
        data = json.load(f)["data"]

    overall = defaultdict(empty_title_counts)
    by_surface = defaultdict(lambda: defaultdict(empty_title_counts))

    for entry in data:
        # Filter by year if specified
        entry_year = entry.get("year")
        if year is not None and entry_year != year:
            continue

        winner = entry.get("winner", "").strip()
        if not winner or winner not in player_set:
            continue

        level_raw = entry.get("tourney_level", "")
        level_key = CHAMPS_LEVEL_MAP.get(level_raw)
        if level_key is None:
            continue  # ITF or unknown

        surface = entry.get("surface", "").strip().capitalize()
        if surface not in VALID_SURFACES:
            surface = "Hard"  # fallback (shouldn't happen)

        # Distinguish year-end finals from elite trophies (small year-end)
        if level_key == "finals":
            if entry.get("tourney_name", "").strip() == "Wta Finals":
                actual_key = "yearEndFinals"
            else:
                actual_key = "finals"   # small year-end (Zhuhai, Sofia, etc.)
        else:
            actual_key = level_key

        overall[winner][actual_key] += 1
        by_surface[winner][surface][actual_key] += 1

    # Add total to each overall dict
    for name in overall:
        overall[name]["total"] = sum(
            overall[name][k] for k in TITLE_KEYS
        )

    return overall, by_surface

# ─── Win / Loss by surface ────────────────────────────────────────────────────

def load_surface_records(matches_dir, player_set, year=None):
    """Returns {canonicalName: {surface: {"w": int, "l": int}}}.
    If year is provided, only matches from that year are included.
    """
    records = defaultdict(lambda: defaultdict(lambda: {"w": 0, "l": 0}))

    for fpath in sorted(glob.glob(os.path.join(matches_dir, "wta_matches_*.csv"))):
        m = re.search(r"(\d{4})", os.path.basename(fpath))
        if not m:
            continue
        file_year = int(m.group(1))
        if year is not None and file_year != year:
            continue
        if file_year < START_YEAR:
            continue

        with open(fpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if "W/O" in row.get("score", ""):
                    continue
                surface = row.get("surface", "").strip().capitalize()
                if surface not in VALID_SURFACES:
                    continue
                winner = row.get("winner_name", "").strip()
                loser  = row.get("loser_name",  "").strip()
                if winner in player_set:
                    records[winner][surface]["w"] += 1
                if loser in player_set:
                    records[loser][surface]["l"] += 1

    return records

# ─── Win / Loss vs Top 8 (opponent's rank at time of match) ──────────────────

TOP8_RANK_THRESHOLD = 8

def load_vs_top8_records(matches_dir, player_set, year=None):
    """
    Returns {canonicalName: {"w": int, "l": int}} counting only matches where
    the OPPONENT's ranking at the time of the match was <= TOP8_RANK_THRESHOLD.
    Rows with missing/unparseable rank values are skipped (can't be verified).
    If year is provided, only matches from that year are included.
    """
    records = defaultdict(lambda: {"w": 0, "l": 0})

    def parse_rank(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    for fpath in sorted(glob.glob(os.path.join(matches_dir, "wta_matches_*.csv"))):
        m = re.search(r"(\d{4})", os.path.basename(fpath))
        if not m:
            continue
        file_year = int(m.group(1))
        if year is not None and file_year != year:
            continue
        if file_year < START_YEAR:
            continue

        with open(fpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if "W/O" in row.get("score", ""):
                    continue
                winner = row.get("winner_name", "").strip()
                loser  = row.get("loser_name",  "").strip()

                loser_rank  = parse_rank(row.get("loser_rank"))
                winner_rank = parse_rank(row.get("winner_rank"))

                if winner in player_set and loser_rank is not None and loser_rank <= TOP8_RANK_THRESHOLD:
                    records[winner]["w"] += 1
                if loser in player_set and winner_rank is not None and winner_rank <= TOP8_RANK_THRESHOLD:
                    records[loser]["l"] += 1

    return records

# ─── Player statistic builder ──────────────────────────────────────────────

def build_player_stat(player, overall_titles, surface_titles, records, vs_top8_records):
    """
    Build a complete statistic object for a single player from given data sources.
    Returns dict with keys: titles, surface, overall, vsTop8
    """
    cname = player["canonicalName"]
    ot = overall_titles.get(cname, {**empty_title_counts(), "total": 0})

    surface_stats = {}
    for surf in OUTPUT_SURFACES:
        rec = records.get(cname, {}).get(surf, {"w": 0, "l": 0})
        w, l = rec["w"], rec["l"]
        total = w + l
        st = surface_titles.get(cname, {}).get(surf, empty_title_counts())
        surface_stats[surf] = {
            "w":     w,
            "l":     l,
            "total": total,
            "pct":   round(w / total * 100, 1) if total > 0 else None,
            "titles": {k: st.get(k, 0) for k in TITLE_KEYS},
        }

    all_w = sum(surface_stats[s]["w"] for s in surface_stats)
    all_l = sum(surface_stats[s]["l"] for s in surface_stats)
    all_t = all_w + all_l

    vt8 = vs_top8_records.get(cname, {"w": 0, "l": 0})
    vt8_w, vt8_l = vt8["w"], vt8["l"]
    vt8_total = vt8_w + vt8_l

    return {
        "titles": {
            "total":        ot.get("total", 0),
            "grandSlam":    ot.get("grandSlam", 0),
            "wta1000":      ot.get("wta1000", 0),
            "wta500":       ot.get("wta500", 0),
            "wta250":       ot.get("wta250", 0),
            "finals":       ot.get("finals", 0),        # small year-end
            "yearEndFinals": ot.get("yearEndFinals", 0), # Wta Finals
        },
        "surface": surface_stats,
        "overall": {
            "w":    all_w,
            "l":    all_l,
            "total": all_t,
            "pct":  round(all_w / all_t * 100, 1) if all_t > 0 else None,
        },
        "vsTop8": {
            "w":     vt8_w,
            "l":     vt8_l,
            "total": vt8_total,
            "pct":   round(vt8_w / vt8_total * 100, 1) if vt8_total > 0 else None,
        },
    }

# ─── Assemble ─────────────────────────────────────────────────────────────────

def build_stats():
    rank_file   = find_rank_file()
    champs_file = os.path.join(OUTPUT_DIR, "wta_calendar_champs_start_2009.json")

    print(f"Rank file  : {rank_file}")
    print(f"Champs file: {champs_file}")

    players    = load_top100(rank_file)
    player_set = {p["canonicalName"] for p in players}

    # Determine current season
    current_year = datetime.now().year
    print(f"Current season year: {current_year}")

    # --- Career data ---
    overall_titles_career, surface_titles_career = load_titles(champs_file, player_set, year=None)
    records_career = load_surface_records(MATCHES_DIR, player_set, year=None)
    vs_top8_career = load_vs_top8_records(MATCHES_DIR, player_set, year=None)

    # --- Season data ---
    overall_titles_season, surface_titles_season = load_titles(champs_file, player_set, year=current_year)
    records_season = load_surface_records(MATCHES_DIR, player_set, year=current_year)
    vs_top8_season = load_vs_top8_records(MATCHES_DIR, player_set, year=current_year)

    output = []
    for p in players:
        career = build_player_stat(p,
                                   overall_titles_career,
                                   surface_titles_career,
                                   records_career,
                                   vs_top8_career)
        season = build_player_stat(p,
                                   overall_titles_season,
                                   surface_titles_season,
                                   records_season,
                                   vs_top8_season)

        output.append({
            "rank":        p["rank"],
            "fullName":    p["fullName"],
            "countryCode": p["countryCode"],
            "dateOfBirth": p["dateOfBirth"],
            "points":      p["points"],
            "career":      career,
            "season":      season,
        })

    return output

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    stats = build_stats()

    out_path = os.path.join(OUTPUT_DIR, "wta_top100_surface_stats.json")
    with open(out_path, "w", encoding="utf-8") as f:
        import time
        json.dump({"generated_at": int(time.time()), "data": stats},
                  f, ensure_ascii=False, indent=2)

    print(f"\nOutput → {out_path}  ({len(stats)} records)")