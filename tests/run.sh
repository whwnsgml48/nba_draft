#!/bin/sh
# 전체 검증 — 데이터 빌드 → 임베드 → 로직/렌더/불변식/순서/호가/사용법/타수 → 리허설
set -e
cd "$(dirname "$0")/.."

echo "═══ 실전 빌드 (14팀 × 9인) ═══"
python3 build_db.py
echo
python3 embed.py
echo
for t in p1 render board p2 order p3 help offline keystrokes; do node "tests/$t.mjs"; echo; done

echo "═══ 리허설 빌드 (12팀 × 10인 — 작년 규격) ═══"
python3 build_db.py --teams 12 --slots 10 --seed-from-prior \
  --out data/players.rehearsal.json --report data/build_report.rehearsal.json
echo
python3 embed.py --data data/players.rehearsal.json --out console.rehearsal.html
echo
node tests/rehearsal.mjs
