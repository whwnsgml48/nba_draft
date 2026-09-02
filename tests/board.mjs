// 로스터 보드 — 뽑은 선수가 실제로 보이는지. 이전 팀 카드는 10px 흐린 한 줄에
// overflow:hidden 으로 잘려 사실상 안 보였다.
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const find = n => A.IDX.find(e => e.p.n === n);
function put(name, t, price){ A.pick=find(name); A.team=t; A.stage=2; A.commit(price); }

console.log("── 성(姓) 축약 ──");
eq("단순", A.shortName("Nicolas Claxton"), "Claxton");
eq("발음기호 유지", A.shortName("Alperen Şengün"), "Şengün");
eq("접미사는 성이 아니다", A.shortName("Jimmy Butler III"), "Butler III");
eq("Jr. 도 유지", A.shortName("Jaren Jackson Jr."), "Jackson Jr.");
eq("하이픈 성", A.shortName("Shai Gilgeous-Alexander"), "Gilgeous-Alexander");
eq("한 단어", A.shortName("김철수"), "김철수");

console.log("── 9칸이 항상 전부 그려진다 ──");
A.reset(); A.renderBoard();
let h = A.html("board");
eq("팀 블록 14개", (h.match(/class="tb[ "]/g)||[]).length, 14);
eq("슬롯 14×9 = 126칸", (h.match(/class="sl[ "]/g)||[]).length, 126);
eq("빈 칸 126개", (h.match(/class="sl open"/g)||[]).length, 126);
ok("슬롯 번호 표시", h.includes("<u>1</u>") && h.includes("<u>9</u>"));

console.log("── 낙찰이 보드에 드러난다 ──");
put("Nikola Jokić", 0, 86);
A.renderBoard(); h = A.html("board"); let t = A.text("board");
ok("성이 보인다", t.includes("Jokić"), t.slice(0,120));
ok("금액이 보인다", t.includes("$86"), t.slice(0,120));
ok("포지션이 보인다", t.includes("C"));
ok("전체 이름은 title 로 남는다", h.includes('title="Nikola Jokić"'));
eq("빈 칸 하나 줄었다", (h.match(/class="sl open"/g)||[]).length, 125);
ok("방금 낙찰은 강조된다", h.includes('class="sl fresh"'), "fresh 없음");

put("Luka Dončić", 1, 77);
A.renderBoard(); h = A.html("board");
eq("강조는 최신 1건만", (h.match(/class="sl fresh"/g)||[]).length, 1);

console.log("── 팀 머리글 ──");
A.reset();
put("Nikola Jokić", 3, 86);
A.renderBoard(); t = A.text("board");
ok("잔액 표시", t.includes("$114"), t.slice(0,200));
ok("최대입찰가 표시", t.includes("max $107"), t.slice(0,200));
ok("인원 표시", t.includes("1/9"), t.slice(0,200));
ok("지명자 표시", A.html("board").includes("<i>지명</i>"));
ok("지명 팀에 테두리", A.html("board").includes("nomnow"));

console.log("── 로스터가 꽉 찬 팀 ──");
A.reset();
for(let i=0;i<9;i++) put(A.DB.players[i].n, 2, 1);
A.renderBoard(); h = A.html("board");
const blocks = h.split('class="tb');
const full = blocks.find(b=>b.includes("9/9"));
ok("로스터가 꽉 찬 팀 블록에 빈 칸 없음", full && !full.split('class="tb')[0].includes('sl open'),
   "빈 칸 남음");
eq("전체 빈 칸 = 126-9", (h.match(/class="sl open"/g)||[]).length, 117);

console.log("── 부족 포지션·예산 플래그 ──");
A.reset();
const guards = A.DB.players.filter(p=>p.pos.every(x=>x==="PG"||x==="SG")).slice(0,9);
guards.forEach(p=>put(p.n, 5, 1));
A.renderBoard(); t = A.text("board");
ok("부족 포지션이 보드에 표시", /SF|PF|C/.test(t), t.slice(0,200));
A.reset();
put("Nikola Jokić", 6, 192);
A.renderBoard();
ok("예산 소진 플래그", A.text("board").includes("예산 소진"), A.text("board").slice(0,200));

console.log("── 입찰가 입력 시 불가 팀 흐려짐 ──");
A.reset();
A.pick = find("Nikola Jokić"); A.team = null; A.stage = 2; A.q.value = "150";
A.renderBoard();
// 클래스는 "tb dim nomnow" 처럼 조합되므로 완전일치로 세면 안 된다
const dimCount = () => (A.html("board").match(/class="tb[^"]*\bdim\b[^"]*"/g)||[]).length;
eq("초기엔 흐려진 팀 0 (max 192)", dimCount(), 0);
A.q.value = "199";
A.renderBoard();
eq("199 는 14팀 전부 불가", dimCount(), 14);
A.q.value = "192";
A.renderBoard();
eq("192 는 상한이라 전부 가능", dimCount(), 0);

console.log("── 126건 완료 후 ──");
A.reset();
let pi = 0;
for(let ti=0; ti<14; ti++) for(let k=0;k<9;k++){ const w=A.DB.players[pi].n; pi++; put(w, ti, 1); }
A.renderBoard(); h = A.html("board");
eq("빈 칸 0", (h.match(/class="sl open"/g)||[]).length, 0);
eq("채워진 칸 126", (h.match(/class="sl[ "]/g)||[]).length - 0, 126);
ok("전 팀 9/9", (A.text("board").match(/9\/9/g)||[]).length===14, A.text("board").slice(0,200));

summary();
