"""
scrapers/naukri.py — Scrape Naukri.com job listings (no API, no cost)
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

NAUKRI_SEARCHES = [
    ("business-consultant-jobs", "delhi-ncr"),
    ("business-analyst-jobs",    "delhi-ncr"),
    ("product-manager-jobs",     "delhi-ncr"),
    ("it-sales-jobs",            "delhi-ncr"),
    ("business-development-jobs","delhi-ncr"),
]


def scrape_naukri(max_jobs: int = 40) -> list[dict]:
    """
    Scrape Naukri.com search results pages.
    Uses clean URL structure: naukri.com/{keyword}-jobs-in-{location}
    """
    all_jobs = []
    seen_urls = set()

    for keyword, location in NAUKRI_SEARCHES:
        if len(all_jobs) >= max_jobs:
            break
        try:
            url = f"https://www.naukri.com/{keyword}-in-{location}"
            print(f"  [Naukri] Scraping: {url}")

            resp = requests.get(
                url,
                headers={
                    "User-Agent":      random.choice(USER_AGENTS),
                    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer":         "https://www.naukri.com/",
                    "Connection":      "keep-alive",
                },
                timeout=20
            )

            if resp.status_code != 200:
                print(f"  [Naukri] Status {resp.status_code}")
                time.sleep(5)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Naukri uses article tags for job cards
            cards = soup.select("article.jobTuple, div.jobTuple, div[class*='srp-jobtuple']")

            # Fallback: try JSON embedded in page (Naukri often includes it)
            if not cards:
                cards = soup.select("a.title, div.job-title-wrapper")

            for card in cards:
                try:
                    # Title
                    title_el = card.select_one(
                        "a.title, a[class*='jobTitle'], h2 a, .title a"
                    )
                    if not title_el:
                        continue
                    title   = title_el.get_text(strip=True)
                    job_url = title_el.get("href", "")
                    if not job_url.startswith("http"):
                        job_url = "https://www.naukri.com" + job_url
                    job_url = job_url.split("?")[0]

                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Company
                    company_el = card.select_one(
                        "a.subTitle, a[class*='companyName'], span[class*='comp-name'], .company-name"
                    )
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    # Location
                    loc_el = card.select_one(
                        "li[class*='location'], span[class*='loc'], ul.top-jd-dtl li:nth-child(2)"
                    )
                    location_text = loc_el.get_text(strip=True) if loc_el else "Delhi NCR"

                    # Experience
                    exp_el = card.select_one(
                        "li[class*='experience'], span[class*='exp']"
                    )
                    experience = exp_el.get_text(strip=True) if exp_el else ""

                    # Description snippet
                    desc_el = card.select_one(
                        "div[class*='job-description'], span[class*='job-desc'], ul[class*='tags-gt']"
                    )
                    description = desc_el.get_text(" ", strip=True) if desc_el else ""

                    # Skills tags
                    skill_tags = card.select("ul[class*='tags-gt'] li, span[class*='skill-tag']")
                    if skill_tags:
                        skills_str = ", ".join(s.get_text(strip=True) for s in skill_tags)
                        description = (description + " Skills: " + skills_str).strip()

                    all_jobs.append({
                        "title":           title,
                        "company":         company,
                        "location":        location_text,
                        "url":             job_url,
                        "platform":        "Naukri",
                        "employment_type": "Full-time",
                        "description":     description[:2000],
                        "posted_date":     "",
                    })

                except Exception:
                    continue

            print(f"  [Naukri] Parsed {len(cards)} cards — total: {len(all_jobs)}")
            time.sleep(random.uniform(4, 7))   # Be polite

        except Exception as e:
            print(f"  [Naukri] Error for {keyword}: {e}")
            time.sleep(5)

    return all_jobs[:max_jobs]


if __name__ == "__main__":
    jobs = scrape_naukri(max_jobs=10)
    for j in jobs:
        print(f"  ✓ {j['title']} @ {j['company']} [{j['platform']}]")
    print(f"Total: {len(jobs)}")
