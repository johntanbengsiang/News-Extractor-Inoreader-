"""
Scrapes https://www.ap-ha.com/news-publications and builds an RSS feed
containing ONLY the "Newsletter" category posts (the monthly
"AP Hospitality Bulletin Asia Pacific" articles).

Designed to run on a schedule via GitHub Actions. Writes feed.xml to the
repo root, which GitHub Pages then serves as a live RSS URL.
"""

import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.ap-ha.com/news-publications"
FEED_TITLE = "AP Hospitality Advisors - Bulletin"
FEED_DESCRIPTION = "AP Hospitality Bulletin Asia Pacific (monthly newsletter only)"
# This should match wherever GitHub Pages ends up serving the repo from.
# Update after you know your GitHub username/repo name.
FEED_SELF_URL = "https://REPLACE_ME.github.io/ap-ha-rss-feed/feed.xml"
FEED_SITE_URL = SOURCE_URL

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PersonalRSSBot/1.0; +https://github.com/)"
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def is_month_token(text: str) -> bool:
    return text.strip().lower() in MONTHS


def is_day_token(text: str) -> bool:
    t = text.strip()
    return t.isdigit() and 1 <= int(t) <= 31


def extract_posts(html: str):
    """
    Walk the document in order. Track the most recently seen category
    link and the most recently seen month/day text tokens. When we hit
    a link to /post/..., attach whatever category/month/day we've seen
    most recently (this matches the linear layout of the page: category
    label, month, day, then the post title link).
    """
    soup = BeautifulSoup(html, "html.parser")

    posts = []
    current_category = None
    current_month = None
    current_day = None
    seen_post_urls = set()

    for el in soup.descendants:
        # Track category links, e.g. <a href="/blog-category/newsletter">Newsletter</a>
        if el.name == "a" and el.get("href"):
            href = el["href"]
            if "/blog-category/" in href:
                current_category = el.get_text(strip=True)
                continue
            if "/post/" in href:
                url = href
                if url.startswith("/"):
                    url = "https://www.ap-ha.com" + url
                title = el.get_text(strip=True)
                if not title:
                    # Some post links wrap only an image; skip empty-title dupes
                    continue
                if url in seen_post_urls:
                    continue
                seen_post_urls.add(url)
                posts.append({
                    "title": title,
                    "url": url,
                    "category": current_category,
                    "month": current_month,
                    "day": current_day,
                })
                continue

        # Track bare text tokens for month / day (NavigableStrings)
        if isinstance(el, str):
            text = el.strip()
            if not text:
                continue
            if is_month_token(text):
                current_month = MONTHS[text.lower()]
                current_day = None  # reset until we see the day for this entry
            elif is_day_token(text) and current_month is not None:
                current_day = int(text)

    return posts


def infer_years(posts):
    """
    The site shows month + day but no year. Posts are listed newest-first.
    Walk forward assuming year stays the same or decreases as we go back
    in time; decrement year whenever the month number increases going
    down the list (i.e. we've wrapped from Jan back into Dec of the prior year).
    """
    now = datetime.now(timezone.utc)
    year = now.year
    prev_month = None

    for i, p in enumerate(posts):
        if p["month"] is None:
            p["year"] = year
            continue
        if i == 0:
            # If the very first (newest) post's month is after the current
            # month, it must belong to last year.
            if p["month"] > now.month:
                year -= 1
        else:
            if prev_month is not None and p["month"] > prev_month:
                year -= 1
        p["year"] = year
        prev_month = p["month"]
    return posts


def build_rss(posts):
    now_rfc822 = format_datetime(datetime.now(timezone.utc))

    items_xml = []
    for p in posts:
        day = p["day"] or 1
        month = p["month"] or 1
        try:
            pub_dt = datetime(p["year"], month, day, 12, 0, 0, tzinfo=timezone.utc)
        except ValueError:
            pub_dt = datetime.now(timezone.utc)
        pub_rfc822 = format_datetime(pub_dt)

        title = escape_xml(p["title"])
        link = escape_xml(p["url"])
        guid = escape_xml(p["url"])

        items_xml.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{guid}</guid>
      <pubDate>{pub_rfc822}</pubDate>
    </item>""")

    items_block = "\n".join(items_xml)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape_xml(FEED_TITLE)}</title>
    <link>{escape_xml(FEED_SITE_URL)}</link>
    <atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{escape_xml(FEED_SELF_URL)}" rel="self" type="application/rss+xml" />
    <description>{escape_xml(FEED_DESCRIPTION)}</description>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
{items_block}
  </channel>
</rss>
"""
    return rss


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def main():
    html = fetch_html(SOURCE_URL)
    posts = extract_posts(html)

    # Only keep the Bulletin/Newsletter category
    bulletin_posts = [p for p in posts if p["category"] and p["category"].lower() == "newsletter"]

    if not bulletin_posts:
        print("WARNING: no newsletter posts found. Site structure may have changed.", file=sys.stderr)

    bulletin_posts = infer_years(bulletin_posts)

    rss = build_rss(bulletin_posts)

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print(f"Wrote feed.xml with {len(bulletin_posts)} bulletin items.")


if __name__ == "__main__":
    main()
