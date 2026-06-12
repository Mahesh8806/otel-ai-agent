"""
models.py — Shared settings and constants used by all ETL files.
"""

# The website we are scraping
WEBSITE = "https://otel-hackathon-data-site.vercel.app"

# The website uses these values to mean "nothing / unknown"
# We will turn these into NULL in the database
NULL_VALUES = {"", "?", "-", "N/A", "—", "–", "null", "none"}

# These are the field names on each reservation detail page
RESERVATION_FIELDS = [
    "arrival_date", "departure_date", "nights", "reservation_status",
    "create_datetime", "cancellation_datetime", "guest_country",
    "is_block", "is_walk_in", "number_of_spaces", "space_type",
    "market_code", "channel_code", "source_name", "rate_plan_code",
    "adr_room", "lead_time", "company_name", "travel_agent_name",
]
