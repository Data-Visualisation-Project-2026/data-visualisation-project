#!/usr/bin/env python3
"""
Tehran Times Iran War Scraper
Scans article IDs in a known range (sequential IDs) to collect full date coverage.
Scrapes full text with httpx + BeautifulSoup. No Playwright needed.

Usage:
    python tehrantimes_scraper.py

Output:
    tehrantimes_output/articles.csv
    tehrantimes_output/progress.json  (resume-safe)
"""

import csv
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL    = "https://www.tehrantimes.com"
# ID range estimated from known anchors:
#   Mar 2 2026 = 524396,  Apr 6 2026 = ~525229  (~24 articles/day)
#   Feb 27 back-estimated = ~524200
ID_START    = 524_200
ID_END      = 525_650
DELAY       = 1.0   # seconds between requests

OUTPUT_DIR    = Path("tehrantimes_output")
ARTICLES_CSV  = OUTPUT_DIR / "articles.csv"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Keywords to filter for Iran war relevance
WAR_KEYWORDS = re.compile(
    r"iran|war|strike|attack|israel|bomb|missile|nuclear|trump|military|"
    r"tehran|weapon|ceasefire|hormuz|sanction|zionist|irgc|revolution.guard",
    re.I
)

ARTICLE_FIELDS = [
    "article_id", "url", "title", "description",
    "published_datetime", "authors", "section", "tags",
    "dateline", "body_text",
    "image_urls", "image_captions",
    "scraped_at",
]


def url_to_id(url: str) -> str:
    m = re.search(r"/news/(\d+)/", url)
    return m.group(1) if m else url.split("/")[-1][:40]


# ---------------------------------------------------------------------------
# Step 1 — Check if an ID is a valid article and return its URL
# ---------------------------------------------------------------------------

def check_id(article_id: int, client: httpx.Client) -> str | None:
    """HEAD-check an article ID. Returns URL if it exists, None if 404/error."""
    url = f"{BASE_URL}/news/{article_id}/"
    try:
        r = client.head(url, timeout=8, follow_redirects=True)
        if r.status_code == 200:
            return str(r.url)
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 2 — Scrape individual article
# ---------------------------------------------------------------------------

def scrape_article(url: str, client: httpx.Client) -> dict:
    r = client.get(url, timeout=20, follow_redirects=True)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    d = {
        "url":        url,
        "article_id": url_to_id(url),
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Title — TT uses h2 for article title, og:title as fallback
    og_title = soup.find("meta", property="og:title")
    if og_title:
        d["title"] = og_title.get("content", "").strip()
    else:
        h2 = soup.find("h2")
        d["title"] = h2.get_text(strip=True) if h2 else ""

    # Description
    desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    d["description"] = desc.get("content", "").strip() if desc else ""

    # Published date — TT uses a custom date class, no meta
    date_el = soup.select_one("[class*='date'], [class*='time'], .date")
    if date_el:
        raw = date_el.get_text(strip=True)
        # Format: "March 2, 2026 - 21:35"
        m = re.search(r"(\w+ \d+, \d{4})", raw)
        if m:
            try:
                d["published_datetime"] = datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                d["published_datetime"] = raw
        else:
            d["published_datetime"] = raw
    else:
        pub = soup.find("meta", property="article:published_time")
        d["published_datetime"] = pub.get("content", "") if pub else ""

    # Authors
    author_els = soup.select("[rel='author'], [class*='author']")
    authors = list({el.get_text(strip=True) for el in author_els if el.get_text(strip=True)})
    d["authors"] = " | ".join(authors)

    # Tags / section
    tag_metas = soup.find_all("meta", property="article:tag")
    d["tags"] = " | ".join({m.get("content", "") for m in tag_metas if m.get("content")})

    sec = soup.find("meta", property="article:section")
    d["section"] = sec.get("content", "") if sec else ""

    # Body text — TT uses <article> for the full article container
    article_el = soup.find("article")
    body_text = ""
    dateline = ""
    if article_el:
        # Remove nav/related news noise
        for noise in article_el.select("nav, aside, [class*='related'], [class*='tags'], h1, h2"):
            noise.decompose()
        paras = article_el.find_all("p")
        texts = [p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20]
        body_text = "\n\n".join(texts)
        if texts:
            m = re.match(r"^(TEHRAN|DUBAI|WASHINGTON|LONDON|BEIJING)[^—\-]*[-–]\s*", texts[0])
            dateline = m.group(0).strip(" -–") if m else ""

    d["body_text"] = body_text
    d["dateline"]  = dateline

    # Images
    image_urls, image_captions = [], []
    if article_el:
        for fig in article_el.find_all("figure"):
            img = fig.find("img")
            cap = fig.find("figcaption")
            if img:
                src = img.get("src") or img.get("data-src") or ""
                if src and not src.endswith(".svg"):
                    if not src.startswith("http"):
                        src = urljoin(BASE_URL, src)
                    image_urls.append(src)
                    image_captions.append(cap.get_text(strip=True) if cap else "")

    d["image_urls"]     = " | ".join(image_urls)
    d["image_captions"] = " | ".join(image_captions)

    return d


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load progress — track which IDs have been checked
    progress: dict = {}
    if PROGRESS_FILE.exists():
        progress = json.loads(PROGRESS_FILE.read_text())
    last_checked_id: int = progress.get("last_checked_id", ID_START - 1)
    done_urls: set        = set(progress.get("done_urls", []))

    articles_file = open(ARTICLES_CSV, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(articles_file, fieldnames=ARTICLE_FIELDS, extrasaction="ignore")
    if ARTICLES_CSV.stat().st_size == 0:
        writer.writeheader()

    total_ids    = ID_END - ID_START + 1
    remaining_ids = ID_END - last_checked_id
    war_count    = sum(1 for _ in open(ARTICLES_CSV)) - 1 if ARTICLES_CSV.stat().st_size > 0 else 0

    print(f"=== Scanning IDs {ID_START}–{ID_END} ({total_ids} total) ===")
    print(f"    Resuming from ID {last_checked_id + 1} ({remaining_ids} remaining)")
    print(f"    War articles saved so far: {war_count}\n")

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for article_id in range(last_checked_id + 1, ID_END + 1):
            url = f"{BASE_URL}/news/{article_id}/"
            checked = 0

            try:
                # GET (not HEAD) — we need the page anyway if it exists
                r = client.get(url, timeout=12, follow_redirects=True)

                if r.status_code == 404:
                    # ID doesn't exist — skip silently
                    pass
                elif r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")

                    # Quick keyword pre-filter on title before full parse
                    og_title = soup.find("meta", property="og:title")
                    title_text = og_title.get("content", "") if og_title else ""
                    if not title_text:
                        h2 = soup.find("h2")
                        title_text = h2.get_text(strip=True) if h2 else ""

                    if not WAR_KEYWORDS.search(title_text):
                        print(f"  {article_id}  skip  {title_text[:60]}")
                    else:
                        # Full scrape
                        data = scrape_article(str(r.url), client)
                        # Double-check body text is war-related
                        if WAR_KEYWORDS.search(data.get("body_text", "")[:500] + data.get("title", "")):
                            writer.writerow(data)
                            articles_file.flush()
                            war_count += 1
                            done_urls.add(str(r.url))
                            body_len = len(data.get("body_text", ""))
                            pub = data.get("published_datetime", "")[:10]
                            print(f"  {article_id}  ✓  [{pub}] {data.get('title','')[:60]}  ({body_len}c)")
                        else:
                            print(f"  {article_id}  skip (body)  {title_text[:60]}")
                else:
                    print(f"  {article_id}  HTTP {r.status_code}")

            except Exception as e:
                print(f"  {article_id}  ERROR: {e}")

            # Save progress every 50 IDs
            last_checked_id = article_id
            if article_id % 50 == 0:
                progress["last_checked_id"] = last_checked_id
                progress["done_urls"]        = list(done_urls)
                progress["war_count"]        = war_count
                PROGRESS_FILE.write_text(json.dumps(progress, indent=2))
                pct = 100 * (article_id - ID_START) / total_ids
                print(f"\n  --- Progress: {article_id}/{ID_END} ({pct:.0f}%) | War articles: {war_count} ---\n")

            time.sleep(DELAY)

    # Final save
    progress["last_checked_id"] = ID_END
    progress["done_urls"]        = list(done_urls)
    progress["war_count"]        = war_count
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

    articles_file.close()
    print(f"\n=== DONE ===")
    print(f"Scanned IDs    : {ID_START}–{ID_END}")
    print(f"War articles   : {war_count}")
    print(f"Output         : {ARTICLES_CSV}")


if __name__ == "__main__":
    main()
