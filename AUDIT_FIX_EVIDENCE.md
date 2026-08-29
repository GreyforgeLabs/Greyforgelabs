# Audit Remediation Evidence

Release: `1.0.0`

Date: 2026-08-28

Findings: GF-AUD-048 and GF-AUD-049

- `catalog.json` is the single versioned source for both `README.md` and `index.html` catalog entries.
- PCAM appears only as a retired archival specification at `GreyforgeLabs/pcam`; the stale `pcam-24` active listing is removed.
- The generator validates catalog shape, non-empty strings, unique names, and credential-free HTTPS URLs.
- CI checks generated-file drift, invalid schema behavior, HTML structure, repository/link presence, and live public links.

Validation:

- `python scripts/generate_catalog.py --check`
- `python -m unittest discover -s tests -v`
- `python scripts/check_catalog_links.py`
- `git diff --check`
