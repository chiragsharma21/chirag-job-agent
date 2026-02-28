"""
scrapers/linkedin.py — Scrape LinkedIn public job search (no login, no API)
Uses the public jobs search URL that LinkedIn exposes without authentication.
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEARCH_QUERIES, TARGET_LOCATIONS

# Rotate user agents to avoid blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.linkedin.com/",
    }


def scrape_linkedin(max_jobs: int = 40) -> list[dict]:
    """
    Scrape LinkedIn public job listings.
    Uses the public /jobs/search/ endpoint — no login needed.
    """
    all_jobs = []
    seen_urls = set()

    # Search for multiple query+location combinations
    searches = [
        ("business consultant", "Delhi NCR, India"),
        ("business analyst", "Noida, India"),
        ("product manager", "Gurugram, India"),
        ("IT sales business development", "Delhi, India"),
        ("pre-sales consultant", "Delhi NCR, India"),
    ]

    for keyword, location in searches:
        if len(all_jobs) >= max_jobs:
            break
        try:
            params = {
                "keywords": keyword,
                "location": location,
                "f_TPR":    "r86400",   # last 24 hours
                "f_E":      "2,3",      # Associate + Mid-Senior
                "start":    "0"
            }
            url = "https://www.linkedin.com/jobs/search/?" + urlencode(params)
            print(f"  [LinkedIn] Searching: {keyword} in {location}")

            resp = requests.get(url, headers=get_headers(), timeout=15)
            if resp.status_code != 200:
                print(f"  [LinkedIn] Status {resp.status_code} — skipping")
                time.sleep(random.uniform(3, 6))
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            job_cards = soup.select("div.job-search-card, li.jobs-search-results__list-item, div.base-card")

            for card in job_cards:
                try:
                    # Title
                    title_el = card.select_one("h3.base-search-card__title, h3.job-search-card__title, a.job-card-list__title")
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    # Company
                    company_el = card.select_one("h4.base-search-card__subtitle, a.job-card-container__company-name, span.job-search-card__company-name")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    # Location
                    loc_el = card.select_one("span.job-search-card__location, span.job-card-container__metadata-item")
                    location_text = loc_el.get_text(strip=True) if loc_el else location

                    # URL
                    link_el = card.select_one("a.base-card__full-link, a.job-card-list__title, a[href*='/jobs/view/']")
                    job_url = ""
                    if link_el and link_el.get("href"):
                        job_url = link_el["href"].split("?")[0]  # remove tracking params
                        if not job_url.startswith("http"):
                            job_url = "https://www.linkedin.com" + job_url

                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Posted time
                    time_el = card.select_one("time, span.job-search-card__listdate")
                    posted = time_el.get("datetime", "") if time_el else ""

                    # Try to get description snippet
                    desc_el = card.select_one("p.job-search-card__snippet, div.job-card-list__footer-wrapper")
                    description = desc_el.get_text(strip=True) if desc_el else ""

                    all_jobs.append({
                        "title":          title,
                        "company":        company,
                        "location":       location_text,
                        "url":            job_url,
                        "platform":       "LinkedIn",
                        "employment_type": "Full-time",
                        "description":    description,
                        "posted_date":    posted,
                    })

                except Exception as e:
                    continue

            print(f"  [LinkedIn] Found {len(job_cards)} cards, collected {len(all_jobs)} total")
            time.sleep(random.uniform(4, 8))   # polite delay

        except Exception as e:
            print(f"  [LinkedIn] Error: {e}")
            time.sleep(5)

    return all_jobs[:max_jobs]


if __name__ == "__main__":
    jobs = scrape_linkedin(max_jobs=10)
    for j in jobs:
        print(f"  ✓ {j['title']} @ {j['company']} — {j['platform']}")
    print(f"Total: {len(jobs)}")
