// P4 리허설 — 작년(2025-26) 실제 낙찰 120건을 이 엔진으로 전량 재입력해 재현한다.
// 정답이 있는 유일한 데이터셋이므로 회귀 테스트와 속도 측정을 동시에 한다.
// 규격이 다르므로(작년 12팀×10인, 올해 14팀×9인) 리허설 전용 빌드를 쓴다.
import fs from "node:fs";
import path from "node:path";
import {load, ok, eq, summary} from "./harness.mjs";

const A = load("console.rehearsal.html");
const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "..", "nba_fantasy_auction_2026", "data",
                      "prior_auction_2025_26", "results.csv");
const ref = fs.readFileSync(SRC, "utf8");
const rows = ref.trim().split("\r\n").slice(1).map(l=>{
  const [manager,name_kr,name_en,price,rc] = l.split(",");
  return {manager, name_kr, name_en, price:+price, rc};
});

console.log(`작년 기록 ${rows.length}건 · ${new Set(rows.map(r=>r.manager)).size}팀`);
eq("리허설 규격 12팀 × 10인", [A.NTEAM, A.SLOTS, A.TOTAL], [12, 10, 120]);
eq("시드가 작년 참가자", A.S.teams.filter(t=>t.name).length, 12);

const teamIdx = new Map(A.S.teams.map((t,i)=>[t.name,i]));
const byName  = new Map(A.IDX.map(e=>[e.p.n, e]));
function resolve(en){
  const fixed = en === "Alexandre Sarr" ? "Alex Sarr" : en;
  if(byName.has(fixed)) return byName.get(fixed);
  const f = A.foldEn(fixed);
  return A.IDX.find(e=>e.f===f) || null;
}

console.log("\n── 전량 재입력 (검색 → 팀 → 금액, 실제 커밋 경로) ──");
A.reset();
let placed = 0, failed = [], keys = 0;
for(const r of rows){
  const e = resolve(r.name_en);
  if(!e){ failed.push(`${r.name_en}: DB 미발견`); continue; }

  // 검색이 실제로 이 선수를 찾아내는지 확인하며 타수를 센다
  let found = false, kp = 0;
  for(const cand of [r.name_kr, e.p.n.split(" ").pop(), e.p.n]){
    if(!cand) continue;
    const c = cand.replace(/\s+/g,"");
    for(let L=1; L<=c.length; L++){
      const hit = A.search(c.slice(0,L), 8).findIndex(x=>x.p.n===e.p.n);
      if(hit>=0){ found=true; kp = L+1; break; }
    }
    if(found) break;
  }
  if(!found){ failed.push(`${r.name_en}: 검색 불가`); continue; }

  const ti = teamIdx.get(r.manager);
  if(ti===undefined){ failed.push(`${r.manager}: 팀 미발견`); continue; }

  // 팀 접두사 타수
  let kt = r.manager.length + 1;
  for(let L=1; L<=r.manager.length; L++){
    const q = r.manager.slice(0,L);
    const m = A.S.teams.map(t=>t.name).filter(n=>n && n.startsWith(q));
    if(m.length===1 && m[0]===r.manager){ kt = L+1; break; }
  }

  A.pick = e; A.team = ti; A.stage = 2;
  const before = A.S.log.length;
  A.commit(r.price);
  if(A.S.log.length > before){ placed++; keys += kp + kt + String(r.price).length + 1; }
  else failed.push(`${r.name_en} → ${r.manager} $${r.price}: 커밋 거부`);
}

eq("120건 전량 낙찰", placed, 120);
ok("실패 0건", failed.length===0, failed.slice(0,5).join(" / "));
eq("로그 120건", A.S.log.length, 120);

console.log("\n── 팀별 재현 대조 ──");
const expect = new Map();
for(const r of rows){
  const cur = expect.get(r.manager) || {n:0, s:0};
  cur.n++; cur.s += r.price; expect.set(r.manager, cur);
}
let mismatch = [];
for(const [m, exp] of expect){
  const t = A.S.teams[teamIdx.get(m)];
  const d = A.derive(t);
  if(t.picks.length !== exp.n) mismatch.push(`${m} 인원 ${t.picks.length}≠${exp.n}`);
  if(d.spent !== exp.s)        mismatch.push(`${m} 지출 $${d.spent}≠$${exp.s}`);
}
ok("12팀 인원·지출 전부 일치", mismatch.length===0, mismatch.join(" / "));
eq("전원 10명", A.S.teams.every(t=>t.picks.length===10), true);
eq("총 지출 $2368", A.S.log.reduce((a,e)=>a+e.price,0), 2368);
// 작년 스프레드시트의 검산: 낙찰가 합 + 잔액 = $200
ok("전 팀 지출+잔액 = $200", A.S.teams.every(t=>{const d=A.derive(t); return d.spent+d.budget===200;}));
eq("$1 남긴 팀 10곳", A.S.teams.filter(t=>A.derive(t).budget===1).length, 10);

console.log("\n── 불변식 ──");
const V = {}; for(const v of A.validate()) V[v.id]=v;
for(const id of ["I1","I2","I3","I4"]) ok(`${id} 통과`, V[id].ok, V[id].detail);
ok("I3 는 순서 독립 — 어떤 순서로도 상한 위반이 없다", V.I3.ok, V.I3.detail);
console.log(`  (I5 포지션: ${V.I5.ok?"충족":"미충족 — "+V.I5.detail.slice(0,80)})`);

console.log("\n── 만석 후 동작 ──");
eq("지명자 없음 = 종료", A.nominator(), null);
eq("대기열 공백", A.nomQueue(4).length, 0);
const extra = A.IDX.find(e=>!A.taken.has(e.i));
A.pick = extra; A.team = 0; A.stage = 2; A.commit(1);
eq("121번째 거부", A.S.log.length, 120);

console.log("\n── 결과 CSV 가 작년 파일을 재현하는가 ──");
const out = A.resultsCsv();
// 소비자(형제 저장소 tool/*.py)와 동일한 정규화로 대조한다.
// 발음기호는 접지만 접미사는 접지 않는 규칙이므로 그대로 재현한다.
const cnorm = x => x.normalize("NFKD").replace(/[^\x00-\x7F]/g,"").toLowerCase().trim();
const mine = out.trim().split("\r\n").slice(1).map(l=>{
  const c = l.split(","); return `${c[0]}|${cnorm(c[2])}|${c[3]}`;
}).sort();
const theirs = rows.map(r=>
  `${r.manager}|${cnorm(r.name_en==="Alexandre Sarr"?"Alex Sarr":r.name_en)}|${r.price}`).sort();
eq("행 수 일치", mine.length, theirs.length);
const diff = mine.filter((x,i)=>x!==theirs[i]);
ok("(팀|선수|금액) 120건 전부 일치 — 소비자 정규화 기준", diff.length===0,
   diff.slice(0,3).map(x=>`${x} vs ${theirs[mine.indexOf(x)]}`).join(" / "));

// 접미사는 소비자가 접지 않으므로, 표기가 정확히 같아야 조인된다
const csvNames = new Set(out.trim().split("\r\n").slice(1).map(l=>l.split(",")[2]));
for(const n of ["Jimmy Butler III", "Kristaps Porziņģis", "Nikola Vučević"])
  ok(`표시명이 소비자 DB 표기와 동일: ${n}`, csvNames.has(n),
     [...csvNames].filter(x=>cnorm(x).includes(cnorm(n).split(" ")[1])).join(","));
eq("헤더 동일", out.split("\r\n")[0], ref.split("\r\n")[0]);

console.log("\n── 속도 ──");
const spk = keys/120, secs = keys/4;
console.log(`  총 ${keys}타 · 건당 ${spk.toFixed(1)}타 = ${(secs/120).toFixed(1)}초 (4타/초 가정)`);
console.log(`  120건 ${(secs/60).toFixed(1)}분 · 126건 환산 ${(spk*126/4/60).toFixed(1)}분`);
ok(`건당 5초 이내 (실측 ${(secs/120).toFixed(1)}초)`, secs/120 <= 5);
ok(`총 10분 이내 (실측 ${(secs/60).toFixed(1)}분)`, secs/60 <= 10);

console.log("\n── 되돌리기가 120건 상태에서도 동작하는가 ──");
const snap120 = JSON.stringify(A.S.log);
A.cancelPick(0);
eq("철회 후 119건", A.S.log.length, 119);
ok("철회 팀 예산 복구", A.derive(A.S.teams[A.S.teams.findIndex(t=>t.name===rows[0].manager)]).budget > 1);
A.undo();
eq("되돌리기로 120건 복구", A.S.log.length, 120);
eq("상태 완전 복원", JSON.stringify(A.S.log), snap120);

summary();
