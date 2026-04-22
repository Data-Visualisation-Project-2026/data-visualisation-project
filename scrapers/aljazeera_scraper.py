#!/usr/bin/env python3
"""
Al Jazeera English Iran War Scraper
Uses GDELT DOC 2.0 API to get article URLs, then fetches full text via httpx + BeautifulSoup.
No Playwright needed — AJ article pages are server-side rendered.

Usage:
    python aljazeera_scraper.py

Output:
    aljazeera_output/articles.csv
    aljazeera_output/images/<article_id>/
"""

import asyncio
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GDELT_API     = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_QUERY   = "iran war domain:aljazeera.com"
START_DATE    = "20260227000000"
END_DATE      = "20260420235959"
MAX_RECORDS   = 250            # GDELT max per request

DELAY         = 1.5            # seconds between article fetches
OUTPUT_DIR    = Path("aljazeera_output")
IMAGES_DIR    = OUTPUT_DIR / "images"
ARTICLES_CSV  = OUTPUT_DIR / "articles.csv"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

ARTICLE_FIELDS = [
    "article_id", "url", "title", "description",
    "published_datetime", "modified_datetime",
    "authors", "section", "tags",
    "dateline", "body_text",
    "image_urls", "image_captions", "image_local_paths",
    "scraped_at",
]


def url_to_id(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return re.sub(r"[^a-z0-9\-]", "-", path.split("/")[-1])[:80]


# ---------------------------------------------------------------------------
# Step 1 — Collect article URLs from GDELT
# ---------------------------------------------------------------------------

def fetch_gdelt_urls() -> list[dict]:
    """Query GDELT API for Al Jazeera Iran war articles. Returns list of {url, title, date}."""
    params = {
        "query":         GDELT_QUERY,
        "mode":          "artlist",
        "maxrecords":    MAX_RECORDS,
        "startdatetime": START_DATE,
        "enddatetime":   END_DATE,
        "format":        "json",
    }
    print(f"Querying GDELT for Al Jazeera articles ({START_DATE[:8]} – {END_DATE[:8]})...")
    r = httpx.get(GDELT_API, params=params, timeout=30)
    r.raise_for_status()
    articles = r.json().get("articles", [])
    print(f"  GDELT returned {len(articles)} article URLs")
    return articles


# ---------------------------------------------------------------------------
# Step 2 — Scrape individual article page
# ---------------------------------------------------------------------------

def scrape_article(url: str) -> dict:
    r = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    d = {
        "url":        url,
        "article_id": url_to_id(url),
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Title
    h1 = soup.find("h1")
    d["title"] = h1.get_text(strip=True) if h1 else ""

    # Description
    desc = (
        soup.find("meta", property="og:description")
        or soup.find("meta", attrs={"name": "description"})
    )
    d["description"] = desc.get("content", "") if desc else ""

    # Published / modified
    pub = soup.find("meta", property="article:published_time")
    d["published_datetime"] = pub.get("content", "") if pub else ""
    mod = soup.find("meta", property="article:modified_time")
    d["modified_datetime"] = mod.get("content", "") if mod else ""

    # Fallback to <time> if no meta
    if not d["published_datetime"]:
        time_el = soup.find("time", attrs={"datetime": True})
        d["published_datetime"] = time_el["datetime"] if time_el else ""

    # Authors
    author_metas = soup.find_all("meta", property="article:author")
    authors = [m.get("content", "") for m in author_metas if m.get("content")]
    if not authors:
        for sel in ["[class*='author-name']", "[class*='article-author']", "[rel='author']"]:
            els = soup.select(sel)
            if els:
                authors = list({e.get_text(strip=True) for e in els if e.get_text(strip=True)})
                break
    d["authors"] = " | ".join(authors)

    # Section + tags
    sec = soup.find("meta", property="article:section")
    d["section"] = sec.get("content", "") if sec else ""

    tag_metas = soup.find_all("meta", property="article:tag")
    d["tags"] = " | ".join({m.get("content", "") for m in tag_metas if m.get("content")})

    # Body text — AJ uses div.wysiwyg for article body
    body_div = soup.select_one("div.wysiwyg")
    body_text = ""
    dateline = ""
    if body_div:
        paras = body_div.find_all("p")
        texts = [p.get_text(strip=True) for p in paras if p.get_text(strip=True)]
        body_text = "\n\n".join(texts)
        if texts:
            m = re.match(r"^([A-Z][A-Z\s,]+[-–]\s)", texts[0])
            dateline = m.group(1).strip() if m else ""
    d["body_text"] = body_text
    d["dateline"]  = dateline

    # Images — all figures in the article
    image_urls, image_captions = [], []
    for fig in soup.find_all("figure"):
        img = fig.find("img")
        cap = fig.find("figcaption")
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src and not src.endswith(".svg"):
                image_urls.append(src)
                image_captions.append(cap.get_text(strip=True) if cap else "")

    d["image_urls"]     = " | ".join(image_urls)
    d["image_captions"] = " | ".join(image_captions)

    return d


# ---------------------------------------------------------------------------
# Step 3 — Download images
# ---------------------------------------------------------------------------

def download_images(image_urls: list[str], article_id: str) -> list[str]:
    article_img_dir = IMAGES_DIR / article_id
    article_img_dir.mkdir(parents=True, exist_ok=True)
    local_paths = []

    with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
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
                resp = client.get(url)
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

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    # Load progress
    progress: dict = {}
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
    done_urls: set      = set(progress.get("done_urls", []))
    all_article_metas: list = progress.get("all_article_metas", [])

    # Phase 1 — collect URLs from GDELT
    if not all_article_metas:
        all_article_metas = fetch_gdelt_urls()
        progress["all_article_metas"] = all_article_metas
        PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

    # Open CSV
    articles_file = open(ARTICLES_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(articles_file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
    if ARTICLES_CSV.stat().st_size == 0:
        writer.writeheader()

    # Phase 2 — scrape each article
    remaining = [m for m in all_article_metas if m["url"] not in done_urls]
    print(f"\n=== Scraping {len(remaining)} articles ({len(done_urls)} already done) ===\n")

    for i, meta in enumerate(remaining):
        url = meta["url"]
        print(f"[{i+1}/{len(remaining)}] {url}")
        try:
            data = scrape_article(url)

            img_url_list = [u for u in data.get("image_urls", "").split(" | ") if u]
            local_paths  = download_images(img_url_list, data["article_id"])
            data["image_local_paths"] = " | ".join(local_paths)

            writer.writerow(data)
            done_urls.add(url)
            progress["done_urls"] = list(done_urls)
            PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

            if data.get("body_text"):
                print(f"  ✓ {len(data['body_text'])} chars | {data.get('published_datetime','')[:10]}")
            else:
                print(f"  ✗ No body text")

            if i % 20 == 0:
                articles_file.flush()

        except Exception as e:
            print(f"  ERROR: {e}")

        time.sleep(DELAY)

    articles_file.close()
    print(f"\n=== DONE === {ARTICLES_CSV}")
    print(f"Articles with body text: {sum(1 for m in all_article_metas if m['url'] in done_urls)}")


if __name__ == "__main__":
    main()
