"""
main.py — AI Job Agent
GitHub Actions calls this once per day. No scheduler needed — Actions IS the scheduler.

Usage:
  python main.py           → full run (scrape + score + email)
  python main.py --test    → test mode (5 jobs per source, prints to console)
  python main.py --stats   → show database stats
"""
import sys
import os
import time
import logging
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import MIN_FIT_SCORE, LOG_PATH
from database import (init_db, insert_job, update_score,
                      get_todays_shortlist, mark_notified, log_run, get_stats)

# ── Logging — writes to file AND console (GitHub Actions shows console live) ──
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


def run_scrapers(test_mode=False):
    from scrapers.linkedin import scrape_linkedin
    from scrapers.indeed   import scrape_indeed_rss
    from scrapers.naukri   import scrape_naukri

    log.info("━" * 50)
    log.info("  🤖 AI JOB AGENT — GitHub Actions Run")
    log.info(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M IST')}")
    log.info("━" * 50)
    log.info("\n🔍 STEP 1/3 — Scraping job sources...")

    limit = 5 if test_mode else 30
    all_raw = []

    for name, fn in [("LinkedIn", scrape_linkedin), ("Indeed", scrape_indeed_rss), ("Naukri", scrape_naukri)]:
        try:
            jobs = fn(max_jobs=limit)
            log.info(f"  {name}: {len(jobs)} jobs found")
            all_raw.extend(jobs)
        except Exception as e:
            log.error(f"  {name} failed: {e}")

    # Deduplicate
    seen, unique = set(), []
    for job in all_raw:
        key = (job.get("url") or job.get("title","") + job.get("company","")).lower()[:100]
        if key not in seen:
            seen.add(key)
            unique.append(job)

    log.info(f"\n  Total unique jobs: {len(unique)}")
    return unique


def run_scoring(jobs, test_mode=False):
    from scorer.engine import score_job

    log.info("\n🧠 STEP 2/3 — Scoring with AI engine...")
    inserted_ids, kept = [], 0

    for i, job in enumerate(jobs):
        try:
            score_data = score_job(job)
            job.update(score_data)
            fit = score_data.get("fit_score", 0)

            status = "✅ KEPT" if fit >= MIN_FIT_SCORE else "🗑  skip"
            log.info(f"  [{i+1:02d}/{len(jobs)}] {status}  {fit}/10  {job['title'][:40]} @ {job.get('company','?')[:20]}")

            if fit >= MIN_FIT_SCORE:
                row_id = insert_job(job)
                if row_id:
                    update_score(row_id, score_data)
                    inserted_ids.append(row_id)
                    kept += 1

        except Exception as e:
            log.error(f"  Error: {e}")

    log.info(f"\n  Result: {kept} new jobs kept out of {len(jobs)} scored")
    return inserted_ids, kept


def run_notification():
    from notifier.email_digest import send_digest

    log.info("\n📬 STEP 3/3 — Sending digest email...")
    shortlist = get_todays_shortlist(min_score=MIN_FIT_SCORE)
    log.info(f"  Today's shortlist: {len(shortlist)} jobs")

    sent = send_digest(shortlist)
    if sent and shortlist:
        mark_notified([j["id"] for j in shortlist])
    return sent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",  action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    if args.stats:
        init_db()
        stats = get_stats()
        log.info(f"📊 Stats: {stats}")
        return

    start = time.time()
    init_db()

    raw_jobs        = run_scrapers(test_mode=args.test)
    ids, kept       = run_scoring(raw_jobs, test_mode=args.test)
    email_sent      = False if args.test else run_notification()

    log_run(len(raw_jobs), len(raw_jobs), kept, 1 if email_sent else 0)

    log.info(f"\n✅ Done in {round(time.time()-start, 1)}s")
    log.info(f"   DB total: {get_stats()['total']} jobs tracked")
    log.info("━" * 50)


if __name__ == "__main__":
    main()
