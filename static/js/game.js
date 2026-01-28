const STORAGE_KEY = "tmhk_are_save_v1";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  return node;
};

const toastEl = $("#toast");
let toastTimer = null;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("toast--show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("toast--show"), 1600);
}

// --- 登場人物（約10名）
// 直接の既存作品の固有設定は使わず、雰囲気だけをミックスしたオリジナル。
const PARTICIPANTS = [
  { id: "haruya", name: "はるや", role: "しゅじんこう / ひらめき" },
  { id: "momone", name: "ももね", role: "しゅじんこう / みつける力" },
  { id: "tarou", name: "たろう", role: "さんかしゃ / くちぐせ『まあいける』" },
  { id: "akane", name: "あかね", role: "さんかしゃ / あんごうすき" },
  { id: "souta", name: "そうた", role: "さんかしゃ / ちからじまん" },
  { id: "rin", name: "りん", role: "さんかしゃ / れいせい" },
  { id: "kei", name: "けい", role: "さんかしゃ / けいさん" },
  { id: "madoka", name: "まどか", role: "さんかしゃ / くうきをよむ" },
  { id: "shun", name: "しゅん", role: "さんかしゃ / しかけ" },
  { id: "hikari", name: "ひかり", role: "さんかしゃ / きおくりょく" },
];

// --- 難易度
// 要件: 小学生向け（やさしい）を基本にしつつ、区分を用意。
const DIFFICULTIES = {
  easy: { label: "やさしい", target: "しょうがくせいむけ", timeMul: 1.15, expMul: 1.0 },
  normal: { label: "ふつう", target: "こうこうせいむけ", timeMul: 1.0, expMul: 1.05 },
  hard: { label: "むずかしい", target: "おとなむけ", timeMul: 0.9, expMul: 1.15 },
  oni: { label: "おに", target: "かなりむずかしい", timeMul: 0.8, expMul: 1.25 },
  extreme: { label: "げきむず", target: "なぞときずきむけ", timeMul: 0.7, expMul: 1.4 },
};

// --- 「お試しで解く」モード
// 目的：小学生でも迷子にならないように、問題文をやさしく言い換えたり
// 追加ヒント/答え表示（任意）を出せるようにする。
const TRIAL_MODE_LABEL = "お試しで解く";

// --- クエスト（章立て）
const QUESTS = [
  {
    id: "join_are",
    episode: "ぷろろーぐ",
    title: "さんかかくにん",
    location: "しろいへや",
    timeLimitSec: 90,
    difficulty: "easy",
    desc:
      "なぞときゲームに さんかしますか？\nさんかするなら、\n『アレ』\nと いれてね。",
    trialHelp:
      "いれる言葉はカタカナ2文字。『アレ』って いれてね。",
    choices: (st) => [
      {
        label: "はなす",
        run: () => logSys("アナウンサー：さんかの合図（あいず）を おくってね。"),
      },
      {
        label: "しらべる",
        run: () => logSys("まっしろ。でぐちは まだない。"),
      },
      {
        label: "むずかしさ",
        run: () => {
          logSys("むずかしさの めやす：");
          logSys("やさしい＝しょうがくせい / ふつう＝こうこうせい / むずかしい＝おとな");
          logSys("おに＝かなりむずかしい / げきむず＝なぞときずきむけ");
          logSys("※ふだんは『やさしい』でOK。おためしもあるよ。"
          );
        },
      },
      {
        label: TRIAL_MODE_LABEL,
        run: () => toggleTrialMode(),
      },
      { label: "やさしい", run: () => setDifficulty("easy") },
      { label: "ふつう", run: () => setDifficulty("normal") },
      { label: "むずかしい", run: () => setDifficulty("hard") },
      { label: "おに", run: () => setDifficulty("oni") },
      { label: "げきむず", run: () => setDifficulty("extreme") },
      {
        label: "なかま",
        run: () => {
          const r = pick(PARTICIPANTS.filter((p) => p.id !== "haruya"));
          logSys(`${r.name}：『あせらないで。ルールを先に見つけよう。』`);
        },
      },
    ],
  },
  {
    id: "q1_nameplate",
    episode: "だい1わ：じごくのしょうたいじょう",
    title: "Q1 ばんごうふだの るーる",
    location: "しろいへや",
    timeLimitSec: 120,
    difficulty: "easy",
    desc:
      "はるやの札は『HRY』、ももねの札は『MMN』。\nじゃあ『たろう』の札は なに？\n（じかん：2ふん）",
    trialHelp:
      "コツ：名前をローマ字にして、A/I/U/E/O（ぼいん）をぜんぶ ぬく。TA RO U → T R",
    choices: () => [
      { label: "めも", run: () => logSys("HA RU YA → H R Y / MO MO NE → M M N") },
      { label: "そうぞう", run: () => logSys("A/I/U/E/O が きえてる…？") },
    ],
  },
  {
    id: "q2_hidden_button",
    episode: "だい1わ：じごくのしょうたいじょう",
    title: "Q2 かくしぼたん",
    location: "しろいへや",
    timeLimitSec: 120,
    difficulty: "easy",
    desc:
      "アナウンサー『白いかべにボタンがあるよ。場所は「おしろの まんなか」』\nかべには『しろいかべ』って かいてある。\nボタンはどこ？\n（じかん：2ふん）",
    trialHelp:
      "『しろい』の まんなかの1文字を こたえるよ。『し・ろ・い』の まんなかは？",
    choices: () => [
      { label: "かべを見る", run: () => logSys("かべ：しろいかべ") },
      { label: "わける", run: () => logSys("『し・ろ・い』…まんなかは？") },
    ],
  },
  {
    id: "q3_distance",
    episode: "だい2わ：わんなげげーむ",
    title: "Q3 ひきょりの けいさん",
    location: "ひろば",
    timeLimitSec: 180,
    difficulty: "easy",
    desc:
      "『ワン』って言うと10メートル のびる首輪（くびわ）がある。\nももねが『ワン！ワン！』って2回言った。\nなんメートル のびた？\n（じかん：3ぷん）",
    trialHelp:
      "10mが2回ぶん。10×2だよ。",
    choices: () => [
      { label: "はなす", run: () => logSys("ももね：ワン！ ワン！") },
      { label: "けいさん", run: () => logSys("1回=10m。回数（かいすう）を かける。") },
    ],
  },
  {
    id: "q4_hidden_one",
    episode: "だい2わ：わんなげげーむ",
    title: "Q4 なぞの ひきょり",
    location: "ひろば",
    timeLimitSec: 180,
    difficulty: "easy",
    desc:
      "アナウンサー『言葉の中に「わん」が かくれてるものを なげてね。いちばん とぶのはどれ？』\n\n1) サンドウイッチ\n2) わんこそば\n3) 台湾（たいわん）\n（じかん：3ぷん）",
    trialHelp:
      "「わん」が いちばん うしろ（さいご）にあるのが いちばん とぶよ。ばんごう（3）でもOK。",
    choices: () => [
      { label: "こうほ", run: () => logSys("サンドウイッチ / わんこそば / たいわん") },
      { label: "きょり", run: () => logSys("『わん』が いちばん うしろにあるのは…") },
    ],
  },
  {
    id: "q5_safe_food",
    episode: "だい3わ：とげとげーむ",
    title: "Q5 あんぜんな たべもの",
    location: "ますめのゆか",
    timeLimitSec: 240,
    difficulty: "easy",
    desc:
      "ゆかに 3つの食べ物。\nウニ（トゲ）が『1文字も入ってない』あんぜんなのは どれ？\n\n1) シュークリーム\n2) ソフトクリーム\n3) ほうれんそう\n（じかん：4ぷん）",
    trialHelp:
      "言葉あそび：『クリーム』の中に『くり（栗）』がある → 栗の『いが』はトゲ。ばんごう（3）でもOK。",
    choices: () => [
      { label: "ゆか", run: () => logSys("シュークリーム / ソフトクリーム / ほうれんそう") },
      { label: "ことば", run: () => logSys("トゲ＝『くり』…？") },
    ],
  },
  {
    id: "q6_toge_kanji",
    episode: "だい3わ：とげとげーむ",
    title: "Q6 とげの かんじ",
    location: "ますめのゆか",
    timeLimitSec: 240,
    difficulty: "easy",
    desc:
      "『トゲ』がある漢字（かんじ）はどれ？\n\n1) 口\n2) 田\n3) 刺\n（じかん：4ぷん）",
    trialHelp:
      "『トゲ＝さす』を思い出して。『刺（さす）』が近いよ。ばんごう（3）でもOK。",
    choices: () => [
      { label: "かんがえる", run: () => logSys("かたち と いみ…どっちも『トゲ』だ。") },
      { label: "なかま", run: () => logSys("りん：『ちょくかん だけだと まけるよ。』") },
    ],
  },
  {
    id: "q7_are_rule",
    episode: "だい4わ：そういうときはあれだ！",
    title: "Q7 あれの ほうそく",
    location: "こうはんせんかいじょう",
    timeLimitSec: 300,
    difficulty: "easy",
    desc:
      "『雨がふったら、アレだ！』→かさを さす まね\n『おなかがすいたら、アレだ！』→ごはんを食べる まね\nじゃあ『ねむくなったら、アレだ！』って言われたら なにする？\n（じかん：5ぷん）",
    trialHelp:
      "眠いときにすること＝寝る（目を閉じる）まね。",
    choices: () => [
      { label: "れい", run: () => logSys("しぜんな こうどうに『なりきる』ゲームだ。") },
      { label: "そうぞう", run: () => logSys("ねむい → まず なにする？") },
    ],
  },
  {
    id: "q8_are_calc",
    episode: "だい4わ：そういうときはあれだ！",
    title: "Q8 あれの けいさん",
    location: "こうはんせんかいじょう",
    timeLimitSec: 300,
    difficulty: "easy",
    desc:
      "かべに『1122＝アレ』ってある。\n数字を ちがう読み方にすると、ことばになるよ。\nアレはなに？\n（じかん：5ぷん）",
    trialHelp:
      "11を『いい』、22を『ふうふ』と読めるよ。",
    choices: () => [
      { label: "かべ", run: () => logSys("1122＝アレ") },
      { label: "よみ", run: () => logSys("11 と 22 に わけて よむ？") },
    ],
  },
  {
    id: "q9_are_numbers",
    episode: "だい5わ：さいごのひとり",
    title: "Q9 AREの しょうたい",
    location: "もにたーしつ",
    timeLimitSec: 420,
    difficulty: "easy",
    desc:
      "Aは1番目、Bは2番目…って数えるよ。\n『ARE』を数字にすると どうなる？\n（じかん：7ぷん）",
    trialHelp:
      "アルファベット順：A=1、R=18、E=5。『1・18・5』の形でOK。",
    choices: () => [
      { label: "きそく", run: () => logSys("A=1, B=2, C=3 …") },
      { label: "かくにん", run: () => logSys("Rは 18ばんめ。Eは 5ばんめ。") },
    ],
  },
  {
    id: "q10_final_answer",
    episode: "だい5わ：さいごのひとり",
    title: "Q10 さいごの こたえ",
    location: "もにたーしつ",
    timeLimitSec: 600,
    difficulty: "easy",
    desc:
      "モニター：【 100 ＋ 0 ＝ 1 】\n『0』のほんとうの意味を、ひらがな3文字で こたえてね。\n（じかん：10ぷん）",
    trialHelp:
      "0は『ゼロ』じゃなくて『〇（まる）』のこと。ひらがなで3文字。",
    choices: () => [
      { label: "かんがえる", run: () => logSys("0は数字じゃない…“形”かもしれない。") },
      { label: "なかま", run: () => logSys("けい：『しきの いみ を かえてみよう。』") },
    ],
  },
];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// --- 状態
function defaultState() {
  return {
    questIndex: 0,
    activePuzzle: QUESTS[0].id,
    solved: Object.fromEntries(QUESTS.map((q) => [q.id, false])),

    // レベル
    level: 1,
    exp: 0,

    // 難易度（デフォルト：小学生向け）
    difficulty: "easy",

    // お試しで解く（超やさしい補助）
    trialMode: true,

    // タイマー
    timer: { startedAt: null, limitSec: null, expired: false },
  };
}

let state = defaultState();

// --- UI refs
const mapEl = $("#map");
const partyEl = $("#party");
const titleEl = $("#sceneTitle");
const descEl = $("#sceneDesc");
const artEl = $("#sceneArt");
const logEl = $("#log");
const choicesEl = $("#choices");
const answerInput = $("#answerInput");

const questBadge = $("#questBadge");
const difficultyBadge = $("#difficultyBadge");
const trialBadge = $("#trialBadge");
const timerEl = $("#timer");

const statProgress = $("#statProgress");
const statLv = $("#statClues");
const statExp = $("#statKeys");

$("#btnSubmit").addEventListener("click", () => submitAnswer());
$("#btnHint").addEventListener("click", () => requestHint());
$("#btnNew").addEventListener("click", () => newGame());
$("#btnSave").addEventListener("click", () => saveGame());
$("#btnLoad").addEventListener("click", () => loadGame());
answerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitAnswer();
});

function logLine(text, kind = "sys") {
  const p = el("p", `logLine logLine--${kind}`);
  p.textContent = text;
  logEl.appendChild(p);
  logEl.scrollTop = logEl.scrollHeight;
}
const logSys = (t) => logLine(t, "sys");
const logOk = (t) => logLine(t, "ok");
const logNg = (t) => logLine(t, "ng");

function currentQuest() {
  return QUESTS[Math.max(0, Math.min(state.questIndex, QUESTS.length - 1))];
}

function setDifficulty(key) {
  if (!DIFFICULTIES[key]) return;
  state.difficulty = key;
  const d = DIFFICULTIES[key];
  toast(`むずかしさ: ${d.label}`);
  logSys(`むずかしさを『${d.label}（${d.target}）』に かえたよ。`);
  renderAll();
}

function toggleTrialMode() {
  state.trialMode = !state.trialMode;
  toast(state.trialMode ? `${TRIAL_MODE_LABEL}: ON` : `${TRIAL_MODE_LABEL}: OFF`);
  logSys(state.trialMode ? "お試しで解く：ヒント多め（たくさん）だよ。" : "お試しで解く：もとにもどしたよ。"
  );
  renderAll();
}

function baseAnswerFor(puzzleId) {
  // お試しモード用の“答えを見る”。（データはサーバー側の正解に合わせる）
  const map = {
    join_are: "アレ",
    q1_nameplate: "TR",
    q2_hidden_button: "い",
    q3_distance: "20",
    q4_hidden_one: "台湾",
    q5_safe_food: "ほうれんそう",
    q6_toge_kanji: "刺",
    q7_are_rule: "ねる",
    q8_are_calc: "いいふうふ",
    q9_are_numbers: "1・18・5",
    q10_final_answer: "まる",
  };
  return map[puzzleId] || null;
}

function buildChoices(q) {
  const base = q.choices(state);
  if (!state.trialMode) return base;

  const extra = [];
  if (q.trialHelp) {
    extra.push({
      label: "やさしい ひんと",
      run: () => logSys(`ひんと（やさしく）：${q.trialHelp}`),
    });
  }

  extra.push({
    label: "こたえを見る",
    run: () => {
      const ans = baseAnswerFor(q.id);
      if (!ans) {
        logSys("（この問題は答え表示に未対応）");
        return;
      }
      if (!confirm("おためし：こたえを見るよ。OK？")) return;
      logSys(`こたえ：${ans}`);
      answerInput.value = ans;
      toast("入力らんに いれたよ");
    },
  });

  return [...extra, ...base];
}

function isQuestUnlocked(index) {
  if (index <= 0) return true;
  return !!state.solved[QUESTS[index - 1].id];
}

// --- レベル/EXP（Lv1→100）
function expToNext(level) {
  // だんだん重くなるが、100まで到達できる程度に。
  // Lv1->2: 80 / Lv50前後: ~900 / Lv99->100: ~1600
  return Math.min(1600, Math.floor(70 + level * 16));
}

function addExp(amount) {
  if (state.level >= 100) {
    state.exp = 0;
    return;
  }
  state.exp += amount;
  while (state.level < 100) {
    const need = expToNext(state.level);
    if (state.exp < need) break;
    state.exp -= need;
    state.level += 1;
    logOk(`れべるあっぷ！ Lv${state.level}`);
  }
  if (state.level >= 100) state.exp = 0;
}

// --- タイマー
let timerInterval = null;
function startTimer(limitSec) {
  stopTimer();
  state.timer = { startedAt: Date.now(), limitSec, expired: false };
  timerInterval = setInterval(() => tickTimer(), 200);
  tickTimer();
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

function remainingSec() {
  if (!state.timer?.startedAt || !state.timer?.limitSec) return null;
  const elapsed = Math.floor((Date.now() - state.timer.startedAt) / 1000);
  return Math.max(0, state.timer.limitSec - elapsed);
}

function tickTimer() {
  const rem = remainingSec();
  if (rem === null) {
    timerEl.textContent = "--:--";
    timerEl.classList.remove("timer--warn");
    return;
  }
  const mm = String(Math.floor(rem / 60)).padStart(2, "0");
  const ss = String(rem % 60).padStart(2, "0");
  timerEl.textContent = `${mm}:${ss}`;
  if (rem <= 20) timerEl.classList.add("timer--warn");
  else timerEl.classList.remove("timer--warn");

  if (rem <= 0 && !state.timer.expired) {
    state.timer.expired = true;
    logNg("じかんぎれ…でも もう一回できるよ。あわてずにね。"
    );
  }
}

// --- 描画
function renderMap() {
  mapEl.innerHTML = "";
  for (let i = 0; i < QUESTS.length; i++) {
    const q = QUESTS[i];
    const btn = el("div", "mapNode");
    const locked = !isQuestUnlocked(i);
    if (locked) btn.classList.add("mapNode--locked");

    const name = el("div", "mapNode__name");
    const prefix = i === state.questIndex ? "▶ " : "";
    const done = state.solved[q.id] ? " ✓" : "";
    name.textContent = `${prefix}${q.title}${done}`;

    const sub = el("div", "mapNode__sub");
    sub.textContent = q.episode;

    btn.appendChild(name);
    btn.appendChild(sub);

    btn.addEventListener("click", () => {
      if (i === state.questIndex) return;
      if (!isQuestUnlocked(i)) {
        toast("まだ進めない");
        return;
      }
      state.questIndex = i;
      startQuest();
    });

    mapEl.appendChild(btn);
  }
}

function renderParty() {
  partyEl.innerHTML = "";
  for (const p of PARTICIPANTS) {
    const row = el("div", "partyMember");
    const left = el("div", "partyMember__name");
    left.textContent = p.name;
    const right = el("div", "partyMember__role");
    right.textContent = p.role;
    row.appendChild(left);
    row.appendChild(right);
    partyEl.appendChild(row);
  }
}

function renderStats() {
  const solvedCount = Object.values(state.solved).filter(Boolean).length;
  const total = QUESTS.length;
  statProgress.textContent = `${Math.floor((solvedCount / total) * 100)}%`;
  statLv.textContent = String(state.level);
  statExp.textContent = state.level >= 100 ? "MAX" : `${state.exp}/${expToNext(state.level)}`;
}

function renderScene() {
  const q = currentQuest();
  titleEl.textContent = q.location;
  descEl.textContent = q.desc;
  artEl.setAttribute("data-art", q.id);

  questBadge.textContent = `${q.episode} / ${q.title}`;
  {
    const d = DIFFICULTIES[state.difficulty] || DIFFICULTIES.easy;
    difficultyBadge.textContent = `むずかしさ: ${d.label}（${d.target}）`;
  }

  if (state.trialMode) {
    trialBadge.hidden = false;
    trialBadge.textContent = TRIAL_MODE_LABEL;
  } else {
    trialBadge.hidden = true;
  }

  choicesEl.innerHTML = "";
  const choices = buildChoices(q);
  for (const c of choices) {
    const b = el("button", "choice");
    b.textContent = c.label;
    b.addEventListener("click", () => c.run());
    choicesEl.appendChild(b);
  }

  answerInput.disabled = false;
  answerInput.placeholder = "ここに こたえを いれてね";
}

function renderAll() {
  renderMap();
  renderParty();
  renderStats();
  renderScene();
}

function startQuest() {
  const q = currentQuest();
  state.activePuzzle = q.id;
  logSys(`【${q.episode}】${q.title}`);
  const d = DIFFICULTIES[state.difficulty] || DIFFICULTIES.easy;
  const limit = Math.max(30, Math.floor(q.timeLimitSec * d.timeMul));
  startTimer(limit);
  renderAll();
}

// --- API
async function submitAnswer() {
  const puzzleId = state.activePuzzle;
  const answer = answerInput.value;

  if (!answer.trim()) {
    toast("こたえを いれてね");
    return;
  }

  try {
    const res = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ puzzleId, answer }),
    });
    const data = await res.json();
    if (!res.ok) {
      logNg(data.message || "エラー");
      return;
    }

    if (!data.ok) {
      logNg(data.message);
      toast("ちがうよ");
      return;
    }

    // 正解
    logOk(data.message);
    state.solved[puzzleId] = true;

    // EXP付与（タイムボーナスあり、時間切れは半減）
    const q = currentQuest();
    const rem = remainingSec() ?? 0;
    const ratio = q.timeLimitSec ? rem / q.timeLimitSec : 0;
    let gain = 120 + Math.floor(120 * ratio);
    if (state.timer.expired) gain = Math.max(30, Math.floor(gain * 0.5));
    {
      const d = DIFFICULTIES[state.difficulty] || DIFFICULTIES.easy;
      gain = Math.max(10, Math.floor(gain * d.expMul));
    }
    addExp(gain);
    logSys(`EXP+${gain}（けいけんち）`);

    // 次へ
    stopTimer();
    answerInput.value = "";

    const idx = QUESTS.findIndex((x) => x.id === puzzleId);
    if (idx >= 0 && idx < QUESTS.length - 1) {
      state.questIndex = idx + 1;
      state.timer = { startedAt: null, limitSec: null, expired: false };
      toast("つぎへ");
      startQuest();
    } else {
      // エンディング（安全な演出）
      logSys("――えんでぃんぐ――");
      logSys("ももね『はるや、やったね！』");
      logSys("はるや『…うん。そういうときは、わらえばいいんだな』");
      toast("クリア！");
      answerInput.disabled = true;
      answerInput.placeholder = "クリア！ おめでとう";
      choicesEl.innerHTML = "";
      const b = el("button", "choice");
      b.textContent = "さいしょから";
      b.addEventListener("click", () => newGame());
      choicesEl.appendChild(b);
      renderStats();
    }
  } catch {
    logNg("つうしんできなかったよ。サーバーがうごいてる？");
  }
}

async function requestHint() {
  const puzzleId = state.activePuzzle;
  try {
    const res = await fetch(`/api/hint/${puzzleId}`);
    const data = await res.json();
    if (!res.ok) {
      logNg(data.message || "エラー");
      return;
    }
    logSys(`ひんと：${data.hint}`);
  } catch {
    logNg("通信に失敗した。サーバーが起動している？");
  }
}

// --- セーブ/ロード
function saveGame() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  toast("セーブしたよ");
}

function loadGame() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    toast("セーブがないよ");
    return;
  }
  try {
    const loaded = JSON.parse(raw);
    state = { ...defaultState(), ...loaded };
    // solvedのキーが足りない場合に備えて補完
    state.solved = { ...Object.fromEntries(QUESTS.map((q) => [q.id, false])), ...(state.solved || {}) };
    if (!DIFFICULTIES[state.difficulty]) state.difficulty = "easy";
    if (typeof state.trialMode !== "boolean") state.trialMode = true;
    toast("ロードしたよ");

    // 直前が未解決ならそこへ戻す
    if (!isQuestUnlocked(state.questIndex)) {
      for (let i = 0; i < QUESTS.length; i++) {
        if (isQuestUnlocked(i)) state.questIndex = i;
      }
    }

    startQuest();
  } catch {
    toast("ロードに しっぱいしたよ");
  }
}

function newGame() {
  state = defaultState();
  logEl.innerHTML = "";
  toast("さいしょから はじめるよ");
  startQuest();
}

// 起動
(async function boot() {
  renderAll();
  logSys("サーバーに つなぐよ…");
  try {
    const res = await fetch("/api/meta");
    const meta = await res.json();
    if (meta?.ok) logSys(`接続OK：${meta.title} v${meta.version}`);
  } catch {
    logNg("つなげないよ。Pythonサーバーを うごかしてね。"
    );
  }

  startQuest();
})();
