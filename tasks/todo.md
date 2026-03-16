# 7タスク実装計画 — chatweb.ai 機能拡張

## 概要
main.py の AGENTS 辞書に新エージェント4体を追加し、ROUTER_PROMPT / PLANNER_PROMPT を更新。
index.html のエージェント選択UIにカテゴリタブ+検索フィルターを追加。
i18n (LANG_STRINGS) に新UI向けキーを全言語(ja/en/zh/ko/fr/es/de/pt)分追加。

---

## 調査結果

### main.py 構造
- AGENTS 辞書: L3807〜L4445 (30エージェント定義)
- ROUTER_PROMPT: L5265〜L5295 (単一JSON出力)
- PLANNER_PROMPT: L5298〜L5327
- ファイルアップロード: `/upload` エンドポイント L8199〜L8254
  - PDF: pdfplumber で最大10ページ/5000文字抽出済み
  - CSV: 50行プレビュー抽出済み
  - Excel (.xlsx): **未対応** → openpyxl を追加する必要あり
  - `_uploaded_files` dict でセッション横断共有
- `tool_site_deploy`: L2074〜 (site_publisher が使う site_deploy ツール)
- Google Workspace エージェントのパターン: `mcp_tools`/`real_tools` に gogcli ツール名を並べ、system に操作説明

### index.html 構造
- エージェント選択モーダル: L1087〜L1096
  - `<div id="agent-selector-modal">` → `<h3>` + `<div id="agent-grid-pills">` + footer
  - footer に「クリックで切り替え」テキストと「閉じる」ボタン
- `renderAgents()`: L1232〜L1283
  - `agent-grid-pills` へ全エージェントをピル形式でレンダリング
  - 選択時 `selectAgent(id)` + `openAgentDetail(id)` を呼ぶ
- LANG_STRINGS: L3853〜L4300 (ja/en/zh/ko/fr/es/de/pt の8言語)
  - 各オブジェクトに同じキーセット。新UIキーは全8言語に追加必要
- `_currentLang`, `t(key)`, `applyLanguage(code)` で国際化

### ファイルアップロードインフラ
- `<input type="file" id="file-input" accept=".pdf,.jpg,.jpeg,.png,.gif,.webp,.csv,.txt,.md">` (L978)
  - `.xlsx` は **accept 属性に未追加** → index.html も変更必要
- アップロード後 `file_id` が `_uploaded_files` に保存される
- `rag` エージェントは `rag_index`/`rag_search` で file_id を受け取る
- `sql` エージェントは `csv_to_db` で file_id からCSVをSQLiteに変換

---

## 実装ステップ

### Task 1: SNS/マーケティングAI (main.py)

**挿入位置**: L4445 (AGENTS辞書の閉じ `}` の直前、`"coder"` エントリのあと)

```python
"sns": {
    "name": "📣 SNS/マーケティングAI",
    "color": "#e11d48",
    "description": "X/LinkedIn/Instagram投稿文・コピーライティング・ハッシュタグ提案",
    "mcp_tools": ["web_search"],
    "real_tools": ["web_search"],
    "system": """...""",
},
```

**ROUTER_PROMPT 更新** (L5291 の `research` 行の直前に追加):
```
- sns: SNS投稿・X(Twitter)・Instagram・LinkedIn・コピーライティング・ハッシュタグ・キャプション
```

**PLANNER_PROMPT 更新** (L5316 の `coder` 行に追記):
```
- sns: SNS/マーケティングコンテンツ作成
```

- [ ] Step 1: `AGENTS` 辞書に `"sns"` エントリを追加（L4444直前に挿入）（小）
- [ ] Step 2: ROUTER_PROMPT に sns ルーティングルールを追加（小）
- [ ] Step 3: PLANNER_PROMPT に sns を追加（小）

---

### Task 2: 会議メモAI (main.py)

**挿入位置**: Task 1 の `sns` エントリの直後

```python
"meeting": {
    "name": "📝 会議メモAI",
    "color": "#0891b2",
    "description": "議事録・アクションアイテム抽出・サマリー生成",
    "mcp_tools": ["docs_create"],
    "real_tools": ["docs_create"],
    "system": """...""",
},
```

**ROUTER_PROMPT 更新**:
```
- meeting: 会議メモ・議事録・アクションアイテム・MTG要約・「議事録を作って」
```

- [ ] Step 1: `AGENTS` 辞書に `"meeting"` エントリを追加（小）
- [ ] Step 2: ROUTER_PROMPT に meeting ルーティングルールを追加（小）

---

### Task 3: エージェント選択UI改善 (index.html)

**変更箇所1: CSS追加** — L247〜L312 の `#agent-selector-modal` スタイルブロックに追記
- カテゴリタブ `.agent-cat-tabs` / `.agent-cat-tab` / `.agent-cat-tab.active` スタイル
- 検索入力 `.agent-search-input` スタイル

**変更箇所2: HTMLモーダル** — L1089〜L1096 のモーダル内部を変更
```html
<div id="agent-selector-modal">
  <h3 data-i18n="ai_agents">AIエージェント</h3>
  <!-- NEW: 検索フィールド -->
  <input class="agent-search-input" id="agent-search" type="text"
         placeholder="エージェントを検索…" oninput="filterAgentGrid(this.value)">
  <!-- NEW: カテゴリタブ -->
  <div class="agent-cat-tabs" id="agent-cat-tabs">
    <button class="agent-cat-tab active" data-cat="all" onclick="setAgentCat('all')">全て</button>
    <button class="agent-cat-tab" data-cat="business" onclick="setAgentCat('business')">ビジネス</button>
    <button class="agent-cat-tab" data-cat="creative" onclick="setAgentCat('creative')">クリエイティブ</button>
    <button class="agent-cat-tab" data-cat="tech" onclick="setAgentCat('tech')">技術</button>
    <button class="agent-cat-tab" data-cat="google" onclick="setAgentCat('google')">Google</button>
  </div>
  <div class="agent-grid" id="agent-grid-pills"></div>
  <div class="agent-selector-footer">...</div>
</div>
```

**変更箇所3: JS追加** — L1282〜L1284 の `selectAgent` 関数の直前に追加
- `AGENT_CATEGORIES` 定数（エージェントid → カテゴリ のマッピング）
- `setAgentCat(cat)` 関数
- `filterAgentGrid(query)` 関数
- 既存 `renderAgents()` 内の grid.innerHTML = '' の後に `applyAgentFilter()` ヘルパー追加

**カテゴリマッピング**:
```javascript
const AGENT_CATEGORIES = {
  // business
  analyst: 'business', legal: 'business', finance: 'business',
  schedule: 'business', notify: 'business', gmail: 'business',
  meeting: 'business', sns: 'business', crm: 'business',
  // creative
  image: 'creative', site_publisher: 'creative', deployer: 'creative',
  presentation: 'creative',
  // tech
  code: 'tech', qa: 'tech', devops: 'tech', mobile: 'tech',
  coder: 'tech', rag: 'tech', sql: 'tech', pdf_reader: 'tech',
  // google
  calendar: 'google', drive: 'google', sheets: 'google',
  docs: 'google', contacts: 'google', tasks: 'google',
};
```

**i18n キー追加** (Task 7 と統合):
- `agent_search_placeholder`: 「エージェントを検索…」
- `cat_all` / `cat_business` / `cat_creative` / `cat_tech` / `cat_google`

- [ ] Step 1: CSS にカテゴリタブ・検索入力スタイルを追加（小）
- [ ] Step 2: HTML モーダルに検索input + タブ div を追加（小）
- [ ] Step 3: `AGENT_CATEGORIES` マッピング定数を追加（小）
- [ ] Step 4: `setAgentCat()` / `filterAgentGrid()` 関数を追加（中）
- [ ] Step 5: `renderAgents()` 内のグリッドレンダリングに `data-cat` 属性を付与するよう修正（小）

---

### Task 4: PDF/ExcelリーダーAI (main.py + index.html)

**main.py 変更**:

1. `upload_file()` (L8199〜) に Excel対応を追加:
   - L8215 の `else: file_type = "text"` を修正し `.xlsx`/`.xls` → `"excel"` に分岐
   - L8224〜L8243 の content 抽出ブロックに `elif file_type == "excel":` を追加
   - `openpyxl` を `import` (L6 付近のインポート行に追加)

2. `AGENTS` 辞書にエントリ追加（meeting の直後）:
```python
"file_reader": {
    "name": "📄 PDF/ExcelリーダーAI",
    "color": "#7c3aed",
    "description": "PDF・Excel・CSVファイルを分析・要約・Q&A",
    "mcp_tools": ["rag_index", "rag_search", "csv_to_db", "sql_query"],
    "real_tools": ["rag_index", "rag_search", "csv_to_db", "sql_query"],
    "system": """...""",
},
```

**index.html 変更**:
- L978: `accept=".pdf,...,.csv,.txt,.md"` → `.xlsx,.xls` を追記

**ROUTER_PROMPT 更新**:
```
- file_reader: アップロードファイル分析・PDF要約・Excel/CSV解析・「ファイルを読んで」「アップロードした資料を」
```

- [ ] Step 1: `main.py` L6 のインポート行に `openpyxl` を追加（小）
- [ ] Step 2: `upload_file()` の Excel 分岐を追加（小）
- [ ] Step 3: `AGENTS` に `file_reader` エントリを追加（小）
- [ ] Step 4: ROUTER_PROMPT に file_reader ルールを追加（小）
- [ ] Step 5: `index.html` の file-input accept 属性に `.xlsx,.xls` を追加（小）

---

### Task 5: プレゼンAI (main.py)

**挿入位置**: `file_reader` エントリの直後

```python
"presentation": {
    "name": "🎤 プレゼンAI",
    "color": "#7c3aed",
    "description": "HTMLスライドショーを生成してXXXXX.chatweb.aiで公開",
    "mcp_tools": ["site_deploy", "web_search"],
    "real_tools": ["site_deploy", "web_search"],
    "system": """...""",
},
```

システムプロンプト要件:
- reveal.js (CDN) を使ったスライドHTML生成ルール
- `site_deploy` で即時公開 → URLを返す
- スライドレイアウト: タイトル/コンテンツ/箇条書き/画像の4テンプレートパターン

**ROUTER_PROMPT 更新**:
```
- presentation: プレゼン・スライド・資料作成・「パワポ」「スライドを作って」「発表資料」
```

- [ ] Step 1: `AGENTS` に `presentation` エントリを追加（小）
- [ ] Step 2: ROUTER_PROMPT に presentation ルールを追加（小）

---

### Task 6: CRM/営業AI (main.py)

**挿入位置**: `presentation` エントリの直後

```python
"crm": {
    "name": "💼 CRM/営業AI",
    "color": "#0369a1",
    "description": "営業パイプライン管理・フォローアップメール・案件トラッキング",
    "mcp_tools": ["site_deploy", "site_list", "gmail_send", "web_search"],
    "real_tools": ["site_deploy", "gmail_send"],
    "hitl_required": True,
    "system": """...""",
},
```

実装方針:
- D1 API (`/api/items`, `/api/kv/:key`) を site_publisher の既存インフラ経由で利用
- CRMダッシュボードHTMLを site_deploy で公開し、`/api/items` でデータ永続化
- フォローアップメール草稿は HITL 承認後に gmail_send で送信

**ROUTER_PROMPT 更新**:
```
- crm: 営業・顧客管理・CRM・パイプライン・フォローアップ・案件・商談
```

- [ ] Step 1: `AGENTS` に `crm` エントリを追加（小）
- [ ] Step 2: ROUTER_PROMPT に crm ルールを追加（小）

---

### Task 7: 多言語UI精度向上 (index.html)

**変更対象**: LANG_STRINGS (L3853〜L4300) の ja/en/zh/ko/fr/es/de/pt の全8言語

**追加する新キー** (Task 3のUI要素 + 不足キー):
```javascript
// カテゴリタブ
cat_all: '全て',
cat_business: 'ビジネス',
cat_creative: 'クリエイティブ',
cat_tech: '技術',
cat_google: 'Google',
agent_search_placeholder: 'エージェントを検索…',
// menu items (現在 data-i18n なし)
menu_tokushoho: '特定商取引法に基づく表記',
menu_link_code: 'LINE/Telegram連携コード',
```

**各言語の翻訳**:
| キー | ja | en | zh | ko |
|---|---|---|---|---|
| cat_all | 全て | All | 全部 | 전체 |
| cat_business | ビジネス | Business | 商务 | 비즈니스 |
| cat_creative | クリエイティブ | Creative | 创意 | 크리에이티브 |
| cat_tech | 技術 | Tech | 技术 | 기술 |
| cat_google | Google | Google | Google | Google |
| agent_search_placeholder | エージェントを検索… | Search agents… | 搜索代理… | 에이전트 검색… |
| menu_tokushoho | 特定商取引法に基づく表記 | Legal Notice | 法律声明 | 법적 고지 |
| menu_link_code | LINE/Telegram連携コード | LINE/Telegram Link Code | LINE/Telegram关联码 | LINE/Telegram연동코드 |

fr/es/de/pt も同様に追加（標準翻訳）。

- [ ] Step 1: `ja` オブジェクトに新キーを追加（小）
- [ ] Step 2: `en` オブジェクトに新キーを追加（小）
- [ ] Step 3: `zh` オブジェクトに新キーを追加（小）
- [ ] Step 4: `ko` オブジェクトに新キーを追加（小）
- [ ] Step 5: `fr`/`es`/`de`/`pt` に新キーを追加（小）
- [ ] Step 6: HTML の `data-i18n` 属性が欠けているボタン要素を確認して追加（小）

---

## テスト方針

各タスク完了後:
- [ ] `python -c "import main"` でシンタックスエラーなし確認
- [ ] ブラウザで `/` を開き、エージェント選択モーダルを開いてカテゴリタブ・検索が動作することを確認
- [ ] 新エージェント (`sns`, `meeting`, `file_reader`, `presentation`, `crm`) がエージェントグリッドに表示されることを確認
- [ ] `curl -X POST /chat/sns -d '{"message":"Instagramの投稿文を作って"}'` でルーティング確認
- [ ] XLSXファイルをアップロードして file_reader エージェントに解析させる
- [ ] presentation エージェントで「3スライドのプレゼンを作って公開して」を試す
- [ ] 言語を EN/ZH/KO に切り替えてカテゴリタブが翻訳されることを確認

---

## リスク

1. **openpyxl 未インストール**: requirements.txt / Dockerfile に追加が必要かもしれない
   → 実装前に `import openpyxl` が通るか確認。通らなければ `pip install openpyxl` + requirements.txt 追記
2. **エージェント数増加でモーダル縦長化**: カテゴリフィルターで解決済み
3. **ROUTER_PROMPT の長さ増加**: claude-haiku の max_tokens=120 は十分。ルール追加は5行以内
4. **LANG_STRINGS の言語漏れ**: fr/es/de/pt の新キーは英語ベースで補完可（`t()` 関数は ja フォールバックあり）

---

## 完了条件

- [ ] 4新エージェント (sns/meeting/file_reader/presentation/crm) が `/agents` エンドポイントで返される
- [ ] エージェント選択モーダルにカテゴリタブと検索フィールドが表示される
- [ ] カテゴリタブ切り替えで対応エージェントのみ表示される
- [ ] 検索フィールドでエージェント名をフィルタリングできる
- [ ] LANG_STRINGS の新キーが ja/en/zh/ko の全4主要言語に定義されている
- [ ] XLSXファイルのアップロードが `/upload` エンドポイントで受け付けられる
- [ ] `python -c "import main"` が成功する

---

## 実装順序 (推奨)

1. Task 1 → Task 2 → Task 6 → Task 5 → Task 4 (main.py 変更をまとめて)
2. Task 3 → Task 7 (index.html 変更をまとめて)
3. テスト一括実行

