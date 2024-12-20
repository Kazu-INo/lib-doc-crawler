# Library Documentation Crawler

Read the Docsのドキュメントをクロールし、テキストコンテンツを抽出するツールです。

## 機能

- trafilaturaを使用してドキュメントのコンテンツを抽出
- 再帰的にページを探索
- 取得したコンテンツをtxtファイルとして保存
- robots.txtに準拠したクローリング
  - Crawl-delayの遵守
  - User-agentとDisallowルールの遵守
- Docker + Poetry環境で実行可能

## 使用方法

### Dockerを使用する場合

1. イメージのビルド:
```bash
docker compose build
```

2. Compose設定ファイルを使用した実行:
```bash
docker compose up --build
```

3. 個別のコマンドとして実行:
```bash
# 基本的な使用方法（URLのみ指定）
docker compose run --rm app python src/crawler.py https://docs.pola.rs/

# 最大ページ数を指定
docker compose run --rm app python src/crawler.py https://docs.pola.rs/ --max-pages 5

# 出力ディレクトリを指定
docker compose run --rm app python src/crawler.py https://docs.pola.rs/ --output-dir custom_docs

# 全ての引数を指定
docker compose run --rm app python src/crawler.py https://docs.pola.rs/ --max-pages 5 --output-dir custom_docs --user-agent "CustomBot/1.0"
```

### ローカルで実行する場合

1. 依存関係のインストール:
```bash
poetry install
```

2. スクリプトの実行:
```bash
# 基本的な使用方法（URLのみ指定）
poetry run python src/crawler.py https://docs.pola.rs/

# 最大ページ数を指定
poetry run python src/crawler.py https://docs.pola.rs/ --max-pages 5

# 出力ディレクトリを指定
poetry run python src/crawler.py https://docs.pola.rs/ --output-dir custom_docs

# 全ての引数を指定
poetry run python src/crawler.py https://docs.pola.rs/ --max-pages 5 --output-dir custom_docs --user-agent "CustomBot/1.0"
```

## コマンドライン引数

以下の引数を指定できます：

- `url`: クロール対象のURL（必須）
- `--max-pages`: クロールする最大ページ数（オプション、デフォルト：制限なし）
- `--output-dir`: 出力ディレクトリ（オプション、デフォルト：docs）
- `--user-agent`: User-Agent文字列（オプション、デフォルト：DocCrawler/1.0）

## robots.txt対応

このクローラーは以下のrobots.txtルールに従います：

- Crawl-delay: 指定された待機時間を遵守
- User-agent: 指定されたUser-agentでアクセス
- Disallowルール: クロール禁止パスを回避

## 出力

クロールしたコンテンツは`docs`ディレクトリに保存されます。
ファイル名はURLのパスから自動的に生成されます。

## 注意事項

- クロール対象のサイトのロボット規約を確認してください
- 過度なリクエストを送信しないよう、適切な`max_pages`を設定してください
