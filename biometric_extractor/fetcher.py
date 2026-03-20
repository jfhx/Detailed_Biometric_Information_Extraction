import re
from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup


@dataclass
class ArticleContent:
    title: str
    main_text: str
    table_text: str


class ArticleFetcher:
    def __init__(self, timeout_seconds: int = 60, max_chars: int = 30000):
        self.timeout_seconds = timeout_seconds
        self.max_chars = max_chars

    def fetch(self, url: str) -> ArticleContent:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = self._extract_title(soup)
        self._remove_noise_tags(soup)

        main_text = self._extract_main_text(soup)
        table_text = self._extract_table_text(soup)

        main_text = self._clean_text(main_text)[: self.max_chars]
        table_text = self._clean_text(table_text)[: self.max_chars]

        return ArticleContent(title=title, main_text=main_text, table_text=table_text)

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        if soup.title and soup.title.text:
            return soup.title.text.strip()
        h1 = soup.find("h1")
        return h1.get_text(" ", strip=True) if h1 else ""

    @staticmethod
    def _remove_noise_tags(soup: BeautifulSoup) -> None:
        for tag_name in [
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav",
            "aside",
            "form",
            "svg",
        ]:
            for node in soup.find_all(tag_name):
                node.decompose()

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        candidates: List[str] = []

        selectors = [
            "article",
            "main",
            "[role='main']",
            ".content",
            ".article",
            ".post-content",
            ".entry-content",
        ]

        for selector in selectors:
            for block in soup.select(selector):
                text = block.get_text("\n", strip=True)
                if len(text) > 200:
                    candidates.append(text)

        if not candidates:
            body = soup.body if soup.body else soup
            return body.get_text("\n", strip=True)

        return max(candidates, key=len)

    def _extract_table_text(self, soup: BeautifulSoup) -> str:
        table_lines: List[str] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                values = [self._clean_text(cell.get_text(" ", strip=True)) for cell in cells]
                values = [v for v in values if v]
                if values:
                    table_lines.append(" | ".join(values))
        return "\n".join(table_lines)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()
