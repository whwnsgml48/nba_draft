// 오프라인 자립 — 이 파일은 네트워크 없는 방에서 열린다. 외부 참조가 하나라도 들어오면
// 드래프트 당일 조용히 깨진다. 정적으로 못 박는다.
import fs from "node:fs";
import path from "node:path";
import {ok, eq, summary} from "./harness.mjs";

const ROOT = path.resolve(import.meta.dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "console.html"), "utf8");

console.log(`console.html ${(html.length/1024).toFixed(0)}KB`);

console.log("── 외부 자원 참조 0건 ──");
const banned = [
  ["절대 URL", /https?:\/\//g],
  ["프로토콜 상대 URL", /(^|[^:])\/\/[a-z0-9-]+\.[a-z]{2,}/gi],
  ["fetch", /\bfetch\s*\(/g],
  ["XMLHttpRequest", /XMLHttpRequest/g],
  ["WebSocket", /\bWebSocket\b/g],
  ["EventSource", /\bEventSource\b/g],
  ["importScripts", /importScripts/g],
  ["CSS @import", /@import/g],
  ["sendBeacon", /sendBeacon/g],
  ["dynamic import", /\bimport\s*\(/g],
  ["src 속성", /\ssrc=/g],
  ["href 속성", /\shref=/g],
  ["CSS url()", /url\(/g],
];
for(const [name, re] of banned){
  const m = html.match(re) || [];
  ok(`${name} 없음`, m.length===0, `${m.length}건: ${[...new Set(m)].slice(0,3).join(" ")}`);
}

console.log("── 단일 파일 완결성 ──");
eq("script 블록 1개 (인라인)", (html.match(/<script>/g)||[]).length, 1);
eq("script src 없음", (html.match(/<script[^>]+src/g)||[]).length, 0);
eq("style 블록 1개 (인라인)", (html.match(/<style>/g)||[]).length, 1);
eq("link 태그 없음", (html.match(/<link/g)||[]).length, 0);
eq("img 태그 없음", (html.match(/<img/g)||[]).length, 0);
eq("iframe 없음", (html.match(/<iframe/g)||[]).length, 0);

console.log("── 시스템 폰트만 사용 ──");
const fonts = [...new Set(html.match(/font-family:[^;}]*/g) || [])];
ok("웹폰트 참조 없음", !fonts.some(f=>/\.woff|\.ttf|\.otf|googleapis/i.test(f)), fonts.join(" | "));
console.log("  " + fonts.join("\n  "));

console.log("── 데이터 임베드 확인 ──");
ok("선수 DB 가 파일 안에 있다", html.includes('"players":['), "임베드 실패");
const m = html.match(/"players":\[/);
ok("자리표시자가 치환됐다", !html.includes("__PLAYERS_JSON__"), "치환 안 됨");
ok("</script> 이스케이프 처리", !/<\/script>/.test(html.slice(html.indexOf("<script>")+8, html.lastIndexOf("</script>"))), "조기 종료 위험");

console.log("── 저장은 브라우저 로컬에만 ──");
ok("localStorage 사용", html.includes("localStorage"));
ok("쿠키 미사용", !html.includes("document.cookie"));
ok("외부 전송 코드 없음", !/navigator\.(sendBeacon|connection)/.test(html));

summary();
