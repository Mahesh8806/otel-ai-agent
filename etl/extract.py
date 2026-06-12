"""
extract.py — Step 1: Scrape raw data from the website.
No cleaning here. Just open pages and return raw text/strings.
"""

import logging
from models import WEBSITE, RESERVATION_FIELDS

log = logging.getLogger("extract")


def extract_lookup_tables(page):
    """
    Go to /reference and read the 3 lookup tables on that page.
    Returns a dict with room_types, market_codes, and channel_codes.
    """
    log.info("Opening /reference page...")
    page.goto(f"{WEBSITE}/reference", wait_until="networkidle")
    page.wait_for_timeout(2000)
    log.info("/reference page loaded")

    tables = page.query_selector_all("table")
    log.info(f"Found {len(tables)} tables on /reference page")

    room_types    = read_table(tables[0]) if len(tables) > 0 else []
    market_codes  = read_table(tables[1]) if len(tables) > 1 else []
    channel_codes = read_table(tables[2]) if len(tables) > 2 else []

    log.info(f"Extracted — room_types: {len(room_types)}, market_codes: {len(market_codes)}, channel_codes: {len(channel_codes)}")

    return {
        "room_types":    room_types,
        "market_codes":  market_codes,
        "channel_codes": channel_codes,
    }


def read_table(table):
    """
    Read one HTML table and return it as a list of dicts.
    Each dict is one row, with column names as keys.
    Example: [{"space_type": "KNG", "room_class": "Deluxe", ...}, ...]
    """
    headers = []
    for th in table.query_selector_all("th"):
        headers.append(th.inner_text().strip().lower())

    rows = []
    for tr in table.query_selector_all("tbody tr"):
        cells = []
        for td in tr.query_selector_all("td"):
            cells.append(td.inner_text().strip())

        row = {}
        for i, header in enumerate(headers):
            row[header] = cells[i] if i < len(cells) else ""

        rows.append(row)

    return rows


def extract_reservation_ids(page):
    """
    Go through all pages of /reservations by clicking the "Next →" button.
    Stops when there is no Next button (last page reached).
    This works no matter how many pages there are in the future.
    Returns a list like ['S5001', 'S5002', ...]
    """
    log.info("Collecting all reservation IDs from /reservations...")

    # Start on page 1
    page.goto(f"{WEBSITE}/reservations", wait_until="networkidle")
    page.wait_for_timeout(2500)

    all_ids = []
    page_number = 1

    while True:
        # Collect all reservation IDs on this page
        links = page.query_selector_all("a[href^='/reservations/']")
        ids_on_this_page = []
        seen = set()

        for link in links:
            href = link.get_attribute("href") or ""
            href = href.rstrip("/")
            rid  = href.split("/")[-1]

            if rid and rid not in seen:
                seen.add(rid)
                ids_on_this_page.append(rid)

        log.info(f"Page {page_number}: found {len(ids_on_this_page)} reservation IDs  (running total: {len(all_ids) + len(ids_on_this_page)})")
        all_ids.extend(ids_on_this_page)

        # Find the Next button using its data-testid attribute
        next_button = page.query_selector("[data-testid='next-page']")

        # On the last page the button exists but is disabled — stop if so
        if next_button is None or next_button.is_disabled():
            log.info("Next button is disabled — this was the last page")
            break

        # Click Next and wait for the new page to load
        log.info(f"Clicking Next → to go to page {page_number + 1}...")
        next_button.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        page_number += 1

    log.info(f"Total reservation IDs collected: {len(all_ids)}")
    return all_ids


def extract_verify_targets(page):
    """
    Scrape the /verify page to get today's expected counts.
    The site regenerates data daily so numbers change — we always fetch live targets.
    Returns a dict like: {"total_stay_rows": 534, "total_reservations": 250, ...}
    """
    log.info("Fetching expected counts from /verify page...")
    page.goto(f"{WEBSITE}/verify", wait_until="networkidle")
    page.wait_for_timeout(2000)

    # The page shows key/value pairs as alternating lines of text
    body_text = page.inner_text("body")
    lines = [line.strip() for line in body_text.split("\n") if line.strip()]

    targets = {}
    for i, line in enumerate(lines):
        if i + 1 < len(lines):
            try:
                # If the next line is a plain number, this line is the key
                value = int(lines[i + 1].replace(",", ""))
                targets[line.lower().replace(" ", "_")] = value
            except ValueError:
                pass

    log.info(f"Live verify targets: {targets}")
    return targets


def extract_reservation_detail(page, reservation_id):
    """
    Open one reservation detail page and scrape:
    - fields: arrival date, status, market code, etc.
    - stay_rows: the nightly revenue table (one row per night)

    Returns a dict with reservation_id, fields, and stay_rows.
    All values are raw strings — no cleaning yet.
    """
    log.debug(f"Scraping reservation {reservation_id}")
    page.goto(f"{WEBSITE}/reservations/{reservation_id}", wait_until="networkidle")
    page.wait_for_timeout(1500)

    # Fields appear as label + value pairs in the page body text
    body_text = page.inner_text("body")
    lines = []
    for line in body_text.split("\n"):
        if line.strip():
            lines.append(line.strip())

    fields = {}
    for i, line in enumerate(lines):
        if line.lower() in RESERVATION_FIELDS:
            if i + 1 < len(lines):
                fields[line.lower()] = lines[i + 1]

    # The nightly revenue is in a table with a "stay_date" column
    stay_rows = []
    for table in page.query_selector_all("table"):
        headers = []
        for th in table.query_selector_all("th"):
            headers.append(th.inner_text().strip().lower())

        if "stay_date" not in headers:
            continue

        for tr in table.query_selector_all("tbody tr"):
            cells = []
            for td in tr.query_selector_all("td"):
                cells.append(td.inner_text().strip())

            if len(cells) >= 3:
                stay_rows.append({
                    "stay_date":                      cells[0],
                    "daily_room_revenue_before_tax":  cells[1],
                    "daily_total_revenue_before_tax": cells[2],
                })

    log.debug(f"  {reservation_id}: {len(fields)} fields, {len(stay_rows)} stay nights")

    return {
        "reservation_id": reservation_id,
        "fields":         fields,
        "stay_rows":      stay_rows,
    }
