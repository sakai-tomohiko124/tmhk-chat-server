# デプロイメント状況レポート

## 現在の状況

**ステータス**: ❌ サーバーに接続できません

### 実行したテスト結果

1. ✅ **PEM鍵ファイル**: 存在確認 OK (`C:\Users\skyto\ARE\tmhk-chat.pem`)
2. ✅ **ポートスキャン**: ポート22と5000が開いている
3. ❌ **Ping**: タイムアウト
4. ❌ **SSH接続**: Connection timed out

### エラーメッセージ
```
ssh: connect to host 52.69.241.31 port 22: Connection timed out
```

## 問題の原因

接続タイムアウトが発生する主な原因：

### 1. EC2インスタンスが停止している（最も可能性が高い）
- インスタンスが「停止済み」または「終了」状態
- AWSコンソールで確認が必要

### 2. IPアドレスが変更された
- EC2インスタンスを再起動するとパブリックIPが変わる
- Elastic IPを使用していない場合に発生

### 3. セキュリティグループの設定ミス
- インバウンドルールが正しく設定されていない
- 特定のIPからのみ許可している場合、あなたのIPが変わった可能性

## 解決手順

### ステップ1: AWSコンソールでEC2インスタンスを確認

1. AWSマネジメントコンソールにログイン
   - https://console.aws.amazon.com/

2. EC2ダッシュボードを開く
   - https://console.aws.amazon.com/ec2/

3. 「インスタンス」をクリック

4. インスタンスの状態を確認：

   **インスタンスが「停止済み」の場合：**
   - インスタンスを選択
   - 「インスタンスの状態」→「インスタンスを開始」をクリック
   - 起動完了まで待機（通常1-2分）

   **インスタンスが「実行中」の場合：**
   - パブリックIPv4アドレスを確認
   - 現在の設定: `52.69.241.31`
   - IPが異なる場合は、下記の「IPアドレス変更時の対応」へ

### ステップ2: セキュリティグループの確認

1. インスタンスを選択
2. 「セキュリティ」タブをクリック
3. セキュリティグループ名をクリック
4. 「インバウンドルール」を確認

**必要な設定：**

| タイプ | プロトコル | ポート範囲 | ソース |
|--------|-----------|-----------|--------|
| SSH | TCP | 22 | 0.0.0.0/0 または あなたのIP |
| カスタムTCP | TCP | 5000 | 0.0.0.0/0 |

**設定が不足している場合：**
- 「インバウンドルールを編集」をクリック
- 「ルールを追加」で上記の設定を追加
- 「ルールを保存」

### ステップ3: インスタンス起動後の確認

**Windowsコマンドプロンプトで実行：**

```cmd
cd c:\Users\skyto\Downloads\tmhk-chat-server\tmhk-chat-server-main
.\check_server.bat
```

または

**Git Bashで実行：**

```bash
ssh -i "C:/Users/skyto/ARE/tmhk-chat.pem" ubuntu@52.69.241.31
```

### ステップ4: 接続成功後のデプロイ

**Windowsコマンドプロンプトで実行：**

```cmd
cd c:\Users\skyto\Downloads\tmhk-chat-server\tmhk-chat-server-main
.\DEPLOY_NOW.bat
```

または

**Git Bashで手動デプロイ：**

```bash
ssh -i "C:/Users/skyto/ARE/tmhk-chat.pem" ubuntu@52.69.241.31 << 'EOF'
cd ~
if [ -d tmhk-chat-server ]; then
  cd tmhk-chat-server
  git fetch origin
  git reset --hard origin/main
else
  git clone https://github.com/sakai-tomohiko124/tmhk-chat-server.git
  cd tmhk-chat-server
fi

pip3 install -r requirements.txt
python3 scripts/init_database.py 2>/dev/null || true

if pm2 describe tmhk-chat >/dev/null 2>&1; then
  pm2 restart tmhk-chat
else
  pm2 start app.py --name tmhk-chat --interpreter python3
  pm2 save
  pm2 startup
fi

pm2 status
EOF
```

## IPアドレス変更時の対応

EC2インスタンスの新しいIPアドレスを確認したら、以下のファイルを更新してください：

### 更新が必要なファイル

1. `check_server.bat` - 6行目
2. `DEPLOY_NOW.bat` - 7行目
3. `MANUAL_DEPLOY.md` - 複数箇所
4. `TROUBLESHOOTING.md` - 複数箇所

**例：IPが `52.69.241.31` から `13.112.XXX.XXX` に変わった場合**

```cmd
# 現在のディレクトリで一括置換（PowerShell）
cd c:\Users\skyto\Downloads\tmhk-chat-server\tmhk-chat-server-main

# すべてのファイルで置換
Get-ChildItem -Recurse -File | ForEach-Object {
    (Get-Content $_.FullName) -replace '52.69.241.31', '13.112.XXX.XXX' | Set-Content $_.FullName
}
```

その後、変更をコミット：

```cmd
git add .
git commit -m "Update server IP address"
git push origin main
```

## Elastic IPの設定（推奨）

IPアドレスが変わらないようにするには、Elastic IPを割り当てます：

1. EC2ダッシュボードで「Elastic IP」をクリック
2. 「Elastic IPアドレスを割り当てる」をクリック
3. 「割り当て」をクリック
4. 割り当てられたIPを選択
5. 「アクション」→「Elastic IPアドレスの関連付け」
6. インスタンスを選択して「関連付け」

これにより、インスタンスを停止・起動してもIPアドレスが変わりません。

## トラブルシューティング

### Q: AWSコンソールにログインできない
A: IAMユーザー名とパスワードを確認してください。ルートユーザーでログインする場合は、メールアドレスとパスワードが必要です。

### Q: インスタンスが見つからない
A: リージョンを確認してください。インスタンスは特定のリージョン（例：アジアパシフィック（東京）ap-northeast-1）に作成されています。

### Q: SSH鍵ファイルが見つからない
A: `C:\Users\skyto\ARE\tmhk-chat.pem` にファイルが存在するか確認してください。なければ、AWSコンソールから新しい鍵ペアを作成し、インスタンスに関連付ける必要があります。

### Q: セキュリティグループを変更したのに接続できない
A: セキュリティグループの変更は即座に反映されますが、念のため1-2分待ってから再試行してください。

## 連絡先

問題が解決しない場合：

1. AWSサポートに問い合わせ
2. GitHub Issuesで質問: https://github.com/sakai-tomohiko124/tmhk-chat-server/issues

## 参考リンク

- AWS EC2 Documentation: https://docs.aws.amazon.com/ec2/
- AWSコンソール: https://console.aws.amazon.com/
- プロジェクトGitHub: https://github.com/sakai-tomohiko124/tmhk-chat-server

---

**最終更新**: 2025年11月15日  
**ステータス**: EC2インスタンスの起動が必要
