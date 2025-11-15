# EC2インスタンスステータスチェック失敗の修正方法

## 現在の問題

**インスタンスID**: i-0ce5c86f67e13ef6e (tmhk-chat-server)
**ステータス**: 実行中
**問題**: インスタンスの接続性チェックに失敗

```
✅ システムの接続性チェックに合格
❌ インスタンスの接続性チェックに失敗
✅ アタッチ済みのEBS接続性チェックに合格
```

## 即座に試す解決方法

### 方法1: インスタンスの再起動（推奨）

1. AWS EC2コンソールで `tmhk-chat-server` を選択
2. 「インスタンスの状態」→「インスタンスを再起動」をクリック
3. 確認ダイアログで「再起動」をクリック
4. 2-3分待つ
5. ステータスチェックが緑色になることを確認

**コマンドラインから実行する場合:**
```bash
aws ec2 reboot-instances --instance-ids i-0ce5c86f67e13ef6e --region ap-northeast-1
```

### 方法2: 停止→起動（再起動で直らない場合）

1. 「インスタンスの状態」→「インスタンスを停止」
2. ステータスが「stopped」になるまで待つ（1-2分）
3. 「インスタンスの状態」→「インスタンスを開始」
4. ステータスが「running」になるまで待つ
5. ステータスチェックが合格することを確認

⚠️ **注意**: 停止→起動すると、パブリックIPアドレスが変わる可能性があります（Elastic IPを使用していない場合）

## 再起動後の確認手順

### 1. ステータスチェックの確認

EC2コンソールで以下が緑色のチェックマークになっていることを確認:
- システムの接続性チェック: ✅
- インスタンスの接続性チェック: ✅

### 2. 接続テスト

```cmd
ping tmhk-chat.ddns.net -n 4
```

成功すれば:
```
応答: バイト数 =32 時間 <10ms TTL=xxx
```

### 3. SSH接続テスト

```cmd
ssh -i "C:\Users\skyto\ARE\tmhk-chat.pem" -o ConnectTimeout=10 ubuntu@52.69.241.31 "echo 'Connection OK'"
```

### 4. デプロイ実行

接続が確認できたら:
```cmd
DEPLOY_NOW.bat
```

## インスタンスステータスチェック失敗の一般的な原因

### 1. カーネルパニック
- **症状**: インスタンスは実行中だが応答しない
- **解決**: 再起動

### 2. ネットワーク設定ミス
- **症状**: ネットワークインターフェースが正しく設定されていない
- **解決**: 停止→起動で初期化

### 3. メモリ不足
- **症状**: アプリケーションが多すぎてメモリが枯渇
- **解決**: 不要なプロセスを停止、またはインスタンスタイプをアップグレード

### 4. ディスクフル
- **症状**: ルートボリュームの空き容量がない
- **解決**: 不要なファイルを削除

## 再起動後も直らない場合

### システムログの確認

1. EC2コンソールでインスタンスを選択
2. 「アクション」→「モニタリングとトラブルシューティング」→「システムログを取得」
3. エラーメッセージを確認

### インスタンスのスクリーンショットを取得

1. 「アクション」→「モニタリングとトラブルシューティング」→「インスタンスのスクリーンショットを取得」
2. カーネルパニックやブート失敗のメッセージを確認

### 最終手段: 新しいインスタンスを起動

1. 現在のEBSボリュームのスナップショットを作成
2. スナップショットから新しいAMIを作成
3. 新しいインスタンスを起動
4. Elastic IPを新しいインスタンスに関連付け

## 予防策

### 1. Elastic IPの割り当て

固定IPアドレスを使用することで、IPアドレスの変更を防ぐ:

1. EC2コンソール → 「Elastic IP」
2. 「Elastic IPアドレスを割り当てる」
3. 割り当てたIPをインスタンスに関連付け

### 2. CloudWatchアラームの設定

ステータスチェック失敗時に自動再起動:

```bash
# アラームの作成（CLI例）
aws cloudwatch put-metric-alarm \
  --alarm-name tmhk-chat-status-check \
  --alarm-actions arn:aws:automate:ap-northeast-1:ec2:reboot \
  --metric-name StatusCheckFailed_Instance \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=InstanceId,Value=i-0ce5c86f67e13ef6e
```

### 3. 定期的なバックアップ

1. EBSスナップショットの自動作成（AWS Backup）
2. 重要なデータはS3にも保存

## DDNSの更新

IPアドレスが変わった場合、DDNSを更新:

### No-IPの場合

1. No-IPにログイン
2. `tmhk-chat.ddns.net` の設定を開く
3. 新しいIPアドレスに更新

### 自動更新（DUCクライアント）

サーバーにNo-IP DUCをインストールして自動更新:

```bash
# インスタンスにSSH接続後
sudo apt update
sudo apt install noip2 -y
sudo noip2 -C  # 設定
sudo systemctl enable noip2
sudo systemctl start noip2
```

## 次のステップ

1. **今すぐ**: インスタンスを再起動
2. **待つ**: 2-3分でステータスチェックが合格
3. **テスト**: `ping tmhk-chat.ddns.net` で接続確認
4. **デプロイ**: `DEPLOY_NOW.bat` を実行
5. **アクセス**: http://tmhk-chat.ddns.net:5000

---

**重要**: 再起動は通常、1-2分で完了し、ほとんどのインスタンスステータスチェックの問題を解決します。
