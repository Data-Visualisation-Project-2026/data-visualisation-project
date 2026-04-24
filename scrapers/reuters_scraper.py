#!/usr/bin/env python3
"""
Reuters Iran War Scraper
Uses the Reuters Arc Publishing search API (articles-by-search-v2) for metadata,
then visits each article page for full body text and images.

Requires: playwright (with Chrome channel), httpx
    pip install playwright httpx
    playwright install chrome   # if Chrome is not already installed

Usage:
    # Step 1 — inspect one article to verify selectors (opens visible browser)
    python reuters_scraper.py --inspect

    # Step 2 — full scrape (past year by default)
    python reuters_scraper.py

    # Custom date range
    python reuters_scraper.py --start-date 2025-01-01 --end-date 2026-04-19

    # Metadata-only (no article page visits, much faster)
    python reuters_scraper.py --metadata-only

Output:
    reuters_output/articles.csv
    reuters_output/images/<article_id>/image_1.jpg ...
"""

import argparse
import asyncio
import csv
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlencode, quote

import httpx
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
QUERY        = "iran war"
SEARCH_BASE  = "https://www.reuters.com/site-search/"
API_BASE     = "https://www.reuters.com/pf/api/v3/content/fetch/articles-by-search-v2"
PAGE_SIZE    = 20
DELAY        = 2        # seconds between requests
OUTPUT_DIR   = Path("reuters_output")
IMAGES_DIR   = OUTPUT_DIR / "images"
ARTICLES_CSV = OUTPUT_DIR / "articles.csv"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

CHROME_COOKIES_DIR = Path.home() / "Library/Application Support/Google/Chrome/Default"

ARTICLE_FIELDS = [
    "article_id", "url", "title", "description",
    "published_datetime", "updated_datetime",
    "authors", "author_emails",
    "section", "primary_tag", "tags",
    "kicker", "subtype", "content_code",
    "word_count", "read_minutes",
    "dateline", "body_text",
    "thumbnail_url", "thumbnail_caption", "thumbnail_alt",
    "image_urls", "image_captions", "image_alts", "image_local_paths",
    "scraped_at",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_temp_profile() -> Path:
    """Copy Chrome profile files to a temp dir for a fresh context with real cookies."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "Default").mkdir()
    for fname in ("Cookies", "Local State"):
        src = CHROME_COOKIES_DIR / fname
        if src.exists():
            shutil.copy(src, tmpdir / "Default" / fname)
    # Copy Local Storage for richer session state
    ls_src = CHROME_COOKIES_DIR / "Local Storage"
    ls_dst = tmpdir / "Default" / "Local Storage"
    if ls_src.exists():
        shutil.copytree(ls_src, ls_dst)
    return tmpdir


def build_api_url(keyword: str, offset: int, start_date: str, end_date: str) -> str:
    query_params = json.dumps({
        "keyword": keyword,
        "offset": offset,
        "orderby": "relevance",
        "size": PAGE_SIZE,
        "start_date": start_date,
        "end_date": end_date,
        "website": "reuters",
    }, separators=(",", ":"))
    return f"{API_BASE}?query={quote(query_params)}&d=359&mxId=00000000&_website=reuters"


async def fetch_api_page(page, api_url: str) -> dict | None:
    """Call the Reuters search API from within the browser context (bypasses DataDome)."""
    try:
        result = await page.evaluate(
            """async (url) => {
                const resp = await fetch(url, {credentials: 'include'});
                if (!resp.ok) return {error: resp.status};
                return await resp.json();
            }""",
            api_url,
        )
        return result
    except Exception as e:
        print(f"    API fetch error: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 0 — Inspect article page (run once to verify selectors)
# ---------------------------------------------------------------------------

async def inspect_article(article_url: str):
    tmpdir = make_temp_profile()
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(tmpdir),
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        print(f"Loading: {article_url}")
        await page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)

        # Body paragraphs
        paras = await page.query_selector_all("[class*='paragraph']")
        print(f"\n=== {len(paras)} paragraphs found ===")
        for i, p_el in enumerate(paras[:5]):
            txt = (await p_el.inner_text()).strip()
            print(f"  [{i}] {txt[:120]}")

        # Figures
        figs = await page.query_selector_all("figure")
        print(f"\n=== {len(figs)} figures ===")
        for i, fig in enumerate(figs[:3]):
            img = await fig.query_selector("img")
            cap = await fig.query_selector("figcaption")
            src = await img.get_attribute("src") if img else ""
            cap_txt = (await cap.inner_text()).strip() if cap else ""
            print(f"  [{i}] src={src[:80]} | caption={cap_txt[:80]}")

        await ctx.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Step 1 — Collect article metadata via search API
# ---------------------------------------------------------------------------

async def collect_articles(
    page, start_date: str, end_date: str, max_results: int = 0
) -> list[dict]:
    articles = []
    offset = 0
    print(f"\n=== PHASE 1: Collecting article metadata via API ===")
    print(f"  Date range: {start_date[:10]} → {end_date[:10]}")

    while True:
        api_url = build_api_url(QUERY, offset, start_date, end_date)
        print(f"  Offset {offset}: {api_url[:100]}...")
        data = await fetch_api_page(page, api_url)

        if not data or "result" not in data:
            print(f"    No data or unexpected response. Stopping.")
            break

        result = data["result"]
        batch = result.get("articles", [])
        if not batch:
            print(f"    Empty batch at offset {offset}. Done.")
            break

        for item in batch:
            authors     = item.get("authors", [])
            author_names  = " | ".join(a.get("name", "") for a in authors)
            author_emails = " | ".join(a.get("id", "") for a in authors)

            kicker_names = item.get("kicker", {}).get("names", [])
            section = " > ".join(kicker_names) if kicker_names else ""

            primary_tag = item.get("primary_tag", {})
            tag_text = primary_tag.get("text", "") if primary_tag else ""

            thumb = item.get("thumbnail") or {}

            canonical = item.get("canonical_url", "")
            url = urljoin("https://www.reuters.com", canonical)

            articles.append({
                "article_id":        item.get("id", ""),
                "url":               url,
                "title":             item.get("title", ""),
                "description":       item.get("description", ""),
                "published_datetime": item.get("published_time", ""),
                "updated_datetime":  item.get("updated_time", ""),
                "authors":           author_names,
                "author_emails":     author_emails,
                "section":           section,
                "primary_tag":       tag_text,
                "subtype":           item.get("subtype", ""),
                "content_code":      item.get("content_code", ""),
                "word_count":        item.get("word_count", ""),
                "read_minutes":      item.get("read_minutes", ""),
                "thumbnail_url":     thumb.get("resizer_url", thumb.get("url", "")),
                "thumbnail_caption": thumb.get("caption", ""),
                "thumbnail_alt":     thumb.get("alt_text", ""),
            })

        print(f"    -> {len(batch)} articles (total so far: {len(articles)})")
        offset += PAGE_SIZE

        if max_results and len(articles) >= max_results:
            print(f"  Reached max_results={max_results}")
            break

        # Check pagination info
        pagination = result.get("pagination", {})
        total = pagination.get("total_size", 0) or pagination.get("total", 0)
        if total and offset >= total:
            print(f"  Reached total ({total} articles). Done.")
            break

        await asyncio.sleep(DELAY)

    print(f"\nTotal articles collected: {len(articles)}")
    return articles


# ---------------------------------------------------------------------------
# Step 2 — Scrape individual article page for body text + images
# ---------------------------------------------------------------------------

async def is_blocked(page) -> bool:
    """Return True if DataDome is showing a bot-protection page."""
    body = await page.content()
    return (
        "Please enable JS" in body
        or "captcha-delivery.com" in body
        or "datadome" in body.lower()
        or await page.title() == "reuters.com"
    )


async def reprime_session(page, search_url: str):
    """Reload the Reuters search page to refresh DataDome cookies."""
    print("  [session] Re-priming DataDome session...")
    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(8)
    if await is_blocked(page):
        print("  [session] Still blocked after re-prime — waiting longer...")
        await asyncio.sleep(15)
    else:
        print("  [session] Session refreshed OK.")


async def scrape_article_body(page, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(DELAY)

    result = {"tags": "", "kicker": "", "body_text": "", "dateline": "",
              "image_urls": "", "image_captions": "", "image_alts": ""}

    if await is_blocked(page):
        raise RuntimeError("BLOCKED")

    # Tags
    tag_els = await page.query_selector_all("[class*='tags'] a, [class*='topic'] a")
    tags = list({(await t.inner_text()).strip() for t in tag_els if (await t.inner_text()).strip()})
    result["tags"] = " | ".join(tags)

    # Kicker / section breadcrumb
    kicker_els = await page.query_selector_all("[class*='article-header'] [class*='kicker'] a")
    kicker_parts = [(await k.inner_text()).strip() for k in kicker_els]
    result["kicker"] = " > ".join(kicker_parts)

    # Body paragraphs
    para_els = await page.query_selector_all("[class*='paragraph']")
    texts = [(await p.inner_text()).strip() for p in para_els]
    texts = [t for t in texts if t]
    result["body_text"] = "\n\n".join(texts)

    # Dateline — first paragraph often starts with "CITY, Date -"
    if texts:
        m = re.match(r"^([A-Z][A-Z\s,]+,\s+\w+ \d+)", texts[0])
        result["dateline"] = m.group(1).strip() if m else ""

    # Figures within article body (skip thumbnail / promo images)
    figs = await page.query_selector_all(
        "[class*='article-body'] figure, [class*='ArticleBody'] figure"
    )
    image_urls, image_captions, image_alts = [], [], []
    for fig in figs:
        img = await fig.query_selector("img")
        cap = await fig.query_selector("figcaption")
        if img:
            src = (await img.get_attribute("src") or
                   await img.get_attribute("data-src") or "")
            image_urls.append(src)
            image_alts.append((await img.get_attribute("alt") or "").strip())
        else:
            image_urls.append("")
            image_alts.append("")
        image_captions.append((await cap.inner_text()).strip() if cap else "")

    result["image_urls"]     = " | ".join(image_urls)
    result["image_captions"] = " | ".join(image_captions)
    result["image_alts"]     = " | ".join(image_alts)

    return result


# ---------------------------------------------------------------------------
# Step 3 — Download images
# ---------------------------------------------------------------------------

async def download_images(image_urls: list[str], article_id: str) -> list[str]:
    article_img_dir = IMAGES_DIR / article_id
    article_img_dir.mkdir(parents=True, exist_ok=True)
    local_paths = []

    async with httpx.AsyncClient(
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        follow_redirects=True,
    ) as client:
        for i, url in enumerate(image_urls):
            if not url:
                local_paths.append("")
                continue
            ext  = Path(urlparse(url).path).suffix or ".jpg"
            name = f"image_{i+1}{ext}"
            dest = article_img_dir / name
            if dest.exists():
                local_paths.append(str(dest))
                continue
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    dest.write_bytes(resp.content)
                    local_paths.append(str(dest))
                    print(f"    Saved {name} ({len(resp.content)//1024} KB)")
                else:
                    print(f"    HTTP {resp.status_code}: {url[:70]}")
                    local_paths.append("")
            except Exception as e:
                print(f"    Download error: {e}")
                local_paths.append("")

    return local_paths


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def main(start_date: str, end_date: str, metadata_only: bool, max_results: int, batch_size: int):
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    # Resume support
    progress: dict = {}
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
    done_urls: set = set(progress.get("done_urls", []))
    all_articles: list = progress.get("all_articles", [])

    articles_file = open(ARTICLES_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(articles_file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
    if ARTICLES_CSV.stat().st_size == 0:
        writer.writeheader()

    tmpdir = make_temp_profile()
    try:
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(
                user_data_dir=str(tmpdir),
                channel="chrome",
                headless=False,   # DataDome blocks headless; keep visible
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()

            # Prime the session: load search page once to get DataDome cookies
            print("Priming session (loading Reuters search page)...")
            search_url = (
                f"{SEARCH_BASE}?query={quote(QUERY)}"
                f"&date=custom&dateFrom={start_date[:10]}&dateTo={end_date[:10]}"
                f"&offset=0&sort=relevance"
            )
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(6)

            title = await page.title()
            if await is_blocked(page):
                print("  Blocked on startup — waiting 15s and retrying once...")
                await asyncio.sleep(15)
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(8)
                if await is_blocked(page):
                    print("ERROR: Still blocked after retry. Visit reuters.com in Chrome and try again.")
                    await ctx.close()
                    return

            print(f"Session primed. Page title: {await page.title()}")

            # Phase 1: collect metadata
            if not all_articles:
                all_articles = await collect_articles(page, start_date, end_date, max_results)
                progress["all_articles"] = all_articles
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

            if metadata_only:
                print("\n-- metadata-only mode: writing CSV without article body --")
                for a in all_articles:
                    a.setdefault("scraped_at", datetime.now(tz=timezone.utc).isoformat())
                    writer.writerow(a)
                articles_file.flush()
            else:
                # Phase 2: visit each article for body text + images
                remaining = [a for a in all_articles if a["url"] not in done_urls]
                batch = remaining[:batch_size] if batch_size else remaining
                print(f"\n=== PHASE 2: Scraping batch of {len(batch)} articles ===")
                print(f"  ({len(done_urls)} done, {len(remaining)} remaining total)\n")

                for i, article in enumerate(batch):
                    url = article["url"]
                    print(f"\n[{i+1}/{len(batch)}] {url}")
                    try:
                        body_data = await scrape_article_body(page, url)
                        if not body_data.get("body_text"):
                            print("  WARNING: empty body — likely blocked. Stopping batch early.")
                            break
                        article.update(body_data)
                        article["scraped_at"] = datetime.now(tz=timezone.utc).isoformat()

                        img_list = [u for u in article.get("image_urls", "").split(" | ") if u]
                        local_paths = await download_images(img_list, article["article_id"])
                        article["image_local_paths"] = " | ".join(local_paths)

                        writer.writerow(article)
                        articles_file.flush()
                        done_urls.add(url)
                        progress["done_urls"] = list(done_urls)
                        PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
                    except RuntimeError as e:
                        if "BLOCKED" in str(e):
                            print("  BLOCKED — stopping batch early. Re-run after visiting reuters.com in Chrome.")
                            break
                        print(f"  ERROR: {e}")
                    except Exception as e:
                        print(f"  ERROR: {e}")

                    await asyncio.sleep(DELAY)

                remaining_after = len([a for a in all_articles if a["url"] not in done_urls])
                print(f"\n  Batch complete. {len(done_urls)} done, {remaining_after} remaining.")

            await ctx.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    articles_file.close()
    print(f"\n=== DONE ===")
    print(f"Articles : {ARTICLES_CSV}")
    print(f"Images   : {IMAGES_DIR}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reuters Iran War Scraper")
    parser.add_argument(
        "--inspect",
        metavar="URL",
        nargs="?",
        const="https://www.reuters.com/world/middle-east/new-mediators-emerge-iran-war-2026-04-01/",
        help="Inspect a single article page to verify selectors",
    )
    parser.add_argument(
        "--start-date",
        default=(datetime.now(tz=timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        help="Start date ISO 8601, e.g. 2025-01-01T00:00:00Z (default: 1 year ago)",
    )
    parser.add_argument(
        "--end-date",
        default=datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        help="End date ISO 8601, e.g. 2026-04-19T00:00:00Z (default: now)",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only collect metadata from search API (no body text, much faster)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=0,
        help="Stop Phase 1 after N articles (0 = unlimited)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Articles to scrape per run in Phase 2 (default: 50). Re-run to continue.",
    )
    args = parser.parse_args()

    if args.inspect:
        asyncio.run(inspect_article(args.inspect))
    else:
        asyncio.run(main(
            start_date=args.start_date,
            end_date=args.end_date,
            metadata_only=args.metadata_only,
            max_results=args.max_results,
            batch_size=args.batch_size,
        ))
