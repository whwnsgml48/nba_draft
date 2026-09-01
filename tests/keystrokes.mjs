// P1 속도 선검증 — 작년 실제 낙찰 120건을 이 엔진으로 입력할 때 필요한 타수를 센다.
// "스프레드시트보다 빠른가"를 P4 리허설 전에 근사 측정하는 것.
import fs from "node:fs";
import path from "node:path";
import {load} from "./harness.mjs";

const A = load();
const ROOT = path.resolve(import.meta.dirname, "..");
const SRC = path.join(ROOT, "..", "nba_fantasy_auction_2026", "data",
                      "prior_auction_2025_26", "results.csv");

const rows = fs.readFileSync(SRC, "utf8").trim().split("\n").slice(1)
  .map(l => { const [manager,name_kr,name_en,price] = l.split(","); return {manager,name_kr,name_en,price:+price}; });

const byName = new Map(A.IDX.map(e => [e.p.n, e]));
function resolve(en){
  // build_db 의 NAME_FIX 와 동일한 교정
  const fixed = en === "Alexandre Sarr" ? "Alex Sarr" : en;
  if(byName.has(fixed)) return byName.get(fixed);
  const f = A.foldEn(fixed);
  return A.IDX.find(e => e.f === f) || null;
}

// 선수 단계: 후보 상위 8까지 숫자키로 선택 가능. 최소 타수 = 접두길이 + 1(선택키)
function playerKeys(e, kr){
  let best = Infinity, bestQ = null;
  const cands = [];
  if(kr) cands.push(kr.replace(/\s+/g,""));
  cands.push(e.p.n.split(" ").pop(), e.p.n);       // 성, 풀네임
  for(const c of cands){
    for(let L=1; L<=c.length; L++){
      const q = c.slice(0,L);
      const r = A.search(q, 8);
      const at = r.findIndex(x => x.p.n === e.p.n);
      if(at >= 0){
        const k = L + 1;                            // 접두 + Enter(1위) 또는 숫자키
        if(k < best){ best = k; bestQ = q + (at===0?"⏎":`[${at+1}]`); }
        break;
      }
    }
  }
  return {keys: best, q: bestQ};
}

// 팀 단계: 접두 몇 자에 유일해지는지
function teamKeys(mgr){
  const names = A.S.teams.map(t=>t.name).filter(Boolean);
  for(let L=1; L<=mgr.length; L++){
    const q = mgr.slice(0,L);
    const hit = names.filter(n=>n.startsWith(q));
    if(hit.length===1 && hit[0]===mgr) return L+1;
  }
  return mgr.length+1;
}

let total=0, worst=[], unresolved=[], detail=[];
for(const r of rows){
  const e = resolve(r.name_en);
  if(!e){ unresolved.push(r.name_en); continue; }
  const pk = playerKeys(e, r.name_kr);
  const tk = teamKeys(r.manager);
  const ak = String(r.price).length + 1;            // 금액 + Enter
  const k = pk.keys + tk + ak;
  total += k;
  detail.push({en:e.p.n, kr:r.name_kr, k, pq:pk.q, pk:pk.keys, tk, ak});
}
detail.sort((a,b)=>b.k-a.k);

const n = detail.length;
const avg = total/n;
console.log(`작년 낙찰 ${rows.length}건 중 ${n}건 측정 (미해결 ${unresolved.length}건)`);
if(unresolved.length) console.log("  미해결:", unresolved);
console.log(`\n총 타수 ${total} · 건당 평균 ${avg.toFixed(1)}타`);
console.log(`선수 단계 평균 ${(detail.reduce((a,d)=>a+d.pk,0)/n).toFixed(1)}타 · ` +
            `팀 ${(detail.reduce((a,d)=>a+d.tk,0)/n).toFixed(1)}타 · ` +
            `금액 ${(detail.reduce((a,d)=>a+d.ak,0)/n).toFixed(1)}타`);

console.log(`\n타수 상위 8건 (검색이 가장 안 듣는 케이스)`);
for(const d of detail.slice(0,8))
  console.log(`  ${d.k}타  ${d.en.padEnd(26)} ${String(d.kr).padEnd(8)} q=${d.pq}`);

const hist = {};
for(const d of detail) hist[d.k] = (hist[d.k]||0)+1;
console.log(`\n분포: ` + Object.keys(hist).map(Number).sort((a,b)=>a-b)
  .map(k=>`${k}타:${hist[k]}`).join(" "));

// 판정 — 숙련 타이핑 4타/초 가정
const secs = total/4;
console.log(`\n126건 환산 ${(total/n*126).toFixed(0)}타 ≈ ${(total/n*126/4/60).toFixed(1)}분 (4타/초 가정)`);
console.log(`${n}건 ${(secs/60).toFixed(1)}분 · 건당 ${(secs/n).toFixed(1)}초`);
const passSpeed = (secs/n) <= 5;
console.log(`\n  ${passSpeed?"PASS":"FAIL"}  건당 5초 이내`);
console.log(`  ${unresolved.length===0?"PASS":"FAIL"}  작년 120건 전원 DB에서 해결`);
process.exit(passSpeed && unresolved.length===0 ? 0 : 1);
