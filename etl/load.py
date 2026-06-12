"""
load.py — Step 3: Save cleaned data to PostgreSQL.
          Step 4: Verify the counts are correct.

All saves use "upsert" — if a row already exists, update it.
This means re-running the ETL will never create duplicates.
"""

import os
import logging
import psycopg2
import psycopg2.extras

log = logging.getLogger("load")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5433/hotel_hackathon"
)


def get_db():
    """Open and return a PostgreSQL connection."""
    return psycopg2.connect(DATABASE_URL)


# ── Save lookup tables ────────────────────────────────────────────────────────

def load_room_types(records):
    log.info(f"Loading {len(records)} room types into database...")
    conn = get_db()
    cur  = conn.cursor()

    values = []
    for r in records:
        values.append((r["space_type"], r["room_class"], r["display_name"], r["number_of_rooms"]))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO room_type_lookup (space_type, room_class, display_name, number_of_rooms)
        VALUES %s
        ON CONFLICT (space_type) DO UPDATE SET
            room_class      = EXCLUDED.room_class,
            display_name    = EXCLUDED.display_name,
            number_of_rooms = EXCLUDED.number_of_rooms
    """, values)

    conn.commit()
    conn.close()
    log.info(f"room_type_lookup — {len(records)} rows saved OK")


def load_market_codes(records):
    log.info(f"Loading {len(records)} market codes into database...")
    conn = get_db()
    cur  = conn.cursor()

    values = []
    for r in records:
        values.append((r["market_code"], r["market_name"], r["macro_group"], r["description"]))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO market_code_lookup (market_code, market_name, macro_group, description)
        VALUES %s
        ON CONFLICT (market_code) DO UPDATE SET
            market_name = EXCLUDED.market_name,
            macro_group = EXCLUDED.macro_group,
            description = EXCLUDED.description
    """, values)

    conn.commit()
    conn.close()
    log.info(f"market_code_lookup — {len(records)} rows saved OK")


def load_channel_codes(records):
    log.info(f"Loading {len(records)} channel codes into database...")
    conn = get_db()
    cur  = conn.cursor()

    values = []
    for r in records:
        values.append((r["channel_code"], r["channel_name"], r["channel_group"]))

    psycopg2.extras.execute_values(cur, """
        INSERT INTO channel_code_lookup (channel_code, channel_name, channel_group)
        VALUES %s
        ON CONFLICT (channel_code) DO UPDATE SET
            channel_name  = EXCLUDED.channel_name,
            channel_group = EXCLUDED.channel_group
    """, values)

    conn.commit()
    conn.close()
    log.info(f"channel_code_lookup — {len(records)} rows saved OK")


# ── Save reservation rows ─────────────────────────────────────────────────────

def load_reservations(rows):
    """
    Save stay rows to the database.
    If the same (reservation_id + stay_date) already exists, update it.
    Returns (number saved, number of errors).
    """
    if not rows:
        log.warning("load_reservations called with empty list — nothing to save")
        return 0, 0

    conn   = get_db()
    cur    = conn.cursor()
    saved  = 0
    errors = 0

    for row in rows:
        try:
            cur.execute("""
                INSERT INTO reservations_hackathon (
                    reservation_id, arrival_date, departure_date, stay_date,
                    reservation_status, create_datetime, cancellation_datetime,
                    guest_country, is_block, is_walk_in, number_of_spaces,
                    space_type, market_code, channel_code, source_name,
                    rate_plan_code, daily_room_revenue_before_tax,
                    daily_total_revenue_before_tax, nights, adr_room,
                    lead_time, company_name, travel_agent_name
                ) VALUES (
                    %(reservation_id)s, %(arrival_date)s, %(departure_date)s,
                    %(stay_date)s, %(reservation_status)s, %(create_datetime)s,
                    %(cancellation_datetime)s, %(guest_country)s,
                    %(is_block)s, %(is_walk_in)s, %(number_of_spaces)s,
                    %(space_type)s, %(market_code)s, %(channel_code)s,
                    %(source_name)s, %(rate_plan_code)s,
                    %(daily_room_revenue_before_tax)s,
                    %(daily_total_revenue_before_tax)s,
                    %(nights)s, %(adr_room)s, %(lead_time)s,
                    %(company_name)s, %(travel_agent_name)s
                )
                ON CONFLICT (reservation_id, stay_date) DO UPDATE SET
                    reservation_status             = EXCLUDED.reservation_status,
                    cancellation_datetime          = EXCLUDED.cancellation_datetime,
                    number_of_spaces               = EXCLUDED.number_of_spaces,
                    daily_room_revenue_before_tax  = EXCLUDED.daily_room_revenue_before_tax,
                    daily_total_revenue_before_tax = EXCLUDED.daily_total_revenue_before_tax,
                    adr_room                       = EXCLUDED.adr_room
            """, row)
            saved += 1

        except Exception as e:
            conn.rollback()
            errors += 1
            log.error(f"Failed to save {row.get('reservation_id')} / {row.get('stay_date')}: {e}")

    conn.commit()
    conn.close()

    if errors:
        log.warning(f"Saved {saved} rows, {errors} errors")
    else:
        log.debug(f"Saved {saved} rows OK")

    return saved, errors


# ── Verify counts ─────────────────────────────────────────────────────────────

def verify(live_targets):
    """
    Check that the database has the right number of rows.
    live_targets: dict scraped from /verify page e.g. {"total_stay_rows": 534, ...}
    Prints a pass/fail table. Returns True if all checks pass.
    """
    # Map the site's /verify keys to our SQL queries
    checks = [
        ("Total stay rows",     "SELECT COUNT(*) FROM reservations_hackathon",                                                              live_targets.get("total_stay_rows")),
        ("Unique reservations", "SELECT COUNT(DISTINCT reservation_id) FROM reservations_hackathon",                                        live_targets.get("total_reservations")),
        ("Cancelled",           "SELECT COUNT(DISTINCT reservation_id) FROM reservations_hackathon WHERE reservation_status = 'Cancelled'",  live_targets.get("cancelled_reservations")),
        ("Room types",          "SELECT COUNT(*) FROM room_type_lookup",                                                                     3),
        ("Market codes",        "SELECT COUNT(*) FROM market_code_lookup",                                                                   10),
        ("Channel codes",       "SELECT COUNT(*) FROM channel_code_lookup",                                                                  4),
    ]

    log.info("Running verification checks...")
    conn = get_db()
    cur  = conn.cursor()
    all_passed = True

    print(f"\n  {'Check':<22} {'Got':>6}  {'Expected':>8}  Result")
    print(f"  {'-' * 50}")

    for check_name, sql, expected in checks:
        cur.execute(sql)
        got = cur.fetchone()[0]

        if got == expected:
            result = "PASS"
            log.info(f"VERIFY {check_name}: {got} == {expected} — PASS")
        else:
            result = f"FAIL (expected {expected})"
            log.warning(f"VERIFY {check_name}: got {got}, expected {expected} — FAIL")
            all_passed = False

        print(f"  {check_name:<22} {got:>6}  {expected:>8}  {result}")

    print(f"  {'-' * 50}")

    if all_passed:
        log.info("ALL CHECKS PASSED — database is complete!")
    else:
        log.warning("Some checks failed — re-run the ETL to fix missing rows")

    conn.close()
    return all_passed
