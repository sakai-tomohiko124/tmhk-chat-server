# 天気予報・鉄道運行情報スクレイピングシステム

## 概要
このシステムは、天気予報と鉄道運行情報を自動的に取得し、**6時間後**に古いデータを自動削除します。

## ファイル構成

```
/workspaces/tmhk-chat-server/
├── scraper2.py           # 天気予報スクレイピング（気象庁 + ウェザーニュース）
├── scrape_train.py       # 鉄道運行情報スクレイピング（Yahoo!路線）
├── run_scrapers.py       # 統合実行スクリプト（cron設定可能）
├── weather_info.json     # 天気予報データ（最新版）
├── train_info.json       # 鉄道運行情報データ（最新版）
├── archive/              # アーカイブディレクトリ
│   ├── weather/          # 天気予報アーカイブ（6時間保持）
│   └── train/            # 鉄道運行アーカイブ（6時間保持）
└── .github/workflows/    # GitHub Actions設定
    ├── scrape_weather.yml  # 天気予報自動取得（1日4回）
    └── scrape_train.yml    # 鉄道情報自動取得（1日4回）
```

## 主な機能

### 1. 自動データ削除機能（**6時間後に削除**）
- **保持期間**: 6時間
- **削除対象**: `archive/weather/` と `archive/train/` 内の古いファイル
- **動作**: スクリプト実行時に自動的に6時間以上前のアーカイブを削除
- **メリット**: サーバー容量の節約、動作の高速化、クレーム対応完了

### 2. アーカイブ機能
- 新しいデータ取得時に、現在のデータをアーカイブに保存
- ファイル名形式: `weather_YYYYMMDD_HHMMSS.json` / `train_YYYYMMDD_HHMMSS.json`

### 3. 自動実行設定
#### GitHub Actions（推奨）
- **頻度**: 1日4回（0時、6時、12時、18時 JST）
- **利点**: サーバー不要、完全自動化、Git履歴で管理
- **設定済み**: `.github/workflows/scrape_weather.yml` と `.github/workflows/scrape_train.yml`

#### ローカルcron（サーバー運用時）
- 毎日午前0時（JST）に自動実行
- 古いアーカイブの自動削除も同時に実行

## 使用方法

### GitHub Actionsで自動実行（推奨・本番環境）

#### 1. リポジトリにpush
```bash
git add .
git commit -m "Add weather and train scrapers with 6-hour retention"
git push origin main
```

#### 2. GitHub Actionsが自動実行
- **実行タイミング**: 1日4回（0時、6時、12時、18時 JST）
- **自動削除**: 6時間以上前のアーカイブは自動削除
- **自動コミット**: 結果は自動的にコミット＆プッシュされる

#### 3. 手動実行も可能
1. GitHubリポジトリ → **Actions** タブ
2. "Scrape Weather Info" または "Scrape Train Info" を選択
3. **Run workflow** をクリック

---

### 手動実行（ローカルテスト）

```bash
# 天気予報のみ取得
python3 scraper2.py

# 鉄道運行情報のみ取得
python3 scrape_train.py

# 両方を一括実行
python3 run_scrapers.py
```

### 自動実行設定（サーバーでcron登録）

```bash
# cronに登録（毎日午前0時に自動実行）
python3 run_scrapers.py --install-cron

# cron登録を解除
python3 run_scrapers.py --uninstall-cron
```

### ログ確認

```bash
# ログファイルの確認
cat logs/scraper.log

# リアルタイムでログを監視
tail -f logs/scraper.log
```

## データ仕様

### weather_info.json（天気予報）

```json
{
  "publishingOffice": "気象庁",
  "reportDatetime": "2025-11-14T17:00:00+09:00",
  "forecasts": [
    {
      "date": "2025-11-14",
      "weather": "晴れ　夜　くもり",
      "temp_min": "10",
      "temp_max": "17",
      "chance_of_rain": ["--", "--", "--", "10"]
    }
  ],
  "hourly_forecast": [
    {
      "iso_time": "2025-11-14T09:00:00",
      "time": "09:00",
      "weather": "晴れ",
      "temp": "16",
      "precip": 0
    }
  ]
}
```

### train_info.json（鉄道運行情報）

```json
{
  "lastUpdated": "2025-11-14T09:27:12.828477",
  "lines": [
    {
      "name": "山手線",
      "status": "平常運転",
      "detail": "事故・遅延情報はありません"
    },
    {
      "name": "湘南新宿ライン",
      "status": "列車遅延",
      "detail": "東海道本線内で発生した動物支障の..."
    }
  ]
}
```

## トラブルシューティング

### アーカイブが削除されない場合

```bash
# アーカイブディレクトリの確認
ls -lh archive/weather/
ls -lh archive/train/

# 手動でスクリプトを実行（削除処理も実行される）
python3 run_scrapers.py
```

### ディスク容量の確認

```bash
# ワークスペース全体の容量確認
du -sh /workspaces/tmhk-chat-server/

# アーカイブディレクトリの容量確認
du -sh archive/
```

### cronが動作しない場合

```bash
# cronの登録状況を確認
crontab -l

# cronサービスの状態確認
sudo service cron status

# cronサービスの起動
sudo service cron start
```

## 技術仕様

### データ保持期間
- **最新データ**: 無期限（`weather_info.json`, `train_info.json`）
- **アーカイブデータ**: 6時間（それ以降は自動削除）

### 実行スケジュール（GitHub Actions）
- **頻度**: 1日4回
- **時刻**: 0時、6時、12時、18時（JST）
- **処理内容**:
  1. 古いアーカイブの削除（6時間以上前）
  2. 現在のデータをアーカイブに保存
  3. 新しいデータの取得
  4. 最新データファイルの更新
  5. GitHubへ自動コミット＆プッシュ

### 依存ライブラリ
- `requests`: HTTPリクエスト
- `beautifulsoup4`: HTMLパース（鉄道情報）
- `lxml`: XMLパーサー

## セキュリティとパフォーマンス

### パフォーマンス改善
- ✅ **6時間後の自動削除**により、ディスク容量を大幅に節約
- ✅ アーカイブファイル数の制限で検索速度を向上
- ✅ 1日4回の実行で、常に最新情報を提供
- ✅ GitHub Actionsで完全自動化（サーバー負荷ゼロ）

### エラーハンドリング
- ネットワークエラー時は、エラー情報をJSONに記録
- ファイル削除エラーは警告ログに出力（処理は継続）
- スクリプト実行エラーは、ログファイルに詳細を記録

## メンテナンス

### 定期的な確認項目（GitHub Actionsの場合）
1. **Actions** タブで実行履歴を確認
2. エラーがないか確認
3. 最新データの更新日時確認（`weather_info.json`, `train_info.json`）

### 定期的な確認項目（ローカルサーバーの場合）
1. ログファイルのサイズ確認（`logs/scraper.log`）
2. アーカイブディレクトリの容量確認
3. 最新データの更新日時確認

### 手動クリーンアップ（必要に応じて）

```bash
# 全アーカイブを削除（最新データは保持）
rm -rf archive/weather/* archive/train/*

# ログファイルのクリア
> logs/scraper.log
```

## 実装完了まとめ

### ✅ 改善点
1. **保持期間を3日→6時間に変更**
   - サーバー容量の大幅削減
   - 古いデータの蓄積を防止
   - クレーム対応完了

2. **GitHub Actions導入**
   - 1日4回自動実行（0時、6時、12時、18時 JST）
   - サーバー負荷ゼロ
   - Git履歴で変更管理
   - 完全自動化

3. **ファイル構成**
   - `.github/workflows/scrape_weather.yml` - 天気予報自動取得
   - `.github/workflows/scrape_train.yml` - 鉄道情報自動取得
   - `scraper2.py` - 天気予報スクレイパー（6時間保持）
   - `scrape_train.py` - 鉄道情報スクレイパー（6時間保持）
   - `run_scrapers.py` - 統合実行スクリプト

### 📊 期待効果
- **ディスク容量**: 3日分 → 6時間分（約1/12に削減）
- **実行頻度**: 1日1回 → 1日4回（情報の鮮度向上）
- **メンテナンス**: 完全自動化（手動作業不要）

### 🚀 次のステップ
```bash
# GitHubにpush
git add .
git commit -m "Add weather/train scrapers with 6-hour retention and GitHub Actions"
git push origin main

# GitHub Actionsが自動的に開始されます
# https://github.com/sakai-tomohiko124/tmhk-chat-server/actions で確認
```

## 問い合わせ
不具合やクレームがあった場合は、ログファイル（`logs/scraper.log`）を確認してください。
