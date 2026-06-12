"""
transform.py — Step 2: Clean and format the raw scraped data.
Converts raw strings into proper Python types (int, float, bool, None).
"""

import logging
from models import NULL_VALUES

log = logging.getLogger("transform")


# ── Helper functions ──────────────────────────────────────────────────────────

def to_str(value):
    """Return a clean string, or None if the value means 'nothing'."""
    if value is None:
        return None
    v = str(value).strip()
    if v.lower() in NULL_VALUES:
        return None
    return v


def to_int(value):
    """Convert to integer. Returns None if it fails."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def to_float(value):
    """Convert to float. Handles commas like 1,234.56. Returns None if it fails."""
    try:
        clean = str(value).strip().replace(",", "")
        return float(clean)
    except (TypeError, ValueError):
        return None


def to_bool(value):
    """Convert 'true', 'yes', '1' to True. Everything else is False."""
    return str(value).strip().lower() in ("true", "yes", "1", "t")


# ── Transform lookup tables ───────────────────────────────────────────────────

def transform_room_types(raw_list):
    log.info(f"Transforming {len(raw_list)} room type rows...")
    result = []
    for r in raw_list:
        result.append({
            "space_type":      r["space_type"],
            "room_class":      r["room_class"],
            "display_name":    r["display_name"],
            "number_of_rooms": to_int(r["number_of_rooms"]),
        })
    log.info(f"Room types ready: {len(result)} rows")
    return result


def transform_market_codes(raw_list):
    log.info(f"Transforming {len(raw_list)} market code rows...")
    result = []
    for r in raw_list:
        result.append({
            "market_code": r["market_code"],
            "market_name": r["market_name"],
            "macro_group": r["macro_group"],
            "description": r.get("description", ""),
        })
    log.info(f"Market codes ready: {len(result)} rows")
    return result


def transform_channel_codes(raw_list):
    log.info(f"Transforming {len(raw_list)} channel code rows...")
    result = []
    for r in raw_list:
        result.append({
            "channel_code":  r["channel_code"],
            "channel_name":  r["channel_name"],
            "channel_group": r["channel_group"],
        })
    log.info(f"Channel codes ready: {len(result)} rows")
    return result


# ── Transform one reservation ─────────────────────────────────────────────────

def transform_reservation(raw):
    """
    Convert one scraped reservation into a list of database rows.

    Rule: one DB row per NIGHT of the stay.
    A 3-night reservation becomes 3 rows, each with a different stay_date.

    Returns a list of clean row dicts ready to save to PostgreSQL.
    """
    fields = raw["fields"]
    rid    = raw["reservation_id"]
    result = []

    log.debug(f"Transforming {rid} — {len(raw['stay_rows'])} nights")

    for stay in raw["stay_rows"]:

        row = {
            "reservation_id":   rid,

            "arrival_date":     to_str(fields.get("arrival_date")),
            "departure_date":   to_str(fields.get("departure_date")),
            "stay_date":        to_str(stay["stay_date"]),

            "reservation_status":    to_str(fields.get("reservation_status")) or "Reserved",
            "create_datetime":       to_str(fields.get("create_datetime")),
            "cancellation_datetime": to_str(fields.get("cancellation_datetime")),

            "guest_country": to_str(fields.get("guest_country")),
            "is_block":      to_bool(fields.get("is_block",   "false")),
            "is_walk_in":    to_bool(fields.get("is_walk_in", "false")),

            "number_of_spaces": to_int(fields.get("number_of_spaces")) or 1,
            "space_type":       to_str(fields.get("space_type")),

            "market_code":    to_str(fields.get("market_code")),
            "channel_code":   to_str(fields.get("channel_code")),
            "source_name":    to_str(fields.get("source_name"))    or "",
            "rate_plan_code": to_str(fields.get("rate_plan_code")) or "",

            "daily_room_revenue_before_tax":  to_float(stay["daily_room_revenue_before_tax"])  or 0.0,
            "daily_total_revenue_before_tax": to_float(stay["daily_total_revenue_before_tax"]) or 0.0,

            "nights":    to_int(fields.get("nights"))    or 1,
            "adr_room":  to_float(fields.get("adr_room")) or 0.0,
            "lead_time": to_int(fields.get("lead_time"))  or 0,

            "company_name":      to_str(fields.get("company_name")),
            "travel_agent_name": to_str(fields.get("travel_agent_name")),
        }

        # Skip this row if any critical field is missing
        required = ["reservation_id", "arrival_date", "departure_date",
                    "stay_date", "space_type", "market_code", "channel_code"]

        missing_fields = [f for f in required if row[f] is None]

        if missing_fields:
            log.warning(f"SKIP {rid} / {stay['stay_date']} — missing fields: {missing_fields}")
            continue

        result.append(row)

    return result
