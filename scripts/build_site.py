"""Static site builder: assembles docs/ output from posts/ + templates/base.html."""
import datetime as dt
import html
import json
import math
import re
import shutil
import sys
from pathlib import Path

WORDS_PER_MINUTE = 220
TOC_MIN_HEADINGS = 3
H2_RE = re.compile(r"<h2(\s[^>]*)?>(.*?)</h2>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def load_homepage_config(repo_root: Path) -> dict | None:
    """Load homepage.json from repo_root if present; return None if absent (backward compatible)."""
    config_path = repo_root / "homepage.json"
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_site_config(repo_root: Path) -> dict | None:
    """Load site.json from repo_root if present; return None if absent (backward compatible)."""
    config_path = repo_root / "site.json"
    if not config_path.exists():
        return None
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_posts(posts_dir: Path) -> list[dict]:
    """Load all posts from posts_dir, pairing each .json metadata file with its .html body."""
    posts = []
    for meta_path in sorted(posts_dir.glob("*.json")):
        slug = meta_path.stem
        body_path = posts_dir / f"{slug}.html"
        if not body_path.exists():
            raise FileNotFoundError(f"missing body file for post '{slug}': {body_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for key in ("title", "date"):
            if key not in meta:
                raise ValueError(f"missing '{key}' in {meta_path}")
        body = body_path.read_text(encoding="utf-8")
        posts.append({
            "slug": slug,
            "title": meta["title"],
            "date": meta["date"],
            "body": body,
            "description": meta.get("description"),
            "unlisted": meta.get("unlisted", False),
            "hero": meta.get("hero"),
        })
    return posts


def format_date(iso_date: str) -> str:
    """'2026-10-04' -> 'October 4, 2026'."""
    day = dt.date.fromisoformat(iso_date)
    return f"{day:%B} {day.day}, {day.year}"


def reading_minutes(body: str) -> int:
    """Estimated reading time of an HTML fragment, rounded up, at least one minute."""
    words = len(TAG_RE.sub(" ", body).split())
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def slugify(text: str) -> str:
    plain = html.unescape(TAG_RE.sub("", text)).lower()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-") or "section"


def add_heading_ids(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Give every <h2> an id (keeping existing ones) and return (body, [(id, heading html)])."""
    headings = []
    seen: dict[str, int] = {}

    def replace(match):
        attrs, text = match.group(1) or "", match.group(2)
        existing = re.search(r'\bid="([^"]+)"', attrs)
        anchor = existing.group(1) if existing else slugify(text)
        seen[anchor] = seen.get(anchor, 0) + 1
        if seen[anchor] > 1:
            anchor = f"{anchor}-{seen[anchor]}"
        headings.append((anchor, text.strip()))
        if existing:
            return match.group(0)
        return f'<h2 id="{anchor}"{attrs}>{text}</h2>'

    return H2_RE.sub(replace, body), headings


def render_toc(headings: list[tuple[str, str]]) -> str:
    """'In this guide' jump list; omitted for short posts."""
    if len(headings) < TOC_MIN_HEADINGS:
        return ""
    items = "\n".join(f'<li><a href="#{anchor}">{TAG_RE.sub("", text)}</a></li>' for anchor, text in headings)
    return f'<nav class="toc" aria-label="Contents"><p class="toc-title">In this guide</p>\n<ol>\n{items}\n</ol></nav>\n'


def render_post_hero(hero: dict | None) -> str:
    """Lead image with an optional photo credit and licence link."""
    if not hero:
        return ""
    def esc(value: str) -> str:
        return html.escape(value, quote=True)
    caption = ""
    if hero.get("credit"):
        credit = esc(hero["credit"])
        if hero.get("credit_url"):
            credit = f'<a href="{esc(hero["credit_url"])}" rel="nofollow">{credit}</a>'
        licence = ""
        if hero.get("license"):
            licence = esc(hero["license"])
            if hero.get("license_url"):
                licence = f'<a href="{esc(hero["license_url"])}" rel="license nofollow">{licence}</a>'
            licence = f", {licence}"
        caption = f"<figcaption>Photo: {credit}{licence}</figcaption>"
    return (
        f'<figure class="post-hero"><img src="{esc(hero["src"])}" alt="{esc(hero.get("alt", ""))}" '
        f'width="1200" height="675">{caption}</figure>\n'
    )


def buy_attributes(config: dict) -> str:
    """Paddle overlay trigger when 'paddle_price_id' is set, otherwise a plain link to 'buy_url'."""
    if config.get("paddle_price_id"):
        return f'href="#" data-paddle-price-id="{config["paddle_price_id"]}"'
    return f'href="{config["buy_url"]}"'


def render_post_cta(config: dict | None) -> str:
    """Product box shown at the end of every listed post."""
    if not config:
        return ""
    return (
        f'<aside class="post-cta">\n'
        f'<img src="{config["product_image"]}" alt="{config["product_name"]}" loading="lazy">\n'
        f'<div><p class="cta-kicker">Make it easy to keep track</p>\n'
        f'<h3>{config["product_name"]}</h3>\n'
        f'<p>{config["product_description"]}</p>\n'
        f'<p><a class="buy-button" {buy_attributes(config)}>{config["buy_label"]} &middot; {config["product_price"]}</a></p></div>\n'
        f'</aside>\n'
    )


def compose_article(post: dict, cta_html: str) -> str:
    """Article body for a listed post: meta line, lead image, contents, text, product box.

    Unlisted pages (terms, privacy, thank-you) keep their body as written.
    """
    if post.get("unlisted"):
        return post["body"]
    body, headings = add_heading_ids(post["body"])
    # the "back to the guide" link reads as a breadcrumb, so it stays above everything else
    crumb = ""
    crumb_match = re.match(r'\s*(<p class="pillar-link">.*?</p>)\s*', body, re.S)
    if crumb_match:
        crumb, body = crumb_match.group(1) + "\n", body[crumb_match.end():]
    meta = (
        f'<p class="post-meta"><time datetime="{post["date"]}">{format_date(post["date"])}</time>'
        f' &middot; {reading_minutes(post["body"])} min read</p>\n'
    )
    # a leading key-takeaways box answers the question, so it goes before the contents list
    summary = ""
    summary_match = re.match(r'\s*(<div class="key-takeaways">.*?</div>)\s*', body, re.S)
    if summary_match:
        summary, body = summary_match.group(1) + "\n", body[summary_match.end():]
    return crumb + meta + render_post_hero(post.get("hero")) + summary + render_toc(headings) + body + "\n" + cta_html


def render_head_meta(title: str, description: str | None, url: str | None, og_type: str, image_url: str | None) -> str:
    """Render description, canonical and Open Graph tags; a tag is skipped when its source value is missing."""
    def attr(value: str) -> str:
        return html.escape(value, quote=True)

    tags = []
    if description:
        tags.append(f'<meta name="description" content="{attr(description)}">')
    if url:
        tags.append(f'<link rel="canonical" href="{attr(url)}">')
    tags.append(f'<meta property="og:type" content="{og_type}">')
    tags.append(f'<meta property="og:title" content="{attr(title)}">')
    if description:
        tags.append(f'<meta property="og:description" content="{attr(description)}">')
    if url:
        tags.append(f'<meta property="og:url" content="{attr(url)}">')
    if image_url:
        tags.append(f'<meta property="og:image" content="{attr(image_url)}">')
    return "\n".join(tags)


def render_post(template: str, post: dict, head_meta: str = "") -> str:
    """Fill the base template with one post's title/date/body."""
    return (
        template
        .replace("{{TITLE}}", post["title"])
        .replace("{{DATE}}", post["date"])
        .replace("{{HEAD_META}}", head_meta)
        .replace("{{BODY}}", post["body"])
    )


def render_more_products(groups: list[dict]) -> str:
    """Render the homepage 'more products' section: one heading + card grid per group of related products."""
    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    if not groups:
        return ""
    parts = ['<section class="more-products">\n']
    for group in groups:
        parts.append(f'<h3>{esc(group["heading"])}</h3>\n<div class="product-grid">\n')
        for item in group["items"]:
            parts.append(
                f'<a class="product-card" href="{esc(item["url"])}">'
                f'<img src="{esc(item["image"])}" alt="{esc(item["name"])}" loading="lazy">'
                f'<strong>{esc(item["name"])}</strong>'
                f'<span>{esc(item["blurb"])}</span>'
                f'<span class="price">{esc(item["price"])}</span></a>\n'
            )
        parts.append("</div>\n")
    parts.append("</section>\n")
    return "".join(parts)


def render_hero(config: dict) -> str:
    """Render the homepage hero + product highlight block from a homepage.json config dict.

    The buy button opens a Paddle overlay checkout when 'paddle_price_id' is set, otherwise links to 'buy_url'.
    An optional 'more_products' list adds a related-products section below the main product.
    """
    buy_attrs = buy_attributes(config)
    return (
        f'<h2>{config["headline"]}</h2>\n'
        f'<p>{config["tagline"]}</p>\n'
        f'<div class="product-box">\n'
        f'<img src="{config["product_image"]}" alt="{config["product_name"]}">\n'
        f'<h3>{config["product_name"]} — {config["product_price"]}</h3>\n'
        f'<p>{config["product_description"]}</p>\n'
        f'<p><a class="buy-button" {buy_attrs}>{config["buy_label"]}</a></p>\n'
        f'</div>\n'
        f'{render_more_products(config.get("more_products", []))}'
        f'<h3>Latest Posts</h3>\n'
    )


def render_index(template: str, posts: list[dict], hero_html: str = "", head_meta: str = "", title: str = "Home") -> str:
    """Fill the base template with a card per post (thumbnail, title, description, date), newest first.

    Posts marked 'unlisted' are excluded. Optionally prefixed with a hero/product block.
    """
    listed_posts = [p for p in posts if not p.get("unlisted", False)]
    cards = []
    for p in sorted(listed_posts, key=lambda p: p["date"], reverse=True):
        hero = p.get("hero")
        thumb = (f'<img src="{html.escape(hero["src"], quote=True)}" alt="" loading="lazy">' if hero else "")
        description = f'<span class="post-card-desc">{html.escape(p["description"])}</span>' if p.get("description") else ""
        cards.append(
            f'<li><a class="post-card" href="{p["slug"]}.html">{thumb}<span class="post-card-text">'
            f'<strong>{p["title"]}</strong>{description}'
            f'<span class="post-card-date">{format_date(p["date"])}</span></span></a></li>'
        )
    items = "\n".join(cards)
    body = f'{hero_html}<ul class="post-list">\n{items}\n</ul>'
    return (
        template
        .replace("{{TITLE}}", title)
        .replace("{{DATE}}", "")
        .replace("{{HEAD_META}}", head_meta)
        .replace("{{BODY}}", body)
    )


def render_sitemap(posts: list[dict], base_url: str) -> str:
    """Render sitemap.xml content: the index page plus one entry per post page, newest first."""
    ordered = sorted(posts, key=lambda p: p["date"], reverse=True)
    entries = [
        f'<url><loc>{base_url}{p["slug"]}.html</loc><lastmod>{p["date"]}</lastmod></url>'
        for p in ordered
    ]
    index_lastmod = f'<lastmod>{ordered[0]["date"]}</lastmod>' if ordered else ""
    index_entry = f"<url><loc>{base_url}index.html</loc>{index_lastmod}</url>"
    body = "\n".join([index_entry] + entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def build_site(posts_dir: Path, template_path: Path, output_dir: Path) -> list[Path]:
    """Build the full site: one HTML file per post plus an index.html. Returns written paths."""
    template = template_path.read_text(encoding="utf-8")
    posts = load_posts(posts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    site_config = load_site_config(posts_dir.parent) or {}
    base_url = site_config.get("base_url")
    image_url = f'{base_url}{site_config["og_image"]}' if base_url and site_config.get("og_image") else None

    written = []
    images_dir = posts_dir.parent / "images"
    if images_dir.is_dir():
        shutil.copytree(images_dir, output_dir / "images", dirs_exist_ok=True)
        written.extend(p for p in (output_dir / "images").rglob("*") if p.is_file())

    homepage_config = load_homepage_config(posts_dir.parent)
    cta_html = render_post_cta(homepage_config)
    for post in posts:
        out_path = output_dir / f"{post['slug']}.html"
        post_url = f"{base_url}{post['slug']}.html" if base_url else None
        post_image = f'{base_url}{post["hero"]["src"]}' if base_url and post.get("hero") else image_url
        head_meta = render_head_meta(post["title"], post["description"], post_url, "article", post_image)
        page = {**post, "body": compose_article(post, cta_html)}
        out_path.write_text(render_post(template, page, head_meta), encoding="utf-8")
        written.append(out_path)

    hero_html = ""
    if homepage_config:
        hero_html = render_hero(homepage_config)
        image_name = homepage_config["product_image"]
        image_bytes = (posts_dir.parent / "product" / image_name).read_bytes()
        image_dest = output_dir / image_name
        image_dest.write_bytes(image_bytes)
        written.append(image_dest)
        for group in homepage_config.get("more_products", []):
            for item in group["items"]:
                thumb_dest = output_dir / item["image"]
                thumb_dest.parent.mkdir(parents=True, exist_ok=True)
                thumb_dest.write_bytes((posts_dir.parent / "product" / item["image"]).read_bytes())
                written.append(thumb_dest)

    if base_url:
        sitemap_xml = render_sitemap(posts, base_url)
        # sitemap-posts.xml is a fresh name for Search Console, which kept reporting
        # "couldn't fetch" for sitemap.xml after an early failed read
        for name in ("sitemap.xml", "sitemap-posts.xml"):
            sitemap_path = output_dir / name
            sitemap_path.write_text(sitemap_xml, encoding="utf-8")
            written.append(sitemap_path)

    index_title = site_config.get("title", "Home")
    index_url = f"{base_url}index.html" if base_url else None
    index_meta = render_head_meta(index_title, site_config.get("description"), index_url, "website", image_url)
    index_path = output_dir / "index.html"
    index_path.write_text(render_index(template, posts, hero_html, index_meta, index_title), encoding="utf-8")
    written.append(index_path)
    return written


def main(argv):
    if len(argv) != 4:
        print("usage: build_site.py <posts_dir> <template_path> <output_dir>", file=sys.stderr)
        return 2
    posts_dir, template_path, output_dir = (Path(a) for a in argv[1:4])
    try:
        written = build_site(posts_dir, template_path, output_dir)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"build failed: {e}", file=sys.stderr)
        return 1
    print(f"Built {len(written)} files into {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
