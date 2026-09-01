// console.html 의 <script> 를 최소 DOM 셧 위에서 실제로 실행한다.
// 검색·최대입찰가·커밋·철회·되돌리기를 브라우저 없이 검증하기 위한 것.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const ROOT = path.resolve(import.meta.dirname, "..");

function stubEl(id){
  const e = {
    id, _html:"", value:"", textContent:"", placeholder:"", innerHTML:"",
    classList:{ _s:new Set(),
      add(c){this._s.add(c)}, remove(c){this._s.delete(c)},
      contains(c){return this._s.has(c)} },
    style:{}, dataset:{},
    addEventListener(){}, focus(){}, click(){},
    querySelectorAll(){return []}, querySelector(){return null},
    appendChild(){}, remove(){},
    set onclick(_v){}, set onchange(_v){},
  };
  Object.defineProperty(e, "innerHTML", {
    get(){return e._html}, set(v){e._html = String(v)},
  });
  return e;
}

export function load(file = "console.html"){
  const html = fs.readFileSync(path.join(ROOT, file), "utf8");
  const m = html.match(/<script>\n([\s\S]*?)\n<\/script>\s*$/);
  if(!m) throw new Error("script 블록을 찾지 못했다");
  const code = m[1].replace(/<\\\//g, "</");

  const els = new Map();
  const get = id => { if(!els.has(id)) els.set(id, stubEl(id)); return els.get(id); };
  const store = new Map();

  const sandbox = {
    document: {
      getElementById: get,
      addEventListener(){},
      createElement: () => stubEl("tmp"),
      body: { appendChild(){}, },
      activeElement: null,
    },
    localStorage: {
      getItem: k => (store.has(k) ? store.get(k) : null),
      setItem: (k,v) => store.set(k, String(v)),
    },
    window: {},
    console, setTimeout, clearTimeout, Blob:class{}, FileReader:class{},
    URL:{createObjectURL:()=>"", revokeObjectURL(){}},
    confirm: () => true,
    setInterval: () => 0, clearInterval(){},
    Date,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, {filename:"console.html"});

  // 내부 함수/상태를 테스트에서 쓰기 위해 스코프에서 끌어낸다
  const api = vm.runInContext(`({
    search, derive, commit, cancelPick, undo, redo, choose, addAdhoc,
    resetEntry, render, recompute, blank, foldEn, choseong,
    nominator, nomQueue, advanceNom, retreatNom, canNominate, nomAtPos,
    normOrder, S_defaultOrder, renderCard, renderBoard, shortName, CATS, fmtCat,
    validate, teamPos, maxPosMatch, replayI3, SLOT_POS, renderInv, parseOrderText,
    liveOpen, liveBid, liveSell, liveCancel, liveHigh, liveLeft, toggleMode,
    openHelp, closeHelp,
    commitWith, CLOSE_SEC, renderLive, resultsCsv, CSV_HEADER, csvCell, parseLiveBid,
    renderResults,
    get S(){return S}, set S(v){S=v},
    get stage(){return stage}, set stage(v){stage=v},
    get pick(){return pick}, set pick(v){pick=v},
    get team(){return team}, set team(v){team=v},
    get taken(){return taken},
    get nomPos(){return S.nomPos}, set nomPos(v){S.nomPos=v},
    IDX, DB, TOTAL, SLOTS, BUDGET, NTEAM,
    q: document.getElementById("q"),
  })`, sandbox);
  api.reset = () => { api.S = api.blank(); api.recompute(); api.resetEntry(); };
  api.html = id => get(id).innerHTML;          // 렌더 산출 문자열 검증용
  api.text = id => get(id).innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return api;
}

let pass=0, fail=0;
export function ok(name, cond, detail=""){
  if(cond) { pass++; console.log(`  PASS  ${name}`); }
  else { fail++; console.log(`  FAIL  ${name}${detail?"  → "+detail:""}`); }
}
export function eq(name, got, want){
  ok(name, JSON.stringify(got)===JSON.stringify(want), `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
}
export function summary(){
  console.log(`\n${pass} pass / ${fail} fail`);
  process.exit(fail?1:0);
}
