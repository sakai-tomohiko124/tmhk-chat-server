# tmhk_chat.py

from flask import Flask

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# '/' というURLにアクセスが来た時に、この関数が実行される
@app.route('/')
def index():
    return "これは、TMHKchatです！　今後お楽しみに！"

# このファイルが直接実行された場合にのみ、開発用の簡易サーバーを起動
# Gunicornから呼ばれるときはこちらは実行されない
if __name__ == '__main__':
    app.run(debug=True)


