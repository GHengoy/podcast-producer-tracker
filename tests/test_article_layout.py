import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import json
import tempfile
import unittest

from build_site import (
    add_heading_ids, build_site, compose_article, format_date, reading_minutes,
    render_index, render_post_cta, render_toc,
)

TEMPLATE = "<html><head><title>{{TITLE}}</title>{{HEAD_META}}</head><body><h1>{{TITLE}}</h1>{{BODY}}</body></html>"
HERO = {
    "src": "images/hero/a.jpg", "alt": "Two cats", "credit": "Jane Doe",
    "credit_url": "https://example.com/photo", "license": "CC BY 2.0",
    "license_url": "https://creativecommons.org/licenses/by/2.0/",
}
HOMEPAGE = {
    "headline": "H", "tagline": "T", "product_name": "Tracker", "product_price": "$9",
    "product_description": "A tracker.", "product_image": "cover.png", "buy_label": "Get it",
    "buy_url": "https://example.com/buy",
}
BODY = "<p>Intro</p>\n<h2>First Part</h2>\n<p>x</p>\n<h2>Second &amp; Last</h2>\n<p>y</p>\n<h2>Third?</h2>"


class TestHelpers(unittest.TestCase):
    def test_add_heading_ids_slugifies_and_collects(self):
        body, headings = add_heading_ids(BODY)
        self.assertIn('<h2 id="first-part">First Part</h2>', body)
        self.assertIn('<h2 id="second-last">', body)
        self.assertEqual(headings[0], ("first-part", "First Part"))
        self.assertEqual(headings[1], ("second-last", "Second &amp; Last"))

    def test_add_heading_ids_keeps_existing_id_and_dedupes(self):
        body, headings = add_heading_ids('<h2 id="keep">A</h2><h2>B</h2><h2>B</h2>')
        self.assertEqual([h[0] for h in headings], ["keep", "b", "b-2"])

    def test_toc_needs_three_headings(self):
        self.assertEqual(render_toc([("a", "A"), ("b", "B")]), "")
        toc = render_toc([("a", "A"), ("b", "B"), ("c", "C")])
        self.assertIn('href="#c"', toc)

    def test_reading_minutes_rounds_up_with_minimum_one(self):
        self.assertEqual(reading_minutes("<p>word</p>"), 1)
        self.assertEqual(reading_minutes("<p>" + "w " * 450 + "</p>"), 3)

    def test_format_date(self):
        self.assertEqual(format_date("2026-10-04"), "October 4, 2026")


class TestComposeArticle(unittest.TestCase):
    def post(self, **extra):
        return {"slug": "a", "title": "A", "date": "2026-10-04", "body": BODY, "hero": HERO, **extra}

    def test_has_meta_hero_toc_body_and_cta_in_order(self):
        html = compose_article(self.post(), render_post_cta(HOMEPAGE))
        order = [html.index(s) for s in ('class="post-meta"', 'class="post-hero"', 'class="toc"', "Intro", 'class="post-cta"')]
        self.assertEqual(order, sorted(order))
        self.assertIn("October 4, 2026", html)
        self.assertIn('src="images/hero/a.jpg"', html)
        self.assertIn('href="https://creativecommons.org/licenses/by/2.0/"', html)

    def test_leading_key_takeaways_come_before_toc(self):
        body = '<p class="pillar-link"><a href="p.html">Back</a></p>\n<div class="key-takeaways"><ul><li>k</li></ul></div>\n' + BODY
        html = compose_article(self.post(body=body), "")
        self.assertLess(html.index('class="pillar-link"'), html.index('class="post-meta"'))
        self.assertLess(html.index("key-takeaways"), html.index('class="toc"'))

    def test_unlisted_page_is_plain(self):
        html = compose_article(self.post(unlisted=True), render_post_cta(HOMEPAGE))
        self.assertNotIn("post-meta", html)
        self.assertNotIn("toc", html)
        self.assertNotIn("post-cta", html)

    def test_hero_without_credit_has_no_caption(self):
        html = compose_article(self.post(hero={"src": "images/hero/a.jpg", "alt": "x"}), "")
        self.assertIn('class="post-hero"', html)
        self.assertNotIn("<figcaption", html)

    def test_cta_uses_paddle_when_configured(self):
        cta = render_post_cta({**HOMEPAGE, "paddle_price_id": "pri_1"})
        self.assertIn('data-paddle-price-id="pri_1"', cta)


class TestIndexCards(unittest.TestCase):
    def test_cards_show_thumbnail_and_description(self):
        posts = [{"slug": "a", "title": "A", "date": "2026-08-20", "body": "", "description": "About A", "hero": HERO}]
        html = render_index(TEMPLATE, posts)
        self.assertIn('class="post-card"', html)
        self.assertIn('src="images/hero/a.jpg"', html)
        self.assertIn("About A", html)


class TestBuildCopiesImages(unittest.TestCase):
    def test_images_dir_copied_and_hero_used_as_og_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            posts = root / "posts"
            posts.mkdir()
            (posts / "a.json").write_text(json.dumps({"title": "A", "date": "2026-08-21", "hero": HERO}), encoding="utf-8")
            (posts / "a.html").write_text(BODY, encoding="utf-8")
            (root / "images" / "hero").mkdir(parents=True)
            (root / "images" / "hero" / "a.jpg").write_bytes(b"jpg")
            (root / "site.json").write_text(json.dumps({"base_url": "https://example.com/s/"}), encoding="utf-8")
            template = root / "base.html"
            template.write_text(TEMPLATE, encoding="utf-8")

            build_site(posts, template, root / "docs")

            self.assertEqual((root / "docs" / "images" / "hero" / "a.jpg").read_bytes(), b"jpg")
            html = (root / "docs" / "a.html").read_text(encoding="utf-8")
            self.assertIn('content="https://example.com/s/images/hero/a.jpg"', html)
            self.assertIn('id="first-part"', html)


if __name__ == "__main__":
    unittest.main()
