"""
main.py — Runs the full ETL pipeline from start to finish.

  Step 1: EXTRACT   — open the website and scrape the data
  Step 2: TRANSFORM — clean up the data (fix types, handle nulls)
  Step 3: LOAD      — save the data to PostgreSQL
  Step 4: VERIFY    — check the counts are correct

Run with:
    python main.py
"""

import sys
import logging
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()  # reads DATABASE_URL from the .env file

from playwright.sync_api import sync_playwright

from extract   import extract_lookup_tables, extract_reservation_ids, extract_reservation_detail, extract_verify_targets
from transform import transform_room_types, transform_market_codes, transform_channel_codes, transform_reservation
from load      import get_db, load_room_types, load_market_codes, load_channel_codes, load_reservations, verify


# ── Set up logging ────────────────────────────────────────────────────────────
# This controls how log messages look in the terminal.
# Format: 2024-01-15 10:23:45 | INFO | your message here

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),  # print to terminal
    ]
)

log = logging.getLogger("main")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    log.info("=" * 55)
    log.info("  Hotel Hackathon ETL Pipeline")
    log.info("  Extract → Transform → Load → Verify")
    log.info("=" * 55)

    # Test the database connection before we start scraping
    log.info("Connecting to database...")
    try:
        conn = get_db()
        conn.close()
        log.info("Database connection OK")
    except Exception as e:
        log.error(f"Cannot connect to database: {e}")
        log.error("Is Docker running?  Try:  docker-compose up -d")
        sys.exit(1)

    # Open a headless browser (no window will appear on screen)
    log.info("Launching headless browser...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page    = browser.new_page()
        log.info("Browser ready")

        # ── Lookup tables ──────────────────────────────────────────────
        log.info("-" * 55)
        log.info("LOOKUP TABLES — Extract → Transform → Load")
        log.info("-" * 55)

        raw_lookups = extract_lookup_tables(page)   # Step 1

        load_room_types(   transform_room_types(   raw_lookups["room_types"]   ))
        load_market_codes( transform_market_codes( raw_lookups["market_codes"] ))
        load_channel_codes(transform_channel_codes(raw_lookups["channel_codes"]))

        log.info("Lookup tables done")

        # ── Reservations ───────────────────────────────────────────────
        log.info("-" * 55)
        log.info("RESERVATIONS — Extract → Transform → Load")
        log.info("-" * 55)

        # Step 1: Get a list of all reservation IDs first
        all_ids = extract_reservation_ids(page)
        log.info(f"Found {len(all_ids)} reservations to process")

        total_saved  = 0
        total_errors = 0

        # For each reservation: Extract → Transform → Load
        for i, rid in enumerate(all_ids, start=1):

            raw_detail  = extract_reservation_detail(page, rid)  # Step 1
            clean_rows  = transform_reservation(raw_detail)       # Step 2
            saved, errs = load_reservations(clean_rows)           # Step 3

            total_saved  += saved
            total_errors += errs

            # Log progress every 25 reservations (and first 3 and last one)
            if i % 25 == 0 or i <= 3 or i == len(all_ids):
                log.info(f"[{i:>3}/{len(all_ids)}] {rid} — {saved} rows saved  (running total: {total_saved})")

        # Fetch live expected counts from /verify before closing the browser
        live_targets = extract_verify_targets(page)

        browser.close()
        log.info("Browser closed")

    # Final summary
    log.info("-" * 55)
    log.info(f"DONE — Reservations: {len(all_ids)} | Rows saved: {total_saved} | Errors: {total_errors}")
    log.info("-" * 55)

    # ── Step 4: Verify ─────────────────────────────────────────────────
    log.info("VERIFY — Checking row counts in database")
    verify(live_targets)


def run_verify_only():
    """Open the browser, fetch live targets from /verify, check the database."""
    log.info("Running verify only...")

    log.info("Connecting to database...")
    try:
        conn = get_db()
        conn.close()
        log.info("Database connection OK")
    except Exception as e:
        log.error(f"Cannot connect to database: {e}")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page    = browser.new_page()
        live_targets = extract_verify_targets(page)
        browser.close()

    verify(live_targets)


if __name__ == "__main__":
    if "--verify" in sys.argv:
        run_verify_only()
    else:
        main()
