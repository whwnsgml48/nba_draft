import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const nameOf = e => e.p.n;
const find = n => A.IDX.find(e => e.p.n === n);

console.log("── 검색: 영문 (1차 경로) ──");
eq("성(姓) 우선 'jokic'", A.search("jokic",3).map(nameOf)[0], "Nikola Jokić");
eq("발음기호 무시 'doncic'", A.search("doncic",3).map(nameOf)[0], "Luka Dončić");
eq("성 접두 'wemb'", A.search("wemb",3).map(nameOf)[0], "Victor Wembanyama");
eq("이름 접두 'giannis'", A.search("giannis",3).map(nameOf)[0], "Giannis Antetokounmpo");
eq("이니셜 'sga'", A.search("sga",3).map(nameOf)[0], "Shai Gilgeous-Alexander");
eq("이니셜 'kd'", A.search("kd",3).map(nameOf)[0], "Kevin Durant");
eq("이니셜 'naw'", A.search("naw",3).map(nameOf)[0], "Nickeil Alexander-Walker");
eq("접미사 무시 'jackson jr'", A.search("jaren jackson",3).map(nameOf)[0], "Jaren Jackson Jr.");
ok("동성 다수 'thompson' 전원 노출",
   A.search("thompson",8).map(nameOf).includes("Klay Thompson") &&
   A.search("thompson",8).map(nameOf).includes("Amen Thompson"),
   JSON.stringify(A.search("thompson",8).map(nameOf)));
eq("2타 'ta' 도 결과 있음", A.search("ta",5).length>0, true);

console.log("── 검색: 한글 별칭 · 초성 ──");
eq("별칭 완전일치 '웸비'", A.search("웸비",3).map(nameOf)[0], "Victor Wembanyama");
eq("별칭 '제이덥'", A.search("제이덥",3).map(nameOf)[0], "Jalen Williams");
eq("별칭 '막윌'", A.search("막윌",3).map(nameOf)[0], "Mark Williams");
eq("보강 별칭 '테이텀'", A.search("테이텀",3).map(nameOf)[0], "Jayson Tatum");
eq("초성 'ㅇㅂ' → 웸비", A.search("ㅇㅂ",5).map(nameOf).includes("Victor Wembanyama"), true);
eq("초성 'ㅇㅋㅊ' → 요키치", A.search("ㅇㅋㅊ",5).map(nameOf)[0], "Nikola Jokić");
eq("공백 무시 '아멘탐슨'", A.search("아멘탐슨",3).map(nameOf)[0], "Amen Thompson");
eq("빈 질의는 0건", A.search("  ",5).length, 0);

console.log("── 최대입찰가 규칙: 잔액 − (남은 슬롯 − 1) ──");
A.reset();
eq("초기 최대입찰가", A.derive(A.S.teams[0]).maxBid, 200 - (9-1));
eq("초기 잔액", A.derive(A.S.teams[0]).budget, 200);

console.log("── 커밋 ──");
function commitBy(playerName, teamIdx, price){
  A.pick = find(playerName); A.team = teamIdx; A.stage = 2;
  A.commit(price);
}
A.reset();
commitBy("Victor Wembanyama", 4, 87);
eq("낙찰 1건", A.S.log.length, 1);
eq("로스터 반영", A.S.teams[4].picks.length, 1);
eq("잔액 차감", A.derive(A.S.teams[4]).budget, 113);
eq("최대입찰가 재계산", A.derive(A.S.teams[4]).maxBid, 113 - (8-1));
eq("지명 순번은 낙찰자와 무관하게 다음 순번", A.nominator(), 1);
eq("낙찰 선수는 검색에서 제외", A.search("웸비",3).length, 0);

console.log("── 규칙 위반 차단 ──");
A.reset();
commitBy("Nikola Jokić", 0, 193);          // 200 - 8 = 192 가 상한
eq("최대입찰가 초과는 거부", A.S.log.length, 0);
commitBy("Nikola Jokić", 0, 192);
eq("상한 정확히는 허용", A.S.log.length, 1);
eq("이후 남은 8슬롯에 $1씩", A.derive(A.S.teams[0]).budget, 8);
eq("최대입찰가 $1", A.derive(A.S.teams[0]).maxBid, 1);
commitBy("Luka Dončić", 0, 2);
eq("$1 초과 거부", A.S.log.length, 1);
commitBy("Luka Dončić", 0, 0);
eq("$0 거부", A.S.log.length, 1);

console.log("── 로스터 한도 9명 ──");
A.reset();
const cheap = A.DB.players.slice(-12).map(p=>p.n);
cheap.slice(0,9).forEach((n,i)=> commitBy(n, 1, 1));
eq("9명 채움", A.S.teams[1].picks.length, 9);
eq("풀 상태 최대입찰가 0", A.derive(A.S.teams[1]).maxBid, 0);
commitBy(cheap[9], 1, 1);
eq("10번째 거부", A.S.teams[1].picks.length, 9);

console.log("── 철회 / 되돌리기 ──");
A.reset();
commitBy("Nikola Jokić", 2, 86);
commitBy("Luka Dončić", 3, 77);
eq("2건", A.S.log.length, 2);
A.cancelPick(0);                            // 가운데(첫) 건 철회
eq("철회 후 1건", A.S.log.length, 1);
eq("철회 팀 잔액 복구", A.derive(A.S.teams[2]).budget, 200);
eq("남은 건 유지", A.S.teams[3].picks.length, 1);
eq("철회 시 순번 한 칸 복귀", A.nominator(), 1);
eq("철회 선수 검색 복귀", A.search("요키치",3).length, 1);
A.undo();
eq("되돌리기로 철회 취소", A.S.log.length, 2);
A.redo();
eq("다시 실행", A.S.log.length, 1);

console.log("── 지명 로테이션 (2026-09-01 규칙 변경) ──");
A.reset();
const tn = i => A.S.teams[i].name;
eq("첫 지명은 1번", tn(A.nominator()), "준희");
eq("대기열 4명", A.nomQueue(4).map(tn), ["준희","정명","단열","경찬"]);
commitBy("Nikola Jokić", 9, 50);        // 두현이 낙찰받아도 순번은 진행만 한다
eq("낙찰자와 무관", tn(A.nominator()), "정명");
commitBy("Luka Dončić", 9, 40);
eq("연속 진행", tn(A.nominator()), "단열");
A.reset();
// 14바퀴 후 처음으로 돌아온다
for(let i=0;i<14;i++) commitBy(A.DB.players[i].n, i, 1);
eq("14건 후 1번으로 회귀", tn(A.nominator()), "준희");
eq("전 팀 1명씩", A.S.teams.every(t=>t.picks.length===1), true);

// 로스터가 꽉 찬 팀은 건너뛴다
A.reset();
for(let s2=0;s2<9;s2++){ const w=A.DB.players[100+s2].n; commitBy(w, 1, 1); }
eq("정명 로스터 꽉 찼음", A.S.teams[1].picks.length, 9);
A.nomPos = 0;
eq("꽉 찬 팀 제외", A.nomQueue(3).map(tn), ["준희","단열","경찬"]);
A.nomPos = 1;
eq("꽉 찬 팀에서 시작해도 제외", tn(A.nominator()), "단열");

// 이름 빈 팀도 건너뛴다
A.reset();
A.S.teams[1].name = "";
A.nomPos = 0;
eq("빈 이름 팀 스킵", A.nomQueue(2).map(tn), ["준희","단열"]);

console.log("── 13캣 성적 데이터 ──");
A.reset();
const jok = A.IDX.find(e=>e.p.n==="Nikola Jokić").p;
ok("13캣 전 항목 존재", A.CATS.every(([k])=>k in jok.st), JSON.stringify(Object.keys(jok.st)));
eq("PTS", jok.st.PTS>25, true);
eq("A/T 산출", jok.st.AT>2, true);
eq("DD 추정 존재", jok.st.DD>50, true);
eq("FG% 표시 변환", A.fmtCat("FG", jok.st.FG), (jok.st.FG*100).toFixed(1));
eq("결측은 —", A.fmtCat("DD", null), "—");
const rook = A.IDX.find(e=>e.p.n==="AJ Dybantsa").p;
eq("신인은 성적 전부 결측", rook.st.PTS, null);
const zeroTov = A.DB.players.find(p=>p.st.TOV===0);
eq("TOV=0 이면 A/T 는 null (0으로 나눌 수 없다)", zeroTov.st.AT, null);

console.log("── 임시 등재 (DB에 없는 선수) ──");
A.reset();
const before = A.IDX.length;
A.q.value = "김철수";
A.addAdhoc("김철수");
eq("IDX 증가", A.IDX.length, before+1);
eq("stage 전진", A.stage, 1);
A.team = 5; A.stage = 2; A.commit(3);
eq("임시 선수 낙찰됨", A.S.log[0].n, "김철수");
eq("adhoc 기록", A.S.adhoc, ["김철수"]);

console.log("── 총량 불변식 I1: 낙찰가 합 + 잔액 = $200 ──");
A.reset();
[[0,"Nikola Jokić",86],[0,"Luka Dončić",50],[0,"Kevin Durant",30]].forEach(([t,n,p])=>commitBy(n,t,p));
const d = A.derive(A.S.teams[0]);
eq("I1 성립", d.spent + d.budget, 200);
eq("I1 값 확인", [d.spent, d.budget], [166, 34]);

summary();
