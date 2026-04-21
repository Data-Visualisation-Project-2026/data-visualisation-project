#!/usr/bin/env python3
"""
BBC News Iran War Scraper
Scrapes BBC search results for 'iran war', follows each article for full body text.

BBC uses auto-generated CSS class names (design system), so we rely on
semantic selectors and meta tags rather than class names.

Usage:
    python bbc_scraper.py --inspect   # verify selectors first
    python bbc_scraper.py             # full scrape

Output:
    bbc_output/articles.csv
    bbc_output/images/<article_id>/
"""

import argparse
import asyncio
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEARCH_URL    = "https://www.bbc.com/search?q=iran+war&page={page}"
TOTAL_PAGES   = 20
DELAY         = 2
OUTPUT_DIR    = Path("bbc_output")
IMAGES_DIR    = OUTPUT_DIR / "images"
ARTICLES_CSV  = OUTPUT_DIR / "articles.csv"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

ARTICLE_FIELDS = [
    "article_id", "url", "title", "description",
    "published_datetime", "modified_datetime",
    "authors", "section", "tags",
    "dateline", "body_text",
    "image_urls", "image_captions", "image_local_paths",
    "scraped_at",
]

# BBC article URL patterns to accept
BBC_ARTICLE_PATTERN = re.compile(
    r"bbc\.com/(news|sport|future|culture|travel|worklife|reel)/[^\"'\s]+"
)


def url_to_id(url: str) -> str:
    path = urlparse(url).path.strip("/")
    # BBC article IDs are often the last path segment (e.g. world-middle-east-12345678)
    return path.replace("/", "-")[-80:]


def is_bbc_article(url: str) -> bool:
    if not BBC_ARTICLE_PATTERN.search(url):
        return False
    # Exclude non-article pages
    exclude = ("/audio/", "/sounds/", "/iplayer/", "/live/", "/av/",
               "/topics/", "/newsletters/", "/sport/", "bbc.co.uk/sport")
    return not any(x in url for x in exclude)


# ---------------------------------------------------------------------------
# Inspect
# ---------------------------------------------------------------------------
async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        url = SEARCH_URL.format(page=1)
        print(f"Loading {url} ...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # BBC search results
        for sel in [
            "[data-testid='newport-card']",
            "[data-testid='internal-link']",
            "li[class*='SearchResult']",
            "li article",
            "ol li",
        ]:
            els = await page.query_selector_all(sel)
            if els:
                print(f"\n=== {len(els)} elements match '{sel}' ===")
                for i, el in enumerate(els[:2]):
                    print(f"\n--- Card {i+1} ---")
                    link = await el.query_selector("a[href]")
                    if link:
                        href  = await link.get_attribute("href") or ""
                        title = (await link.inner_text()).strip()
                        print(f"  URL  : {urljoin('https://www.bbc.com', href)}")
                        print(f"  Title: {title[:100]}")
                    time_el = await el.query_selector("time, [datetime]")
                    if time_el:
                        dt = await time_el.get_attribute("datetime") or await time_el.inner_text()
                        print(f"  Date : {dt[:50]}")
                break
        else:
            print("No card selector matched. Dumping article links:")
            links = await page.query_selector_all("a[href*='/news/']")
            for lnk in links[:8]:
                href = await lnk.get_attribute("href") or ""
                text = (await lnk.inner_text()).strip()
                if text:
                    print(f"  {urljoin('https://www.bbc.com', href)[:80]}  |  {text[:60]}")
        await browser.close()


# ---------------------------------------------------------------------------
# Search page
# ---------------------------------------------------------------------------
async def scrape_search_page(page, page_num: int) -> list[str]:
    url = SEARCH_URL.format(page=page_num)
    print(f"  Search page {page_num}: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(4)

    urls = set()

    # Use confirmed card selector first
    cards = await page.query_selector_all("[data-testid='newport-card']")
    if cards:
        for card in cards:
            link = await card.query_selector("a[href]")
            if not link:
                continue
            href = await link.get_attribute("href") or ""
            full = urljoin("https://www.bbc.com", href)
            if is_bbc_article(full):
                urls.add(full)
    else:
        # Fallback: all links on page filtered by URL pattern
        links = await page.query_selector_all("a[href]")
        for lnk in links:
            href = await lnk.get_attribute("href") or ""
            full = urljoin("https://www.bbc.com", href)
            if is_bbc_article(full):
                urls.add(full)

    print(f"    -> {len(urls)} article URLs")
    return list(urls)


# ---------------------------------------------------------------------------
# Article page
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
    h1 = await page.query_selector("h1")
    d["title"] = (await h1.inner_text()).strip() if h1 else ""

    # Description
    desc = await page.query_selector('meta[name="description"], meta[property="og:description"]')
    d["description"] = await desc.get_attribute("content") if desc else ""

    # Timestamps — BBC reliably puts these in meta tags
    pub = await page.query_selector('meta[property="article:published_time"]')
    d["published_datetime"] = await pub.get_attribute("content") if pub else ""

    mod = await page.query_selector('meta[property="article:modified_time"]')
    d["modified_datetime"] = await mod.get_attribute("content") if mod else ""

    # Fallback to <time> element
    if not d["published_datetime"]:
        time_el = await page.query_selector("time[datetime]")
        d["published_datetime"] = await time_el.get_attribute("datetime") if time_el else ""

    # Authors — BBC uses <meta> or byline elements
    author_metas = await page.query_selector_all('meta[property="article:author"]')
    authors = [await m.get_attribute("content") for m in author_metas]
    if not authors:
        byline = await page.query_selector(
            '[class*="byline"], [data-testid="byline"], '
            '[class*="contributor"], [class*="author"]'
        )
        if byline:
            authors = [(await byline.inner_text()).strip()]
    d["authors"] = " | ".join(a for a in authors if a)

    # Tags / section
    tag_metas = await page.query_selector_all('meta[property="article:tag"]')
    tags = [await t.get_attribute("content") for t in tag_metas]
    d["tags"] = " | ".join(set(tags))

    section_meta = await page.query_selector('meta[property="article:section"]')
    d["section"] = await section_meta.get_attribute("content") if section_meta else ""

    # Body text — BBC uses [data-component="text-block"] or article > div > p
    # Try semantic selectors in order of specificity
    body_text = ""
    dateline = ""

    text_blocks = await page.query_selector_all('[data-component="text-block"] p')
    if text_blocks:
        texts = [(await p.inner_text()).strip() for p in text_blocks]
    else:
        # Fallback: main article paragraphs
        article_el = await page.query_selector("article, main, [role='main']")
        if article_el:
            paras = await article_el.query_selector_all("p")
        else:
            paras = await page.query_selector_all("p")
        texts = [(await p.inner_text()).strip() for p in paras]

    if texts:
        body_text = "\n\n".join(t for t in texts if t and len(t) > 20)
        m = re.match(r"^([A-Z][A-Z\s,]+-\s)", texts[0])
        dateline = m.group(1).strip() if m else ""

    d["body_text"] = body_text
    d["dateline"]  = dateline

    # Images
    figures = await page.query_selector_all("figure")
    image_urls, image_captions = [], []
    for fig in figures:
        img = await fig.query_selector("img")
        cap = await fig.query_selector("figcaption")
        if img:
            src = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
            if src and not src.endswith(".svg"):
                image_urls.append(src)
                image_captions.append((await cap.inner_text()).strip() if cap else "")

    d["image_urls"]     = " | ".join(image_urls)
    d["image_captions"] = " | ".join(image_captions)

    return d


# ---------------------------------------------------------------------------
# Download images
# ---------------------------------------------------------------------------
async def download_images(image_urls: list[str], article_id: str) -> list[str]:
    article_img_dir = IMAGES_DIR / article_id
    article_img_dir.mkdir(parents=True, exist_ok=True)
    local_paths = []
    async with httpx.AsyncClient(
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    ) as client:
        for i, url in enumerate(image_urls):
            if not url:
                local_paths.append("")
                continue
            ext  = Path(urlparse(url).path).suffix or ".jpg"
            dest = article_img_dir / f"image_{i+1}{ext}"
            if dest.exists():
                local_paths.append(str(dest))
                continue
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    dest.write_bytes(resp.content)
                    local_paths.append(str(dest))
                else:
                    local_paths.append("")
            except Exception:
                local_paths.append("")
    return local_paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    progress: dict = {}
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
    done_urls: set     = set(progress.get("done_urls", []))
    all_article_urls: list = progress.get("all_article_urls", [])

    articles_file = open(ARTICLES_CSV, "a", newline="", encoding="utf-8")
    article_writer = csv.DictWriter(articles_file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
    if ARTICLES_CSV.stat().st_size == 0:
        article_writer.writeheader()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # Phase 1 — collect URLs
        if not all_article_urls:
            print("=== PHASE 1: Collecting article URLs ===")
            seen = set()
            for page_num in range(1, TOTAL_PAGES + 1):
                try:
                    urls = await scrape_search_page(page, page_num)
                    for u in urls:
                        if u not in seen:
                            seen.add(u)
                            all_article_urls.append(u)
                except Exception as e:
                    print(f"  Page {page_num} error: {e}")
                await asyncio.sleep(DELAY)
            progress["all_article_urls"] = all_article_urls
            PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
            print(f"\nTotal unique articles: {len(all_article_urls)}")

        # Phase 2 — scrape articles
        remaining = [u for u in all_article_urls if u not in done_urls]
        print(f"\n=== PHASE 2: Scraping {len(remaining)} articles ===")

        for i, url in enumerate(remaining):
            print(f"\n[{i+1}/{len(remaining)}] {url}")
            try:
                data = await scrape_article(page, url)
                img_url_list = [u for u in data.get("image_urls", "").split(" | ") if u]
                local_paths  = await download_images(img_url_list, data["article_id"])
                data["image_local_paths"] = " | ".join(local_paths)
                article_writer.writerow(data)
                done_urls.add(url)
                progress["done_urls"] = list(done_urls)
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
                if i % 10 == 0:
                    articles_file.flush()
            except Exception as e:
                print(f"  ERROR: {e}")
            await asyncio.sleep(DELAY)

        await browser.close()

    articles_file.close()
    print(f"\n=== DONE === {ARTICLES_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()
    if args.inspect:
        asyncio.run(inspect())
    else:
        asyncio.run(main())
