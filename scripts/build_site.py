"""Static site builder: assembles docs/ output from posts/ + templates/base.html."""
import html
import json
import sys
from pathlib import Path


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
        })
    return posts


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


def render_hero(config: dict) -> str:
    """Render the homepage hero + product highlight block from a homepage.json config dict.

    The buy button opens a Paddle overlay checkout when 'paddle_price_id' is set, otherwise links to 'buy_url'.
    """
    if config.get("paddle_price_id"):
        buy_attrs = f'href="#" data-paddle-price-id="{config["paddle_price_id"]}"'
    else:
        buy_attrs = f'href="{config["buy_url"]}"'
    return (
        f'<h2>{config["headline"]}</h2>\n'
        f'<p>{config["tagline"]}</p>\n'
        f'<div class="product-box">\n'
        f'<img src="{config["product_image"]}" alt="{config["product_name"]}">\n'
        f'<h3>{config["product_name"]} — {config["product_price"]}</h3>\n'
        f'<p>{config["product_description"]}</p>\n'
        f'<p><a class="buy-button" {buy_attrs}>{config["buy_label"]}</a></p>\n'
        f'</div>\n'
        f'<h3>Latest Posts</h3>\n'
    )


def render_index(template: str, posts: list[dict], hero_html: str = "", head_meta: str = "", title: str = "Home") -> str:
    """Fill the base template with a list of links to all posts, newest first. Posts marked 'unlisted' are excluded. Optionally prefixed with a hero/product block."""
    listed_posts = [p for p in posts if not p.get("unlisted", False)]
    items = "\n".join(
        f'<li><a href="{p["slug"]}.html">{p["title"]}</a> — {p["date"]}</li>'
        for p in sorted(listed_posts, key=lambda p: p["date"], reverse=True)
    )
    body = f"{hero_html}<ul>\n{items}\n</ul>"
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
    for post in posts:
        out_path = output_dir / f"{post['slug']}.html"
        post_url = f"{base_url}{post['slug']}.html" if base_url else None
        head_meta = render_head_meta(post["title"], post["description"], post_url, "article", image_url)
        out_path.write_text(render_post(template, post, head_meta), encoding="utf-8")
        written.append(out_path)

    homepage_config = load_homepage_config(posts_dir.parent)
    hero_html = ""
    if homepage_config:
        hero_html = render_hero(homepage_config)
        image_name = homepage_config["product_image"]
        image_bytes = (posts_dir.parent / "product" / image_name).read_bytes()
        image_dest = output_dir / image_name
        image_dest.write_bytes(image_bytes)
        written.append(image_dest)

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
