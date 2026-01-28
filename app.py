import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


# --- Puzzle API ---
# クライアント側は状態(localStorage)を持ち、サーバーは「答えの検証」と
# 返答テキスト（演出）とヒントのみを返します。

PUZZLES = {
    # 参加合言葉
    "join_are": {
        "type": "ja",
        "answers": ["アレ"],
        "ok": "OK！ さんかかくにん。ゲームが はじまる…",
        "ng": "さんかするなら『アレ』って いれてね。",
        "hint": "かたかな2文字。",
    },
    # 第1話：地獄の招待状
    "q1_nameplate": {
        "type": "en",
        "answers": ["TR"],
        "ok": "せいかい！ るーるが わかった。",
        "ng": "ちがうよ。『A/I/U/E/O』を消すのがコツ！",
        "hint": "名前をローマ字にして、A/I/U/E/O（ぼいん）をぜんぶ消そう。TA RO U → T R",
    },
    "q2_hidden_button": {
        "type": "ja",
        "answers": ["い"],
        "ok": "せいかい！『い』がおせた。かべが うごいた。",
        "ng": "ちがうよ。『しろい』のまんなかを見て！",
        "hint": "『し・ろ・い』のまんなか1文字はどれ？",
    },
    # 第2話：ワン投げゲーム
    "q3_distance": {
        "type": "num",
        "answers": ["20", "２０"],
        "ok": "せいかい！ くびわが のびた。",
        "ng": "ちがうよ。10メートル×回数だよ。",
        "hint": "『ワン』1回＝10m。2回なら10×2。",
    },
    "q4_hidden_one": {
        "type": "ja",
        "answers": ["台湾", "たいわん", "3", "３"],
        "ok": "せいかい！ いちばん うしろに『わん』がある。",
        "ng": "ちがうよ。『わん』が言葉のどこにあるか見よう。",
        "hint": "『わん』がいちばん最後（いちばん遠い）にあるのが正解。ばんごう（3）でもOK。",
    },
    # 第3話：トゲトゲーム
    "q5_safe_food": {
        "type": "ja",
        "answers": ["ほうれんそう", "3", "３"],
        "ok": "せいかい！ トゲが 1文字もない。",
        "ng": "ちがうよ。『クリーム』が入ってるか見てみよう。",
        "hint": "言葉あそび：『クリーム』の中に『くり（栗）』が入ってる→栗はいが（トゲ）。ばんごう（3）でもOK。",
    },
    "q6_toge_kanji": {
        "type": "ja",
        "answers": ["刺", "さし", "さす", "3", "３"],
        "ok": "せいかい！ そのとおり。",
        "ng": "ちがうよ。『トゲ＝さす』を思い出して。",
        "hint": "『刺』は『さす』って読む。ばんごう（3）でもOK。",
    },
    # 第4話：そういうときはアレだ！
    "q7_are_rule": {
        "type": "ja",
        "answers": ["寝る", "ねる", "寝るまね", "ねるまね", "目を閉じる", "めをとじる"],
        "ok": "せいかい！ そういうときは…アレだ！",
        "ng": "ちがうよ。ねむい時にすることを思い出して。",
        "hint": "ねむい → 寝る（目を閉じる）まね。",
    },
    "q8_are_calc": {
        "type": "ja",
        "answers": ["いいふうふ", "良い夫婦", "いい夫婦"],
        "ok": "せいかい！ 1122＝いいふうふ。",
        "ng": "ちがうよ。11と22に分けて読もう。",
        "hint": "11＝『いい』、22＝『ふうふ』って読めるよ。",
    },
    # 第5話：最後の一人
    "q9_are_numbers": {
        "type": "numset",
        "answers": ["1 18 5", "1,18,5", "1・18・5", "1/18/5", "1 18 05"],
        "ok": "せいかい！ ARE＝1・18・5。",
        "ng": "ちがうよ。A=1、B=2…で数えるよ。",
        "hint": "A=1、R=18、E=5。『1・18・5』みたいに書けばOK。",
    },
    "q10_final_answer": {
        "type": "ja",
        "answers": ["まる"],
        "ok": "せいかい！ とびらが ひらいた。",
        "ng": "ちがうよ。『0』を数字じゃなく『形』として見よう。",
        "hint": "0＝『〇（まる）』。ひらがな3文字。",
    },
}


_spaces_re = re.compile(r"\s+")
_punct_re = re.compile(r"[・,，/／\\\-−ー―:：]")


def _norm_common(text: str) -> str:
    text = text.strip()
    text = _spaces_re.sub(" ", text)
    text = _punct_re.sub(" ", text)
    return text.strip()


def _normalize_en(text: str) -> str:
    return "".join(_norm_common(text).upper().split())


def _normalize_numset(text: str) -> str:
    # "1・18・5" 等を "1 18 5" に寄せる
    return " ".join([p for p in _norm_common(text).split(" ") if p])


def _json_bytes(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _guess_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    return ctype or "application/octet-stream"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "tmhk-http/1.0"

    @property
    def root_dir(self) -> Path:
        return Path(__file__).resolve().parent

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, obj: object) -> None:
        self._send_bytes(status, _json_bytes(obj), "application/json; charset=utf-8")

    def _send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        self._send_bytes(status, text.encode("utf-8"), content_type)

    def _send_file(self, status: int, file_path: Path) -> None:
        data = file_path.read_bytes()
        self._send_bytes(status, data, f"{_guess_type(file_path)}")

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _handle_index(self) -> None:
        index_path = self.root_dir / "index.html"
        fallback = self.root_dir / "templates" / "index.html"
        if index_path.exists():
            self._send_file(HTTPStatus.OK, index_path)
            return
        if fallback.exists():
            self._send_file(HTTPStatus.OK, fallback)
            return
        self._send_text(HTTPStatus.NOT_FOUND, "index.html not found")

    def _handle_static(self, req_path: str) -> None:
        # /static/... を root/static/... にマップ
        rel = req_path.removeprefix("/static/")
        rel = unquote(rel)
        static_root = (self.root_dir / "static").resolve()
        target = (static_root / rel).resolve()
        if static_root not in target.parents and target != static_root:
            self._send_text(HTTPStatus.FORBIDDEN, "forbidden")
            return
        if not target.exists() or not target.is_file():
            self._send_text(HTTPStatus.NOT_FOUND, "not found")
            return
        self._send_file(HTTPStatus.OK, target)

    def _handle_api_meta(self) -> None:
        self._send_json(
            HTTPStatus.OK,
            {"ok": True, "title": "そういう時は、AREだ！ — RPG謎解き", "version": "1.0.0"},
        )

    def _handle_api_hint(self, puzzle_id: str) -> None:
        if puzzle_id not in PUZZLES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "未知のパズルです。"})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "hint": PUZZLES[puzzle_id]["hint"]})

    def _handle_api_check(self) -> None:
        data = self._read_json_body()
        puzzle_id = data.get("puzzleId")
        answer = data.get("answer", "")

        if not puzzle_id or puzzle_id not in PUZZLES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "未知のパズルです。"})
            return

        puzzle = PUZZLES[puzzle_id]
        answers = puzzle.get("answers", [])
        puzzle_type = puzzle.get("type")

        if puzzle_type == "en":
            ok = _normalize_en(str(answer)) in {_normalize_en(str(a)) for a in answers}
        elif puzzle_type in {"num", "numset"}:
            ok = _normalize_numset(str(answer)) in {_normalize_numset(str(a)) for a in answers}
        else:
            ok = str(answer).strip() in {str(a).strip() for a in answers}

        self._send_json(HTTPStatus.OK, {"ok": ok, "message": puzzle["ok"] if ok else puzzle["ng"]})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in {"/", "/index.html"}:
            self._handle_index()
            return
        if path.startswith("/static/"):
            self._handle_static(path)
            return
        if path == "/api/meta":
            self._handle_api_meta()
            return
        if path.startswith("/api/hint/"):
            puzzle_id = path.removeprefix("/api/hint/")
            self._handle_api_hint(puzzle_id)
            return

        self._send_text(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/check":
            self._handle_api_check()
            return

        self._send_text(HTTPStatus.NOT_FOUND, "not found")

    def log_message(self, fmt: str, *args) -> None:
        # うるさすぎるので最小限（必要ならここを戻してください）
        return


def run_server(host: str, port: int) -> None:
    if load_dotenv is not None:
        load_dotenv()

    httpd = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
