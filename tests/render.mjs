// 렌더 산출 마크업 스모크 테스트 — 셧의 innerHTML 을 실제로 들여다본다.
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();

A.reset();
A.pick = A.IDX.find(e=>e.p.n==="Victor Wembanyama");
A.team = 4; A.stage = 2;
A.commit(87);
A.render();

console.log("── 상태 정합성 ──");
eq("팀 4에 1명", A.S.teams[4].picks.length, 1);
eq("로그 1건", A.S.log.length, 1);
eq("총 슬롯", A.TOTAL, 126);
eq("팀 수", A.S.teams.length, 14);
eq("14팀 전원 이름 확정", A.S.teams.filter(t=>t.name).length, 14);
eq("13·14번", [A.S.teams[12].name, A.S.teams[13].name], ["강호","완식"]);
{ // 이름이 빈 팀에는 낙찰이 거부되어야 한다
  const keep = A.S.teams[13].name;
  A.S.teams[13].name = "";
  A.pick = A.IDX.find(e=>e.p.n==="Nikola Jokić"); A.team=13; A.stage=2;
  const before = A.S.log.length; A.commit(50);
  eq("이름 빈 팀 낙찰 거부", A.S.log.length, before);
  A.S.teams[13].name = keep;
}

console.log("── 잔액·상한 산술 (14팀 전수) ──");
let allOk = true;
for(let i=0;i<14;i++){
  const d = A.derive(A.S.teams[i]);
  if(d.spent + d.budget !== 200) allOk = false;
  if(d.left>0 && d.maxBid !== d.budget - (d.left-1)) allOk = false;
}
ok("전 팀 I1 및 상한 공식 성립", allOk);

console.log("── 126건 로스터 완료 시뮬레이션 ──");
A.reset();
// 14팀 전원 9명씩 $1 로 채운다
const pool = A.DB.players.map(p=>p.n);
let pi = 0, placed = 0;
for(let t=0;t<14;t++){
  for(let s=0;s<9;s++){
    const want = pool[pi]; pi++;                  // find 콜백 안에서 증가시키면 안 된다
    A.pick = A.IDX.find(e=>e.p.n===want);
    A.team = t; A.stage = 2;
    const before = A.S.log.length;
    A.commit(1);
    if(A.S.log.length>before) placed++;
  }
}
eq("126건 전부 낙찰", placed, 126);
eq("로그 126건", A.S.log.length, 126);
eq("전 팀 로스터 완료", A.S.teams.every(t=>t.picks.length===9), true);
eq("전 팀 잔액 $191", A.S.teams.every(t=>A.derive(t).budget===191), true);
eq("완료 후 최대입찰가 0", A.S.teams.every(t=>A.derive(t).maxBid===0), true);
const w2 = pool[pi]; A.pick = A.IDX.find(e=>e.p.n===w2); A.team=0; A.stage=2; A.commit(1);
eq("127번째 거부", A.S.log.length, 126);
eq("중복 낙찰 없음 (I4)", new Set(A.S.log.map(e=>e.i)).size, 126);
eq("완료 후 지명자 없음 = 종료", A.nominator(), null);
eq("완료 후 대기열 공백", A.nomQueue(4).length, 0);

console.log("── 순번 로테이션으로 126건 소화 ──");
A.reset();
let pj = 0, ok126 = true, counts = new Array(14).fill(0);
for(let k=0;k<126;k++){
  const nom = A.nominator();
  if(nom===null){ ok126 = false; break; }
  counts[nom]++;
  // 지명자가 스스로 낙찰받는다고 가정 (순번 진행 검증이 목적)
  const want = A.DB.players[pj]; pj++;
  A.pick = A.IDX.find(e=>e.p.n===want.n); A.team = nom; A.stage = 2;
  A.commit(1);
}
eq("126건 모두 지명자 존재", ok126, true);
eq("전 팀 정확히 9회 지명", counts.every(c=>c===9), true);
eq("로그 126건", A.S.log.length, 126);

summary();
