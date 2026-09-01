#!/usr/bin/env python3
"""선수 DB 빌드 — console.html에 임베드할 players.min.json 생성.

의존성 0 (stdlib만). 네트워크 접근 없음. 소스는 모두 로컬 파일.

  python3 build_db.py [--src ../nba_fantasy_auction_2026] [--out data/players.min.json]

RENEWAL.md 3절 참조. 우선순위:
  스탯  measured_full(혼합) > 2025-26 > 2024-25 > manual(루키)
  팀    players.json(큐레이션) > player_lines(2026-27) > BBRef(2TM류는 미상 처리)
  포지션 pos_yahoo > players.json pos > BBRef pos  (문자열은 야후 슬롯으로 전개)
"""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter

# results.csv / players.json 표기 → BBRef 표준 표기.
# BBRef가 약칭을 쓰는 소수 케이스만 수동 교정한다.
NAME_FIX = {
    "Alexandre Sarr": "Alex Sarr",
}

# 2026 드래프트 상위 3인 — 2025-26 NBA 실적이 없어 어떤 스탯 소스에도 없다.
# players.json의 시장가만 갖고 수동 등재한다.
ROOKIE_NAMES = ["AJ Dybantsa", "Darryn Peterson", "Cameron Boozer"]

MULTI_TEAM = {"2TM", "3TM", "4TM", "5TM"}

# 포지션 문자열 → 야후 슬롯 자격. players.json은 'F/C' 'G' 같은 묶음 표기를 쓰고
# BBRef는 단일 표기를 쓴다. pos_yahoo가 있으면 그것이 최우선.
POS_EXPAND = {
    "PG": ["PG"], "SG": ["SG"], "SF": ["SF"], "PF": ["PF"], "C": ["C"],
    "G": ["PG", "SG"], "F": ["SF", "PF"],
    "G/F": ["SG", "SF"], "F/G": ["SG", "SF"],
    "F/C": ["PF", "C"], "C/F": ["PF", "C"],
    "PG/SG": ["PG", "SG"], "SG/SF": ["SG", "SF"], "SF/PF": ["SF", "PF"],
    "PF/C": ["PF", "C"],
}

STAT_KEYS = ["GP", "MPG", "PTS", "REB", "OREB", "AST", "STL", "BLK", "TOV",
             "FG%", "3PM", "3P%", "FT%", "A/T"]


def fold(s):
    """표기 차이를 흡수하는 조인 키. 발음기호·마침표·아포스트로피·접미사 제거."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", "").replace("'", "").replace("’", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def canon(name):
    return fold(NAME_FIX.get(name, name))


def num(v, default=None):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("name", "").strip() != "League Average"]


def stats_from_bbref(row):
    out = {}
    for k in STAT_KEYS:
        out[k] = num(row.get(k))
    return out


def stats_from_measured(m):
    out = {}
    for k in STAT_KEYS:
        out[k] = num(m.get(k))
    return out


def expand_pos(raw, yahoo):
    if yahoo:
        return list(yahoo)
    if not raw:
        return []
    raw = raw.strip()
    if raw in POS_EXPAND:
        return POS_EXPAND[raw]
    # 'PG,SG' 'G-F' 등 미등록 조합은 토큰 단위로 전개
    slots = []
    for tok in re.split(r"[/,\-\s]+", raw):
        for s in POS_EXPAND.get(tok.strip().upper(), []):
            if s not in slots:
                slots.append(s)
    return slots


def statline(s):
    """검색 결과 한 줄에 들어가는 압축 표시 — 동명이인·동성 선수 구분용."""
    if s.get("PTS") is None:
        return ""
    def f(v, d=1):
        return "-" if v is None else f"{v:.{d}f}"
    return f"{f(s['PTS'])}/{f(s['REB'])}/{f(s['AST'])}"


# 리그 13캣 순서 (league_settings.json categories) 에 MPG·GP 를 덧붙인 표시용 블록.
# 커미셔너 화면에 성적을 실제로 보여주려면 압축 3개로는 부족하다.
def statblock(s, m):
    def r(v, d=1):
        return None if v is None else round(v, d)
    at = s.get("A/T")
    if at is None and s.get("AST") is not None and s.get("TOV"):
        at = s["AST"] / s["TOV"]
    return {
        "PTS": r(s.get("PTS")), "REB": r(s.get("REB")), "OREB": r(s.get("OREB")),
        "AST": r(s.get("AST")), "STL": r(s.get("STL")), "BLK": r(s.get("BLK")),
        "TOV": r(s.get("TOV")), "3PM": r(s.get("3PM")),
        "FG": r(s.get("FG%"), 3), "3P": r(s.get("3P%"), 3), "FT": r(s.get("FT%"), 3),
        "AT": r(at, 2),
        "DD": r((m or {}).get("DD_est_season"), 0),   # 시즌 더블더블 추정 (실측 171명만)
        "MPG": r(s.get("MPG")), "GP": r(s.get("GP")),
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(here, "..", "nba_fantasy_auction_2026"),
                    help="nba_fantasy_auction_2026 저장소 경로")
    ap.add_argument("--out", default=os.path.join(here, "data", "players.min.json"))
    ap.add_argument("--report", default=os.path.join(here, "data", "build_report.json"))
    # 리허설용 규격 오버라이드. 작년은 12팀×10인, 올해는 14팀×9인이라 작년 데이터를
    # 그대로 재입력하려면 규격을 맞춰야 한다. 실전 산출물은 건드리지 않는다.
    ap.add_argument("--teams", type=int, help="팀 수 오버라이드 (리허설)")
    ap.add_argument("--slots", type=int, help="로스터 슬롯 오버라이드 (리허설)")
    ap.add_argument("--seed-from-prior", action="store_true",
                    help="팀 시드를 작년 옥션 결과의 참가자로 대체 (리허설)")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    D = os.path.join(src, "data")
    B = os.path.join(D, "stats_2025_26", "bbref")
    need = {
        "cur": os.path.join(B, "2025-26_per_game.csv"),
        "prev": os.path.join(B, "2024-25_per_game.csv"),
        "measured": os.path.join(D, "stats_2025_26", "measured_full.json"),
        "pool": os.path.join(D, "players.json"),
        "prior": os.path.join(D, "prior_auction_2025_26", "results.csv"),
        "lines": os.path.join(D, "stats_2025_26", "player_lines.csv"),
        "league": os.path.join(D, "league_settings.json"),
    }
    extra_path = os.path.join(here, "data", "aliases_extra.json")
    missing = [f"{k}: {v}" for k, v in need.items() if not os.path.exists(v)]
    if missing:
        sys.exit("소스 파일 없음:\n  " + "\n  ".join(missing))

    cur = {fold(r["name"]): r for r in read_csv(need["cur"])}
    prev = {fold(r["name"]): r for r in read_csv(need["prev"])}
    lines = {fold(r["player"]): r for r in csv.DictReader(open(need["lines"], encoding="utf-8"))}
    measured = json.load(open(need["measured"], encoding="utf-8"))["players"]
    measured = {canon(k): v for k, v in measured.items()}
    pool = {canon(p["name"]): p for p in json.load(open(need["pool"], encoding="utf-8"))}
    prior_rows = list(csv.DictReader(open(need["prior"], encoding="utf-8")))
    league = json.load(open(need["league"], encoding="utf-8"))
    if args.teams:
        league["league"]["teams"] = args.teams
    if args.slots:
        league["league"]["roster_slots"] = args.slots
    NTEAM_EXPECT = league["league"]["teams"]
    REHEARSAL = bool(args.teams or args.slots or args.seed_from_prior)

    # 한글 별칭 + 작년 낙찰가
    aliases, prior_price, alias_miss = {}, {}, []
    for r in prior_rows:
        k = canon(r["name_en"])
        if k not in cur and k not in prev and k not in pool:
            alias_miss.append(r)
            continue
        aliases.setdefault(k, []).append(r["name_kr"].strip())
        prior_price[k] = int(r["price"])

    # 보강 별칭 (data/aliases_extra.json) — 작년 미지명 선수는 results.csv에 별칭이 없다
    extra_n, extra_miss = 0, []
    if os.path.exists(extra_path):
        for name, ent in json.load(open(extra_path, encoding="utf-8")).items():
            if name.startswith("_"):
                continue
            k = canon(name)
            if k not in cur and k not in prev and k not in pool:
                extra_miss.append(name)
                continue
            for a in ent["kr"]:
                if a not in aliases.setdefault(k, []):
                    aliases[k].append(a)
                    extra_n += 1

    # players.json이 이미 병합해 둔 작년가도 흡수 (results.csv 미수록 보강)
    for k, p in pool.items():
        if p.get("prior_auction_price") and k not in prior_price:
            prior_price[k] = int(p["prior_auction_price"])

    keys = set(cur) | set(prev) | set(pool)
    for n in ROOKIE_NAMES:
        keys.add(canon(n))

    players, prov = [], Counter()
    in_pool = []          # 검증 전용 — 출력 레코드에는 넣지 않는다
    for k in sorted(keys):
        p = pool.get(k)
        c, v = cur.get(k), prev.get(k)
        m = measured.get(k)

        # 표시 이름: 큐레이션 풀 > BBRef.
        #   결과 CSV 가 차년도 캘리브레이션으로 들어가고, 그쪽은 players.json 과
        #   `NFKD → ascii → lower` 로 조인한다. 그 정규화는 발음기호는 접지만
        #   **접미사는 접지 않는다** — BBRef 'Jimmy Butler' vs 풀 'Jimmy Butler III' 는
        #   조인이 조용히 실패한다. 소비자가 쓰는 표기를 정본으로 삼는다.
        name = (p or {}).get("name") or (c or v or {}).get("name")
        if not name:
            continue

        # 스탯
        if m:
            s, ssrc = stats_from_measured(m), "blend"
        elif c:
            s, ssrc = stats_from_bbref(c), "2025-26"
        elif v:
            s, ssrc = stats_from_bbref(v), "2024-25"
        else:
            s, ssrc = {kk: None for kk in STAT_KEYS}, "manual"
        prov[ssrc] += 1

        # 팀 (2026-27 기준으로 가장 신뢰할 수 있는 값)
        team, tsrc = None, None
        if p and p.get("team"):
            team, tsrc = p["team"], "pool"
        elif k in lines and lines[k].get("team_2026_27"):
            team, tsrc = lines[k]["team_2026_27"], "lines"
        else:
            raw = (c or v or {}).get("team", "")
            if raw and raw not in MULTI_TEAM:
                team, tsrc = raw, "bbref"
            else:
                team, tsrc = None, "unknown"

        # 포지션
        yahoo = (p or {}).get("pos_yahoo")
        raw_pos = (p or {}).get("pos") or (c or v or {}).get("pos") or ""
        slots = expand_pos(raw_pos, yahoo)
        psrc = "yahoo" if yahoo else ("pool" if (p or {}).get("pos") else "bbref")

        # 검색 랭킹 가중치 — 지명될 확률 순으로 3계층.
        # 출장시간으로 정렬하면 풀 안에서 Camara가 Jokić 위로 올라간다. 값은 가격이 정한다.
        gp, mpg = s.get("GP") or 0, s.get("MPG") or 0
        ly = prior_price.get(k)
        if p and p.get("market_high") is not None:
            w = 1_000_000 + p["market_high"] * 1000          # 올해 시장가 풀 174명
        elif ly is not None:
            w = 500_000 + ly * 1000                          # 작년 낙찰 이력만 있는 선수
        else:
            w = round(gp * mpg, 1)                           # 나머지는 출장 부하 순

        rec = {
            "n": name,
            "t": team,
            "pos": slots,
            "pos_raw": raw_pos or None,
            "kr": aliases.get(k, []),
            "line": statline(s),
            "st": statblock(s, m),
            "gp": None if s.get("GP") is None else round(s["GP"], 1),
            "w": w,
            "src": {"stat": ssrc, "team": tsrc, "pos": psrc},
        }
        if ssrc == "manual":
            rec["line"] = "2026 신인"
        if ly is not None:
            rec["ly"] = ly            # 작년 낙찰가는 리그 공유 사실 — 유지한다
        # ── 여기서 시장가·my_max·tag·부상제외 플래그를 의도적으로 버린다 ──
        # 전부 사용자의 사적 판단이고, 이 툴은 커미셔너(타인일 수 있음)에게 파일째로
        # 넘어간다. RENEWAL 0절 경계는 UI가 아니라 데이터 층에서 지켜야 한다.
        players.append(rec)
        in_pool.append(bool(p))

    order = sorted(range(len(players)), key=lambda j: (-players[j]["w"], players[j]["n"]))
    players = [players[j] for j in order]
    in_pool = [in_pool[j] for j in order]
    # w 에는 market_high 가 그대로 복원 가능한 형태로 들어 있다(1_000_000 + mh*1000).
    # 검색 랭킹에 필요한 것은 순서뿐이므로 서수로 바꿔 금액을 지운다.
    for rank, r in enumerate(players):
        del r["w"]
        r["rk"] = rank

    # 팀명 시드 — data/teams.json 이 정본. state.json(Streamlit 잔재)은 P5에서 삭제되므로
    # 거기에 의존하지 않는다. 파일이 없을 때만 구 상태파일로 폴백한다.
    seed_teams = []
    if args.seed_from_prior:
        seen = []
        for r in prior_rows:
            if r["manager"] not in seen:
                seen.append(r["manager"])
        seed_teams = seen
    tfile = os.path.join(here, "data", "teams.json")
    if seed_teams:
        pass
    elif os.path.exists(tfile):
        seed_teams = [t for t in json.load(open(tfile, encoding="utf-8"))["teams"] if t.strip()]
    else:
        state = os.path.join(here, "data", "state.json")
        if os.path.exists(state):
            seed_teams = list(json.load(open(state, encoding="utf-8")).get("teams", {}))

    out = {
        "meta": {
            "built_by": "build_db.py",
            "src_repo": src,
            "players": len(players),
            "pool_players": len(pool),
            "aliases": sum(1 for r in players if r["kr"]),
            "aliases_prior": len(prior_rows),
            "aliases_extra": extra_n,
            "stat_provenance": dict(prov),
            # 이 note 는 산출물에 실려 커미셔너에게 전달된다. 사적 도구·전략의
            # 존재를 언급하지 않는다.
            "note": "옥션 진행 장부용 최소 DB. 리그 공유 사실만 담는다 — "
                    "이름·팀·포지션·13캣 성적·작년 낙찰가.",
        },
        "league": league,
        # 2026-09-01 사용자 확정: 지명은 순번 로테이션. 형제 저장소의
        # league_settings.json 은 "직전 낙찰자"로 남아 있으므로 여기서 덮어쓴다.
        "rules_override": {
            "nomination": "round_robin",
            "nomination_order": seed_teams,
            "changed": "2026-09-01",
            "was": league["auction_rules"]["nominator"],
        },
        "seed_teams": seed_teams,
        "players": players,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    # ---- P0 인수 조건 검증 ----
    checks = []
    checks.append(("2025-26 CSV 로드 583행(헤더+League Average 제외 582명)",
                   len(cur) == 582, f"{len(cur)}명"))
    checks.append(("합집합 풀 ≥ 680명", len(players) >= 680, f"{len(players)}명"))
    checks.append(("별칭 120건 히트율 100%", len(alias_miss) == 0,
                   f"실패 {len(alias_miss)}건" + (f" {[r['name_en'] for r in alias_miss]}" if alias_miss else "")))
    checks.append((f"큐레이션 풀 {len(pool)}명 전원 등재",
                   sum(in_pool) == len(pool), f"{sum(in_pool)}/{len(pool)}"))
    checks.append(("풀 선수가 검색 랭킹 상단 점유",
                   all(in_pool[:len(pool)]),
                   f"상단 {len(pool)}위 중 풀 {sum(in_pool[:len(pool)])}명"))
    if REHEARSAL:
        print(f"  ⚠ 리허설 빌드 — {NTEAM_EXPECT}팀 × {league['league']['roster_slots']}인 "
              f"(실전은 teams.json / league_settings.json 기준)")
    checks.append((f"팀 시드 {NTEAM_EXPECT}명 전원 확정",
                   len(seed_teams) == NTEAM_EXPECT and all(seed_teams),
                   f"{len(seed_teams)}명 {seed_teams}"))
    checks.append(("루키 3명 등재",
                   all(any(r["n"] == n for r in players) for n in ROOKIE_NAMES), ""))
    checks.append(("보강 별칭 전원 매칭", not extra_miss,
                   f"실패 {len(extra_miss)}건 {extra_miss}" if extra_miss else ""))
    have_pts = sum(1 for r in players if r["st"]["PTS"] is not None)
    checks.append(("PTS 실적 보유 = 전체 − 신인 3명",
                   have_pts == len(players) - len(ROOKIE_NAMES),
                   f"{have_pts}/{len(players)}"))
    # A/T 는 TOV=0 이면 정의되지 않는다 (GP 6~7 소표본이 per-game 반올림으로 0.0 이 되는 경우).
    # 따라서 "전원 보유"가 아니라 "TOV>0 인 전원 보유"가 옳은 불변식이다.
    at_gap = [r["n"] for r in players if (r["st"]["TOV"] or 0) > 0 and r["st"]["AT"] is None]
    checks.append(("A/T 산출 (TOV>0 전원)", not at_gap,
                   f"누락 {len(at_gap)}명 {at_gap[:5]}" if at_gap else
                   f"{sum(1 for r in players if r['st']['AT'] is not None)}명 산출 · "
                   f"TOV=0 으로 정의불가 {sum(1 for r in players if (r['st']['TOV'] or 0)==0 and r['st']['TOV'] is not None)}명"))
    PRIVATE = ("ml", "mh", "mymax", "tag", "inj", "w", "my_max", "market_low",
               "market_high", "surplus", "obtainable", "verdict")
    leaked = sorted({k for r in players for k in r if k in PRIVATE})
    # 큐레이션 풀 선수의 표시 이름이 players.json 과 정확히 일치해야 한다 (조인 안전)
    pool_names = {p["name"] for p in pool.values()}
    have = {r["n"] for r in players}
    name_gap = sorted(pool_names - have)
    checks.append(("풀 선수 표시명이 players.json 과 정확히 일치", not name_gap,
                   f"불일치 {len(name_gap)}명 {name_gap[:5]}" if name_gap else f"{len(pool_names)}명"))
    checks.append(("사적 판단 필드 유출 0건 (시장가·my_max·tag)", not leaked, f"유출 {leaked}"))
    checks.append(("포지션 자격 미상 0명",
                   all(r["pos"] for r in players),
                   f"미상 {sum(1 for r in players if not r['pos'])}명"))

    report = {
        "out": args.out,
        "bytes": os.path.getsize(args.out),
        "counts": {
            "players": len(players), "aliases": out["meta"]["aliases"],
            "market_pool": sum(in_pool),
            "prior_price": sum(1 for r in players if "ly" in r),
            "team_unknown": sum(1 for r in players if r["t"] is None),
            "pos_unknown": sum(1 for r in players if not r["pos"]),
        },
        "stat_provenance": dict(prov),
        "alias_miss": [{"kr": r["name_kr"], "en": r["name_en"]} for r in alias_miss],
        "alias_extra_miss": extra_miss,
        "checks": [{"name": n, "pass": bool(ok), "detail": d} for n, ok, d in checks],
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print(f"→ {args.out}  ({report['bytes']:,} bytes)")
    print(f"  선수 {len(players)}명 · 별칭 {out['meta']['aliases']}명 · "
          f"큐레이션 풀 {report['counts']['market_pool']}명 · 작년가 {report['counts']['prior_price']}명")
    print(f"  사적 판단 필드(시장가·my_max·tag): 미포함")
    print(f"  스탯 출처 {dict(prov)}")
    print(f"  팀 미상 {report['counts']['team_unknown']}명 · 포지션 미상 {report['counts']['pos_unknown']}명")
    print()
    for n, ok, d in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  ({d})" if d else ""))
    failed = [n for n, ok, _ in checks if not ok]
    if failed:
        print(f"\nP0 인수 조건 미충족 {len(failed)}건")
        return 1
    print("\nP0 인수 조건 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
