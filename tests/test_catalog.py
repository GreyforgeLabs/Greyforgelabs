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
from generate_catalog import load_catalog, render_cards, render_index, render_readme, validate_catalog  # noqa: E402


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
        for path, content in render_cards(self.data).items():
            self.assertEqual(path.read_text(), content)

    def test_every_active_project_has_a_card_in_the_readme(self) -> None:
        readme = render_readme(self.data)
        for path in render_cards(self.data):
            self.assertIn(f"assets/cards/{path.name}", readme)
            self.assertTrue(path.read_text().startswith("<svg "))

    def test_sley_is_the_linked_flagship(self) -> None:
        self.assertEqual([row[0] for row in self.data["flagship"]], ["Sley"])
        for rendered in (render_readme(self.data), render_index(self.data)):
            self.assertIn("https://github.com/sley-lang", rendered)
        self.assertIn("https://github.com/sley-lang/sley", render_readme(self.data))

    def test_unknown_category_is_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["openforge_utilities"][0][5] = "misc"
        with self.assertRaisesRegex(ValueError, "category must be one of"):
            validate_catalog(broken)

    def test_active_catalog_contains_only_the_approved_oss_tools(self) -> None:
        expected = {
            "reprieve", "omarchy-hotbar", "omarchy-grabbar", "atomic-json-store",
            "node-healthcheck", "service-cartographer", "devcap", "memory-quality-gate",
            "sqlite-checkpoint", "cooldown-guard", "voiceops",
        }
        self.assertEqual({row[0] for row in self.data["openforge_utilities"]}, expected)
        for rendered in (render_readme(self.data), render_index(self.data)):
            for name in expected:
                self.assertIn(f"https://github.com/GreyforgeLabs/{name}", rendered)

    def test_historical_projects_are_labeled_and_separate_from_active_tools(self) -> None:
        history = {row[0]: row[4] for row in self.data["archived_specs"]}
        self.assertEqual(set(history), {"sley-legacy", "pcam", "geminibot"})
        self.assertIn("Sley 1.2", history["sley-legacy"])
        self.assertIn("legacy", history["sley-legacy"].lower())
        self.assertIn("retired", history["pcam"].lower())
        self.assertIn("draft", history["pcam"].lower())
        self.assertIn("no conformance class claimed", history["pcam"].lower())
        self.assertIn("archived", history["geminibot"].lower())
        self.assertIn("no further releases", history["geminibot"].lower())
        for rendered in (render_readme(self.data), render_index(self.data)):
            self.assertIn("Historical Projects", rendered)
            for name in history:
                self.assertIn(f"https://github.com/GreyforgeLabs/{name}", rendered)

    def test_current_public_surfaces_are_oss_only(self) -> None:
        self.assertEqual(self.data["products"], [])
        surfaces = [json.dumps(self.data), render_readme(self.data), render_index(self.data)]
        retired = (
            "zjx", "forgeshield", "forgestrike",
            "forgequant", "agent cards", "forgevideo", "forgeclaw", "/store",
            "privacy tools", "privacy utilities", "market research", "private-package",
            "software products", "llms.txt",
        )
        for surface in surfaces:
            for phrase in retired:
                self.assertNotIn(phrase, surface.lower())

    def test_legacy_record_identifies_the_source_tag_not_a_missing_release(self) -> None:
        self.assertIn(
            ["Sley 1.2.1 legacy source tag", "https://github.com/GreyforgeLabs/sley-legacy/tree/v1.2.1"],
            self.data["proof_trail"],
        )

    def test_readme_link_inventory_stops_at_html_attribute_quotes(self) -> None:
        for url in generated_surface_urls():
            self.assertNotIn('"', url)
            self.assertNotIn("'", url)

    def test_catalog_links_do_not_depend_on_social_network_access(self) -> None:
        for rendered in (render_readme(self.data), render_index(self.data)):
            self.assertNotIn("https://x.com/", rendered)

    def test_empty_products_are_valid_and_hide_the_product_section(self) -> None:
        data = copy.deepcopy(self.data)
        data["products"] = []
        validate_catalog(data)
        rendered = render_index(data)
        self.assertNotIn('id="products-title"', rendered)
        self.assertNotIn('class="card-grid product-grid"', rendered)

    def test_nonempty_products_still_render_when_explicitly_supplied(self) -> None:
        data = copy.deepcopy(self.data)
        data["products"] = [["Example & Tool", "OSS", "https://example.invalid", "A <tool>"]]
        validate_catalog(data)
        rendered = render_index(data)
        self.assertIn('id="products-title"', rendered)
        self.assertIn("Example &amp; Tool", rendered)
        self.assertIn("A &lt;tool&gt;", rendered)

    def test_empty_required_tables_are_still_rejected(self) -> None:
        for key in ("surfaces", "flagship", "openforge_utilities", "archived_specs", "proof_trail"):
            with self.subTest(key=key):
                broken = copy.deepcopy(self.data)
                broken[key] = []
                with self.assertRaisesRegex(ValueError, "non-empty list"):
                    validate_catalog(broken)

    def test_credential_bearing_urls_are_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["proof_trail"][0][1] = "https://user:password@example.invalid"
        with self.assertRaisesRegex(ValueError, "credential-free HTTPS URL"):
            validate_catalog(broken)

    def test_invalid_schema_is_rejected(self) -> None:
        broken = copy.deepcopy(self.data)
        broken["openforge_utilities"][0] = ["too", "short"]
        with self.assertRaisesRegex(ValueError, "exactly 6 strings"):
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
        self.assertIn("https://github.com/GreyforgeLabs", urls)
        self.assertIn("https://greyforge.tech/about", urls)

    def test_catalog_is_valid_json(self) -> None:
        self.assertIsInstance(json.loads((ROOT / "catalog.json").read_text()), dict)


if __name__ == "__main__":
    unittest.main()
