import os
import time
from typing import Set, Optional, Dict
from urllib.robotparser import RobotFileParser
import trafilatura
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse

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

    def __init__(self, base_url: str, output_dir: str = "docs", user_agent: str = "DocCrawler/1.0") -> None:
        """クローラーの初期化

        Args:
            base_url: クロール対象のベースURL（例：https://docs.python.org/ja/3/）
            output_dir: テキストファイルの出力先ディレクトリ（デフォルト: "docs"）
            user_agent: クロール時に使用するUser-Agent文字列（デフォルト: "DocCrawler/1.0"）

        Note:
            - 出力ディレクトリが存在しない場合は自動的に作成されます
            - robots.txtが存在しない場合は警告が表示されます
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.user_agent = user_agent
        self.visited_urls: Set[str] = set()
        
        # 出力ディレクトリの作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
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

        robots.txtからクローラーの待機時間を取得します。以下の順序で値を取得を試みます：
        1. Crawl-delay指定
        2. Request-rate指定
        3. 指定がない場合はNone

        Returns:
            float | None: Crawl-delay値（秒）。取得できない場合はNone
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
        
        # 基本的なチェック
        if not (parsed_url.netloc == parsed_base.netloc
                and parsed_url.path.endswith((".html", "/"))
                and "/_sources/" not in parsed_url.path
                and "/_static/" not in parsed_url.path):
            return False
        
        # robots.txtのルールをチェック
        return self.rp.can_fetch(self.user_agent, url)
    
    def extract_links(self, url: str) -> Set[str]:
        """ページ内の有効なリンクを抽出

        指定されたURLのページからリンクを抽出し、is_valid_urlで有効と判定された
        リンクのみを返します。相対URLは絶対URLに変換されます。

        Args:
            url: リンクを抽出するページのURL

        Returns:
            Set[str]: 有効なリンクのセット。エラーが発生した場合は空のセット

        Note:
            - 抽出したリンクは標準出力に表示されます
            - リンクの総数も表示されます
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

        指定されたURLから始めて、見つかったリンクを再帰的にクロールします。
        各ページのテキストコンテンツを抽出し、ファイルとして保存します。

        Args:
            url: クロール開始URL
            max_pages: 最大クロールページ数（Noneの場合は制限なし）

        Note:
            - 既にクロール済みのURLは再クロールされません
            - robots.txtのCrawl-delayを考慮してクロールします
            - 抽出したテキストは{output_dir}ディレクトリに保存されます
            - ファイル名はURLパスから自動生成されます
        """
        headers = {"User-Agent": self.user_agent}
        if url in self.visited_urls:
            return
        
        if max_pages is not None and len(self.visited_urls) >= max_pages:
            return
        
        self.visited_urls.add(url)
        print(f"Crawling: {url}")
        
        try:
            # Crawl-delayを適用
            time.sleep(self.crawl_delay)
            
            # ページの内容を取得
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded)
                print(f"\n取得したコンテンツ:\n{content[:500]}...\n") # 最初の500文字を表示
                if content:
                    # ファイル名を作成（URLのパスから）
                    path_parts = urlparse(url).path.strip("/").split("/")
                    filename = "_".join(path_parts[1:]) or "index"
                    if not filename.endswith(".txt"):
                        filename += ".txt"
                    
                    # コンテンツを保存
                    output_path = os.path.join(self.output_dir, filename)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    print(f"Saved: {output_path}")
            
            # リンクを抽出して再帰的にクロール
            links = self.extract_links(url)
            for link in links:
                self.crawl(link, max_pages)
                
        except Exception as e:
            print(f"Error crawling {url}: {e}")

def main() -> None:
    """コマンドライン引数を解析してクローラーを実行

    以下のコマンドライン引数をサポートします：
    - url: クロール対象のURL（必須）
    - --max-pages: クロールする最大ページ数
    - --output-dir: 出力ディレクトリ
    - --user-agent: User-Agent文字列

    Example:
        $ python crawler.py https://docs.python.org/ja/3/ --max-pages 5
        $ python crawler.py https://docs.pola.rs/ --output-dir polars_docs
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Read the Docsドキュメントクローラー')
    parser.add_argument('url', help='クロール対象のURL（例：https://docs.pola.rs/）')
    parser.add_argument('--max-pages', type=int, help='クロールする最大ページ数（デフォルト：制限なし）')
    parser.add_argument('--output-dir', default='docs', help='出力ディレクトリ（デフォルト：docs）')
    parser.add_argument('--user-agent', default='DocCrawler/1.0', help='User-Agent文字列（デフォルト：DocCrawler/1.0）')
    
    args = parser.parse_args()
    
    crawler = DocCrawler(args.url, output_dir=args.output_dir, user_agent=args.user_agent)
    crawler.crawl(args.url, max_pages=args.max_pages)

if __name__ == "__main__":
    main()
