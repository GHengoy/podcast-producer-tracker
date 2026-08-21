# Gumroad Integration Decision

**api_creation_available:** undocumented

**chosen_approach:** manual-assist

## Findings

Gumroad's official public API documentation at https://gumroad.com/api does **not** document a product creation endpoint.

However, a `POST /v2/products` route *does exist* in Gumroad's open-source Rails codebase (https://github.com/antiwork/gumroad/blob/master/config/routes.rb and app/controllers/api/v2/links_controller.rb), complete with OAuth scoping and parameter validation. This creates ambiguity:

| Aspect | Finding |
|--------|---------|
| **Official public docs** | No product creation endpoint documented at gumroad.com/api |
| **Source code route** | Route exists: `resources :links, path: "products", only: [:create, ...]` |
| **OAuth scope** | `edit_products` scope configured in source |
| **Status** | Undocumented; could be internal-only or subject to change without notice |

### Risk Assessment

Using an undocumented API endpoint for live product creation poses several risks:

1. **No SLA or stability guarantee** - Gumroad could change or remove this endpoint without warning
2. **No public support** - If it breaks, there's no official channel to report it
3. **Not in public API contract** - Building mission-critical automation on this is unsupported
4. **Indistinguishable from internal routes** - The route's presence in open-source code doesn't prove it's meant for third-party use

**Conclusion:** This endpoint exists but is not a supported public API, so it cannot be treated as a reliable integration point for Task 7.

## Approach

**Manual creation by user** is the chosen approach because:

1. **Supported workflow** - Gumroad's dashboard is the documented, supported way to create products
2. **Stability** - User-facing UI is version-controlled and tested; no risk of breaking changes
3. **Analogous to account setup** - Just like the user manually signs up for Gumroad, they'll manually create the first product
4. **Graceful fallback** - Task 7 will provide clear instructions instead of failing on undocumented API

### User Handoff for Task 7

When Task 7 runs, it will provide the user with a simple checklist to create the product manually:

**Product Details to Paste:**

- **Title:** `{product_title from Task 6}`
- **Description:** `{product_description from Task 6}`
- **Price:** `{USD price from Task 6}`

**File to Upload:**

- **Filename:** `multi-cat-tracker.zip` (or name from Task 6)
- **Location:** `{prepared zip file path}`
- **What it contains:** Complete multi-cat tracker tool

**User Steps:**

1. Visit https://gumroad.com/dashboard
2. Click **Create** or **New Product**
3. Enter the **Title** (copy from above)
4. Enter the **Description** (copy from above)
5. Set the **Price** in USD (copy from above)
6. Upload the **Product File** (the ZIP from Task 6)
7. Choose **Product Type:** "Digital Product"
8. Click **Publish**
9. Copy the resulting product URL (gumroad.com/your-username/product-slug)
10. Share this URL back with Task 7 or the automation system

This mirrors the user's existing Gumroad account setup (which they already agreed to handle directly) and treats product creation the same way: a one-time manual step with clear guidance.

### No API Integration (For Now)

If Gumroad publishes official product creation API docs in the future, this decision can be revisited. Until then, manual creation via the dashboard is the safest, most supported path.

## Provenance

This finding (no confirmed public product-creation API; manual-assist is the approach) was originally researched for the multi-cat-tracker venture and independently, skeptically re-verified there. It is a platform-wide fact about Gumroad, not niche-specific, so it's reused verbatim here rather than re-researched. If Gumroad's public API changes, this decision should be revisited across all venture repos, not just this one.

## Result

<To be filled in once the product is manually listed on Gumroad and the live URL is confirmed.>
