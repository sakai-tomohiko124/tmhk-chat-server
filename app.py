import os
import re

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

    @app.get("/")
    def index():
        return render_template("index.html")

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
    _punct_re = re.compile(r"[・,，/／\\\\\-−ー―:：]")

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

    @app.post("/api/check")
    def api_check():
        data = request.get_json(silent=True) or {}
        puzzle_id = data.get("puzzleId")
        answer = data.get("answer", "")

        if puzzle_id not in PUZZLES:
            return jsonify({"ok": False, "message": "未知のパズルです。"}), 400

        puzzle = PUZZLES[puzzle_id]
        answers = puzzle.get("answers", [])
        puzzle_type = puzzle.get("type")

        if puzzle_type == "en":
            ok = _normalize_en(answer) in {_normalize_en(a) for a in answers}
        elif puzzle_type in {"num", "numset"}:
            ok = _normalize_numset(answer) in {_normalize_numset(a) for a in answers}
        else:
            ok = answer.strip() in {a.strip() for a in answers}

        return jsonify({"ok": ok, "message": puzzle["ok"] if ok else puzzle["ng"]})

    @app.get("/api/hint/<puzzle_id>")
    def api_hint(puzzle_id: str):
        if puzzle_id not in PUZZLES:
            return jsonify({"ok": False, "message": "未知のパズルです。"}), 400
        return jsonify({"ok": True, "hint": PUZZLES[puzzle_id]["hint"]})

    @app.get("/api/meta")
    def api_meta():
        return jsonify(
            {
                "ok": True,
                "title": "そういう時は、AREだ！ — RPG謎解き",
                "version": "1.0.0",
            }
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
