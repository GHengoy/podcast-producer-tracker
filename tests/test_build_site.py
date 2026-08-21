import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import json
import tempfile
import unittest

from build_site import build_site, load_posts, render_post, render_index, main

TEMPLATE = "<html><head><title>{{TITLE}}</title></head><body><h1>{{TITLE}}</h1><p>{{DATE}}</p>{{BODY}}</body></html>"


class TestBuildSite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.posts_dir = self.root / "posts"
        self.posts_dir.mkdir()
        self.template_path = self.root / "base.html"
        self.template_path.write_text(TEMPLATE, encoding="utf-8")
        self.output_dir = self.root / "docs"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_post(self, slug, title, date, body):
        (self.posts_dir / f"{slug}.json").write_text(
            json.dumps({"title": title, "date": date}), encoding="utf-8"
        )
        (self.posts_dir / f"{slug}.html").write_text(body, encoding="utf-8")

    def test_load_posts_pairs_json_and_html(self):
        self._write_post("first-post", "First Post", "2026-08-21", "<p>hello</p>")
        posts = load_posts(self.posts_dir)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["title"], "First Post")
        self.assertEqual(posts[0]["body"], "<p>hello</p>")

    def test_load_posts_missing_body_raises(self):
        (self.posts_dir / "orphan.json").write_text(
            json.dumps({"title": "Orphan", "date": "2026-08-21"}), encoding="utf-8"
        )
        with self.assertRaises(FileNotFoundError):
            load_posts(self.posts_dir)

    def test_build_site_writes_one_file_per_post_plus_index(self):
        self._write_post("first-post", "First Post", "2026-08-21", "<p>hello</p>")
        self._write_post("second-post", "Second Post", "2026-08-22", "<p>world</p>")
        written = build_site(self.posts_dir, self.template_path, self.output_dir)
        self.assertEqual(len(written), 3)
        self.assertTrue((self.output_dir / "first-post.html").exists())
        self.assertTrue((self.output_dir / "second-post.html").exists())
        self.assertTrue((self.output_dir / "index.html").exists())

    def test_render_post_fills_placeholders(self):
        post = {"title": "T", "date": "2026-08-21", "body": "<p>B</p>"}
        html = render_post(TEMPLATE, post)
        self.assertIn("<title>T</title>", html)
        self.assertIn("<p>B</p>", html)
        self.assertNotIn("{{", html)

    def test_render_index_lists_posts_newest_first(self):
        posts = [
            {"slug": "a", "title": "A", "date": "2026-08-20", "body": ""},
            {"slug": "b", "title": "B", "date": "2026-08-22", "body": ""},
        ]
        html = render_index(TEMPLATE, posts)
        self.assertLess(html.index("b.html"), html.index("a.html"))

    def test_load_posts_missing_title_raises_valueerror(self):
        (self.posts_dir / "missing-title.json").write_text(
            json.dumps({"date": "2026-08-21"}), encoding="utf-8"
        )
        (self.posts_dir / "missing-title.html").write_text("<p>body</p>", encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            load_posts(self.posts_dir)
        self.assertIn("missing 'title'", str(ctx.exception))

    def test_main_wrong_arg_count_returns_2(self):
        exit_code = main(["build_site.py"])
        self.assertEqual(exit_code, 2)
        exit_code = main(["build_site.py", "a", "b"])
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
