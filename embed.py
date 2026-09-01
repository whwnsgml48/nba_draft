#!/usr/bin/env python3
"""console.src.html + data/players.min.json → console.html (단일 파일, 의존성 0).

  python3 embed.py

fetch()는 file:// 에서 CORS로 막히므로 데이터를 인라인으로 박아야 오프라인 단일 파일이 된다.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "console.src.html")
DATA = os.path.join(HERE, "data", "players.min.json")
OUT = os.path.join(HERE, "console.html")
TOKEN = "__PLAYERS_JSON__"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA, help="임베드할 players JSON")
    ap.add_argument("--out", default=OUT, help="출력 HTML")
    a = ap.parse_args()
    globals()["DATA"], globals()["OUT"] = a.data, a.out
    for p in (SRC, DATA):
        if not os.path.exists(p):
            sys.exit(f"없음: {p}  (players.min.json은 build_db.py로 생성)")

    src = open(SRC, encoding="utf-8").read()
    if TOKEN not in src:
        sys.exit(f"{TOKEN} 자리표시자가 템플릿에 없다")

    raw = open(DATA, encoding="utf-8").read()
    db = json.loads(raw)

    # </script> 가 데이터 안에 있으면 스크립트 블록이 조기 종료된다. 선수명에는 없지만 방어한다.
    payload = raw.replace("</", "<\\/")

    html = src.replace(TOKEN, payload)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"→ {OUT}  ({os.path.getsize(OUT):,} bytes)")
    print(f"  선수 {len(db['players'])}명 · "
          f"{db['league']['league']['teams']}팀 · ${db['league']['league']['budget']} · "
          f"로스터 {db['league']['league']['roster_slots']}명 "
          f"(총 {db['league']['league']['teams'] * db['league']['league']['roster_slots']}건)")
    print(f"  외부 요청 0건 확인: "
          f"{'PASS' if not any(t in html for t in ('http://', 'https://', 'fetch(', 'XMLHttpRequest')) else 'FAIL'}")


if __name__ == "__main__":
    main()
