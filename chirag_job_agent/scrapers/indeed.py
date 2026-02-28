"""
scrapers/indeed.py — Scrape Indeed via RSS + HTML (no API, no cost)
Indeed exposes a free RSS feed for job searches — very reliable.
"""
import time
import random
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

INDEED_SEARCHES = [
    {"q": "business consultant",             "l": "Delhi, India"},
    {"q": "business analyst",                "l": "Noida, India"},
    {"q": "product manager",                 "l": "Gurugram, India"},
    {"q": "IT sales business development",   "l": "Delhi NCR"},
    {"q": "pre sales consultant",            "l": "Delhi NCR"},
    {"q": "associate product manager",       "l": "Delhi, India"},
]


def scrape_indeed_rss(max_jobs: int = 40) -> list[dict]:
    """
    Use Indeed's free RSS feed endpoint.
    https://in.indeed.com/rss?q=keyword&l=location&sort=date&fromage=1
    """
    all_jobs = []
    seen_urls = set()

    for search in INDEED_SEARCHES:
        if len(all_jobs) >= max_jobs:
            break
        try:
            params = {
                "q":       search["q"],
                "l":       search["l"],
                "sort":    "date",
                "fromage": "1",       # last 1 day
                "limit":   "15",
            }
            rss_url = "https://in.indeed.com/rss?" + urlencode(params)
            print(f"  [Indeed] Querying RSS: {search['q']} in {search['l']}")

            resp = requests.get(
                rss_url,
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=15
            )

            if resp.status_code != 200:
                print(f"  [Indeed] Status {resp.status_code}")
                time.sleep(3)
                continue

            # Parse XML RSS
            root = ET.fromstring(resp.content)
            ns   = {"content": "http://purl.org/rss/1.0/modules/content/"}
            items = root.findall(".//item")

            for item in items:
                try:
                    title   = item.findtext("title", "").strip()
                    link    = item.findtext("link", "").strip()
                    company = item.findtext("source", "").strip()
                    desc    = item.findtext("description", "").strip()
                    pub     = item.findtext("pubDate", "").strip()

                    # Clean HTML from description
                    if desc:
                        desc = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)
                    # Remove tracking junk from URL
                    clean_url = link.split("?")[0] if link else ""

                    if not title or not clean_url or clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)

                    all_jobs.append({
                        "title":           title,
                        "company":         company or "Unknown",
                        "location":        search["l"],
                        "url":             clean_url,
                        "platform":        "Indeed",
                        "employment_type": "Full-time",
                        "description":     desc[:2000],
                        "posted_date":     pub,
                    })

                except Exception:
                    continue

            print(f"  [Indeed] Collected {len(items)} items — total so far: {len(all_jobs)}")
            time.sleep(random.uniform(2, 4))

        except ET.ParseError as e:
            print(f"  [Indeed] XML parse error: {e} — trying HTML fallback")
            html_jobs = _scrape_indeed_html(search["q"], search["l"], seen_urls)
            all_jobs.extend(html_jobs)
        except Exception as e:
            print(f"  [Indeed] Error: {e}")
            time.sleep(3)

    return all_jobs[:max_jobs]


def _scrape_indeed_html(query: str, location: str, seen_urls: set) -> list[dict]:
    """Fallback: scrape Indeed HTML search results."""
    jobs = []
    try:
        params = {"q": query, "l": location, "sort": "date", "fromage": "1"}
        url = "https://in.indeed.com/jobs?" + urlencode(params)
        resp = requests.get(
            url,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            timeout=15
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job_seen_beacon, div.resultContent, td.resultContent")

        for card in cards:
            try:
                title_el   = card.select_one("h2.jobTitle span, a.jcs-JobTitle")
                company_el = card.select_one("span.companyName, [data-testid='company-name']")
                loc_el     = card.select_one("div.companyLocation, [data-testid='text-location']")
                link_el    = card.select_one("a[id^='job_'], a.jcs-JobTitle")

                title   = title_el.get_text(strip=True)   if title_el   else ""
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                loc     = loc_el.get_text(strip=True)     if loc_el     else location
                href    = link_el.get("href", "")         if link_el    else ""
                job_url = ("https://in.indeed.com" + href).split("?")[0] if href else ""

                if not title or not job_url or job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": job_url, "platform": "Indeed",
                    "employment_type": "Full-time", "description": "",
                    "posted_date": "",
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  [Indeed HTML] Error: {e}")
    return jobs


if __name__ == "__main__":
    jobs = scrape_indeed_rss(max_jobs=10)
    for j in jobs:
        print(f"  ✓ {j['title']} @ {j['company']} [{j['platform']}]")
    print(f"Total: {len(jobs)}")
