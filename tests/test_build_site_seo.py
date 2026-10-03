import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import json
import tempfile
import unittest

from build_site import build_site, render_head_meta, render_hero

TEMPLATE = "<html><head><title>{{TITLE}}</title>{{HEAD_META}}</head><body><h1>{{TITLE}}</h1><p>{{DATE}}</p>{{BODY}}</body></html>"


class TestHeadMeta(unittest.TestCase):
    def test_includes_description_canonical_and_open_graph(self):
        html = render_head_meta("My Title", "A description", "https://example.com/site/a.html", "article", "https://example.com/site/cover.png")
        self.assertIn('<meta name="description" content="A description">', html)
        self.assertIn('<link rel="canonical" href="https://example.com/site/a.html">', html)
        self.assertIn('<meta property="og:type" content="article">', html)
        self.assertIn('<meta property="og:title" content="My Title">', html)
        self.assertIn('<meta property="og:description" content="A description">', html)
        self.assertIn('<meta property="og:url" content="https://example.com/site/a.html">', html)
        self.assertIn('<meta property="og:image" content="https://example.com/site/cover.png">', html)

    def test_skips_tags_with_missing_values(self):
        html = render_head_meta("My Title", None, None, "article", None)
        self.assertNotIn("description", html)
        self.assertNotIn("canonical", html)
        self.assertNotIn("og:image", html)
        self.assertIn('<meta property="og:title" content="My Title">', html)

    def test_escapes_attribute_values(self):
        html = render_head_meta('Cats & "Dogs"', None, None, "article", None)
        self.assertIn('content="Cats &amp; &quot;Dogs&quot;"', html)


class TestHero(unittest.TestCase):
    CONFIG = {
        "headline": "H", "tagline": "T", "product_name": "P", "product_price": "$1",
        "product_description": "D", "product_image": "cover.png", "buy_label": "Buy",
    }

    def test_paddle_price_id_renders_paddle_trigger(self):
        html = render_hero({**self.CONFIG, "paddle_price_id": "pri_123"})
        self.assertIn('href="#" data-paddle-price-id="pri_123"', html)

    def test_buy_url_renders_plain_link(self):
        html = render_hero({**self.CONFIG, "buy_url": "https://example.com/buy"})
        self.assertIn('href="https://example.com/buy"', html)
        self.assertNotIn("data-paddle-price-id", html)


class TestBuildSiteSeo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.posts_dir = self.root / "posts"
        self.posts_dir.mkdir()
        self.template_path = self.root / "base.html"
        self.template_path.write_text(TEMPLATE, encoding="utf-8")
        self.output_dir = self.root / "docs"
        (self.posts_dir / "a.json").write_text(
            json.dumps({"title": "Post A", "date": "2026-08-21", "description": "About A"}), encoding="utf-8")
        (self.posts_dir / "a.html").write_text("<p>a</p>", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_site_json(self, **extra):
        config = {"base_url": "https://example.com/site/", **extra}
        (self.root / "site.json").write_text(json.dumps(config), encoding="utf-8")

    def test_post_page_gets_description_and_canonical(self):
        self._write_site_json(og_image="cover.png")
        build_site(self.posts_dir, self.template_path, self.output_dir)
        html = (self.output_dir / "a.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="description" content="About A">', html)
        self.assertIn('<link rel="canonical" href="https://example.com/site/a.html">', html)
        self.assertIn('<meta property="og:image" content="https://example.com/site/cover.png">', html)
        self.assertNotIn("{{", html)

    def test_index_uses_site_title_and_description(self):
        self._write_site_json(title="My Site", description="Site description")
        build_site(self.posts_dir, self.template_path, self.output_dir)
        html = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>My Site</title>", html)
        self.assertIn('<meta name="description" content="Site description">', html)
        self.assertIn('<link rel="canonical" href="https://example.com/site/index.html">', html)
        self.assertIn('<meta property="og:type" content="website">', html)

    def test_without_site_json_index_title_stays_home(self):
        build_site(self.posts_dir, self.template_path, self.output_dir)
        html = (self.output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Home</title>", html)
        self.assertNotIn("canonical", html)


if __name__ == "__main__":
    unittest.main()
