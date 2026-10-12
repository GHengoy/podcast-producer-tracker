import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import json
import tempfile
import unittest

from build_site import build_site, render_hero, render_more_products

TEMPLATE = "<html><head><title>{{TITLE}}</title>{{HEAD_META}}</head><body>{{BODY}}</body></html>"

ITEM = {
    "name": "Cat Log", "price": "$7.99", "blurb": "Excel & Google Sheets",
    "image": "more/cat-log.jpg", "url": "https://example.gumroad.com/l/abc",
}
HERO = {
    "headline": "H", "tagline": "T", "product_name": "P", "product_price": "$1",
    "product_description": "D", "product_image": "cover.png", "buy_label": "Buy",
    "buy_url": "https://example.com/buy",
}


class TestRenderMoreProducts(unittest.TestCase):
    def test_renders_heading_and_card_per_item(self):
        html = render_more_products([{"heading": "More tools", "items": [ITEM, {**ITEM, "name": "Kit"}]}])
        self.assertIn("<h3>More tools</h3>", html)
        self.assertEqual(html.count('class="product-card"'), 2)
        self.assertIn('href="https://example.gumroad.com/l/abc"', html)
        self.assertIn('src="more/cat-log.jpg"', html)
        self.assertIn("$7.99", html)

    def test_escapes_text(self):
        html = render_more_products([{"heading": "A & B", "items": [{**ITEM, "name": "<x>"}]}])
        self.assertIn("A &amp; B", html)
        self.assertIn("&lt;x&gt;", html)

    def test_empty_groups_render_nothing(self):
        self.assertEqual(render_more_products([]), "")

    def test_hero_places_more_products_before_latest_posts(self):
        html = render_hero({**HERO, "more_products": [{"heading": "More tools", "items": [ITEM]}]})
        self.assertLess(html.index("More tools"), html.index("Latest Posts"))
        self.assertLess(html.index("product-box"), html.index("More tools"))

    def test_hero_without_more_products_has_no_section(self):
        self.assertNotIn("more-products", render_hero(HERO))


class TestBuildSiteCopiesMoreProductImages(unittest.TestCase):
    def test_images_copied_into_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            posts = root / "posts"
            posts.mkdir()
            (posts / "a.json").write_text(json.dumps({"title": "A", "date": "2026-08-21"}), encoding="utf-8")
            (posts / "a.html").write_text("<p>a</p>", encoding="utf-8")
            template = root / "base.html"
            template.write_text(TEMPLATE, encoding="utf-8")
            (root / "product" / "more").mkdir(parents=True)
            (root / "product" / "cover.png").write_bytes(b"cover")
            (root / "product" / "more" / "cat-log.jpg").write_bytes(b"thumb")
            config = {**HERO, "more_products": [{"heading": "More", "items": [ITEM]}]}
            (root / "homepage.json").write_text(json.dumps(config), encoding="utf-8")

            build_site(posts, template, root / "docs")

            self.assertEqual((root / "docs" / "more" / "cat-log.jpg").read_bytes(), b"thumb")
            self.assertIn("product-card", (root / "docs" / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
