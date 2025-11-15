# TMHKchat - AI機能の使い方

## 新機能: リアルタイムAIチャット（WebSocket対応）

ChatGPTのようなリアルタイムでストリーミング表示されるAIアシスタント機能を追加しました。

### 機能の特徴

- 🤖 **リアルタイムストリーミング**: WebSocketを使用してChatGPTのように、AIの回答が1文字ずつリアルタイムで表示されます
- 💬 **会話履歴の保持**: 過去10件の会話を記憶して、文脈を理解した回答を生成
- 🎨 **モダンなUI**: 画面右下のボタンからいつでもAIチャットを開けます
- 📱 **レスポンシブ対応**: スマホでも快適に使えます
- 🔄 **2つのAIエンジン**: OpenAI GPT-3.5とGoogle Gemini Proの両方に対応

### 技術的な実装

#### WebSocket対応
従来のHTTP SSE（Server-Sent Events）方式から、Flask-SocketIOを使用したWebSocket方式に変更しました。これにより：

- **より低遅延**: リアルタイム双方向通信
- **安定性向上**: 既存のチャット機能と同じWebSocket接続を共有
- **スケーラビリティ**: Redisを使用した複数ワーカー対応

#### 使用されるイベント

**クライアント → サーバー:**
- `send_to_openai`: OpenAI GPTにメッセージ送信
- `send_to_ai`: Google Gemini AIにメッセージ送信

**サーバー → クライアント:**
- `openai_chunk`: OpenAIからのストリーミングチャンク
- `openai_done`: OpenAIからの応答完了
- `openai_response`: OpenAIからのエラー応答
- `ai_response`: Gemini AIからの応答

### セットアップ手順

#### 1. OpenAI APIキーの取得

1. [OpenAI Platform](https://platform.openai.com/api-keys)にアクセス
2. アカウントを作成またはログイン
3. 「Create new secret key」をクリックしてAPIキーを生成
4. 生成されたキーをコピー（後で確認できないので必ず保存してください）

#### 2. 環境変数の設定

**ローカル開発環境の場合:**

1. `.env`ファイルを作成:
```bash
cp .env.example .env
```

2. `.env`ファイルを編集してAPIキーを設定:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**本番環境(AWS)の場合:**

1. サーバーにSSH接続:
```bash
ssh -i "tmhk-chat.pem" ubuntu@52.69.241.31
```

2. 作業フォルダに移動:
```bash
cd ~/tmhk-chat-server
```

3. `.env`ファイルを作成・編集:
```bash
nano .env
```

以下の内容を追加:
```
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-your-actual-api-key-here
```

保存して終了（Ctrl+O → Enter → Ctrl+X）

4. 環境変数を読み込むようにpm2設定を更新:
```bash
pm2 delete tmhk-chat-server
pm2 start ./venv/bin/gunicorn --name tmhk-chat-server --interpreter ./venv/bin/python -- --workers 3 --bind unix:chat.sock -m 007 app:app
pm2 save
```

#### 3. 依存関係のインストール

```bash
# 仮想環境を有効化
source venv/bin/activate

# 新しいパッケージをインストール
pip install -r requirements.txt
```

#### 4. アプリの再起動

**ローカル:**
```bash
python app.py
```

**本番環境:**
```bash
pm2 restart tmhk-chat-server
```

### 使い方

1. チャット画面を開く
2. 右下の🤖ボタンをクリック
3. AIチャットパネルが開きます
4. メッセージを入力して送信
5. AIの回答がリアルタイムでストリーミング表示されます

### トラブルシューティング

#### APIキーが設定されていない場合

エラーメッセージ: `OpenAI API key not configured`

**解決方法:**
- `.env`ファイルに正しいAPIキーが設定されているか確認
- アプリを再起動

#### AI応答が表示されない

**確認事項:**
1. ブラウザのコンソール(F12)でエラーを確認
2. サーバーログを確認:
```bash
pm2 logs tmhk-chat-server
```
3. OpenAI APIの利用制限に達していないか確認

#### ストリーミングが途中で止まる

**原因:**
- ネットワークの問題
- APIレート制限

**解決方法:**
- ページをリロードして再試行
- しばらく待ってから再度試す

### 料金について

OpenAI APIは従量課金制です:
- **gpt-3.5-turbo**: 1,000トークンあたり$0.0015（入力）、$0.002（出力）
- 日本語約500文字 ≈ 1,000トークン程度
- 月間無料枠: 新規ユーザーには$5クレジット付与（3ヶ月有効）

**コスト削減のヒント:**
- 会話履歴を10件に制限（コード内で設定済み）
- 必要な時だけAIチャットを使用
- 使用状況は[OpenAI Usage Dashboard](https://platform.openai.com/usage)で確認可能

### カスタマイズ

`app.py`の`ai_stream`関数で以下を調整できます:

```python
stream = openai_client.chat.completions.create(
    model="gpt-3.5-turbo",  # モデルを変更 (gpt-4など)
    messages=messages,
    stream=True,
    temperature=0.7,  # 0-1: 創造性の度合い
    max_tokens=1000   # 最大回答長
)
```

### セキュリティ注意事項

⚠️ **重要:**
- `.env`ファイルは絶対にGitにコミットしないでください
- APIキーは他人と共有しないでください
- 定期的にAPIキーをローテーションしてください
- `.gitignore`に`.env`が含まれていることを確認してください
