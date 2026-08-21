"""Static site builder: assembles docs/ output from posts/ + templates/base.html."""
import json
import sys
from pathlib import Path


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
        })
    return posts


def render_post(template: str, post: dict) -> str:
    """Fill the base template with one post's title/date/body."""
    return (
        template
        .replace("{{TITLE}}", post["title"])
        .replace("{{DATE}}", post["date"])
        .replace("{{BODY}}", post["body"])
    )


def render_index(template: str, posts: list[dict]) -> str:
    """Fill the base template with a list of links to all posts, newest first."""
    items = "\n".join(
        f'<li><a href="{p["slug"]}.html">{p["title"]}</a> — {p["date"]}</li>'
        for p in sorted(posts, key=lambda p: p["date"], reverse=True)
    )
    body = f"<ul>\n{items}\n</ul>"
    return (
        template
        .replace("{{TITLE}}", "Home")
        .replace("{{DATE}}", "")
        .replace("{{BODY}}", body)
    )


def build_site(posts_dir: Path, template_path: Path, output_dir: Path) -> list[Path]:
    """Build the full site: one HTML file per post plus an index.html. Returns written paths."""
    template = template_path.read_text(encoding="utf-8")
    posts = load_posts(posts_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for post in posts:
        out_path = output_dir / f"{post['slug']}.html"
        out_path.write_text(render_post(template, post), encoding="utf-8")
        written.append(out_path)

    index_path = output_dir / "index.html"
    index_path.write_text(render_index(template, posts), encoding="utf-8")
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
