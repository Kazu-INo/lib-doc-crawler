import os
import time
from typing import Set, Optional
from urllib.robotparser import RobotFileParser
import trafilatura
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
from markitdown import MarkItDown

class DocCrawler:
    """ドキュメントサイトをクロールしてテキストコンテンツを抽出するクローラー

    このクローラーは主にRead the Docsスタイルのドキュメントサイトに対して動作するように設計されています。
    robots.txtを考慮し、指定されたドメイン内のHTMLページのみを対象とします。

    Attributes:
        base_url (str): クロール対象のベースURL
        output_dir (str): 抽出したテキストの保存先ディレクトリ
        user_agent (str): クロール時に使用するUser-Agent文字列
        visited_urls (Set[str]): クロール済みURLを管理するセット
        library_name (str): クロール対象のライブラリ名（URLから抽出）
        rp (RobotFileParser): robots.txtを解析するパーサー
        crawl_delay (float): クロール間隔（秒）
    """

    def __init__(
        self, 
        base_url: str, 
        output_dir: str = "output", 
        user_agent: str = "DocCrawler/1.0",
        output_file_name: str = "crawled_content.md"
    ) -> None:
        """クローラーの初期化

        Args:
            base_url: クロール対象のベースURL（例：https://docs.python.org/ja/3/）
            output_dir: 抽出したテキストの保存先ディレクトリ（デフォルト: output）
            user_agent: クロール時に使用するUser-Agent文字列（デフォルト: "DocCrawler/1.0"）
            output_file_name: すべてのコンテンツを書き出す単一ファイル名
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.visited_urls: Set[str] = set()

        # 出力ディレクトリを作成
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # 「すべてのページを集約するためのファイル」を一意に決める
        self.output_file_path = os.path.join(self.output_dir, output_file_name)

        # ライブラリ名の取得（URLから）
        self.library_name = urlparse(base_url).path.strip("/").split("/")[0]

        # robots.txtの解析
        self.rp = RobotFileParser()
        parsed_url = urlparse(base_url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        self.rp.set_url(robots_url)
        try:
            self.rp.read()
            print(f"robots.txtを読み込みました: {robots_url}")
        except Exception as e:
            print(f"Warning: robots.txtの読み込みに失敗しました: {e}")

        # Crawl-delay（デフォルト: 1秒）
        self.crawl_delay = self._get_crawl_delay() or 1.0

    def _get_crawl_delay(self) -> Optional[float]:
        """robots.txtからCrawl-delayを取得

        Returns:
            float | None: 取得したCrawl-delay値（秒）。取得できない場合はNone
        """
        try:
            return float(self.rp.crawl_delay("*") or self.rp.request_rate("*").seconds)
        except (AttributeError, TypeError):
            return None

    def is_valid_url(self, url: str) -> bool:
        """URLが有効なクロール対象かを判定

        以下の条件をすべて満たすURLを有効と判定します：
        1. base_urlと同じドメイン
        2. .htmlで終わるか、/で終わる（ディレクトリ）
        3. /_sources/や/_static/を含まない
        4. robots.txtのルールに違反しない

        Args:
            url: 判定対象のURL

        Returns:
            bool: URLが有効な場合はTrue、それ以外はFalse
        """
        parsed_base = urlparse(self.base_url)
        parsed_url = urlparse(url)

        # 同じドメインかどうか
        if parsed_url.netloc != parsed_base.netloc:
            return False

        # パスが .html で終わる、または / で終わること
        if not (parsed_url.path.endswith(".html") or parsed_url.path.endswith("/")):
            return False

        # /_sources/, /_static/ を含まないこと
        if "/_sources/" in parsed_url.path or "/_static/" in parsed_url.path:
            return False

        # robots.txtルールに違反していないか
        return self.rp.can_fetch(self.user_agent, url)

    def extract_links(self, url: str) -> Set[str]:
        """ページ内の有効なリンクを抽出

        Args:
            url: リンクを抽出するページのURL

        Returns:
            Set[str]: 有効なリンクのセット。エラー時は空集合
        """
        headers = {"User-Agent": self.user_agent}
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            links = set()

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                absolute_url = urljoin(url, href)

                if self.is_valid_url(absolute_url):
                    print(f"有効なリンクを発見: {absolute_url}")
                    links.add(absolute_url)

            print(f"\n合計 {len(links)} 個の有効なリンクを発見\n")
            return links
        except Exception as e:
            print(f"Error extracting links from {url}: {e}")
            return set()

    def crawl(self, url: str, max_pages: Optional[int] = None) -> None:
        """再帰的にページをクロールしてコンテンツを抽出

        Args:
            url: クロール開始URL
            max_pages: 最大クロールページ数（Noneの場合は制限なし）
        """
        # すでに訪問したURL、または最大ページ数に達した場合は処理終了
        if url in self.visited_urls:
            return
        if max_pages is not None and len(self.visited_urls) >= max_pages:
            return

        self.visited_urls.add(url)
        print(f"Crawling: {url}")

        try:
            # Crawl-delayを考慮
            time.sleep(self.crawl_delay)

            # ページの内容を取得
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                print(f"Warning: Could not fetch content from {url}")
                return

            # テキスト抽出
            content = trafilatura.extract(downloaded)
            if not content:
                print(f"Warning: Could not extract content from {url}")
                return

            print(f"\n取得したコンテンツ(先頭500文字):\n{content[:500]}...\n")

            # コンテンツを保存（単一ファイルに追記）
            self._save_content(url, content)

            # 再帰的にリンクをクロール
            links = self.extract_links(url)
            for link in links:
                self.crawl(link, max_pages)

        except Exception as e:
            print(f"Error crawling {url}: {e}")

    def _save_content(self, url: str, content: str) -> None:
        """抽出したコンテンツを1つのMarkdownファイルに追記"""
        try:
            md = MarkItDown()
            markdown_content = md.convert(content)
        except Exception as e:
            print(f"Markdown変換に失敗しました。プレーンテキストのまま保存します: {e}")
            markdown_content = content  # 失敗時はプレーンテキスト

        # ファイル末尾に追記する
        page_content = f"""
---
source: {url}
crawled_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

{markdown_content}

---
"""

        # "append"モードで書き込む → 同一ファイルにどんどん追記
        try:
            with open(self.output_file_path, "a", encoding="utf-8") as f:
                f.write(page_content)
            print(f"[SUCCESS] {url} のコンテンツを {self.output_file_path} に追記しました。")
        except Exception as e:
            print(f"[ERROR] ファイル書き込みに失敗しました: {e}\n→ パス: {self.output_file_path}")

def main() -> None:
    """コマンドライン引数を解析してクローラーを実行

    以下のコマンドライン引数をサポートします：
    - url: クロール対象のURL（必須）
    - --max-pages: クロールする最大ページ数
    - --output-dir: 出力ディレクトリ
    - --user-agent: User-Agent文字列
    """
    import argparse

    parser = argparse.ArgumentParser(description='Read the Docsドキュメントクローラー')
    parser.add_argument('url', help='クロール対象のURL（例：https://docs.pola.rs/）')
    parser.add_argument('--max-pages', type=int, help='クロールする最大ページ数（デフォルト：制限なし）')
    parser.add_argument('--user-agent', default='DocCrawler/1.0', help='User-Agent文字列（デフォルト：DocCrawler/1.0）')
    parser.add_argument('--output-dir', default='output', help='出力ディレクトリ（デフォルト：output）')

    args = parser.parse_args()

    # 出力ファイル名は自由に変更OK
    crawler = DocCrawler(
        base_url=args.url, 
        output_dir=args.output_dir, 
        user_agent=args.user_agent,
        output_file_name="crawled_content.md"  # すべてのコンテンツを集約するファイル
    )
    crawler.crawl(args.url, max_pages=args.max_pages)

if __name__ == "__main__":
    main()
