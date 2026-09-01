// 지명 순서 조정 — 당일 추첨 결과를 입력하는 경로.
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const N = () => A.S.teams.map(t=>t.name);
const tn = i => A.S.teams[i].name;
const find = n => A.IDX.find(e => e.p.n === n);
function commitBy(name, t, price){ A.pick = find(name); A.team = t; A.stage = 2; A.commit(price); }

console.log("── 접두사 나열 파싱 ──");
A.reset();
const names = N();
const r1 = A.parseOrderText("병 준 진 경 원 윤 단 지 두 수 철 정 강 완", names);
eq("14개 파싱 성공", r1.err, undefined);
eq("순서대로 매핑", r1.order.map(i=>names[i]),
   ["병욱","준희","진빈","경찬","원준","윤범","단열","지원","두현","수현","철웅","정명","강호","완식"]);

const r2 = A.parseOrderText("병 준", names);
ok("일부만 입력하면 빠진 팀 지목", r2.err && r2.err.includes("빠진 팀"), r2.err);

const r3 = A.parseOrderText("ㅋ 준 진 경 원 윤 단 지 두 수 철 정 강 완", names);
ok("없는 접두사 거부", r3.err && r3.err.includes("맞는 팀이 없다"), r3.err);

const r4 = A.parseOrderText("지 지 진 경 원 윤 단 병 두 수 철 정 강 완", names);
ok("중복 접두사는 두 번째에서 빠진 팀으로 걸린다", !!r4.err, r4.err);

// 모호성: 지원(8) 과 지훈(11) 을 공존시켜 '지' 가 둘을 가리키게 만든다
const nm2 = names.slice(); nm2[11] = "지훈";       // 철웅 → 지훈
eq("지 로 시작하는 팀 2개", nm2.filter(n=>n.startsWith("지")).length, 2);
const r5 = A.parseOrderText("지", nm2);
ok("모호하면 즉시 거부하고 후보를 보여준다",
   r5.err && r5.err.includes("모호") && r5.err.includes("지원") && r5.err.includes("지훈"), r5.err);
const r6 = A.parseOrderText("지원 준 정 단 경 병 원 윤 진 두 수 지훈 강 완", nm2);
eq("두 글자로 해소", r6.err, undefined);
eq("해소된 매핑", r6.order.slice(0,2).map(i=>nm2[i]), ["지원","준희"]);
ok("지훈도 제자리", nm2[r6.order[11]]==="지훈", nm2[r6.order[11]]);

const r7 = A.parseOrderText("  ", names);
ok("빈 입력 거부", !!r7.err, r7.err);

console.log("── 순서가 로테이션에 실제로 반영된다 ──");
A.reset();
eq("기본순 첫 지명", tn(A.nominator()), "준희");
A.S.order = A.parseOrderText("병 준 진 경 원 윤 단 지 두 수 철 정 강 완", names).order;
A.S.nomPos = 0;
eq("순서 변경 후 첫 지명", tn(A.nominator()), "병욱");
eq("대기열도 따라온다", A.nomQueue(4).map(tn), ["병욱","준희","진빈","경찬"]);
commitBy("Nikola Jokić", 3, 50);
eq("진행", tn(A.nominator()), "준희");

console.log("── 진행 중 순서 변경은 낙찰 이력에 영향 없음 ──");
A.reset();
commitBy("Nikola Jokić", 0, 80);
commitBy("Luka Dončić", 1, 70);
const before = JSON.stringify(A.S.log);
A.S.order = A.parseOrderText("완 강 철 수 두 지 단 윤 원 경 진 병 정 준", names).order;
A.S.nomPos = 0;
A.normOrder();
eq("로그 불변", JSON.stringify(A.S.log), before);
eq("잔액 불변", A.derive(A.S.teams[0]).budget, 120);
eq("새 순서 지명자", tn(A.nominator()), "완식");

console.log("── 순서 정규화 (훼손 방어) ──");
A.reset();
A.S.order = [3,3,3];                       // 중복·누락
A.normOrder();
eq("길이 복구", A.S.order.length, 14);
eq("중복 제거 후 선두 유지", A.S.order[0], 3);
eq("전 팀 포함", new Set(A.S.order).size, 14);
A.S.order = [99,-1,"x",2];
A.normOrder();
eq("잘못된 값 제거", A.S.order.length, 14);
eq("유효값은 앞에", A.S.order[0], 2);
A.S.nomPos = 99; A.normOrder();
eq("nomPos 범위 보정", A.S.nomPos, 0);

console.log("── 만석 스킵은 새 순서에서도 동작 ──");
A.reset();
A.S.order = A.parseOrderText("병 준 진 경 원 윤 단 지 두 수 철 정 강 완", names).order;
A.S.nomPos = 0;
for(let i=0;i<9;i++) commitBy(A.DB.players[i].n, 4, 1);   // 병욱 만석
eq("병욱 만석", A.S.teams[4].picks.length, 9);
A.S.nomPos = 0;
eq("만석 팀 건너뛴 대기열", A.nomQueue(3).map(tn), ["준희","진빈","경찬"]);

console.log("── 이름 빈 팀은 순서 뒤로 밀린다 ──");
A.reset();
const nm3 = names.slice(); nm3[13] = "";
const r8 = A.parseOrderText("병 준 진 경 원 윤 단 지 두 수 철 정 강", nm3);
eq("13개만으로 성공", r8.err, undefined);
eq("빈 팀은 마지막", r8.order[13], 13);

summary();
