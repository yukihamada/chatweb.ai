# DynamoDB → Turso (libSQL) Migration Plan for nanobot-lambda

## 概要

nanobot-lambda (AWS Lambda) が現在 DynamoDB に直接アクセスしている約 233 箇所を、
既存の `DbBackend` trait + `LibSqlBackend` 実装 (Turso remote) に切り替える。

nanobot-fly はすでに `LibSqlBackend` を使っており、実装・スキーマ・migration は完成済み。
Lambda 側に残っている作業は「接続初期化」「AppState への注入」「http.rs 内の DynamoDB 直呼び出しの置き換え」の 3 段階のみ。

---

## 調査結果

### 既存実装の状態 (完成済み)
- `crates/nanobot-core/src/db/backend.rs` — `DbBackend` trait (39 メソッド定義済み)
- `crates/nanobot-core/src/db/libsql.rs` — `LibSqlBackend` 実装 (Turso remote / local SQLite / :memory: の 3 モード)
- `crates/nanobot-core/src/db/schema.sql` — 完全スキーマ (13 テーブル、インデックス付き)
- `crates/nanobot-fly/src/main.rs` — LibSqlBackend の初期化パターン (参照実装)

### AppState の構造 (`service/http.rs:464`)
```rust
pub db: Option<Arc<dyn crate::db::DbBackend>>,  // libSQL 用。None = DynamoDB モード
#[cfg(feature = "dynamodb-backend")]
pub dynamo_client: Option<aws_sdk_dynamodb::Client>,
#[cfg(feature = "dynamodb-backend")]
pub config_table: Option<String>,
```
`db` が Some の場合は DbBackend を使い、None の場合は `dynamo_client` 直呼びのコードパスが動く。
現在 Lambda では `db = None` のまま起動している。

### http.rs の DynamoDB 直呼び箇所
- 総行数: 25,928 行
- `dynamo_client` / `aws_sdk_dynamodb` 参照: 303 箇所
- `if let Some(ref db) = state.db` の DbBackend パス: 4 箇所のみ (OAuth Google / メール登録ログイン)

### DynamoDB ヘルパー関数 (すべて置き換え対象)
| 関数名 | 対応する DbBackend メソッド |
|--------|------------------------|
| `get_or_create_user(dynamo, table, uid)` | `db.get_or_create_user(uid)` |
| `get_or_create_user_cached(state, uid)` | `db.get_or_create_user(uid)` + キャッシュ |
| `deduct_credits(dynamo, table, uid, amt)` | `db.deduct_credits(uid, amt)` |
| `deduct_credits_direct(dynamo, table, uid, amt)` | `db.deduct_credits(uid, amt)` |
| `add_credits_to_user(dynamo, table, uid, amt)` | `db.add_credits(uid, amt)` |
| `find_user_by_email(dynamo, table, email)` | `db.find_user_by_email(email)` |
| `find_user_by_stripe_customer(dynamo, table, cid)` | scan → `db.find_user_by_email` (要補完) |
| `link_stripe_to_user(dynamo, table, uid, plan, cid)` | `db.update_user_plan(uid, plan, Some(cid))` |
| `read_memory_context(dynamo, table, uid)` | `db.get_memory(uid, "long_term")` etc. |
| `save_memory(dynamo, table, uid, content)` | `db.set_memory(uid, kind, content)` |
| `append_daily_memory(dynamo, table, uid, content)` | `db.get_memory` + `db.set_memory` |
| `check_rate_limit(dynamo, table, key, max)` | `db.check_rate_limit(key, 60, max)` |
| `check_rate_limit_hourly(dynamo, table, key, max)` | `db.check_rate_limit(key, 3600, max)` |
| `emit_audit_log(...)` | `db.append_audit(entry)` |
| skill CRUD (handle_list_skills, etc.) | `db.list_public_skills()` etc. |
| coupon (handle_coupon_redeem, etc.) | `db.redeem_coupon()` etc. |
| stats (increment hourly, daily UU) | `db.increment_hourly_stats()` etc. |
| auth token (create/resolve/delete) | `db.create_auth_token()` etc. |
| API key (create/lookup/list/revoke) | `db.create_api_key()` etc. |
| shared conv (create/get) | `db.create_shared_conversation()` etc. |
| push subscription | `db.upsert_push_subscription()` etc. |
| config kv (get_config/set_config) | `db.get_config()` / `db.set_config()` |

### DynamoDB テーブル → libSQL テーブルマッピング
| DynamoDB PK パターン | libSQL テーブル |
|---------------------|---------------|
| `USER#{id}` / `INFO` | `users` |
| `AUTH#{token}` / `SESSION` | `auth_tokens` |
| `MEMORY#{id}` / `LONG_TERM` or `DAILY#{date}` | `memory` |
| `SHARE#{hash}` / `INFO` | `shared_conversations` |
| `CONV_SHARE#{id}` / `INFO` | `conv_share_index` |
| `SKILL#{id}` / `INFO` | `skills` |
| `SKILL_INDEX` / `SK#{id}` | `skills` (is_public=1 scan) |
| `SKILL_AUTHOR#{uid}` / `SK#{id}` | `skills` (author_user_id index) |
| `USER_SKILL#{uid}` / `SK#{id}` | `installed_skills` |
| `COUPON#{code}` / `INFO` | `coupons` |
| `REDEEM#{uid}#{code}` / `INFO` | `coupon_redemptions` |
| `AB_CRO#{event}` / `DAY#{date}` | `ab_events` |
| `AUDIT#{date}` | `audit_logs` |
| `RATELIMIT#{key}` / `WINDOW#{window}` | `rate_limits` |
| `CONFIG#api_keys` / `LATEST` | `config_kv` (pk="CONFIG#api_keys", sk="LATEST") |
| `PUSH#{uid}` / `EP#{endpoint}` | `push_subscriptions` |
| channel map (inline in users.channels) | `channel_map` |
| email credential | `email_credentials` |

### 環境変数 (追加が必要)
| 変数名 | 説明 | 例 |
|--------|------|---|
| `DATABASE_URL` | Turso DB URL | `libsql://nanobot-prod.turso.io` |
| `DATABASE_TOKEN` | Turso auth token | `eyJ...` |

既存の DynamoDB 変数 (`DYNAMODB_SESSIONS_TABLE`, `DYNAMODB_CONFIG_TABLE`) は引き続き使用可。
ただし `db` が Some になると DynamoDB は sessions 以外使わなくなる。

### Cargo features
- `nanobot-lambda` は現在 `features = ["saas"]` で nanobot-core を依存
- `saas = ["dynamodb-backend", "stripe", "lambda", "http-api"]`
- Turso 対応のために `libsql-backend` を追加する必要がある
- 最終的には feature flag でどちらかを選択可能にする設計

---

## libSQL スキーマ (確認済み・変更不要)

スキーマは `/Users/yuki/workspace/ai/chatweb.ai/crates/nanobot-core/src/db/schema.sql` に完全に定義済み。
`LibSqlBackend::run_migrations()` が起動時に `CREATE TABLE IF NOT EXISTS` で適用する。

---

## 実装ステップ

### Phase 1: nanobot-lambda の feature 追加 (推定: 小)
- [ ] `crates/nanobot-lambda/Cargo.toml` の nanobot-core features に `libsql-backend` を追加
  ```toml
  nanobot-core = { path = "../nanobot-core", features = ["saas", "libsql-backend"] }
  ```
- [ ] `crates/nanobot-lambda/src/main.rs` に LibSqlBackend 初期化を追加
  ```rust
  use nanobot_core::db::LibSqlBackend;
  // ...
  if let Ok(db_url) = std::env::var("DATABASE_URL") {
      let db_token = std::env::var("DATABASE_TOKEN").ok();
      match LibSqlBackend::new(&db_url, db_token.as_deref()).await {
          Ok(db) => {
              db.run_migrations().await.ok();
              app_state.db = Some(Arc::new(db));
              info!("Turso DB connected: {}", db_url);
          }
          Err(e) => warn!("Turso DB init failed: {}. Falling back to DynamoDB.", e),
      }
  }
  ```
  - `DATABASE_URL` が未設定なら DynamoDB フォールバック (既存動作を維持)
  - nanobot-fly での実装パターン (`main.rs:52-59`) を参照
- [ ] `cargo check -p nanobot-lambda` でコンパイルエラーがないことを確認

### Phase 2: http.rs のデュアルパス補完 (推定: 大)
現在 `state.db` が Some の場合にのみ 4 箇所でサポートされている。
残りの全 DynamoDB 直呼び箇所を `if let Some(ref db) = state.db { ... } else if let Some(ref dynamo) = state.dynamo_client { ... }` パターンで包む。

優先順序:

1. **認証系** (リクエスト毎に必須)
   - `auth_user_id()` — `db.resolve_auth_token(token)` への切り替え
   - `create_auth_token` 呼び出し箇所 — `db.create_auth_token(token, uid, expires)` 

2. **ユーザー・クレジット** (チャット毎に必須)
   - `get_or_create_user_cached()` — `db.get_or_create_user(uid)` + 既存キャッシュロジック
   - `deduct_credits()` — `db.deduct_credits(uid, amt)`
   - `add_credits_to_user()` — `db.add_credits(uid, amt)`

3. **メモリ**
   - `read_memory_context()` — `db.get_memory(uid, "long_term")` + `db.get_memory(uid, "daily:YYYY-MM-DD")`
   - `save_memory()` / `append_daily_memory()` — `db.set_memory(uid, kind, content)`

4. **レートリミット**
   - `check_rate_limit()` — `db.check_rate_limit(key, 60, max)`
   - `check_rate_limit_hourly()` — `db.check_rate_limit(key, 3600, max)`

5. **スキル・クーポン・共有会話・統計・監査**
   - 各 handler の if/else パターンに DbBackend パスを追加

### Phase 3: セッションストアの libSQL 対応 (推定: 中)
現在 Lambda は `DynamoSessionStore` を使用。
libSQL バックエンドへの切り替え案:
- `memory` テーブルに `SESSION#{key}` kind として格納 (シンプル)
- または `sessions` テーブルを新規追加してスキーマを拡張
- nanobot-fly は `FileSessionStore` を使っているため、Lambda でも同様に `FileSessionStore` を `/tmp` 上で使うことも可能

推奨: 最初は `/tmp` 上の `FileSessionStore` をセッションストアとして継続使用し、
`db` だけ Turso に向ける。セッションは Lambda の cold start 毎にリセットされるが許容範囲。

### Phase 4: Lambda 環境変数設定 (推定: 小)
```bash
aws lambda update-function-configuration \
  --function-name nanobot-prod \
  --environment "Variables={
    DATABASE_URL=libsql://nanobot-prod.turso.io,
    DATABASE_TOKEN=eyJ...
  }"
```
または infra/template.yaml の Globals に追加。

### Phase 5: テスト・検証 (推定: 中)
- [ ] `cargo test -p nanobot-core --features libsql-backend` でユニットテスト
- [ ] `DATABASE_URL=:memory: cargo test -p nanobot-core` で in-process テスト
- [ ] Lambda ローカル実行 (`cargo lambda watch`) で E2E テスト
- [ ] 本番デプロイ前に Turso でデータ確認 (turso db shell)

---

## 注意事項・リスク

### データ移行
- 既存 DynamoDB データを Turso に移行するスクリプトが必要 (ユーザー・クレジット・メモリ)
- 移行前に両方に書き込む dual-write 期間を設けることを検討
- または「新規ユーザーは Turso、既存ユーザーは DynamoDB」と割り切るフェーズも有り

### クレジットの原子性
- DynamoDB: `UpdateItem` の `if_not_exists` + conditional expression で atomic
- libSQL: `BEGIN IMMEDIATE; UPDATE ... WHERE credits_remaining >= ?; COMMIT` で実装済み (`LibSqlBackend::deduct_credits`)
- 移行後は libSQL の atomic update が正しく動くことを確認する

### Lambda の cold start
- libsql クレート は tokio 上で動作するため Lambda との相性は良い
- ただし Turso への初回接続に 50-200ms 程度かかる可能性あり
- `Builder::new_remote_replica` (embedded replica) を使うと接続が高速化できる

### feature flag の衝突
- `saas` feature が `dynamodb-backend` を含む
- `libsql-backend` を追加しても `dynamodb-backend` は残るため、両方のコードがコンパイルされる
- http.rs の `#[cfg(feature = "dynamodb-backend")]` ブロックは引き続き有効
- 最終的には `libsql-backend` が Some の場合は DynamoDB パスを完全スキップするランタイム分岐で十分

### 移行ロールバック
- `DATABASE_URL` 環境変数を削除すれば即座に DynamoDB フォールバックに戻る
- ゼロダウンタイムで切り替え可能な設計を維持すること

---

## テスト方針
- [ ] `cargo test -p nanobot-core --features libsql-backend -- db::` でスキーマ・CRUD テスト
- [ ] Turso staging DB (`libsql://nanobot-staging.turso.io`) で本番前検証
- [ ] `curl https://chatweb.ai/health` で Lambda ヘルスチェック
- [ ] チャット送信 → クレジット消費 → `/api/v1/auth/me` で残高確認
- [ ] ログイン → セッション → メモリ読み書き の E2E

---

## 完了条件
- [ ] `DATABASE_URL=libsql://...` を Lambda に設定すると全ての操作が Turso に向く
- [ ] `DATABASE_URL` 未設定時は既存 DynamoDB で動作する (後方互換)
- [ ] チャット・認証・クレジット・メモリ・スキルが全て正常動作
- [ ] `cargo test -p nanobot-core --features libsql-backend` がグリーン
- [ ] Turso の管理画面でデータが正しく書き込まれていることを確認

---

## 関連ファイル

### 変更が必要なファイル
- `crates/nanobot-lambda/Cargo.toml` — `libsql-backend` feature 追加
- `crates/nanobot-lambda/src/main.rs` — LibSqlBackend 初期化 + AppState.db 設定
- `crates/nanobot-core/src/service/http.rs` — 全 DynamoDB 直呼び箇所に DbBackend デュアルパス追加

### 参照のみ (変更不要)
- `crates/nanobot-core/src/db/backend.rs` — DbBackend trait (完成済み)
- `crates/nanobot-core/src/db/libsql.rs` — LibSqlBackend 実装 (完成済み)
- `crates/nanobot-core/src/db/schema.sql` — スキーマ (完成済み)
- `crates/nanobot-fly/src/main.rs` — 実装パターンの参照実装
