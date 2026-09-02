// P2 — 불변식 5종. 인수 조건: "위반 케이스 수동 주입 시 전부 검출".
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const V = () => { const m = {}; for(const v of A.validate()) m[v.id] = v; return m; };
const find = n => A.IDX.find(e => e.p.n === n);
function commitBy(name, t, price){ A.pick = find(name); A.team = t; A.stage = 2; A.commit(price); }

console.log("── 정상 상태 ──");
A.reset();
eq("5종 전부 통과", Object.values(V()).every(v=>v.ok), true);
eq("불변식 개수", A.validate().length, 5);
eq("등급: I1~I4 err · I5 info",
   A.validate().map(v=>v.level), ["err","err","err","err","info"]);

console.log("── I1 장부 정합 (로스터 ↔ 로그) ──");
A.reset();
commitBy("Nikola Jokić", 0, 86);
eq("정상", V().I1.ok, true);
A.S.teams[0].picks[0].price = 90;           // 로스터만 조작 → 로그와 불일치
eq("금액 불일치 검출", V().I1.ok, false);
ok("위반 팀 지목", V().I1.detail.includes("준희"), V().I1.detail);
A.S.teams[0].picks[0].price = 86;
eq("복구", V().I1.ok, true);
A.S.teams[0].picks.push({i:-2, n:"유령", pos:["C"], price:0});   // 인원 불일치
eq("인원 불일치 검출", V().I1.ok, false);
ok("인원 사유 표시", V().I1.detail.includes("명"), V().I1.detail);
A.reset();
// 예산 초과 상태 주입 (커밋 경로로는 만들 수 없다)
A.S.teams[0].picks = [{i:-3, n:"과지출", pos:["C"], price:250}];
A.S.log = [{i:-3, n:"과지출", pos:["C"], t:0, price:250}];
eq("예산 초과 검출", V().I1.ok, false);
ok("초과 사유 표시", V().I1.detail.includes("250"), V().I1.detail);
// 동어반복이 아님을 명시적으로 확인
A.reset();
commitBy("Nikola Jokić", 0, 86);
const d0 = A.derive(A.S.teams[0]);
eq("파생 등식은 여전히 항상 참 (그래서 검사로 쓰지 않는다)", d0.spent + d0.budget, 200);

console.log("── I2 로스터 한도 ──");
A.reset();
for(let i=0;i<9;i++) commitBy(A.DB.players[i].n, 3, 1);
eq("9명 정상", V().I2.ok, true);
A.S.teams[3].picks.push({i:-1, n:"침입자", pos:["C"], price:1});
eq("10명 검출", V().I2.ok, false);
ok("초과 팀·인원 표시", V().I2.detail.includes("경찬") && V().I2.detail.includes("10명"), V().I2.detail);

console.log("── I3 낙찰가가 당시 최대입찰가 이내 (로그 시간순 재생) ──");
A.reset();
commitBy("Nikola Jokić", 0, 100);
commitBy("Luka Dončić", 0, 90);             // 100 쓰고 남은 슬롯 7 → 최대 $94
eq("정상 2건", V().I3.ok, true);
A.S.log[1].price = 96;                      // 당시 상한 초과로 조작
eq("시점 상한 초과 검출", V().I3.ok, false);
ok("사유 표시", V().I3.detail.includes("당시 최대"), V().I3.detail);
A.S.log[1].price = 0;
eq("$0 검출", V().I3.ok, false);
ok("최소가 사유", V().I3.detail.includes("최소"), V().I3.detail);
// 순서가 뒤바뀌면 같은 금액도 위반이 된다 — 재생이 실제로 시점을 본다는 증거
A.reset();
commitBy("Nikola Jokić", 0, 100);
commitBy("Luka Dončić", 0, 90);
eq("원래 순서는 통과", V().I3.ok, true);
[A.S.log[0], A.S.log[1]] = [A.S.log[1], A.S.log[0]];
A.S.log[0].price = 190; A.S.log[1].price = 100;
eq("시점을 실제로 검사한다", V().I3.ok, false);

console.log("── I4 중복 낙찰 ──");
A.reset();
commitBy("Nikola Jokić", 0, 50);
eq("정상", V().I4.ok, true);
A.S.log.push({...A.S.log[0], t:1});
eq("중복 검출", V().I4.ok, false);
ok("중복 선수명 표시", V().I4.detail.includes("Jokić"), V().I4.detail);

console.log("── I5 포지션 라인업 실현 가능 ──");
A.reset();
eq("빈 로스터는 충족 가능", V().I5.ok, true);
// 이분 매칭 자체
const gg = [{pos:["PG","SG"]},{pos:["PG","SG"]},{pos:["PG","SG"]}];
eq("가드 3명 → 2슬롯만 채움", A.maxPosMatch(gg).size, 2);
const five = [{pos:["PG"]},{pos:["SG"]},{pos:["SF"]},{pos:["PF"]},{pos:["C"]}];
eq("정확히 5명 → 5슬롯", A.maxPosMatch(five).size, 5);
const flex = [{pos:["PG","SG"]},{pos:["SG"]},{pos:["PF","C"]},{pos:["C"]},{pos:["SF"]}];
eq("교차 배정 필요 → 5슬롯", A.maxPosMatch(flex).size, 5);
eq("빈 포지션 선수는 어떤 슬롯도 못 채움", A.maxPosMatch([{pos:[]}]).size, 0);

// 가드만 9명 → 로스터가 찼는데 SF/PF/C 없음
A.reset();
const guards = A.DB.players.filter(p=>p.pos.every(x=>x==="PG"||x==="SG")).slice(0,9);
eq("가드 9명 확보", guards.length, 9);
guards.forEach(p=>commitBy(p.n, 6, 1));
eq("로스터 완료", A.S.teams[6].picks.length, 9);
eq("I5 위반", V().I5.ok, false);
ok("부족 포지션 지목", ["SF","PF","C"].every(x=>V().I5.detail.includes(x)), V().I5.detail);
eq("I5 는 정보 등급", A.validate().find(v=>v.id==="I5").level, "info");
eq("경고여도 I1~I4 는 정상", ["I1","I2","I3","I4"].every(k=>V()[k].ok), true);

// 로스터 완료 전에도 "이미 불가능"이면 경고
A.reset();
const g2 = A.DB.players.filter(p=>p.pos.every(x=>x==="PG"||x==="SG")).slice(0,7);
g2.forEach(p=>commitBy(p.n, 7, 1));
const q = A.teamPos(A.S.teams[7]);
eq("가드 7명 · 남은 슬롯 2", [q.size, q.left], [2, 2]);
eq("2+2 < 5 → 이미 불가능", q.doomed, true);
eq("로스터 완료 전에도 경고", V().I5.ok, false);

// 포지션 낙찰은 절대 차단하지 않는다 (라이브 진행 중 오판 방지)
A.reset();
const g3 = A.DB.players.filter(p=>p.pos.every(x=>x==="PG"||x==="SG")).slice(0,9);
g3.forEach(p=>commitBy(p.n, 8, 1));
eq("포지션 위반이어도 9건 전부 낙찰됨", A.S.teams[8].picks.length, 9);

console.log("── 배너는 장부 정확성만 말한다 ──");
A.reset();
eq("정상은 전부 통과", A.validate().every(v=>v.ok), true);
A.reset();
const g4 = A.DB.players.filter(p=>p.pos.every(x=>x==="PG"||x==="SG")).slice(0,9);
g4.forEach(p=>commitBy(p.n, 8, 1));
const lv = A.validate();
eq("포지션 미충족이어도 하드 불변식 위반 0", lv.filter(v=>!v.ok && v.level==="err").length, 0);
eq("경고 등급 위반도 0", lv.filter(v=>!v.ok && v.level==="warn").length, 0);
eq("정보 등급으로만 뜬다", lv.filter(v=>!v.ok && v.level==="info").map(v=>v.id), ["I5"]);
A.renderInv();
eq("배너가 노란색으로 내려가지 않는다", lv.filter(v=>!v.ok && v.level!=="info").length, 0);

summary();
