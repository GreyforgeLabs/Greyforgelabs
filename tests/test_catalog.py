from __future__ import annotations

import copy
import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_catalog_links import catalog_urls, check_url, generated_surface_urls  # noqa: E402
from generate_catalog import load_catalog, render_index, render_readme, validate_catalog  # noqa: E402


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getcode(self) -> int:
        return self.status


class _HtmlProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_catalog()

    def test_generated_surfaces_match_catalog(self) -> None:
        self.assertEqual((ROOT / "README.md").read_text(), render_readme(self.data))
        self.assertEqual((ROOT / "index.html").read_text(), render_index(self.data))

    def test_invalid_schema_is_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["openforge_utilities"][0] = ["too", "short"]
        with self.assertRaisesRegex(ValueError, "exactly 5 strings"):
            validate_catalog(broken)

    def test_duplicate_names_are_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["archived_specs"].append(copy.deepcopy(broken["archived_specs"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate name"):
            validate_catalog(broken)

    def test_insecure_or_malformed_urls_are_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["proof_trail"][0][1] = "http://example.invalid"
        with self.assertRaisesRegex(ValueError, "credential-free HTTPS URL"):
            validate_catalog(broken)

    def test_broken_link_result_fails(self) -> None:
        error = check_url("https://example.invalid", opener=lambda *_args, **_kwargs: _Response(404))
        self.assertEqual(error, "https://example.invalid: HTTP 404")

    def test_rendered_html_has_expected_structure_and_links(self) -> None:
        parser = _HtmlProbe()
        rendered = render_index(self.data)
        parser.feed(rendered)
        self.assertIn("html", parser.tags)
        self.assertIn("main", parser.tags)
        self.assertIn("footer", parser.tags)
        for url in catalog_urls(self.data):
            if "github.com/GreyforgeLabs/" in url:
                self.assertIn(url, rendered + render_readme(self.data))

    def test_generated_surface_links_are_inventoryable(self) -> None:
        urls = generated_surface_urls()
        self.assertIn("https://x.com/GreyforgeLabs", urls)
        self.assertIn("https://greyforge.tech/about", urls)

    def test_catalog_is_valid_json(self) -> None:
        self.assertIsInstance(json.loads((ROOT / "catalog.json").read_text()), dict)


if __name__ == "__main__":
    unittest.main()
