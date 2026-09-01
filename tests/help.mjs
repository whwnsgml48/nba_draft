// 내장 사용법 — 진행자가 다른 사람일 수 있으므로 README 없이 파일만으로 쓸 수 있어야 한다.
import fs from "node:fs";
import path from "node:path";
import {load, ok, eq, summary} from "./harness.mjs";
const A = load();
const html = fs.readFileSync(path.join(import.meta.dirname, "..", "console.html"), "utf8");
const strip = s => s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

console.log("── 첫 실행 동작 ──");
ok("처음 열면 자동으로 뜬다", A.html("hp")!==undefined);
A.reset();
A.openHelp();
A.closeHelp();
eq("닫으면 본 것으로 기록", A.S.helpSeen, true);
eq("자동표시 해제 기본값", !!A.S.helpSkip, false);

console.log("── 내용 커버리지 ──");
const body = strip(html.slice(html.indexOf('id="hp"'), html.indexOf('id="iv"')));
const must = [
  ["빠른 기록 3단계", "선수 → 팀 → 금액"],
  ["별칭·초성 검색", "초성"],
  ["임시 등재", "임시 등재"],
  ["라이브 모드 전환키", "Tab"],
  ["자동 $1 입찰", "자동 $1 입찰"],
  ["붙여쓰기 입찰", "병34"],
  ["자동 낙찰 안 함", "자동 낙찰하지 않는다"],
  ["시간 되돌리기", "시간 되돌리기"],
  ["개별 철회", "개별 철회"],
  ["순번 로테이션", "순번 로테이션"],
  ["당일 순서 입력", "접두사만 순서대로"],
  ["최대입찰가 공식", "잔액 − (남은 슬롯 − 1)"],
  ["장부 배너 의미", "장부 배너"],
  ["포지션은 막지 않음", "낙찰을 막지 않는다"],
  ["OREB 설명", "공격 리바운드"],
  ["A/T 설명", "어시스트÷턴오버"],
  ["DD 설명", "더블더블"],
  ["TOV 색 의미", "낮을수록 좋은"],
  ["— 의 뜻", "산출 불가"],
  ["출처: 혼합", "GP가중 혼합"],
  ["출처: 결장", "2025-26 결장"],
  ["출처: 신인", "NBA 실적 없음"],
  ["자동 저장", "자동 저장"],
  ["결과 CSV", "결과 CSV"],
  ["오프라인", "비행기 모드"],
];
for(const [name, needle] of must) ok(name, body.includes(needle), `"${needle}" 없음`);

console.log("── 발견 경로 ──");
ok("상단 버튼 존재", html.includes('id="bHelp"'));
ok("버튼 라벨에 ? 표시", /id="bHelp"[^>]*>사용법 \?/.test(html));
ok("? 키 처리", html.includes('e.key==="?"'));
ok("F1 키 처리", html.includes('e.key==="F1"'));
ok("Esc 로 닫힘", /hp"\)\.classList\.contains\("on"\)/.test(html));

console.log("── 정보 경계 유지 ──");
for(const t of ["my_max","시장가","코어 플랜","피벗","태우기"])
  ok(`설명에 ${t} 없음`, !body.includes(t), `"${t}" 노출`);

summary();
