const STORAGE_KEY = "chrono-slate:v2";

const DIFFICULTIES = /** @type {const} */ ({
  beginner: "初心者",
  elementary: "小学生",
  junior: "中学生",
  high: "高校生",
  adult: "大人",
});

const MISSION_MAX = 10;
const SLATE_SLOTS = 16;
const FRAG_MAX = 10; // 10問＝10欠片（本章）

// 0..9 の欠片は「置くべき場所(0..15)」が固定。DQ7風に“場所一致”。
const FRAGMENTS = /** @type {const} */ ([
  { id: 0, slot: 0, sig: "A1" },
  { id: 1, slot: 5, sig: "B2" },
  { id: 2, slot: 10, sig: "C3" },
  { id: 3, slot: 15, sig: "D4" },
  { id: 4, slot: 3, sig: "A4" },
  { id: 5, slot: 12, sig: "D1" },
  { id: 6, slot: 6, sig: "B3" },
  { id: 7, slot: 9, sig: "C2" },
  { id: 8, slot: 1, sig: "A2" },
  { id: 9, slot: 14, sig: "D3" },
]);

// スパイ映画っぽい暗号/法則/ひらめき中心。図表はHTMLで出せるように html を用意。
// answers は「表記ゆれ」対策で複数許容（normalize後に比較）。
const PUZZLE_SETS = {
  beginner: [
    {
      id: "m01",
      title: "M1//起動：コードネーム",
      body: "『ERA』を反対から読むと？（カタカナ2文字）",
      hint: "逆から読むだけ。",
      answers: ["アレ"],
      rewardFragId: 0,
    },
    {
      id: "m02",
      title: "M2//石板：場所一致①",
      body: "石板のマスは 10×10。上から2段目、左から2番目のマスは『B2』。上から5段目、左から3番目のマスは、『  』だ",
      hint: "アルファベットは縦、数字は横。",
      answers: ["C5"],
      rewardFragId: 1,
    },
    {
      id: "m03",
      title: "M3//タイム回路：同じにする",
      body: "PRESENT TIME と DESTINATION TIME を『同じ』にするとき、同じは何を表している？（カタカナ2文字）",
      hint: "同じを英語で、SAMEという",
      answers: ["サメ"],
      rewardFragId: 2,
    },
    {
      id: "m04",
      title: "M4//分岐：AかB",
      body: "次のうち『偶数』はどっち？ A=7  /  B=8（答えは A か B）",
      hint: "2で割り切れる数。",
      answers: ["B"],
      setBranch: "B",
      rewardFragId: 3,
    },
    {
      id: "m05",
      title: "M5//暗号：ずらす①",
      body: "アルファベットを1つ進める暗号。B→C。では Z→？（1文字）",
      hint: "Aに戻る。",
      answers: ["A"],
      rewardFragId: 4,
    },
    {
      id: "m06",
      title: "M6//法則：仲間はずれ",
      body: "仲間はずれはどれ？  りんご / みかん / バナナ / えんぴつ（ひらがなで）",
      hint: "食べ物じゃないもの。",
      answers: ["えんぴつ"],
      rewardFragId: 5,
    },
    {
      id: "m07",
      title: "M7//表：たし算",
      body: "次の表で ? に入る数は？（数字）",
      html:
        '<div class="puzzle__figure"><div class="puzzle__figureTitle">TABLE</div><table class="puzzle__table" aria-label="加法表"><tr><th>□</th><th>1</th><th>2</th></tr><tr><th>3</th><td>4</td><td>5</td></tr><tr><th>4</th><td>5</td><td>?</td></tr></table><div class="tiny">ルール：行見出し＋列見出し</div></div>',
      hint: "4+2。",
      answers: ["6"],
      rewardFragId: 6,
    },
    {
      id: "m08",
      title: "M8//なぞなぞ",
      body: "『　暗いときに使わず、夜に使う』もの。なに？（ひらがな）",
      hint: "寝る時に使う。",
      answers: ["まくら"],
      rewardFragId: 7,
    },
    {
      id: "m09",
      title: "M9//タイム：順番",
      body: "1→2→3→？ の次は？（数字）",
      hint: "順番どおり。",
      answers: ["4"],
      rewardFragId: 8,
    },
    {
      id: "m10",
      title: "M10//石板：完成条件",
      body: "石板の欠片シグナル『S1』は、スロット番号(0〜15)で何番？（左上0、右へ+1、下へ+4）",
      hint: "S=3行目、1列目。",
      answers: ["13"],
      rewardFragId: 9,
    },
  ],

  elementary: [
    {
      id: "m01",
      title: "M1//スパイ暗号：あたま読み",
      body: "次の言葉の『最初の文字』だけ読むと何になる？\n\nサクラ / イヌ / トカゲ\n（カタカナ3文字）",
      hint: "頭文字をつなぐ。",
      answers: ["サイト"],
      rewardFragId: 0,
    },
    {
      id: "m02",
      title: "M2//石板：場所一致①",
      body: "石板の座標は A1〜D4。左上はA1。右下は？（例: A1）",
      hint: "縦A〜D、横1〜4。",
      answers: ["D4"],
      rewardFragId: 1,
    },
    {
      id: "m03",
      title: "M3//法則：増え方",
      body: "2, 4, 7, 11, 16, ？（数字）",
      hint: "増える数が1ずつ大きくなる。",
      answers: ["22"],
      rewardFragId: 2,
    },
    {
      id: "m04",
      title: "M4//分岐：未来へ行く",
      body: "次のうち“未来”っぽいのはどっち？ A=1999 / B=2035（答えはAかB）",
      hint: "年が大きいほう。",
      answers: ["B"],
      setBranch: "B",
      rewardFragId: 3,
    },
    {
      id: "m05",
      title: "M5//暗号：ずらす②",
      body: "A→C、B→D のように『2つ先』にずらす。では X→？（1文字）",
      hint: "X→Y→Z→A。",
      answers: ["Z"],
      rewardFragId: 4,
    },
    {
      id: "m06",
      title: "M6//図：矢印パズル",
      body: "矢印をたどると最後はどの文字？（1文字）",
      html:
        '<div class="puzzle__figure"><div class="puzzle__figureTitle">GRID</div><div class="puzzle__grid3" aria-label="矢印グリッド"><div class="puzzle__cell">A →</div><div class="puzzle__cell">B ↓</div><div class="puzzle__cell">C</div><div class="puzzle__cell">D</div><div class="puzzle__cell">E →</div><div class="puzzle__cell">F</div><div class="puzzle__cell">G</div><div class="puzzle__cell">H</div><div class="puzzle__cell">I</div></div><div class="tiny">スタートは左上(A)。矢印の方向へ移動。</div></div>',
      hint: "A→B→E→F。",
      answers: ["F"],
      rewardFragId: 5,
    },
    {
      id: "m07",
      title: "M7//国語：ことば遊び",
      body: "『かいだん』を1文字だけ変えて『かいせん』にしたい。どこを何に変える？（答えは変更後の言葉）",
      hint: "“だ”を“せ”に。",
      answers: ["かいせん"],
      rewardFragId: 6,
    },
    {
      id: "m08",
      title: "M8//理科：影",
      body: "太陽が西にあるとき、影はどっちにできる？（ひらがな3文字）",
      hint: "反対側。",
      answers: ["ひがし"],
      rewardFragId: 7,
    },
    {
      id: "m09",
      title: "M9//算数：時計",
      body: "3時の短い針はどの数字の近く？（数字）",
      hint: "そのまま。",
      answers: ["3"],
      rewardFragId: 8,
    },
    {
      id: "m10",
      title: "M10//石板：場所一致②",
      body: "石板の『B3』は、上から何段目・左から何番目？（例: 1-1 のように）",
      hint: "Bは2段目、3は左から3番目。",
      answers: ["2-3", "2ー3", "2−3"],
      rewardFragId: 9,
    },
  ],

  junior: [
    {
      id: "m01",
      title: "M1//英語×発想：二重の意味",
      body: "『TIME FLIES』のFLIESは“飛ぶ”以外に何の意味がある？（カタカナ2文字）",
      hint: "虫の名前。",
      answers: ["ハエ"],
      rewardFragId: 0,
    },
    {
      id: "m02",
      title: "M2//暗号：シーザー(3)",
      body: "暗号文：KHOOR  をシーザー暗号(3つ戻す)で復号すると？（英大文字）",
      hint: "K→H。",
      answers: ["HELLO"],
      rewardFragId: 1,
    },
    {
      id: "m03",
      title: "M3//法則：差の差",
      body: "1, 2, 4, 7, 11, 16, ?（数字）",
      hint: "+1,+2,+3,+4,+5…",
      answers: ["22"],
      rewardFragId: 2,
    },
    {
      id: "m04",
      title: "M4//分岐：パラドックス回避",
      body: "『過去を変えると未来が変わる』。この考え方に近い言葉はどっち？ A=因果 / B=無関係（答えはAかB）",
      hint: "原因と結果。",
      answers: ["A"],
      setBranch: "A",
      rewardFragId: 3,
    },
    {
      id: "m05",
      title: "M5//数学：座標",
      body: "石板座標B2を(行,列)=(?,?)で表すと？（例: 1,1）",
      hint: "B=2行目。",
      answers: ["2,2", "2，2", "2 2"],
      rewardFragId: 4,
    },
    {
      id: "m06",
      title: "M6//表：入れ替え",
      body: "次の表の規則で ? は何？（数字）",
      html:
        '<div class="puzzle__figure"><div class="puzzle__figureTitle">TABLE</div><table class="puzzle__table" aria-label="規則表"><tr><th>入力</th><th>出力</th></tr><tr><td>12</td><td>21</td></tr><tr><td>34</td><td>43</td></tr><tr><td>56</td><td>?</td></tr></table><div class="tiny">ヒント：左右を入れ替え</div></div>',
      hint: "56→65。",
      answers: ["65"],
      rewardFragId: 5,
    },
    {
      id: "m07",
      title: "M7//理科：電気",
      body: "乾電池の＋極と−極をつなぐと電流はどっち向き？（＋→− / −→＋ のどちらかで回答）",
      hint: "中学理科の定義（電流は＋から−）。",
      answers: ["+->-", "＋→−", "+→-"],
      rewardFragId: 6,
    },
    {
      id: "m08",
      title: "M8//国語：回文",
      body: "『たけやぶやけた』は回文。回文の条件を一言で言うと？（ひらがな3文字）",
      hint: "前から読んでも後ろから読んでも…",
      answers: ["おなじ"],
      rewardFragId: 7,
    },
    {
      id: "m09",
      title: "M9//社会：時差の発想",
      body: "日本が昼なら、地球の反対側は“だいたい”何？（ひらがな2文字）",
      hint: "夜。",
      answers: ["よる"],
      rewardFragId: 8,
    },
    {
      id: "m10",
      title: "M10//スパイ：並べ替え",
      body: "文字列『ＭＩＴＥ』を“時間順”っぽく並べ替えると…？（英大文字4文字）",
      hint: "TIMEのまま…ではない。時計は『T I M E』をそのまま読む？発想問題。",
      answers: ["TIME"],
      rewardFragId: 9,
    },
  ],

  high: [
    {
      id: "m01",
      title: "M1//暗号：だじゃれ",
      body: "暗号文：ＴＥＬ 。〇〇〇に〇〇〇（ひらがな3文字）",
      hint: "よく聴くだじゃれ",
      answers: ["でんわ"],
      rewardFragId: 0,
    },
    {
      id: "m02",
      title: "M2//数学：並び",
      body: "1, 1, 2, 3, 5, 8, ?（数字）",
      hint: "フィボナッチ。",
      answers: ["13"],
      rewardFragId: 1,
    },
    {
      id: "m03",
      title: "M3//国語：同音異義",
      body: "『はんてん』は3つ以上の意味がある。1つ答えて（漢字2文字）",
      hint: "反転/斑点/飯店…など。",
      answers: ["反転", "斑点", "飯店"],
      rewardFragId: 2,
    },
    {
      id: "m04",
      title: "M4//分岐：条件論理",
      body: "『もしAならB』が真で、Aが真のとき、Bは？（真/偽）",
      hint: "命題の基本。",
      answers: ["真"],
      setBranch: "A",
      rewardFragId: 3,
    },
    {
      id: "m05",
      title: "M5//表：魔方陣",
      body: "3×3の魔方陣。縦横斜めの合計が全部15になる。?に入る数は？",
      html:
        '<div class="puzzle__figure"><div class="puzzle__figureTitle">MAGIC</div><div class="puzzle__grid3"><div class="puzzle__cell">8</div><div class="puzzle__cell">1</div><div class="puzzle__cell">6</div><div class="puzzle__cell">3</div><div class="puzzle__cell">5</div><div class="puzzle__cell">7</div><div class="puzzle__cell">4</div><div class="puzzle__cell">9</div><div class="puzzle__cell">?</div></div></div>',
      hint: "最下段も15。",
      answers: ["2"],
      rewardFragId: 4,
    },
    {
      id: "m06",
      title: "M6//英語：アナグラム",
      body: "『LISTEN』が『サイレント』。では『EARTH』は、「　　　」になる（答えはカタカナ3文字）",
      hint: "並び変える",
      answers: ["ハート"],
      rewardFragId: 5,
    },
    {
      id: "m07",
      title: "M7//理科：波",
      body: "波の速さ v は v=λf。λ=2, f=3 のとき v=?（数字）",
      hint: "掛け算。",
      answers: ["6"],
      rewardFragId: 6,
    },
    {
      id: "m08",
      title: "M8//社会：地図記号",
      body: "地図記号で『郵便局』は“〒”みたいな形。では『市役所』の記号は何で表されることが多い？（記号）",
      hint: "市役所の地図記号",
      answers: ["◎"],
      rewardFragId: 7,
    },
    {
      id: "m09",
      title: "M9//スパイ：二段読み",
      body: "次の2行を並べ替えると？（ひらがな6文字）\n\nた い か\nい く ん",
      hint: "列ごとに上→下。",
      answers: ["たいいくかん"],
      rewardFragId: 8,
    },
    {
      id: "m10",
      title: "M10//石板：座標推理",
      body: "欠片シグナル『D3』はスロット番号(0〜15)で何番？（左上0、右へ+1、下へ+4）",
      hint: "D=4行目、3列目。",
      answers: ["14"],
      rewardFragId: 9,
    },
  ],

  adult: [
    {
      id: "m01",
      title: "M1//スパイ：情報圧縮",
      body: "次の文の“母音(A,I,U,E,O)”だけ抜き出せ。\n\nCHRAN SLTI\n（英大文字で）",
      hint: "A,E,I,O,U のみ抽出。",
      answers: ["AI"],
      rewardFragId: 0,
    },
    {
      id: "m02",
      title: "M2//暗号：鍵付き(簡易)",
      body: "鍵=3。文字を3つ戻す。暗号文：FDYD（英大文字）",
      hint: "F→C。",
      answers: ["CAVA"],
      rewardFragId: 1,
    },
    {
      id: "m03",
      title: "M3//論理：矛盾",
      body: "A『私は嘘つきだ』が真だと矛盾する。こういう文を何という？（カタカナ6文字）",
      hint: "有名な“パラ…”",
      answers: ["パラドックス"],
      rewardFragId: 2,
    },
    {
      id: "m04",
      title: "M4//分岐：二択の最適",
      body: "タイムラインAは“安全”だが遅い。Bは“危険”だが速い。任務優先ならどっち？（AかB）",
      hint: "任務＝スピード優先。",
      answers: ["B"],
      setBranch: "B",
      rewardFragId: 3,
    },
    {
      id: "m05",
      title: "M5//表：規則推理",
      body: "次の表で ? は？（数字）",
      html:
        '<div class="puzzle__figure"><div class="puzzle__figureTitle">MATRIX</div><table class="puzzle__table" aria-label="行列"><tr><td>1</td><td>2</td><td>3</td></tr><tr><td>2</td><td>4</td><td>6</td></tr><tr><td>3</td><td>6</td><td>?</td></tr></table><div class="tiny">行×列（九九の一部）</div></div>',
      hint: "3×3。",
      answers: ["9"],
      rewardFragId: 4,
    },
    {
      id: "m06",
      title: "M6//暗号：並び替え(列転置)",
      body: "『A T I E』を2列に交互に書く。\n1列目: A I / 2列目: T E\n1列目→2列目の順に読むと？（英大文字4）",
      hint: "AITE。",
      answers: ["AITE"],
      rewardFragId: 5,
    },
    {
      id: "m07",
      title: "M7//ひらめき：見立て",
      body: "『石板』を“年間の表”に言い換えると？（漢字2文字）",
      hint: "歴史の板＝年表。",
      answers: ["年表"],
      rewardFragId: 6,
    },
    {
      id: "m08",
      title: "M8//論理：最短",
      body: "A→B→Cのうち最短で“情報漏洩”を防ぐならどれを最初に止める？\nA=入口 / B=廊下 / C=金庫（答えはA/B/C）",
      hint: "入口を止める。",
      answers: ["A"],
      rewardFragId: 7,
    },
    {
      id: "m09",
      title: "M9//タイム：逆算",
      body: "今から90分後は、今から何時間何分後？（例: 1時間30分）",
      hint: "60分=1時間。",
      answers: ["1時間30分"],
      rewardFragId: 8,
    },
    {
      id: "m10",
      title: "M10//石板：場所一致・最終",
      body: "欠片『D3』の正しい位置は、上から何段目・左から何番目？（例: 1-1）",
      hint: "D=4段目、3=左から3番目。",
      answers: ["4-3", "4ー3", "4−3"],
      rewardFragId: 9,
    },
  ],
};

const DEFAULT_STATE = {
  difficulty: "beginner",
  puzzleIndex: 0,
  solved: {},
  branch: null,
  inventory: [], // 取得した欠片 id
  placements: {}, // slotIndex -> fragId
  selectedFragId: null,
  destIso: null,
  lastIso: null,
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_STATE };
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_STATE,
      ...parsed,
      solved: parsed?.solved ?? {},
      inventory: Array.isArray(parsed?.inventory) ? parsed.inventory : [],
      placements: parsed?.placements && typeof parsed.placements === "object" ? parsed.placements : {},
    };
  } catch {
    return { ...DEFAULT_STATE };
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function fmt(iso) {
  if (!iso) return "----/--/-- --:--:--";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "----/--/-- --:--:--";
  return `${d.getFullYear()}/${pad2(d.getMonth() + 1)}/${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function nowMeta() {
  const d = new Date();
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function normalizeAnswer(s) {
  return (s ?? "")
    .trim()
    .replace(/[\u3000\s]+/g, "")
    .toUpperCase();
}

function rngSig(i) {
  const bank = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const a = bank[(i * 7) % bank.length];
  const b = bank[(i * 13 + 5) % bank.length];
  return `${a}${b}-${String(i + 1).padStart(2, "0")}`;
}

function el(id) {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing element: ${id}`);
  return node;
}

function logLine(text, kind = "") {
  const line = document.createElement("div");
  line.className = `log__line${kind ? ` log__line--${kind}` : ""}`;
  line.textContent = text;
  el("log").prepend(line);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getSet(state) {
  return PUZZLE_SETS[state.difficulty] ?? PUZZLE_SETS.beginner;
}

function getActivePuzzle(state) {
  const set = getSet(state);
  const idx = Math.min(state.puzzleIndex, set.length - 1);
  return set[idx] ?? null;
}

function fragById(id) {
  return FRAGMENTS.find((f) => f.id === id) ?? null;
}

function slotCoord(slotIndex) {
  const row = Math.floor(slotIndex / 4);
  const col = slotIndex % 4;
  const letters = ["A", "B", "C", "D"];
  return `${letters[row] ?? "?"}${col + 1}`;
}

function isSlotLocked(slotIndex) {
  // 本章は10欠片だけ使う（残りはロック表示）
  const usedSlots = new Set(FRAGMENTS.map((f) => f.slot));
  return !usedSlots.has(slotIndex);
}

function renderTray(state) {
  const tray = el("slateTray");
  tray.innerHTML = "";

  const placed = new Set(Object.values(state.placements).map((v) => Number(v)));

  for (const fragId of state.inventory) {
    const f = fragById(fragId);
    if (!f) continue;

    const b = document.createElement("button");
    b.type = "button";
    b.className = `frag${state.selectedFragId === fragId ? " frag--selected" : ""}${placed.has(fragId) ? " frag--used" : ""}`;
    b.textContent = `FRAG ${String(f.id + 1).padStart(2, "0")} ${f.sig}`;
    b.disabled = placed.has(fragId);
    b.addEventListener("click", () => {
      state.selectedFragId = fragId;
      saveState(state);
      renderAll(state);
      logLine(`SELECT: FRAG ${f.id + 1} (${f.sig})`, "hint");
    });
    tray.appendChild(b);
  }

  if (tray.childElementCount === 0) {
    const msg = document.createElement("div");
    msg.className = "tiny";
    msg.textContent = "欠片はここに並びます（まずは謎を解こう）";
    tray.appendChild(msg);
  }
}

function renderSlate(state) {
  const grid = el("slateGrid");
  grid.innerHTML = "";

  for (let slot = 0; slot < SLATE_SLOTS; slot += 1) {
    const cell = document.createElement("button");
    cell.type = "button";
    const locked = isSlotLocked(slot);
    cell.className = `slatecell${locked ? " slatecell--locked" : ""}`;
    cell.setAttribute("role", "gridcell");

    const coord = document.createElement("div");
    coord.className = "slatecell__coord";
    coord.textContent = slotCoord(slot);
    cell.appendChild(coord);

    const placedFragId = Object.prototype.hasOwnProperty.call(state.placements, String(slot)) ? Number(state.placements[String(slot)]) : null;
    const placedFrag = placedFragId !== null ? fragById(placedFragId) : null;

    const sig = document.createElement("div");
    sig.className = "slatecell__sig";
    sig.textContent = placedFrag ? placedFrag.sig : locked ? "LOCK" : "—";

    cell.appendChild(sig);

    cell.addEventListener("click", () => {
      if (locked) {
        logLine(`SLOT ${slotCoord(slot)}: LOCKED`, "bad");
        return;
      }

      const fragId = state.selectedFragId;
      if (fragId === null || fragId === undefined) {
        logLine("SELECT A FRAGMENT FIRST", "hint");
        return;
      }
      const f = fragById(fragId);
      if (!f) {
        logLine("INVALID FRAGMENT", "bad");
        return;
      }
      if (f.slot !== slot) {
        logLine(`DENIED: ${f.sig} → ${slotCoord(slot)}`, "bad");
        return;
      }
      state.placements[String(slot)] = fragId;
      state.selectedFragId = null;
      saveState(state);
      renderAll(state);
      cell.classList.add("slatecell--pulse");
      setTimeout(() => cell.classList.remove("slatecell--pulse"), 900);
      logLine(`PLACED: ${f.sig} @ ${slotCoord(slot)}`, "good");
    });

    grid.appendChild(cell);
  }
}

function renderTime(state) {
  el("presentTime").textContent = fmt(new Date().toISOString());
  el("destTime").textContent = fmt(state.destIso);
  el("lastTime").textContent = fmt(state.lastIso);

  const input = el("destInput");
  if (state.destIso) {
    const d = new Date(state.destIso);
    if (!Number.isNaN(d.getTime())) {
      const value = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
      input.value = value;
    }
  }
}

function syncFx(state) {
  const placedCount = Object.keys(state.placements).length;
  if (placedCount === 0) {
    logLine("SYNC: NO SIGNAL", "bad");
    return;
  }
  if (placedCount < 4) {
    logLine(`SYNC: PARTIAL LOCK (${placedCount}/${FRAG_MAX})`, "hint");
    return;
  }
  if (placedCount < FRAG_MAX) {
    logLine(`SYNC: STABLE... (${placedCount}/${FRAG_MAX})`, "good");
    return;
  }
  logLine("SYNC: FULL RESONANCE — TIMELINE STABILIZED", "good");
}

function renderPuzzle(state) {
  const p = getActivePuzzle(state);
  const set = getSet(state);

  el("missionMax").textContent = String(MISSION_MAX);
  el("missionNow").textContent = String(Math.min(state.puzzleIndex + 1, MISSION_MAX));
  el("timelineNow").textContent = state.branch ?? "—";

  const title = p ? `${p.title}\n${p.body}` : "全ミッション完了（次の章を追加してね）";
  const html = p?.html ? `${escapeHtml(p.title)}<br>${escapeHtml(p.body)}${p.html}` : escapeHtml(title).replaceAll("\n", "<br>");
  el("puzzleText").innerHTML = html;

  const placedCount = Object.keys(state.placements).length;
  el("fragMax").textContent = String(FRAG_MAX);
  el("fragCount").textContent = String(placedCount);
  el("missingCount").textContent = String(Math.max(0, FRAG_MAX - placedCount));

  // 難易度セレクタ同期
  const sel = el("difficulty");
  if (sel.value !== state.difficulty) sel.value = state.difficulty;
  // set長の保険
  if (state.puzzleIndex >= set.length) {
    el("missionNow").textContent = String(MISSION_MAX);
  }
}

function renderAll(state) {
  el("metaNow").textContent = nowMeta();
  renderPuzzle(state);
  renderSlate(state);
  renderTray(state);
  renderTime(state);
}

function submitAnswer(state) {
  const p = getActivePuzzle(state);
  if (!p) {
    logLine("NO ACTIVE PUZZLE", "hint");
    return;
  }

  const raw = el("answer").value;
  const ans = normalizeAnswer(raw);

  if (!ans) {
    logLine("EMPTY INPUT", "bad");
    return;
  }

  const ok = p.answers.map(normalizeAnswer).includes(ans);

  if (!ok) {
    logLine(`DENIED: ${raw}`, "bad");
    return;
  }

  state.solved[p.id] = true;
  if (p.setBranch) state.branch = p.setBranch;

  // 10問＝10欠片（重複は無視）
  if (typeof p.rewardFragId === "number") {
    if (!state.inventory.includes(p.rewardFragId)) {
      state.inventory.push(p.rewardFragId);
    }
  }

  // 次へ
  const set = getSet(state);
  state.puzzleIndex = Math.min(set.length, state.puzzleIndex + 1);

  saveState(state);
  el("answer").value = "";
  logLine(`ACCESS GRANTED: ${p.id}`, "good");
  if (typeof p.rewardFragId === "number") {
    const f = fragById(p.rewardFragId);
    logLine(`REWARD: FRAGMENT ${String(p.rewardFragId + 1).padStart(2, "0")} ${f?.sig ?? ""}`, "good");
  }
  if (p.setBranch) {
    logLine(`TIMELINE SET: ${p.setBranch}`, "hint");
  }

  renderAll(state);
}

function main() {
  const state = loadState();

  // 初期ログ（過剰に増えないように1回だけ）
  if (!state.solved.__boot_logged) {
    logLine("BOOT: CHRONO SLATE ONLINE", "good");
    logLine("M1: AWAITING INPUT", "hint");
    state.solved.__boot_logged = true;
    saveState(state);
  }

  renderAll(state);

  setInterval(() => {
    el("metaNow").textContent = nowMeta();
    el("presentTime").textContent = fmt(new Date().toISOString());
  }, 1000);

  el("btnSubmit").addEventListener("click", () => submitAnswer(state));
  el("answer").addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitAnswer(state);
  });

  el("difficulty").addEventListener("change", (e) => {
    const v = e.target?.value;
    if (!v || !Object.prototype.hasOwnProperty.call(DIFFICULTIES, v)) return;
    state.difficulty = v;
    state.puzzleIndex = 0;
    state.branch = null;
    state.inventory = [];
    state.placements = {};
    state.selectedFragId = null;
    state.solved = { __boot_logged: true };
    saveState(state);
    el("log").innerHTML = "";
    logLine(`MODE: ${DIFFICULTIES[v]}`, "hint");
    renderAll(state);
  });

  el("btnHint").addEventListener("click", () => {
    const p = getActivePuzzle(state);
    if (!p) return;
    logLine(`HINT: ${p.hint}`, "hint");
  });

  el("btnSkip").addEventListener("click", () => {
    const set = getSet(state);
    state.puzzleIndex = Math.min(set.length, state.puzzleIndex + 1);
    saveState(state);
    logLine("SKIP: NEXT PUZZLE", "hint");
    renderAll(state);
  });

  el("btnAssemble").addEventListener("click", () => {
    const placedCount = Object.keys(state.placements).length;
    if (placedCount < FRAG_MAX) {
      logLine(`ASSEMBLE FAILED: ${placedCount}/${FRAG_MAX}`, "bad");
      return;
    }
    logLine("ASSEMBLE: SLATE RESTORED", "good");
    syncFx(state);
  });

  el("btnShuffle").addEventListener("click", () => {
    // 演出だけ（場所一致のため、配置は変えない）
    logLine("SHUFFLE: RELIC MATRIX REPHASED", "hint");
    saveState(state);
    renderAll(state);
  });

  el("btnSetDest").addEventListener("click", () => {
    const v = el("destInput").value;
    if (!v) {
      logLine("DEST: EMPTY", "bad");
      return;
    }
    const iso = new Date(v).toISOString();
    state.destIso = iso;
    saveState(state);
    logLine(`DEST SET: ${fmt(iso)}`, "good");
    renderAll(state);
  });

  el("btnDepart").addEventListener("click", () => {
    state.lastIso = new Date().toISOString();
    saveState(state);
    logLine("DEPARTURE RECORDED", "good");
    renderAll(state);
  });

  el("btnSync").addEventListener("click", () => syncFx(state));

  el("btnReset").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    location.reload();
  });

  // build id (cache bust用に後で入れ替え可能)
  el("buildId").textContent = "static";
}

main();
