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

    def test_load_homepage_config_returns_none_when_absent(self):
        from build_site import load_homepage_config
        self.assertIsNone(load_homepage_config(self.root))

    def test_load_homepage_config_reads_json(self):
        from build_site import load_homepage_config
        config = {
            "headline": "H", "tagline": "T", "product_name": "P",
            "product_price": "$9.99", "product_description": "D",
            "product_image": "cover.png", "buy_url": "https://example.com/buy",
            "buy_label": "Buy Now",
        }
        (self.root / "homepage.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(load_homepage_config(self.root), config)

    def test_render_hero_includes_headline_and_buy_button(self):
        from build_site import render_hero
        config = {
            "headline": "Headline Text", "tagline": "Tagline text",
            "product_name": "Product Name", "product_price": "$9.99",
            "product_description": "Product description",
            "product_image": "cover.png", "buy_url": "https://example.com/buy",
            "buy_label": "Buy Now",
        }
        html = render_hero(config)
        self.assertIn("Headline Text", html)
        self.assertIn("Tagline text", html)
        self.assertIn("Product Name", html)
        self.assertIn("$9.99", html)
        self.assertIn('href="https://example.com/buy"', html)
        self.assertIn("Buy Now", html)
        self.assertIn("Latest Posts", html)

    def test_render_index_with_hero_html_prepends_before_list(self):
        html = render_index(TEMPLATE, [{"slug": "a", "title": "A", "date": "2026-08-20", "body": ""}], hero_html="<div>HERO</div>")
        self.assertLess(html.index("HERO"), html.index("<ul>"))

    def test_build_site_with_homepage_json_copies_image_and_includes_hero(self):
        from build_site import load_homepage_config
        self._write_post("first-post", "First Post", "2026-08-21", "<p>hello</p>")
        config = {
            "headline": "Headline Text", "tagline": "Tagline text",
            "product_name": "Product Name", "product_price": "$9.99",
            "product_description": "Product description",
            "product_image": "cover.png", "buy_url": "https://example.com/buy",
            "buy_label": "Buy Now",
        }
        (self.root / "homepage.json").write_text(json.dumps(config), encoding="utf-8")
        product_dir = self.root / "product"
        product_dir.mkdir()
        (product_dir / "cover.png").write_bytes(b"fake-image-bytes")
        build_site(self.posts_dir, self.template_path, self.output_dir)
        self.assertTrue((self.output_dir / "cover.png").exists())
        self.assertEqual((self.output_dir / "cover.png").read_bytes(), b"fake-image-bytes")
        index_html = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("Headline Text", index_html)

    def test_build_site_without_homepage_json_unchanged(self):
        self._write_post("first-post", "First Post", "2026-08-21", "<p>hello</p>")
        written = build_site(self.posts_dir, self.template_path, self.output_dir)
        index_html = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("product-box", index_html)
        self.assertEqual(len(written), 2)


if __name__ == "__main__":
    unittest.main()
