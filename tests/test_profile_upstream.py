"""Offline regression tests for curated upstream profile activity."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "profile_upstream.py"
spec = importlib.util.spec_from_file_location("profile_upstream", SCRIPT)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def payload(item, state="open", merged_at=None, title="Sensitive external API title"):
    return {
        "number": item.number,
        "title": title,
        "state": state,
        "draft": False,
        "merged_at": merged_at,
        "updated_at": "2026-11-12T18:00:00Z",
        "base": {"repo": {"full_name": item.repository}},
    }


class UpstreamProfileTests(unittest.TestCase):
    def test_merged_and_open_are_correct(self):
        a = module.TRACKED[0]
        merged = module.render_row(a, payload(a, state="closed", merged_at="2026-11-11T22:45:00Z"))
        self.assertIn("**Merged**", merged)
        self.assertIn("11 Nov 2026", merged)
        b = module.TRACKED[1]
        opened = module.render_row(b, payload(b))
        self.assertIn("| Open |", opened)
        self.assertIn("12 Nov 2026", opened)

    def test_closed_unmerged_is_not_presented_as_merged(self):
        item = module.TRACKED[0]
        row = module.render_row(item, payload(item, state="closed"))
        self.assertIn("Closed (not merged)", row)
        self.assertNotIn("**Merged**", row)

    def test_unknown_repository_is_rejected(self):
        item = module.TRACKED[0]
        bad = payload(item)
        bad["base"]["repo"]["full_name"] = "unreviewed/repository"
        with self.assertRaises(ValueError):
            module.render_row(item, bad)

    def test_title_is_never_published(self):
        item = module.TRACKED[0]
        text = module.render_row(item, payload(item, title="ConfidentialClient privileged information"))
        self.assertNotIn("ConfidentialClient", text)
        self.assertIn(item.summary, text)

    def test_missing_and_duplicate_markers_rejected(self):
        for source in ("README", module.BEGIN + " hi", module.BEGIN * 2 + " x " + module.END):
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    module.replace_section(source, "table")

    def test_repeat_updates_are_idempotent(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text("Top\n" + module.BEGIN + "\nold\n" + module.END + "\nBottom\n", encoding="utf-8")
            def fake(item, token):
                return payload(item, state="closed" if item.number == 4934 else "open", merged_at="2026-11-11T22:45:00Z" if item.number == 4934 else None)
            self.assertTrue(module.refresh(path, fake))
            once = path.read_text(encoding="utf-8")
            self.assertEqual(4, once.count("https://github.com/"))
            self.assertFalse(module.refresh(path, fake))
            self.assertEqual(once, path.read_text(encoding="utf-8"))

    def test_partial_api_failure_does_not_modify_readme(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            original = "Before\n" + module.BEGIN + "\nold\n" + module.END + "\nAfter\n"
            path.write_text(original, encoding="utf-8")
            def fake(item, token):
                if item.number == 1332:
                    raise RuntimeError("HTTP failure")
                return payload(item)
            with self.assertRaises(RuntimeError):
                module.refresh(path, fake)
            self.assertEqual(original, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
