#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog.json"
README = ROOT / "README.md"
INDEX = ROOT / "index.html"
CARDS = ROOT / "assets" / "cards"


CATALOG_VERSION = "1.1.0"
CATEGORIES = ("desktop", "operator", "agent")

TABLE_WIDTHS = {
    "surfaces": 3,
    "flagship": 5,
    "products": 4,
    "openforge_utilities": 6,
    "archived_specs": 5,
    "proof_trail": 2,
}


def validate_url(value: str, location: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{location} must be an absolute credential-free HTTPS URL")


def validate_catalog(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("catalog root must be an object")
    required = ["organization", "surfaces", "flagship", "products", "openforge_utilities", "archived_specs", "proof_trail"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"catalog.json missing required keys: {', '.join(missing)}")
    if data.get("catalog_version") != CATALOG_VERSION:
        raise ValueError(f"catalog_version must be {CATALOG_VERSION}")
    organization = data["organization"]
    if not isinstance(organization, dict):
        raise ValueError("organization must be an object")
    for key in ("name", "tagline", "description"):
        if not isinstance(organization.get(key), str) or not organization[key].strip():
            raise ValueError(f"organization.{key} must be a non-empty string")
    for key, width in TABLE_WIDTHS.items():
        if not isinstance(data[key], list):
            raise ValueError(f"catalog.json key must be a list: {key}")
        if not data[key] and key != "products":
            raise ValueError(f"catalog.json key must be a non-empty list: {key}")
        names: set[str] = set()
        for row_number, row in enumerate(data[key], start=1):
            if not isinstance(row, list) or len(row) != width:
                raise ValueError(f"{key}[{row_number}] must contain exactly {width} strings")
            if any(not isinstance(cell, str) or not cell.strip() for cell in row):
                raise ValueError(f"{key}[{row_number}] must contain only non-empty strings")
            normalized_name = row[0].casefold()
            if normalized_name in names:
                raise ValueError(f"{key} contains duplicate name: {row[0]}")
            names.add(normalized_name)
            for column, cell in enumerate(row):
                if cell.startswith(("http://", "https://")):
                    validate_url(cell, f"{key}[{row_number}][{column}]")
    for row_number, row in enumerate(data["openforge_utilities"], start=1):
        if row[5] not in CATEGORIES:
            raise ValueError(f"openforge_utilities[{row_number}] category must be one of: {', '.join(CATEGORIES)}")
    card_names = [row[0].casefold() for row in data["flagship"] + data["openforge_utilities"]]
    if len(card_names) != len(set(card_names)):
        raise ValueError("flagship and openforge_utilities names must not overlap")
    return data


def load_catalog(path: Path = CATALOG) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return validate_catalog(data)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"invalid catalog: {error}") from error


def md_link(label: str, url: str) -> str:
    return f"[{label}]({url})"


STACK_BADGES = {
    "Rust": ("B7410E", "rust"),
    "Python": ("3776AB", "python"),
    "C++": ("00599C", "cplusplus"),
    "QML": ("41CD52", "qt"),
    "Shell": ("4EAA25", "gnubash"),
    "Node.js": ("339933", "nodedotjs"),
    "Spec": ("64748B", "readthedocs"),
}

SURFACE_BADGES = {
    "greyforge.tech": ("F2B84B", "firefoxbrowser", "000000"),
    "sleylang.org": ("54D6D0", "", "000000"),
    "sley-lang": ("EE7890", "github", "000000"),
    "GreyforgeLabs": ("7EDC89", "github", "000000"),
}

CATEGORY_STYLE = {
    # label, accent start, accent end
    "flagship": ("PROGRAMMING LANGUAGE", "#54d6d0", "#f2b84b"),
    "desktop": ("OMARCHY DESKTOP", "#f2b84b", "#ff7a45"),
    "operator": ("OPERATOR UTILITY", "#7edc89", "#54d6d0"),
    "agent": ("AGENT INFRASTRUCTURE", "#ee7890", "#b58cff"),
}


def shield_label(text: str) -> str:
    return text.replace("-", "--").replace("_", "__").replace(" ", "_").replace("+", "%2B")


def stack_badge(stack: str) -> str:
    color, logo = STACK_BADGES.get(stack, ("64748B", ""))
    logo_part = f"&logo={logo}&logoColor=white" if logo else ""
    url = f"https://img.shields.io/badge/{shield_label(stack)}-{color}?style=flat-square{logo_part}"
    return f'<img alt="{html.escape(stack)}" src="{url}">'


def surface_badge(name: str, url: str) -> str:
    color, logo, logo_color = SURFACE_BADGES.get(name, ("1F2937", "github", "FFFFFF"))
    logo_part = f"&logo={logo}&logoColor={logo_color}" if logo else ""
    src = f"https://img.shields.io/badge/{shield_label(name)}-{color}?style=for-the-badge{logo_part}"
    return f'<a href="{url}"><img alt="{html.escape(name)}" src="{src}"></a>'


def card_cell(name: str, stack: str, repo: str, page: str, desc: str, width: int) -> str:
    return "\n".join([
        f'<td width="{width}%" valign="top">',
        f'<a href="{repo}"><img src="assets/cards/{name}.svg" alt="{html.escape(name)}" width="100%"></a>',
        f"<p>{html.escape(desc)}.</p>",
        f'<p>{stack_badge(stack)} <a href="{page}"><sub>Docs</sub></a></p>',
        "</td>",
    ])


def card_grid(rows: list[list[str]], columns: int) -> list[str]:
    width = 100 // columns
    lines = ["<table>"]
    for start in range(0, len(rows), columns):
        lines.append("<tr>")
        for name, stack, repo, page, desc, _category in rows[start:start + columns]:
            lines.append(card_cell(name, stack, repo, page, desc, width))
        lines.append("</tr>")
    lines.append("</table>")
    return lines


SECTIONS = (
    ("desktop", "Omarchy desktop tools", "Plugins and window tools for [Omarchy](https://omarchy.org), the Hyprland-based Arch Linux setup.", 3),
    ("operator", "Operator utilities", "Small tools for people who run their own Linux hosts, scheduled jobs, and services.", 2),
    ("agent", "Agent infrastructure", "Building blocks for AI agent systems.", 2),
)


def render_readme(data: dict) -> str:
    org = data["organization"]
    lines = [
        "<!-- generated by scripts/generate_catalog.py; edit catalog.json instead -->",
        "",
        '<div align="center">',
        "",
        f'<img src="assets/banner.svg" alt="{org["name"]}. {org["tagline"]}" width="100%">',
        "",
        " ".join(surface_badge(name, url) for name, url, _desc in data["surfaces"]),
        "",
        "</div>",
        "",
        f"<p align=\"center\"><b>{html.escape(org['description'])}</b></p>",
        "",
        '<img src="assets/divider.svg" alt="" width="100%">',
        "",
    ]
    for name, stack, repo, homepage, desc in data["flagship"]:
        lines.extend([
            f"## {name}: machine-native programming for AI agents",
            "",
            "<table>",
            "<tr>",
            '<td width="42%" valign="middle">',
            f'<a href="{repo}"><img src="assets/cards/{name.lower()}.svg" alt="{html.escape(name)}" width="100%"></a>',
            "</td>",
            '<td valign="middle">',
            f"<p>{html.escape(desc)}</p>",
            f'<p><a href="{repo}"><b>Source</b></a> · <a href="{homepage}"><b>sley-lang on GitHub</b></a>'
            f' · <a href="{repo}/releases"><b>Releases</b></a>'
            f' · <a href="{repo}/blob/main/docs/QUICKSTART.md"><b>Quickstart</b></a></p>',
            f"<p>{stack_badge(stack)} "
            '<img alt="Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-3B82F6?style=flat-square"></p>',
            "</td>",
            "</tr>",
            "</table>",
            "",
        ])
    for category, title, blurb, columns in SECTIONS:
        rows = [row for row in data["openforge_utilities"] if row[5] == category]
        if not rows:
            continue
        lines.extend([f"## {title}", "", blurb, ""])
        lines.extend(card_grid(rows, columns))
        lines.append("")
    lines.extend([
        '<img src="assets/divider.svg" alt="" width="100%">',
        "",
        "## Historical Projects",
        "",
        "Finished or retired work, kept public for reference.",
        "",
        "| Project | Stack | Status |",
        "|---|---|---|",
    ])
    for name, stack, repo, page, status in data["archived_specs"]:
        lines.append(f"| {md_link(name, repo)} · {md_link('Docs', page)} | {stack} | {status} |")
    lines.extend([
        "",
        "Records: " + " · ".join(md_link(label, url) for label, url in data["proof_trail"]),
        "",
        '<div align="center">',
        "",
        '<img src="assets/divider.svg" alt="" width="100%">',
        "",
        "Built by [Greyforge Labs](https://greyforge.tech/about). License and authorship notices live in each repository.",
        "",
        f"**{org['tagline']}**",
        "",
        "</div>",
    ])
    return "\n".join(lines) + "\n"


def render_card(name: str, stack: str, category: str) -> str:
    label, start, end = CATEGORY_STYLE[category]
    display = html.escape(name)
    size = 34 if len(name) <= 16 else 28
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 120" width="420" height="120" role="img" aria-label="{display}: {html.escape(label.lower())}, {html.escape(stack)}">
  <!-- generated by scripts/generate_catalog.py; edit catalog.json instead -->
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{start}"/>
      <stop offset="1" stop-color="{end}"/>
    </linearGradient>
    <radialGradient id="wash" cx="1" cy="0" r="1">
      <stop offset="0" stop-color="{end}" stop-opacity="0.28"/>
      <stop offset="1" stop-color="{end}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect x="1" y="1" width="418" height="118" rx="14" fill="#101820"/>
  <rect x="1" y="1" width="418" height="118" rx="14" fill="url(#wash)"/>
  <rect x="1" y="1" width="418" height="118" rx="14" fill="none" stroke="url(#accent)" stroke-width="2"/>
  <rect x="18" y="22" width="6" height="76" rx="3" fill="url(#accent)"/>
  <text x="40" y="45" font-family="ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace" font-size="12" font-weight="700" letter-spacing="2" fill="{start}">{html.escape(label)}</text>
  <text x="40" y="88" font-family="'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif" font-size="{size}" font-weight="800" fill="#edf4f8">{display}</text>
  <text x="400" y="45" text-anchor="end" font-family="ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace" font-size="12" fill="#9aa8b5">{html.escape(stack)}</text>
</svg>
"""


def render_cards(data: dict) -> dict[Path, str]:
    cards = {CARDS / f"{name.lower()}.svg": render_card(name, stack, "flagship") for name, stack, *_rest in data["flagship"]}
    for name, stack, _repo, _page, _desc, category in data["openforge_utilities"]:
        cards[CARDS / f"{name}.svg"] = render_card(name, stack, category)
    return cards


def card(name: str, kicker: str, url: str, desc: str) -> str:
    return "\n".join([
        f'        <a class="card" href="{html.escape(url)}">',
        f"          <span class=\"card-kicker\">{html.escape(kicker)}</span>",
        f"          <h3>{html.escape(name)}</h3>",
        f"          <p>{html.escape(desc)}</p>",
        "        </a>",
    ])


def render_index(data: dict) -> str:
    org = data["organization"]
    product_cards = "\n".join(card(name, kicker, url, desc) for name, kicker, url, desc in data["products"])
    product_section = f"""
    <section class="section" aria-labelledby="products-title">
      <div class="section-heading">
        <p class="eyebrow">Catalog</p>
        <h2 id="products-title">Products</h2>
      </div>
      <div class="card-grid product-grid">
{product_cards}
      </div>
    </section>
""" if data["products"] else ""
    repo_links = "\n".join(
        f'        <a href="{html.escape(repo)}"><strong>{html.escape(name)}</strong><span>{html.escape(desc)}</span></a>'
        for name, _stack, repo, _page, desc, _category in data["openforge_utilities"]
    )
    flagship_cards = "\n".join(
        card(name, "Flagship", homepage, desc) for name, _stack, _repo, homepage, desc in data["flagship"]
    )
    software = [
        {
            "@type": "SoftwareSourceCode",
            "name": name,
            "codeRepository": repo,
            "programmingLanguage": stack,
            "description": desc,
        }
        for name, stack, repo, _page, desc in data["flagship"]
    ] + [
        {
            "@type": "SoftwareSourceCode",
            "name": name,
            "codeRepository": repo,
            "programmingLanguage": stack,
            "description": desc,
        }
        for name, stack, repo, _page, desc, _category in data["openforge_utilities"]
    ]
    structured_data = json.dumps(
        [
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": org["name"],
                "slogan": org["tagline"],
                "description": org["description"],
                "url": "https://greyforge.tech",
                "logo": "https://avatars.githubusercontent.com/u/252855775?v=4",
                "sameAs": [url for _name, url, _desc in data["surfaces"] if url != "https://greyforge.tech"],
                "knowsAbout": [
                    "Sley programming language",
                    "machine-native programming",
                    "AI agents",
                    "Omarchy",
                    "Hyprland",
                    "Linux operator tools",
                ],
            },
            {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "name": "Greyforge Labs open-source projects",
                "itemListElement": [
                    {"@type": "ListItem", "position": index, "item": item}
                    for index, item in enumerate(software, start=1)
                ],
            },
        ],
        indent=2,
    ).replace("</", "<\\/")
    archive_links = "\n".join(
        f'        <a href="{html.escape(repo)}"><strong>{html.escape(name)}</strong><span>{html.escape(status.replace("`", ""))}</span></a>'
        for name, _stack, repo, _page, status in data["archived_specs"]
    )
    proof_links = "\n".join(
        f'        <a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in data["proof_trail"]
    )
    return f"""<!doctype html>
<!-- generated by scripts/generate_catalog.py; edit catalog.json instead -->
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Greyforge Labs on GitHub | Sley, Omarchy Tools, and Open-Source Operator Utilities</title>
  <meta name="description" content="{html.escape(org['description'])}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="https://greyforge.tech/">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Greyforge Labs on GitHub">
  <meta property="og:description" content="{html.escape(org['description'])}">
  <meta property="og:url" content="https://greyforgelabs.github.io/Greyforgelabs/">
  <meta property="og:image" content="https://avatars.githubusercontent.com/u/252855775?v=4">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Greyforge Labs on GitHub">
  <meta name="twitter:description" content="{html.escape(org['description'])}">
  <meta name="theme-color" content="#0b0f14">
  <link rel="stylesheet" href="./assets/github-page.css">
  <script type="application/ld+json">
{structured_data}
  </script>
</head>
<body>
  <header class="site-header">
    <a class="brand-link" href="https://greyforge.tech" aria-label="Greyforge Labs">
      <img src="https://avatars.githubusercontent.com/u/252855775?v=4" alt="Greyforge Labs mark" width="48" height="48">
      <span>Greyforge Labs</span>
    </a>
    <nav aria-label="Primary">
      <a href="#flagship-title">Sley</a>
      <a href="#openforge-title">Open Source</a>
      <a href="#archive-title">History</a>
      <a href="https://github.com/GreyforgeLabs">GitHub</a>
    </nav>
  </header>

  <main>
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="eyebrow">Open-source catalog</p>
        <h1 id="hero-title">Greyforge Labs</h1>
        <p class="tagline">Autonomy, Engineered.</p>
        <p class="hero-text">
          {html.escape(org['description'])}
        </p>
        <div class="hero-actions" aria-label="Main links">
          <a class="button primary" href="https://greyforge.tech">Visit Greyforge</a>
          <a class="button" href="https://github.com/sley-lang/sley">Sley</a>
          <a class="button" href="https://github.com/GreyforgeLabs">GitHub Repos</a>
          <a class="button" href="#openforge-title">Explore Tools</a>
        </div>
      </div>
      <aside class="hero-panel" aria-label="Surface map">
        <span>Language</span>
        <strong>Sley, machine-native programming</strong>
        <span>Open Source</span>
        <strong>Omarchy, operator, and agent tools</strong>
        <span>History</span>
        <strong>Sley legacy and archival projects</strong>
        <span>Documentation</span>
        <strong>Repository records</strong>
        <span>GitHub</span>
        <strong>Repos and releases</strong>
      </aside>
    </section>

    <section class="section" aria-labelledby="flagship-title">
      <div class="section-heading">
        <p class="eyebrow">Flagship</p>
        <h2 id="flagship-title">Sley</h2>
      </div>
      <div class="card-grid flagship-grid">
{flagship_cards}
      </div>
    </section>
{product_section}
    <section class="section" aria-labelledby="openforge-title">
      <div class="section-heading">
        <p class="eyebrow">Open Source</p>
        <h2 id="openforge-title">Active Open-Source Tools</h2>
      </div>
      <div class="repo-list">
{repo_links}
      </div>
    </section>

    <section class="section" aria-labelledby="archive-title">
      <div class="section-heading">
        <p class="eyebrow">Archive</p>
        <h2 id="archive-title">Historical Projects</h2>
      </div>
      <div class="repo-list archive-list">
{archive_links}
      </div>
    </section>

    <section class="section proof" aria-labelledby="proof-title">
      <div class="section-heading">
        <p class="eyebrow">Source and documentation</p>
        <h2 id="proof-title">Repository Records</h2>
      </div>
      <div class="link-row">
{proof_links}
      </div>
    </section>
  </main>

  <footer>
    <span>Built by Greyforge Labs. Individual authorship and license notices remain in each repository.</span>
    <nav aria-label="Footer">
      <a href="https://greyforge.tech">greyforge.tech</a>
      <a href="https://github.com/GreyforgeLabs">GitHub</a>
    </nav>
  </footer>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="rewrite generated files")
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    if args.write == args.check:
        raise SystemExit("choose exactly one of --write or --check")

    data = load_catalog()
    expected = {README: render_readme(data), INDEX: render_index(data), **render_cards(data)}
    orphans = sorted(set(CARDS.glob("*.svg")) - set(expected)) if CARDS.is_dir() else []
    if args.write:
        CARDS.mkdir(parents=True, exist_ok=True)
        for path in orphans:
            path.unlink()
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8")
        return

    stale = [
        str(path.relative_to(ROOT))
        for path, content in expected.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    stale += [f"{path.relative_to(ROOT)} (orphaned)" for path in orphans]
    if stale:
        raise SystemExit("generated files are stale: " + ", ".join(stale))


if __name__ == "__main__":
    main()
