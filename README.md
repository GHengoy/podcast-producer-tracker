# Podcast Producer & Episode Management

A small content-to-product funnel: a blog with podcast production guides and operational templates, linking to a downloadable tracker template sold on Gumroad. See `decisions/niche-selection.md` for why this niche was chosen.

## Layout

- `scripts/` — site builder and content/product validators (Python stdlib only)
- `tests/` — unit tests for the above
- `posts/` — blog post content (one `.json` metadata + `.html` body fragment per post)
- `templates/` — shared HTML template
- `product/` — the tracker CSV + guide, packaged as a zip for Gumroad
- `docs/` — built site output (GitHub Pages serves from here)
