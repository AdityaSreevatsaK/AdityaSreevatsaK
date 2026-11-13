"""Offline tests for automatic public upstream PR discovery and safe rendering."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "profile_upstream.py"
spec = importlib.util.spec_from_file_location("profile_upstream", SCRIPT)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def example(repo="pydantic/httpx2", n=1334, state="open", merged_at=None, title="untrusted title"):
    return {
        "number": n,
        "title": title,
        "user": {"login": m.PROFILE_LOGIN},
        "state": state,
        "updated_at": "2026-11-13T03:20:00Z",
        "html_url": f"https://github.com/{repo}/pull/{n}",
        "repository_url": f"https://api.github.com/repos/{repo}",
        "pull_request": {"html_url": f"https://github.com/{repo}/pull/{n}", "merged_at": merged_at},
    }


def fake_search(opened=(), merged=()):
    def fetch(q, page, token):
        selected = list(merged if "is:merged" in q else opened)
        return {"total_count": len(selected), "incomplete_results": False, "items": selected if page == 1 else []}
    return fetch


class TestSearch(unittest.TestCase):
    def test_query_scopes_to_public_upstream(self):
        q = m.query_for("open")
        self.assertIn("is:public", q)
        self.assertIn("author:AdityaSreevatsaK", q)
        self.assertIn("-user:AdityaSreevatsaK", q)
        self.assertIn("is:open", q)

    def test_new_open_prs_discovered_without_hardcoded_ids(self):
        opened = [example(n=x) for x in [1330, 1332, 1333, 1334, 1555]]
        a, b = m.collect(fake_search(opened))
        self.assertEqual(5, len(a))
        self.assertFalse(b)
        self.assertIn("Pull request #1555", m.render(a, b))

    def test_own_repositories_excluded_even_if_api_fails_to_filter(self):
        opened = [example(repo="AdityaSreevatsaK/httpx2", n=1), example()]
        a, b = m.collect(fake_search(opened))
        self.assertEqual(1, len(a))
        self.assertEqual("pydantic/httpx2", a[0]["repository"])

    def test_open_and_merged_counts(self):
        opens = [example(n=i) for i in range(10, 16)]
        merged = [example(repo="rossjrw/rossjrw", n=4934, state="closed", merged_at="2026-11-11T22:50:50Z")]
        a, b = m.collect(fake_search(opens, merged))
        table = m.render(a, b)
        self.assertIn("Open upstream PRs: 6", table)
        self.assertIn("Merged: 1", table)
        self.assertIn("11 Nov 2026", table)
        self.assertIn("rossjrw/rossjrw", table)

    def test_never_copies_remote_pr_title(self):
        x = example(n=1210, title="unreviewed client details and markdown | injection ](unsafe)")
        a, b = m.collect(fake_search([x]))
        table = m.render(a, b)
        self.assertNotIn("unreviewed client", table)
        self.assertNotIn("unsafe", table)
        self.assertIn("Pull request #1210", table)

    def test_incomplete_search_rejected(self):
        def bad(q, page, token):
            return {"total_count": 1, "incomplete_results": True, "items": [example()]}
        with self.assertRaises(m.UpstreamUpdateError):
            m.collect(bad)

    def test_inconsistent_repo_url_rejected(self):
        x = example()
        x["html_url"] = "https://example.com/unexpected"
        with self.assertRaises(m.UpstreamUpdateError):
            m.to_record(x)

    def test_foreign_author_rejected(self):
        x = example()
        x["user"]["login"] = "someone-else"
        with self.assertRaises(m.UpstreamUpdateError):
            m.to_record(x)

    def test_malformed_merged_missing_merged_at_rejected(self):
        x = example(state="closed", merged_at=None)
        with self.assertRaises(m.UpstreamUpdateError):
            m.to_record(x, expected="merged")

    def test_draft_supported(self):
        x = example()
        x["draft"] = True
        self.assertEqual("Draft", m.to_record(x)["status"])

    def test_duplicate_urls_deduplicated(self):
        a, b = m.collect(fake_search([example(), example()]))
        self.assertEqual(1, len(a))

    def test_display_cap_with_discovery_count(self):
        prs = [m.to_record(example(n=i)) for i in range(100, 120)]
        text = m.render(prs, [])
        self.assertIn("Open upstream PRs: 20", text)
        self.assertEqual(12, text.count("https://github.com/pydantic/httpx2/pull/"))
        self.assertIn("Showing the 12", text)

    def test_search_pagination(self):
        old = m.PER_PAGE
        try:
            m.PER_PAGE = 2
            def fetch(query, page, token):
                a = [example(n=i) for i in range(1, 4)]
                return {"total_count": 3, "incomplete_results": False, "items": a[(page-1)*2:page*2]}
            self.assertEqual(3, len(m.search_all("a", fetch)))
        finally:
            m.PER_PAGE = old

    def test_fails_without_changing_readme_on_api_error(self):
        def crash(query, page, token):
            raise RuntimeError("github unavailable")
        with TemporaryDirectory() as root:
            p = Path(root) / "README.md"
            original = "top\n" + m.BEGIN + "\nold\n" + m.END + "\n"
            p.write_text(original)
            with self.assertRaises(RuntimeError):
                m.refresh(p, crash)
            self.assertEqual(original, p.read_text())

    def test_refresh_idempotent(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "README.md"
            path.write_text("top\n" + m.BEGIN + "\nold\n" + m.END + "\n")
            mock = fake_search([example(n=1334)])
            self.assertTrue(m.refresh(path, mock))
            result = path.read_text()
            self.assertFalse(m.refresh(path, mock))
            self.assertEqual(result, path.read_text())

    def test_marker_validation(self):
        for source in ("No markers", m.BEGIN + " x", m.BEGIN*2 + "x" + m.END):
            with self.assertRaises(m.UpstreamUpdateError):
                m.replace_section(source, "content")


if __name__ == "__main__":
    unittest.main()