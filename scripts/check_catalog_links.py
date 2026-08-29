#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from generate_catalog import load_catalog

ROOT = Path(__file__).resolve().parents[1]


class _ExternalLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: set[str] = set()

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src", "content"} and value and value.startswith("https://"):
                self.urls.add(value)


def catalog_urls(data: object) -> list[str]:
    urls: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith("https://"):
            urls.add(value)

    visit(data)
    return sorted(urls)


def generated_surface_urls() -> set[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    markdown_urls = set(re.findall(r"https://[^\s)>]+", readme))
    parser = _ExternalLinkParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    return markdown_urls | parser.urls


def check_url(url: str, timeout: float = 12.0, opener=urlopen) -> str | None:
    request = Request(url, headers={"User-Agent": "GreyforgeLabs-catalog-link-check/1.0"})
    try:
        with opener(request, timeout=timeout) as response:
            status = response.getcode()
            if status is None or 200 <= status < 400:
                return None
            return f"{url}: HTTP {status}"
    except HTTPError as error:
        return f"{url}: HTTP {error.code}"
    except (URLError, TimeoutError, OSError) as error:
        return f"{url}: {error}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16 or not 1 <= args.timeout <= 30:
        parser.error("workers must be 1..16 and timeout must be 1..30 seconds")

    urls = sorted(set(catalog_urls(load_catalog())) | generated_surface_urls())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        errors = [error for error in pool.map(lambda url: check_url(url, args.timeout), urls) if error]
    if errors:
        print("catalog link check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"catalog link check passed: {len(urls)} unique URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
