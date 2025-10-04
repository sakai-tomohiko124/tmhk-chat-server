# TMHK Chat Server - 機能/エンドポイント追加概要 (拡張分)

本ドキュメントは最近追加/拡張したソーシャル & ゲーミフィケーション関連機能のサマリです。
既存の基本認証・フレンド・タイムライン機能に加えて以下を実装しました。

## 目次
- ポイント / 無料開放 / トライアル
- 新規データベーステーブル
- ブロック / ミュート API
- フォロー API
- 位置情報共有 (ポイント制 `location_share`)
- 連絡先同期 API
- 招待トークン (QR 拡張予定)
- 購入とアクセス制御
- 今後予定 (高度チャット機能)

---
## ポイント / 無料開放 / トライアル
- `award_points(user_id, action)` 一元化。既定マップ:
  - registration=100 / daily_login=20 / message_send=10 / friend_add=15 / invite_success=50 / game_play=20 / tutorial_complete=50
- 14日トライアル: `is_trial_period(user_id)` で登録後14日間は全機能開放。
- キャンペーン日: `is_full_feature_free_day()` で特定日/期間を全機能無料。
- 管理者最優先 → キャンペーン日 → サブスク → トライアル → 個別購入判定。

## 新規DBテーブル
```
blocked_users(id, user_id, blocked_user_id, created_at)
muted_users(id, user_id, muted_user_id, created_at)
follows(id, follower_id, followee_id, created_at)
user_contacts(id, user_id, contact_hash, created_at)
# users テーブルに last_lat, last_lng, location_updated_at を追加
```

## ブロック / ミュート API
| 動作 | メソッド & パス | 説明 | 備考 |
|------|----------------|------|------|
| ブロック | POST `/block/<target_id>` | 対象をブロックしフレンド解除 | 自分自身不可 |
| 解除 | POST `/unblock/<target_id>` | ブロック解除 |  | 
| ミュート | POST `/mute/<target_id>` | 通知抑止用の静的登録 | 振る舞い今後拡張 |
| 解除 | POST `/unmute/<target_id>` | ミュート解除 |  |

- JSON を Accept すれば JSON 返却、フォームは flash+リダイレクト。
- ソケット送信時 (`send_private_message`) で双方向ブロック判定し送信拒否。

## フォロー API
| 動作 | パス | 説明 |
|------|------|------|
| フォロー | POST `/follow/<target_id>` | ブロック関係がある場合は拒否 |
| 解除 | POST `/unfollow/<target_id>` | フォロー解除 |
| Following一覧 | GET `/api/following` | 自分がフォローしているユーザー一覧 |
| Followers一覧 | GET `/api/followers` | 自分をフォローしているユーザー一覧 |

## 位置情報共有 (ポイント制 `location_share`)
| 動作 | パス | 説明 | 条件 |
|------|------|------|------|
| 更新 | POST `/location/update` | 緯度経度保存 | `location_share` 購入 or トライアル/無料日/サブスク |
| 取得 | GET `/location/friends` | 24h以内更新のフレンド位置 | 同上 |

- `FEATURE_COSTS['location_share'] = 100`。
- 未購入時は 402 (Payment Required 相当) と JSON `{feature: 'location_share'}` を返却。

## 連絡先同期 API
| パス | メソッド | 説明 |
|------|----------|------|
| `/contacts/sync` | POST | `{"contacts":["+810901234567", ...]}` を受け、正規化→SHA256で `user_contacts` へ保存。マッチした他ユーザーを返却 |

レスポンス例:
```
{
  "success": true,
  "inserted": 10,
  "matched_users": [{"id":2, "username":"alice", "profile_image":"..."}]
}
```

## 招待トークン (QR 拡張予定)
| パス | メソッド | 説明 |
|------|----------|------|
| `/invite/qr` | GET | 24h 有効招待トークン生成。後でQR画像生成予定。招待成功ポイント加算ロジック共通 |

レスポンス例:
```
{"success":true, "token":"...uuid...", "link":"https://host/accept_invite/<token>"}
```

## 購入とアクセス制御
- 個別機能購入: `/points_status` UI 経由（従来メカニズム）。
- `check_feature_access` が管理者→無料日→サブスク→トライアル→購入を順番に判定。
- 位置情報のみ新規で有料化。他の新規: ブロック/フォロー/ミュート/連絡先同期/招待トークンは無料。

## 高度チャット機能 (実装済)
以下の機能を 1対1 + グループ (一部) に実装済み:
- 編集 / 削除 / 返信 / 転送 / ピン / リアクション / メンション / 既読 / 検索 / リンクプレビュー

### 追加/変更された主カラム (private_messages / messages)
```
is_deleted INTEGER DEFAULT 0
deleted_at TEXT
edited_at TEXT
reply_to_id INTEGER
forward_from_id INTEGER
is_pinned INTEGER DEFAULT 0
link_preview_json TEXT
```

### 新テーブル
```
message_reactions(id, message_id, user_id, reaction_type, created_at) -- UNIQUE(message_id,user_id,reaction_type)
message_mentions(id, message_id, mentioned_user_id, is_read, is_group, created_at)
group_message_reactions(id, message_id, user_id, reaction_type, created_at)
group_message_reads(id, message_id, user_id, read_at)
```

### 外部キー & トリガ
- `message_reactions.message_id` は `private_messages(id)` を参照し `ON DELETE CASCADE` (※ 現状 private_messages はソフトデリート運用で実質発火無し)
- `PRAGMA foreign_keys=ON` を接続時に設定
- 同期トリガ:
  - `trg_pm_deleted_at_sync`: deleted_at 更新時 is_deleted=1 を強制
  - `trg_pm_is_deleted_sync`: is_deleted=1 更新時 deleted_at 未設定なら現在時刻付与

### 新 HTTP エンドポイント
1. `POST /messages/react` body/json: {message_id, reaction} -> 追加/削除 toggle
2. `GET /messages/reactions/<id>` -> {message_id, reactions:[{reaction,count,users:[..]}]}
3. `GET /api/presence?ids=1,2,3` -> 各ユーザの {id,status,last_seen}
4. `GET /api/presence/<id>` -> 単体 presence
5. `GET /api/profile/<id>` -> 公開プロフィール + フォロー関係 (following, followed_by, mutual)
6. `GET /api/followers`, `GET /api/following`, `GET /api/mutuals`
7. `POST /follow/<id>`, `POST /unfollow/<id>`
8. `GET /api/users/search?q=...` (レート制限, username/email LIKE, 除外: 自分/管理者/非アクティブ)
9. `GET /api/friends` (friends / incoming_requests / blocked)
10. `PATCH /api/profile` (status_message,bio,profile_image multipart対応)
11. `GET /api/stories/active` (friend/favorite + self の未期限切れストーリー)
12. `PATCH /api/albums/<id>` (title rename)
13. `DELETE /api/albums/<id>`

Presence status: online (Socket接続中) / recent (<5分) / offline

### 主なエンドポイント (抜粋)
| 種別 | メソッド | パス | 説明 |
|------|----------|------|------|
| 編集 | POST | `/messages/edit/<id>` | 1対1メッセージ編集 |
| 削除 | POST | `/messages/delete/<id>` | 1対1メッセージ削除 (soft) |
| ピン | POST | `/messages/pin/<id>` | ピン ON/OFF |
| ピン一覧 | GET | `/chat/pins/private/<peer_id>` | ピン一覧 (1対1) |
| リアクション | POST | `/messages/react` | toggle 式 |
| リアクション一覧 | GET | `/messages/reactions/<id>` | 集計表示 |
| 返信 | POST | `/messages/reply` | reply_to_id 設定 |
| 転送 | POST | `/messages/forward` | forward_from_id 設定 |
| 既読 | POST | `/messages/read` | is_read=1 |
| 検索 | GET | `/messages/search?q=...` | FTS5 / LIKE フォールバック |
| メンション未読 | GET | `/mentions/unread` | private+group 未読 mention |
| メンション既読 | POST | `/mentions/mark_read` | mention is_read 更新 |
| グループ編集 | POST | `/group/messages/edit/<id>` | messages テーブル編集 |
| グループピン | POST | `/group/messages/pin/<id>` | グループピン |
| グループピン一覧 | GET | `/chat/pins/group/<room_id>` | ピンされた messages |
| グループリアクション | POST | `/group/messages/react` | toggle |
| グループ既読登録 | POST | `/group/messages/read` | group_message_reads 追加 |
| グループ既読一覧 | GET | `/group/messages/readers/<message_id>` | 読了ユーザ一覧 |
| グループ検索 | GET | `/group/messages/search?room_id=..&q=..` | LIKE 検索 |

### ソケットイベント (主)
`new_private_message`, `message_edited`, `message_deleted`, `message_pinned`, `reaction_updated`, `message_replied`, `message_forwarded`, `message_read`, `mention_notification`

グループ用: `new_group_message`, `group_message_edited`, `group_message_deleted`, `group_message_pinned`, `group_reaction_updated`, `group_message_replied`, `group_message_forwarded`, `group_message_read`

---
## リンクプレビュー (Link Preview)
- メッセージ本文に含まれる最初の `http(s)://` URL を抽出しサーバ側で取得。
- OGタグ (`og:title`, `og:description`, `og:image`) / `<title>` を解析し JSON 化して `link_preview_json` に保存。
- クライアントはカード (サムネ/タイトル/説明) をレンダリング。
- 例レスポンスフィールド: `{"url":"...","title":"...","description":"...","image":"..."}`
- 注意: E2EE フェーズ導入時はプレビュー無効化オプション要検討 (内容がサーバに平文送信されるため)。

---
## 翻訳 API
| メソッド | パス | 入力 | 出力 |
|----------|------|------|------|
| POST | `/message/translate` | `text`, `target_lang` | `translated_text`, `detected_source`, `engine`, `fallback` |

- Groq LLM (llama-3.3-70b-versatile) を利用し簡易翻訳。
- 言語判定は正規表現ベース (粗い検出)。失敗や同一言語はフォールバック。
- フィールド: `engine` = groq-llama... / fallback, `fallback`=true 時は未翻訳メモ付加。

---
## グループ既読 (Read Receipts)
- `group_message_reads` に (message_id, user_id, read_at)。
- ソケット: `mark_group_read` により `group_message_read` イベント配信。
- HTTP: `/group/messages/read`, `/group/messages/readers/<id>`。
- 重複記録は `UNIQUE(message_id, user_id)` により抑制。

---
## E2EE 概要 (計画と現状)
- 現在: 公開鍵登録 API (`/e2ee/key/upload`, `/e2ee/key/<user_id>` ) のみ実装。
- 将来: X25519 + AES-GCM。`content_ciphertext`, `content_nonce`, `content_tag`, `encryption_version` をメッセージに追加予定。
- ロードマップ: Phase0(平文) → Phase1(1対1暗号) → Phase2(メッセージ鍵ローテ) → Phase3(グループ SenderKey)。
- 詳細は `docs/E2EE_DESIGN.md` 参照。

---
## 今後の改善候補
- リンクプレビュー キャッシュ / 相対URL解決 / 画像サイズ制限
- 翻訳結果キャッシュ & 多言語UI連携
- E2EE Phase1 列追加 + クライアント実装
- グループメッセージ FTS5 対応
- メンションバッジ常時リアルタイム (ポーリング→push 最適化)

---
## エラーハンドリング方針
- JSON API: 4xx/5xx 時 `{success:false, message:"..."}` を基本形。
- 未購入機能アクセス: 402 を使用し `feature` キーを付与。

## セキュリティ・プライバシー留意
- 連絡先は生値保存せず SHA256 ハッシュ (ソルトなし) → 将来レインボーテーブル耐性強化する場合は pepper 導入検討。
- 位置情報は簡易保存。履歴/精度制御/削除リクエスト対応は今後追加可能。

---
## 簡易呼び出し例 (curl)
```
# ブロック
curl -X POST -H "Cookie: session=..." https://host/block/123

# 位置情報更新 (location_share購入済前提)
curl -X POST -H "Content-Type: application/json" -d '{"lat":35.0, "lng":139.0}' https://host/location/update

# 連絡先同期
curl -X POST -H "Content-Type: application/json" -d '{"contacts":["+810901234567","test@example.com"]}' https://host/contacts/sync
```

---
最終更新: 2025-10-04

---
## 詳細既読 (1対1)
- `private_messages` に `read_at` 列を追加し初回既読時のみ時刻を保存。
- ソケットイベント `message_read` で `{id, reader_id, read_at}` を配信。
- UIは送信者側バブルに `✔ HH:MM` をインライン表示。
- 冪等性: 2回目以降の既読操作では `read_at` を上書きしない。

## 多言語UI / 自動翻訳
- `users.language_code` に希望言語 (既定 `ja`) を保存。`POST /api/user/language` で更新。
- 受信メッセージはユーザー言語と検出言語が異なる場合、自動で翻訳結果を差し替え表示。
- トグルボタンで「翻訳 ↔ 原文」を切替 (キャッシュ: メモリ上 / 再リクエスト防止)。
- API `/message/translate`: Groq LLM 利用 / フォールバック時は原文 or 未翻訳タグ付与。

## 監査ログ (Audit Logs)
テーブル: `audit_logs(id, user_id, action, target_type, target_id, attributes_json, allowed, created_at)`
- 対象アクション (現段階):
  - `react_message`, `react_group_message` (リアクション追加/解除)
  - `mention_user`, `mention_user_group` (メンション生成)
- 失敗してもメインフローを阻害しない設計 (例外は warning ログ)。
- 拡張候補: 削除/編集や管理者操作の完全記録、導出フィールド(端末IP, UA)。

## CSRF ポリシー
- グローバルに Flask-WTF CSRF を有効化。`layout.html` に `<meta name="csrf-token">` を挿入。
- 共通ラッパ `csrfFetch(url, options)` が `X-CSRFToken` を自動付与。
- 主要 POST エンドポイント (ブロック/ミュート/フォロー/位置更新/連絡先同期) から `@csrf.exempt` を除去済。
- 残例外: ユーザー同意 (`/consent`) は初期ロード性簡便のため暫定 exempt。将来的に hidden フィールド付きフォームへ移行可能。
- 推奨テスト: 1) 有効トークン付与時200 2) トークン欠如で403 を確認。

---
## メディア・コンテンツ機能 実装状況 (抜粋 self-audit)
| # | 機能 | 状態 | メモ |
|---|------|------|------|
| 26 | 画像送受信 | 実装 | `/upload_image` でリサイズ(最大1280px) + サムネ(200px)生成。Exif除去/AVIF最適化は未 |
| 27 | 動画送受信 | 部分 | mp4/webm など許可。プレビュー自動生成なし |
| 28 | 音声メッセージ | 実装 | WebM 録音/送信/再生対応 |
| 29 | ファイル共有 | 部分 | 複数拡張子許容 (doc/xls/ppt/pdf/zip) だがサイズ制限のみ・DL UI 最低限 |
| 30 | スタンプ・絵文字 | 実装(最小) | stampsテーブル + `/stamps/upload` `/api/stamps` DELETE `/stamps/<id>` クライアント送信は画像URLとして扱う |
| 31 | GIF画像対応 | 実装(基本) | `/api/gif/search` (GIPHY or Fallback) で検索→URL送信 |
| 32 | 画像フィルター | 未 | クライアント/サーバ双方機能なし |
| 33 | ストーリー機能 | 未 | 7日 TTL投稿DB/UIなし |
| 34 | ライブ配信 | 未 | WebRTC/RTMP 仕組みなし |
| 35 | ショート動画 | 未 | 短尺動画専用フィードなし |
| 36 | youtube音楽同期 | 未 | 埋め込み + 楽曲同期管理なし |
| 37 | AR/VRフィルター | 未 | 3D/AR ランタイムなし |
| 38 | 画像・動画編集 | 未 | トリミング/回転/サムネ生成無し |
| 39 | アルバム作成 | 未 | アルバムテーブル/閲覧UI未 |
| 40 | メディア自動保存 | 未 | 自動DL/保存設定無し (ブラウザ保存依存) |

> 状態凡例: 実装 / 部分 / 未。今回: 画像サムネ + GIF検索 + スタンプ最小CRUD を実装。

### 新規メディア & スタンプ関連エンドポイント
| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/upload_image` | 画像アップロード (field: `image_file`)。`file`, `thumb` パス返却 |
| GET | `/api/gif/search?q=word` | GIF検索 (環境変数 `GIPHY_API_KEY` 無い場合は固定リスト) |
| POST | `/stamps/upload` | カスタムスタンプ画像登録 (field: `stamp_file`, `name`) |
| GET | `/api/stamps` | 自ユーザ + 公開スタンプ一覧 |
| DELETE | `/stamps/<id>` | 自分のスタンプ削除 (管理者は他ユーザ分も可) |

送信時 `message_type` 種類:
| 種類 | 値 | content格納例 |
|------|-----|----------------|
| テキスト | `text` | 本文文字列 |
| 音声 | `voice` | 音声ファイル名 (`/static/assets/uploads/` 配下) |
| 画像 | `image` | オリジナル画像パス |
| GIF | `gif` | GIF画像URL (外部CDN) |
| スタンプ | `stamp` | スタンプ画像パス |

### クライアントUI (B/C 拡張)
- 画像: アップロード後は最大幅200pxサムネ表示。クリックでモーダル拡大 (原寸/URL表示)。将来: サムネと原寸を分離 (`thumb_` プレフィックス) 予定。
- スタンプ: 「スタンプ」ボタン → モーダルで `/api/stamps` 一覧グリッド (48px)。クリックで即送信。アップロード(従来)も並存。
- GIF: 「GIF」ボタン → 検索モーダル (入力 + 結果グリッド 120x90)。クリックで選択GIFのURL送信。
- 翻訳: `message_type='text'` のみ自動翻訳/トグル適用。他メディアは対象外。

### 将来改善案
- EXIF除去と WebP/AVIF 自動変換
- スタンプカテゴリー/お気に入り/最近使用
- GIF 無限スクロール & 選択プレビュー
- 画像原寸プリロード/ズーム/スワイプナビゲーション

---
## Windows (cmd) 起動手順 & トラブルシュート

### 1. 仮想環境作成 & 依存インストール
```
cd server
python -m venv .venv
call .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. 必須環境変数 (必要に応じて `set`)
```
set FLASK_ENV=production
set SECRET_KEY=dev-secret-change-me
rem 管理者アカウント(任意)
set ADMIN_EMAIL=admin@example.com
set ADMIN_PASSWORD=adminpass123
rem Redis 未使用で警告を抑止したい場合
set TMHK_DISABLE_REDIS=1
```

### 3. サーバ起動
```
python server.py
```
既定ポート: 5000 (変更する場合 `set PORT=8000` 等 + server.py に渡る実装があれば利用)。

### 4. ブラウザアクセス
```
http://127.0.0.1:5000/
```

### 5. 代表的フロー動作テスト (手動チェックリスト)
| # | 操作 | 期待結果 |
|---|------|----------|
| 1 | /register GET | 200 & フォームに account_type ラジオ表示 |
| 2 | account_type=work で登録 | community_name 空でも 302 → /main_app リダイレクト |
| 3 | account_type=other で community_name 未入力送信 | バリデーションエラー表示 (同ページ) |
| 4 | account_type=other で community_name 入力 | 302 → /main_app |
| 5 | 新規ユーザでログイン維持後 main_app | main_app.html が描画 (テキスト MAIN_APP でなく) |
| 6 | CSRF トークン削除して POST (例 /follow/<id>) | 403 + CSRF エラーハンドラレスポンス |
| 7 | Redis 無し (TMHK_DISABLE_REDIS=1) | ログに memory limiter 使用メッセージ / 500 無し |
| 8 | 画像アップロード (許容拡張子) | 成功 JSON / UI でサムネ表示 |
| 9 | メッセージ送信 → 検索 | /api/messages/search?q=... で結果 JSON |
| 10 | mention 送信 | /mentions/unread に件数反映 |

### 6. トラブルシュート
| 症状 | 原因候補 | 対処 |
|------|----------|------|
| 500 + Redis ConnectionError | Redis 未起動 / ホスト不達 | `set TMHK_DISABLE_REDIS=1` でメモリ fallback |
| CSRF 403 | トークン欠如 / 期限切れ | `<meta name="csrf-token">` 取得 JS を確認, セッション再ログイン |
| sqlite OperationalError: no such column ... | 新規マイグレーション未適用 | サーバ再起動 (app_context 初期化で ensure_* 実行) |
| TemplateNotFound main_app.html | テンプレ削除/パス変更 | `templates/main_app.html` の存在確認 |
| 画像アップロード失敗 magic エラー | python-magic ビルド不可 | Windows では `python-magic-bin` 導入済みを確認 |
| UnicodeDecodeError tmhk.sql | 文字コード混在 | BOM 付きでないこと確認 / `encoding='utf-8'` 保存 |

### 7. 後方互換と移行注意
- users テーブルへ `account_type` / `community_name` / `email` / `is_admin` 追加を idempotent ALTER で実行。
- 旧クライアントが main_app テキスト応答を前提としていた場合: 本番は常にテンプレを返すよう変更済み。必要なら Feature Flag で旧挙動復旧可。
- レート制限: Redis 未使用時 memory backend (プロセス内) のため多プロセス運用で共有されない → 本番スケール時は Redis 必須。
- パスワードハッシュ移行: 初回数リクエストまたは起動時遅延フックで平文→pbkdf2 へ更新。ログで migrated 件数を確認可能。

### 8. 推奨追加改善 (短期)
1. pytest 導入 (`tests/` 既存構造の整備) / 登録フロー & CSRF テスト自動化
2. Redis オプション設定: 接続タイムアウト/リトライ backoff パラメータ環境変数化
3. main_app 依存エンドポイント( points_status 等 ) の 404 監視 (ログ統計)
4. static アップロードファイルの MIME 安全性 (magic 判定失敗時ブロック)
5. 画像サムネ生成のジョブキュー化 (現在同期 + 部分非同期)

### 9. セキュリティ再点検 TODO
- CSRF exempt 残存エンドポイント( /consent 等 ) の早期解消
- Admin 機能ルートへ rate limit 強化 (ブルートフォース防止)
- password ハッシュアルゴリズムを将来 argon2 / scrypt オプション化
- 添付ファイル AV/マルウェア スキャン (clamd 等) 導入検討

---
## 手動登録フロー再検証ログ (記録用フォーマット例)
```
日時: 2025-10-04 12:34
環境: Windows10 / Python 3.11.9 / TMHK_DISABLE_REDIS=1
Case1(work): OK redirect=/main_app status=200 template_rendered
Case2(other no community_name): validation_error message表示 OK
Case3(other with community_name): OK redirect=/main_app
CSRF missing token: 403 returned OK
```

---
最終更新(本セクション): 2025-10-04
