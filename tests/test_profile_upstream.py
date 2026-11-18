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
        self.assertTrue(any(pr["number"] == 1555 for pr in a))

    def test_own_repositories_excluded_even_if_api_fails_to_filter(self):
        opened = [example(repo="AdityaSreevatsaK/httpx2", n=1), example()]
        a, b = m.collect(fake_search(opened))
        self.assertEqual(1, len(a))
        self.assertEqual("pydantic/httpx2", a[0]["repository"])

    def test_new_wheelgap_merged_pr_included(self):
        merged = example(
            repo="wheelgap/wheelgap", n=341, state="closed",
            merged_at="2026-11-15T17:36:45Z",
        )
        opened, completed = m.collect(fake_search(merged=[merged]))
        self.assertFalse(opened)
        self.assertEqual(1, len(completed))
        table = m.render(opened, completed)
        self.assertEqual("wheelgap/wheelgap", completed[0]["repository"])
        self.assertEqual("**Merged**", completed[0]["status"])
        if m.VIEW_STYLE == "summary":
            self.assertIn("1 merged", table)
        else:
            self.assertIn("wheelgap/wheelgap/pull/341", table)
            self.assertIn("Selected merged PRs", table)
            self.assertNotIn("Counts are a saved GitHub Actions snapshot", table)
            self.assertIn("last sync", table)

    def test_recent_merged_contributions_cover_distinct_upstream_repositories(self):
        def merged(repo, n, day):
            x = example(repo=repo, n=n, state="closed",
                        merged_at=f"2026-11-{day:02d}T12:00:00Z")
            return x
        completed = [
            *[merged("wheelgap/wheelgap", n, 17) for n in range(490, 500)],
            merged("wheelgap/tracker", 140, 17),
            merged("wheelgap/tracker", 142, 16),
            merged("rossjrw/rossjrw", 4934, 11),
        ]
        open_prs, merged_prs = m.collect(fake_search(
            [example(n=1424)], completed
        ))
        content = m.render(open_prs, merged_prs)
        self.assertIn("13 merged", content)
        self.assertIn("1 open", content)
        self.assertIn("wheelgap/tracker", content)
        self.assertIn("rossjrw/rossjrw", content)
        self.assertLessEqual(len(m.selected_merges(merged_prs)), m.MAX_MERGED_SHOWN)
        self.assertLessEqual(content.count("| wheelgap/wheelgap |"), 3)

    def test_live_search_links_match_underlying_state_filters(self):
        merged_link = m.live_search_url("merged")
        self.assertIn("is%3Amerged", merged_link)
        self.assertIn("is%3Apublic", merged_link)
        self.assertIn("-user%3AAdityaSreevatsaK", merged_link)
        self.assertIn("is%3Aopen", m.live_search_url("open"))

    def test_merged_count_includes_every_verified_record_not_just_visible_rows(self):
        merged = [
            example(repo="wheelgap/wheelgap", n=n, state="closed",
                    merged_at="2026-11-17T12:00:00Z")
            for n in range(100, 123)
        ]
        opens, completed = m.collect(fake_search(merged=merged))
        text = m.render(opens, completed)
        self.assertIn("23 merged", text)
        self.assertLessEqual(len(m.selected_merges(completed)), m.MAX_MERGED_SHOWN)

    def test_open_and_merged_counts(self):
        opens = [example(n=i) for i in range(10, 16)]
        merged = [example(repo="rossjrw/rossjrw", n=4934, state="closed", merged_at="2026-11-11T22:50:50Z")]
        a, b = m.collect(fake_search(opens, merged))
        table = m.render(a, b)
        self.assertIn("6 open", table)
        self.assertIn("1 merged", table)
        if m.VIEW_STYLE != "summary":
            self.assertIn("rossjrw/rossjrw", table)

    def test_never_copies_remote_pr_title(self):
        x = example(n=1210, title="unreviewed client details and markdown | injection ](unsafe)")
        a, b = m.collect(fake_search([x]))
        table = m.render(a, b)
        self.assertNotIn("unreviewed client", table)
        self.assertNotIn("unsafe", table)
        self.assertIn("1 open", table)

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

    def test_missing_author_is_rejected(self):
        x = example()
        del x["user"]
        with self.assertRaises(m.UpstreamUpdateError):
            m.to_record(x)

    def test_newly_merged_pr_348_is_included(self):
        merged = example(repo="wheelgap/wheelgap", n=348, state="closed",
                         merged_at="2026-11-15T18:40:00Z")
        opened, completed = m.collect(fake_search(merged=[merged]))
        self.assertFalse(opened)
        self.assertEqual(1, len(completed))
        self.assertIn("/wheelgap/wheelgap/pull/348", m.render(opened, completed))

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
        self.assertIn("20 open", text)
        if m.VIEW_STYLE == "summary":
            self.assertEqual(0, text.count("https://github.com/pydantic/httpx2/pull/"))
        else:
            self.assertLessEqual(text.count("https://github.com/pydantic/httpx2/pull/"), 5)

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