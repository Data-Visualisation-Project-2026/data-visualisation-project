#!/usr/bin/env python3
"""
AP News Iran War Scraper
Scrapes search results pages 1-20, full article body, all images, and Viafoura comments.

Usage:
    # Step 1 — inspect search page structure (run once to verify selectors)
    python ap_scraper.py --inspect

    # Step 2 — run full scrape
    python ap_scraper.py

Output:
    ap_news_output/articles.csv
    ap_news_output/comments.csv
    ap_news_output/images/<article_id>/image_1.jpg ...
"""

import argparse
import asyncio
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import httpx
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEARCH_URL   = "https://apnews.com/search?q=iran%20war%20&s=20&p={page}"
TOTAL_PAGES  = 20
DELAY        = 2        # seconds between page requests
OUTPUT_DIR   = Path("ap_news_output")
IMAGES_DIR   = OUTPUT_DIR / "images"
ARTICLES_CSV = OUTPUT_DIR / "articles.csv"
COMMENTS_CSV = OUTPUT_DIR / "comments.csv"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"   # resume support

ARTICLE_FIELDS = [
    "article_id", "url", "title", "description",
    "published_datetime", "modified_datetime",
    "authors", "author_urls",
    "section", "tags",
    "dateline", "body_text",
    "image_urls", "image_captions", "image_alts", "image_local_paths",
    "scraped_at",
]

COMMENT_FIELDS = [
    "article_id", "thread_id", "comment_id",
    "author_username", "comment_datetime",
    "comment_text", "likes", "dislikes",
    "is_reply", "parent_comment_id",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def url_to_id(url: str) -> str:
    """Extract slug from AP News article URL as a stable ID."""
    m = re.search(r"/article/([^/?#]+)", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


def decode_apnews_image(dims_url: str) -> str:
    """Extract original high-res asset URL from AP News dims CDN URL."""
    if "dims.apnews.com" not in dims_url:
        return dims_url
    parsed = urlparse(dims_url)
    qs = parse_qs(parsed.query)
    original = qs.get("url", [dims_url])[0]
    return unquote(original)


def epoch_ms_to_iso(ts_str: str) -> str:
    """Convert epoch-milliseconds string to ISO 8601."""
    try:
        ts = int(ts_str) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return ts_str


# ---------------------------------------------------------------------------
# Step 0 — Inspect search page (run once to verify selectors)
# ---------------------------------------------------------------------------

async def inspect_search_page():
    """Print raw HTML of first 2 article cards on search page 1."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible so you can watch
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        url = SEARCH_URL.format(page=1)
        print(f"Loading {url} ...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)  # let JS render article cards

        cards = await page.query_selector_all("div.PagePromo")
        print(f"\n=== Found {len(cards)} div.PagePromo cards ===")

        for i, card in enumerate(cards[:3]):
            print(f"\n--- Card {i+1} ---")
            media_link = await card.query_selector("div.PagePromo-media a.Link[href*='/article/']")
            if not media_link:
                media_link = await card.query_selector("a[href*='/article/']")

            if media_link:
                href       = await media_link.get_attribute("href") or ""
                aria_label = await media_link.get_attribute("aria-label") or ""
                print(f"  URL        : {href}")
                print(f"  aria-label : {aria_label}")

            date_el = await card.query_selector("bsp-timestamp[data-timestamp]")
            if date_el:
                ts = await date_el.get_attribute("data-timestamp")
                print(f"  timestamp  : {ts} → {epoch_ms_to_iso(ts)}")

            desc_el = await card.query_selector(
                "[class*='PagePromo-description'], [class*='description'], p"
            )
            if desc_el:
                desc = (await desc_el.inner_text()).strip()
                print(f"  description: {desc[:100]}")

            img_el = await card.query_selector("picture source, img")
            if img_el:
                srcset = await img_el.get_attribute("srcset") or await img_el.get_attribute("src") or ""
                print(f"  image      : {srcset[:100]}")

        await browser.close()


# ---------------------------------------------------------------------------
# Step 1 — Collect article URLs from search pages
# ---------------------------------------------------------------------------

async def scrape_search_page(page, page_num: int) -> list[dict]:
    url = SEARCH_URL.format(page=page_num)
    print(f"  Search page {page_num}: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(4)  # let JS render article cards

    results = []

    # AP News search results use div.PagePromo cards.
    # Title is in aria-label on the media link; other text fields are in PagePromo-content.
    cards = await page.query_selector_all("div.PagePromo")
    if cards:
        for card in cards:
            try:
                # URL + title — the media link's aria-label is always the full article title
                media_link = await card.query_selector("div.PagePromo-media a.Link[href*='/article/']")
                if not media_link:
                    # some cards have no image; fall back to any article link
                    media_link = await card.query_selector("a[href*='/article/']")
                if not media_link:
                    continue

                href     = await media_link.get_attribute("href") or ""
                full_url = urljoin("https://apnews.com", href)
                title    = (await media_link.get_attribute("aria-label") or "").strip()

                # Fallback title from heading text inside the card
                if not title:
                    title_el = await card.query_selector(
                        "h2, h3, [class*='PagePromo-title'], [class*='headline']"
                    )
                    title = (await title_el.inner_text()).strip() if title_el else ""

                # Timestamp — epoch-ms in data-timestamp attribute
                date_el  = await card.query_selector("bsp-timestamp[data-timestamp]")
                date_str = await date_el.get_attribute("data-timestamp") if date_el else ""
                if date_str:
                    date_str = epoch_ms_to_iso(date_str)

                # Description / summary text
                desc_el = await card.query_selector(
                    "[class*='PagePromo-description'], [class*='description'], p"
                )
                desc = (await desc_el.inner_text()).strip() if desc_el else ""

                # Thumbnail — prefer srcset first source for quality
                img_el = await card.query_selector("picture source, img")
                thumb  = ""
                if img_el:
                    thumb = (
                        await img_el.get_attribute("srcset")
                        or await img_el.get_attribute("src")
                        or ""
                    )
                    # srcset may have multiple URLs; take the first one
                    thumb = thumb.split(",")[0].split()[0]

                results.append({
                    "url": full_url, "title": title,
                    "date_str": date_str, "description": desc,
                    "thumbnail": thumb, "search_page": page_num,
                })
            except Exception as e:
                print(f"    Card parse error: {e}")
    else:
        # Fallback: collect all article links directly
        links = await page.query_selector_all("a[href*='/article/']")
        seen = set()
        for lnk in links:
            href = await lnk.get_attribute("href") or ""
            full_url = urljoin("https://apnews.com", href)
            if full_url in seen:
                continue
            seen.add(full_url)
            text = (await lnk.inner_text()).strip()
            results.append({"url": full_url, "title": text, "search_page": page_num})

    print(f"    -> {len(results)} articles found")
    return results


# ---------------------------------------------------------------------------
# Step 2 — Scrape individual article page
# ---------------------------------------------------------------------------

async def scrape_article(page, url: str) -> dict:
    print(f"  Article: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(DELAY)

    d = {
        "url": url,
        "article_id": url_to_id(url),
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Title
    h1 = await page.query_selector("h1.Page-headline")
    d["title"] = (await h1.inner_text()).strip() if h1 else ""

    # Description
    meta = await page.query_selector('meta[property="og:description"]')
    d["description"] = await meta.get_attribute("content") if meta else ""

    # Authors
    author_els = await page.query_selector_all("div.Page-authors a.Link")
    authors, author_urls = [], []
    for a in author_els:
        authors.append((await a.inner_text()).strip())
        author_urls.append(await a.get_attribute("href") or "")
    d["authors"]     = " | ".join(authors)
    d["author_urls"] = " | ".join(author_urls)

    # Timestamps
    pub = await page.query_selector('meta[property="article:published_time"]')
    d["published_datetime"] = await pub.get_attribute("content") if pub else ""

    ts_el = await page.query_selector("bsp-timestamp[data-timestamp]")
    if ts_el:
        ts_raw = await ts_el.get_attribute("data-timestamp")
        d["modified_datetime"] = epoch_ms_to_iso(ts_raw)
    else:
        mod = await page.query_selector('meta[property="article:modified_time"]')
        d["modified_datetime"] = await mod.get_attribute("content") if mod else ""

    # Section + tags
    sec = await page.query_selector('meta[property="article:section"]')
    d["section"] = await sec.get_attribute("content") if sec else ""

    tag_metas = await page.query_selector_all('meta[property="article:tag"]')
    tags = list({await t.get_attribute("content") for t in tag_metas})
    d["tags"] = " | ".join(tags)

    # Body + dateline
    body_div = await page.query_selector("div.RichTextStoryBody")
    body_text, dateline = "", ""
    if body_div:
        paras = await body_div.query_selector_all("p")
        texts = [(await p.inner_text()).strip() for p in paras]
        body_text = "\n\n".join(t for t in texts if t)
        if texts:
            m = re.match(r"^([A-Z][A-Z\s,]+\(AP\))", texts[0])
            dateline = m.group(1).strip() if m else ""
    d["body_text"] = body_text
    d["dateline"]  = dateline

    # Figures — extract hi-res original URLs from dims CDN
    figures = await page.query_selector_all("div.RichTextStoryBody figure, figure.Image")
    image_urls, image_captions, image_alts = [], [], []
    for fig in figures:
        img = await fig.query_selector("img")
        cap = await fig.query_selector("figcaption")
        if img:
            src = await img.get_attribute("src") or ""
            image_urls.append(decode_apnews_image(src))
            image_alts.append((await img.get_attribute("alt") or "").strip())
        else:
            image_urls.append("")
            image_alts.append("")
        image_captions.append((await cap.inner_text()).strip() if cap else "")

    d["image_urls"]     = " | ".join(image_urls)
    d["image_captions"] = " | ".join(image_captions)
    d["image_alts"]     = " | ".join(image_alts)

    return d


# ---------------------------------------------------------------------------
# Step 3 — Scrape Viafoura comments (JS widget)
# ---------------------------------------------------------------------------

async def scrape_comments(page, article_id: str) -> list[dict]:
    """
    Must be called after scrape_article() — the article page is still loaded.
    Scrolls to trigger Viafoura, loads all comments including replies.
    """
    comments = []

    # Scroll to bottom to trigger lazy-load of comment widget
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(3)

    try:
        await page.wait_for_selector("article.vf3-comment", timeout=10000)
    except PWTimeout:
        print("    No comments loaded.")
        return []

    # Get thread ID
    container = await page.query_selector('[id^="vf-all_threads-"]')
    thread_id = ""
    if container:
        cid = await container.get_attribute("id") or ""
        thread_id = cid.removeprefix("vf-all_threads-")

    # Click all "Load more" buttons until none remain
    while True:
        load_more = await page.query_selector(
            'button[data-testid*="load-more"], .vf-load-more, button[class*="load-more"]'
        )
        if not load_more:
            break
        try:
            await load_more.click()
            await asyncio.sleep(2)
        except Exception:
            break

    # Expand all collapsed replies
    reply_toggles = await page.query_selector_all('button[class*="vf3-comment__toggle"], button[aria-label*="replies"]')
    for btn in reply_toggles:
        try:
            await btn.click()
            await asyncio.sleep(0.5)
        except Exception:
            pass

    # Extract all comments
    comment_els = await page.query_selector_all("article.vf3-comment")
    print(f"    {len(comment_els)} comment elements found")

    for i, el in enumerate(comment_els):
        try:
            username_el = await el.query_selector(".vf-post-name-button__username")
            username    = (await username_el.inner_text()).strip() if username_el else ""

            time_el      = await el.query_selector("time.vf-post-details__time")
            comment_dt   = await time_el.get_attribute("datetime") if time_el else ""

            text_el      = await el.query_selector(".vf-content-text p")
            comment_text = (await text_el.inner_text()).strip() if text_el else ""

            like_btn    = await el.query_selector('[data-testid="vf-conversations-like-button"]')
            dislike_btn = await el.query_selector('[data-testid="vf-conversations-dislike-button"]')
            likes    = 0
            dislikes = 0
            if like_btn:
                aria = await like_btn.get_attribute("aria-label") or ""
                m = re.search(r"(\d+)\s+like", aria)
                likes = int(m.group(1)) if m else 0
            if dislike_btn:
                aria = await dislike_btn.get_attribute("aria-label") or ""
                m = re.search(r"(\d+)\s+dislike", aria)
                dislikes = int(m.group(1)) if m else 0

            # Detect if reply by checking ancestor article.vf3-comment count
            is_reply = await page.evaluate(
                """el => {
                    let count = 0, p = el.parentElement;
                    while (p) {
                        if (p.tagName === 'ARTICLE' && p.classList.contains('vf3-comment')) count++;
                        p = p.parentElement;
                    }
                    return count > 0;
                }""",
                el,
            )

            comments.append({
                "article_id":       article_id,
                "thread_id":        thread_id,
                "comment_id":       f"{article_id}_c{i}",
                "author_username":  username,
                "comment_datetime": comment_dt,
                "comment_text":     comment_text,
                "likes":            likes,
                "dislikes":         dislikes,
                "is_reply":         is_reply,
                "parent_comment_id": "",   # TODO: wire up if needed
            })
        except Exception as e:
            print(f"    Comment {i} parse error: {e}")

    return comments


# ---------------------------------------------------------------------------
# Step 4 — Download images
# ---------------------------------------------------------------------------

async def download_images(
    image_urls: list[str], article_id: str
) -> list[str]:
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
            # Infer extension from path; default jpg
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

async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    # Load progress (resume support)
    progress: dict = {}
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
    done_urls: set = set(progress.get("done_urls", []))
    all_article_urls: list = progress.get("all_article_urls", [])

    # Open CSVs in append mode so resume works
    articles_file = open(ARTICLES_CSV, "a", newline="", encoding="utf-8")
    comments_file = open(COMMENTS_CSV, "a", newline="", encoding="utf-8")

    article_writer = csv.DictWriter(articles_file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
    comment_writer = csv.DictWriter(comments_file, fieldnames=COMMENT_FIELDS, extrasaction="ignore")

    # Write headers only if files are new
    if ARTICLES_CSV.stat().st_size == 0:
        article_writer.writeheader()
    if COMMENTS_CSV.stat().st_size == 0:
        comment_writer.writeheader()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # --- Collect article URLs from search pages (skip if already done) ---
        if not all_article_urls:
            print("=== PHASE 1: Collecting article URLs ===")
            seen = set()
            for page_num in range(1, TOTAL_PAGES + 1):
                try:
                    results = await scrape_search_page(page, page_num)
                    for r in results:
                        if r["url"] not in seen:
                            seen.add(r["url"])
                            all_article_urls.append(r["url"])
                except Exception as e:
                    print(f"  Search page {page_num} error: {e}")
                await asyncio.sleep(DELAY)

            progress["all_article_urls"] = all_article_urls
            PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
            print(f"\nTotal unique articles: {len(all_article_urls)}")

        # --- Scrape each article ---
        print(f"\n=== PHASE 2: Scraping {len(all_article_urls)} articles ===")
        remaining = [u for u in all_article_urls if u not in done_urls]
        print(f"  {len(done_urls)} already done, {len(remaining)} remaining\n")

        for i, url in enumerate(remaining):
            print(f"\n[{i+1}/{len(remaining)}] {url}")
            try:
                article_data = await scrape_article(page, url)

                # Download images
                img_url_list  = [u for u in article_data.get("image_urls", "").split(" | ") if u]
                local_paths   = await download_images(img_url_list, article_data["article_id"])
                article_data["image_local_paths"] = " | ".join(local_paths)

                article_writer.writerow(article_data)

                # Comments (page is still on article)
                article_comments = await scrape_comments(page, article_data["article_id"])
                for c in article_comments:
                    comment_writer.writerow(c)

                # Mark done
                done_urls.add(url)
                progress["done_urls"] = list(done_urls)
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

                if i % 5 == 0:
                    articles_file.flush()
                    comments_file.flush()

            except Exception as e:
                print(f"  ERROR: {e}")

            await asyncio.sleep(DELAY)

        await browser.close()

    articles_file.close()
    comments_file.close()
    print(f"\n=== DONE ===")
    print(f"Articles : {ARTICLES_CSV}")
    print(f"Comments : {COMMENTS_CSV}")
    print(f"Images   : {IMAGES_DIR}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Inspect search page HTML to verify article card selectors before full scrape",
    )
    args = parser.parse_args()

    if args.inspect:
        asyncio.run(inspect_search_page())
    else:
        asyncio.run(main())
