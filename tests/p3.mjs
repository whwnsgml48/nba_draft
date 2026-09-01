// P3 — 라이브 호가 · 10초 타이머 · 작년 스키마 CSV.
import fs from "node:fs";
import path from "node:path";
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const tn = i => A.S.teams[i].name;
const find = n => A.IDX.find(e => e.p.n === n);

console.log("── 모드 전환 ──");
A.reset();
eq("기본은 빠른 기록", A.S.mode, "fast");
A.toggleMode();
eq("라이브로 전환", A.S.mode, "live");
A.toggleMode();
eq("되돌아옴", A.S.mode, "fast");

console.log("── 지명 시 자동 $1 입찰 (리그 규칙) ──");
A.reset(); A.S.mode = "live";
A.liveOpen(find("Nikola Jokić"));
eq("호가 열림", A.S.live.n, "Nikola Jokić");
eq("자동 입찰 1건", A.S.live.bids.length, 1);
eq("자동 입찰은 $1", A.liveHigh().price, 1);
eq("자동 입찰자는 지명자", tn(A.liveHigh().t), "준희");
eq("auto 표시", A.S.live.bids[0].auto, true);

console.log("── 입찰 ──");
A.liveBid(4, 30);
eq("최고가 갱신", A.liveHigh().price, 30);
eq("최고 입찰자", tn(A.liveHigh().t), "병욱");
A.liveBid(5, 30);
eq("동가는 거부", A.liveHigh().price, 30);
A.liveBid(5, 29);
eq("하가는 거부", A.liveHigh().price, 30);
A.liveBid(5, 31);
eq("상회는 수락", A.liveHigh().price, 31);
eq("이력 누적", A.S.live.bids.length, 3);
A.liveBid(5, 200);
eq("최대입찰가 초과 거부", A.liveHigh().price, 31);
eq("최대입찰가 = 200-(9-1)", A.derive(A.S.teams[5]).maxBid, 192);
A.liveBid(5, 192);
eq("상한 정확히는 수락", A.liveHigh().price, 192);

console.log("── 타이머 ──");
A.reset(); A.S.mode = "live";
A.liveOpen(find("Luka Dončić"));
const l0 = A.liveLeft();
ok("초기 카운트다운이 10초 이내", l0>0 && l0<=A.CLOSE_SEC, String(l0));
A.S.live.deadline = Date.now() - 1000;
eq("만료되면 0", A.liveLeft(), 0);
eq("만료돼도 자동 낙찰하지 않는다", A.S.log.length, 0);
ok("만료 상태에서도 live 유지", !!A.S.live);
A.liveBid(3, 20);
ok("새 입찰이 타이머를 리셋", A.liveLeft() > 0, String(A.liveLeft()));

console.log("── 낙찰 ──");
A.reset(); A.S.mode = "live";
A.liveOpen(find("Nikola Jokić"));
A.liveBid(4, 40);
A.liveBid(6, 55);
A.liveSell();
eq("낙찰 1건", A.S.log.length, 1);
eq("최고 입찰자에게", tn(A.S.log[0].t), "윤범");
eq("최고가로", A.S.log[0].price, 55);
eq("호가 종료", A.S.live, null);
eq("입찰 이력이 로그에 영속화 (구판 B6 결함)", A.S.log[0].bids.length, 3);
eq("이력 내용", A.S.log[0].bids.map(b=>b.price), [1,40,55]);
eq("지명 순번 진행", tn(A.nominator()), "정명");
eq("잔액 반영", A.derive(A.S.teams[6]).budget, 145);

console.log("── 자동 $1 만으로 낙찰 (아무도 안 붙은 경우) ──");
A.reset(); A.S.mode = "live";
A.liveOpen(find("Klay Thompson"));
A.liveSell();
eq("지명자가 $1에 가져간다", A.S.log[0].price, 1);
eq("낙찰 팀", tn(A.S.log[0].t), "준희");
eq("단독 입찰은 이력 미첨부", A.S.log[0].bids, undefined);

console.log("── 지명 취소 ──");
A.reset(); A.S.mode = "live";
A.liveOpen(find("Nikola Jokić"));
A.liveBid(4, 30);
A.liveCancel();
eq("낙찰 없음", A.S.log.length, 0);
eq("호가 종료", A.S.live, null);
eq("순번 그대로", tn(A.nominator()), "준희");
eq("선수는 다시 검색됨", A.search("요키치",3).length, 1);

console.log("── 만석 팀은 입찰 불가 ──");
A.reset(); A.S.mode = "live";
for(let i=0;i<9;i++){ const w=A.DB.players[i].n; A.pick=find(w); A.team=2; A.stage=2; A.commit(1); }
eq("단열 만석", A.S.teams[2].picks.length, 9);
A.liveOpen(find("Nikola Jokić"));
const hp = A.liveHigh().price;
A.liveBid(2, 50);
eq("만석 팀 입찰 거부", A.liveHigh().price, hp);

console.log("── 결과 CSV: 작년 스키마 바이트 호환 ──");
const REF = path.join(import.meta.dirname, "..", "..", "nba_fantasy_auction_2026",
                      "data", "prior_auction_2025_26", "results.csv");
const ref = fs.readFileSync(REF, "utf8");
const refHeader = ref.split("\r\n")[0];
eq("헤더 일치", A.CSV_HEADER, refHeader);

A.reset();
A.pick = find("Victor Wembanyama"); A.team = 4; A.stage = 2; A.commit(87);
A.pick = find("Nikola Jokić");      A.team = 0; A.stage = 2; A.commit(86);
const csv = A.resultsCsv();
const lines = csv.split("\r\n");
eq("CRLF 로 끝난다", csv.endsWith("\r\n"), true);
eq("LF 단독 없음", /[^\r]\n/.test(csv), false);
eq("헤더 + 2건 + 빈줄", lines.length, 4);
eq("첫 행", lines[1], "병욱,웸비,Victor Wembanyama,87,high");
eq("둘째 행", lines[2], "준희,요키치,Nikola Jokić,86,high");
eq("열 수 = 5", lines[1].split(",").length, 5);
// 작년 파일의 실제 행과 형태 대조
const refRow = ref.split("\r\n")[1];
eq("작년 행과 동일 형태", refRow, "병욱,웸비,Victor Wembanyama,87,high");

console.log("── CSV 이스케이프 ──");
eq("쉼표 포함", A.csvCell("a,b"), '"a,b"');
eq("따옴표 포함", A.csvCell('a"b'), '"a""b"');
eq("평문", A.csvCell("abc"), "abc");
eq("null", A.csvCell(null), "");
A.reset();
A.S.teams[0].name = "가,나";
A.pick = find("Nikola Jokić"); A.team = 0; A.stage = 2; A.commit(50);
ok("쉼표 팀명이 인용된다", A.resultsCsv().includes('"가,나"'), A.resultsCsv().split("\r\n")[1]);

console.log("── 별칭 없는 선수 ──");
A.reset();
A.pick = find("Jayson Tatum") || find("Cooper Flagg");
const nm = A.pick.p.n;
A.team = 0; A.stage = 2; A.commit(60);
const row = A.resultsCsv().split("\r\n")[1].split(",");
eq("name_en 은 항상 채워진다", row[2], nm);
ok("name_kr 은 별칭 있으면 채우고 없으면 빈칸", row[1]!==undefined, JSON.stringify(row));

console.log("── 입찰 입력 파싱 · 미리보기 ──");
A.reset(); A.S.mode="live";
A.liveOpen(find("Nikola Jokić"));
const P = t => { A.q.value = t; return A.parseLiveBid(t); };
eq("빈 입력은 empty", P("").empty, true);
eq("병34 → 병욱 $34", [tn(P("병34").team), P("병34").amount], ["병욱", 34]);
eq("공백 허용 '병 34'", tn(P("병 34").team), "병욱");
ok("금액 없으면 예시 안내", P("병").err === "예: 병34", P("병").err);
ok("팀 없이 숫자만 치면 팀을 요구", P("34").err.includes("팀을 함께"), P("34").err);
ok("없는 팀 지목", P("ㅋ34").err.includes("맞는 팀이 없다"), P("ㅋ34").err);
ok("현재가 미달 거부", P("병1").err.includes("현재가"), P("병1").err);
ok("최대입찰가 초과 거부", P("병200").err.includes("최대"), P("병200").err);
eq("초과여도 파싱 결과는 반환 (오류와 값 동시 제공)", P("병200").amount, 200);
A.q.value = "";
A.liveBid(4, 34);
ok("입찰 후 현재가 기준으로 판정", P("윤20").err.includes("현재가 $34"), P("윤20").err);
eq("현재가 초과는 통과", P("윤35").err, undefined);

console.log("── 다음 동작 패널 ──");
A.reset(); A.S.mode="live";
A.liveOpen(find("Nikola Jokić"));
A.q.value = ""; A.renderResults();
let T = A.text("results");
ok("세 동작이 모두 보인다", ["입찰","낙찰","취소"].every(k=>T.includes(k)), T);
ok("낙찰 대상을 이름과 금액으로 명시", T.includes("준희") && T.includes("$1"), T);
ok("입찰 방법을 예시로 보여준다", T.includes("병34"), T);
ok("빈 입력에서는 낙찰 행이 강조된다",
   /class="act go"[^>]*>\s*<span class="ak">빈 입력/.test(A.html("results")), "강조 없음");

A.q.value = "병34"; A.renderResults();
T = A.text("results");
ok("타이핑하면 파싱 결과를 되비춘다", T.includes("병욱") && T.includes("$34"), T);
ok("유효 입력에서는 입찰 행이 강조된다",
   A.html("results").includes('class="act go"') &&
   /class="act go"[^>]*>\s*<span class="ak">입력 중/.test(A.html("results")), "강조 없음");

A.q.value = "ㅋ34"; A.renderResults();
ok("오류는 붉게 표시된다", A.html("results").includes('class="act bad"'), "bad 클래스 없음");
ok("오류 문구가 보인다", A.text("results").includes("맞는 팀이 없다"), A.text("results"));

A.q.value = ""; A.liveBid(4, 34); A.renderResults();
T = A.text("results");
ok("입찰 후 낙찰 대상이 갱신된다", T.includes("병욱") && T.includes("$34"), T);
ok("자동 단독 표시가 사라진다", !T.includes("자동 $1 단독"), T);

console.log("── 발견성: 모드 전환이 눈에 보이는가 ──");
A.reset();
eq("기본 모드", A.S.mode, "fast");
A.toggleMode();
eq("라이브 전환", A.S.mode, "live");
A.renderLive();
eq("지명 전에도 패널이 뜬다 (전환 확인용)", A.S.live, null);
A.liveOpen(find("Nikola Jokić"));
eq("지명하면 타이머 시작", A.liveLeft() > 0, true);

summary();
