"""
Revenue Manager Agent — Tool Layer

All business rules are enforced HERE, not left to the LLM:
  - Correct grain: rows vs reservations vs room_nights
  - Cancellation exclusion by default
  - Right date field (stay_date vs create_datetime)
  - Right revenue field (room vs total)
  - All joins to lookup tables done here

Tools the agent can call:
  get_revenue_by_month        - OTB revenue breakdown by month
  get_segment_mix             - market segment / macro_group analysis
  get_channel_mix             - channel analysis (OTA concentration risk)
  get_room_type_performance   - ADR and revenue by room type
  get_cancellations           - cancellation analysis by period
  get_pickup_last_n_days      - new bookings in the last N days
  get_group_business          - group block analysis
  get_top_companies           - top corporate accounts by revenue
  get_concentration_risk      - are we too dependent on a few big bookings?
  run_safe_sql                - escape hatch for one-off analytical queries
                                (read-only SELECT only, no DDL/DML)
"""

import os
from typing import Optional
import psycopg2
import psycopg2.extras
from langchain_core.tools import tool

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon@localhost:5432/hotel_hackathon"
)


def _conn():
    return psycopg2.connect(DB_URL)


def _q(sql: str, params=None) -> list[dict]:
    """Run a query and return list of dicts."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]


# ── Tool 1: Revenue on the books by month ────────────────────────────────────

@tool
def get_revenue_by_month(
    revenue_type: str = "total",
    include_cancelled: bool = False,
    year: Optional[int] = None,
) -> str:
    """
    Returns revenue on the books grouped by stay month.

    Args:
        revenue_type: 'room' for room revenue only, 'total' for all revenue
                      including packages/breakfast (default: 'total')
        include_cancelled: include cancelled reservations (default: False)
        year: filter to a specific year (default: all years in dataset)

    Returns a table of: month, room_nights, revenue, unique_reservations, avg_adr
    """
    rev_col = (
        "daily_room_revenue_before_tax"
        if revenue_type == "room"
        else "daily_total_revenue_before_tax"
    )

    filters = [] if include_cancelled else ["reservation_status != 'Cancelled'"]
    if year:
        filters.append(f"EXTRACT(YEAR FROM stay_date) = {int(year)}")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = _q(f"""
        SELECT
            TO_CHAR(stay_date, 'YYYY-MM') AS month,
            SUM(number_of_spaces)         AS room_nights,
            SUM({rev_col})                AS revenue,
            COUNT(DISTINCT reservation_id) AS reservations,
            ROUND(SUM({rev_col}) / NULLIF(SUM(number_of_spaces), 0), 2) AS adr
        FROM reservations_hackathon
        {where}
        GROUP BY TO_CHAR(stay_date, 'YYYY-MM')
        ORDER BY month
    """)

    if not rows:
        return "No data found for the requested period."

    lines = [f"Revenue on the books by month ({revenue_type} revenue, "
             f"{'incl.' if include_cancelled else 'excl.'} cancellations):"]
    lines.append(f"{'Month':<10} {'Room Nights':>12} {'Revenue (€)':>14} {'Reservations':>13} {'ADR':>8}")
    lines.append("-" * 62)
    total_rn = total_rev = 0
    for r in rows:
        lines.append(
            f"{r['month']:<10} {int(r['room_nights'] or 0):>12,} "
            f"{float(r['revenue'] or 0):>14,.2f} "
            f"{int(r['reservations'] or 0):>13,} "
            f"{float(r['adr'] or 0):>8.2f}"
        )
        total_rn += int(r['room_nights'] or 0)
        total_rev += float(r['revenue'] or 0)

    lines.append("-" * 62)
    lines.append(f"{'TOTAL':<10} {total_rn:>12,} {total_rev:>14,.2f}")
    return "\n".join(lines)


# ── Tool 2: Segment mix ──────────────────────────────────────────────────────

@tool
def get_segment_mix(
    month: Optional[str] = None,
    group_by: str = "market_code",
    metric: str = "room_nights",
) -> str:
    """
    Returns business mix broken down by market segment or macro group.

    Args:
        month: filter to a specific month like '2026-07' (default: all future)
        group_by: 'market_code' (detailed) or 'macro_group' (Retail/Corporate/MICE/Leisure)
        metric: 'room_nights', 'revenue', or 'reservations'

    Returns segment breakdown with share % for quick concentration analysis.
    """
    if group_by == "macro_group":
        dim = "m.macro_group"
        dim_label = "macro_group"
    else:
        dim = "r.market_code"
        dim_label = "market_code"

    metric_col = {
        "room_nights": "SUM(r.number_of_spaces)",
        "revenue": "SUM(r.daily_total_revenue_before_tax)",
        "reservations": "COUNT(DISTINCT r.reservation_id)",
    }.get(metric, "SUM(r.number_of_spaces)")

    date_filter = ""
    if month:
        date_filter = f"AND TO_CHAR(r.stay_date, 'YYYY-MM') = '{month}'"

    rows = _q(f"""
        WITH base AS (
            SELECT
                {dim} AS segment,
                {metric_col} AS value
            FROM reservations_hackathon r
            JOIN market_code_lookup m ON r.market_code = m.market_code
            WHERE r.reservation_status != 'Cancelled'
            {date_filter}
            GROUP BY {dim}
        ),
        total AS (SELECT SUM(value) AS grand_total FROM base)
        SELECT
            b.segment,
            b.value,
            ROUND(100.0 * b.value / NULLIF(t.grand_total, 0), 1) AS share_pct
        FROM base b, total t
        ORDER BY b.value DESC
    """)

    if not rows:
        return "No data found."

    period = f" for {month}" if month else " (all future stays)"
    lines = [f"Segment mix by {metric}{period}:"]
    lines.append(f"{'Segment':<25} {'Value':>12} {'Share %':>9}")
    lines.append("-" * 48)
    for r in rows:
        lines.append(
            f"{str(r['segment']):<25} {float(r['value'] or 0):>12,.1f} "
            f"{float(r['share_pct'] or 0):>8.1f}%"
        )

    # OTA concentration warning
    ota_row = next((r for r in rows if r['segment'] == 'OTA'), None)
    if ota_row and float(ota_row['share_pct'] or 0) > 40:
        lines.append(
            f"\n⚠ OTA share is {float(ota_row['share_pct']):.1f}% — "
            "above the 40% caution threshold. Consider direct channel push."
        )

    return "\n".join(lines)


# ── Tool 3: Channel mix ──────────────────────────────────────────────────────

@tool
def get_channel_mix(month: Optional[str] = None) -> str:
    """
    Returns booking channel breakdown: WEB (OTA), REC (Direct), EMA (Offline), WAL (Walk-in).
    Shows room nights, revenue, and share % per channel and channel group.

    Args:
        month: filter to a specific month like '2026-07' (default: all future stays)
    """
    date_filter = ""
    if month:
        date_filter = f"AND TO_CHAR(r.stay_date, 'YYYY-MM') = '{month}'"

    rows = _q(f"""
        WITH base AS (
            SELECT
                c.channel_group,
                c.channel_name,
                r.channel_code,
                SUM(r.number_of_spaces) AS room_nights,
                SUM(r.daily_total_revenue_before_tax) AS revenue,
                COUNT(DISTINCT r.reservation_id) AS reservations
            FROM reservations_hackathon r
            JOIN channel_code_lookup c ON r.channel_code = c.channel_code
            WHERE r.reservation_status != 'Cancelled'
            {date_filter}
            GROUP BY c.channel_group, c.channel_name, r.channel_code
        ),
        total AS (SELECT SUM(room_nights) grand_total FROM base)
        SELECT
            b.*,
            ROUND(100.0 * b.room_nights / NULLIF(t.grand_total, 0), 1) AS share_pct
        FROM base b, total t
        ORDER BY b.room_nights DESC
    """)

    if not rows:
        return "No data found."

    period = f" for {month}" if month else " (all future stays)"
    lines = [f"Channel mix{period}:"]
    lines.append(
        f"{'Channel':<35} {'Room Nights':>12} {'Revenue':>12} {'Share %':>9}"
    )
    lines.append("-" * 72)
    for r in rows:
        lines.append(
            f"{r['channel_name']:<35} {int(r['room_nights'] or 0):>12,} "
            f"{float(r['revenue'] or 0):>12,.0f} "
            f"{float(r['share_pct'] or 0):>8.1f}%"
        )

    # Flag OTA dependency
    web_rows = [r for r in rows if r['channel_code'] == 'WEB']
    if web_rows:
        web_share = float(web_rows[0]['share_pct'] or 0)
        if web_share > 40:
            lines.append(
                f"\n⚠ Web/OTA channel is {web_share:.1f}% of room nights. "
                "High OTA dependency = high commission cost."
            )

    return "\n".join(lines)


# ── Tool 4: Room type performance ────────────────────────────────────────────

@tool
def get_room_type_performance(month: Optional[str] = None) -> str:
    """
    Returns ADR, room nights, revenue, and occupancy context by room type.
    Also shows supply context (how many rooms of each type exist).

    Args:
        month: filter to a specific month (default: all future stays)
    """
    date_filter = ""
    if month:
        date_filter = f"AND TO_CHAR(r.stay_date, 'YYYY-MM') = '{month}'"

    rows = _q(f"""
        SELECT
            rt.display_name,
            rt.space_type,
            rt.room_class,
            rt.number_of_rooms AS total_rooms_supply,
            SUM(r.number_of_spaces) AS room_nights_otb,
            SUM(r.daily_room_revenue_before_tax) AS room_revenue,
            ROUND(
                SUM(r.daily_room_revenue_before_tax) / NULLIF(SUM(r.number_of_spaces), 0),
                2
            ) AS adr
        FROM reservations_hackathon r
        JOIN room_type_lookup rt ON r.space_type = rt.space_type
        WHERE r.reservation_status != 'Cancelled'
        {date_filter}
        GROUP BY rt.display_name, rt.space_type, rt.room_class, rt.number_of_rooms
        ORDER BY adr DESC
    """)

    if not rows:
        return "No data found."

    period = f" for {month}" if month else " (all future stays)"
    lines = [f"Room type performance{period}:"]
    lines.append(
        f"{'Room Type':<22} {'Class':<12} {'Supply':>8} "
        f"{'RN OTB':>8} {'ADR':>8} {'Revenue':>12}"
    )
    lines.append("-" * 75)
    for r in rows:
        lines.append(
            f"{r['display_name']:<22} {r['room_class']:<12} "
            f"{r['total_rooms_supply']:>8} "
            f"{int(r['room_nights_otb'] or 0):>8,} "
            f"{float(r['adr'] or 0):>8.2f} "
            f"{float(r['room_revenue'] or 0):>12,.2f}"
        )
    return "\n".join(lines)


# ── Tool 5: Cancellations ────────────────────────────────────────────────────

@tool
def get_cancellations(
    month: Optional[str] = None,
    breakdown_by: str = "market_code",
) -> str:
    """
    Cancellation analysis: count, room nights lost, revenue at risk.

    Args:
        month: arrival month to analyse (e.g. '2026-07'). Default: all.
        breakdown_by: 'market_code', 'channel_code', or 'month'
    """
    dim_map = {
        "market_code": "r.market_code",
        "channel_code": "r.channel_code",
        "month": "TO_CHAR(r.arrival_date, 'YYYY-MM')",
    }
    dim = dim_map.get(breakdown_by, "r.market_code")
    dim_label = breakdown_by

    date_filter = ""
    if month:
        date_filter = f"AND TO_CHAR(r.arrival_date, 'YYYY-MM') = '{month}'"

    rows = _q(f"""
        SELECT
            {dim} AS dimension,
            COUNT(DISTINCT r.reservation_id) AS cancelled_reservations,
            SUM(r.number_of_spaces) AS room_nights_lost,
            SUM(r.daily_total_revenue_before_tax) AS revenue_at_risk
        FROM reservations_hackathon r
        WHERE r.reservation_status = 'Cancelled'
        {date_filter}
        GROUP BY {dim}
        ORDER BY cancelled_reservations DESC
    """)

    # Also get totals for both cancelled and reserved to show cancel rate
    total_rows = _q(f"""
        SELECT
            r.reservation_status,
            COUNT(DISTINCT r.reservation_id) AS reservations
        FROM reservations_hackathon r
        {('WHERE ' + date_filter[4:]) if date_filter else ''}
        GROUP BY r.reservation_status
    """)

    total_active = sum(
        r['reservations'] for r in total_rows if r['reservation_status'] != 'Cancelled'
    )
    total_cancelled = sum(
        r['reservations'] for r in total_rows if r['reservation_status'] == 'Cancelled'
    )
    cancel_rate = (
        100.0 * total_cancelled / (total_active + total_cancelled)
        if (total_active + total_cancelled) > 0 else 0
    )

    period = f" (arrival month: {month})" if month else ""
    lines = [f"Cancellation analysis{period}:"]
    lines.append(
        f"Overall: {total_cancelled} cancellations out of "
        f"{total_active + total_cancelled} total — "
        f"cancel rate {cancel_rate:.1f}%"
    )
    lines.append("")
    if rows:
        lines.append(
            f"{'By ' + dim_label:<20} {'Cancelled':>12} {'RN Lost':>10} {'Rev at Risk':>14}"
        )
        lines.append("-" * 58)
        for r in rows:
            lines.append(
                f"{str(r['dimension']):<20} {int(r['cancelled_reservations']):>12} "
                f"{int(r['room_nights_lost'] or 0):>10,} "
                f"{float(r['revenue_at_risk'] or 0):>14,.2f}"
            )

    return "\n".join(lines)


# ── Tool 6: Pickup (new bookings last N days) ────────────────────────────────

@tool
def get_pickup_last_n_days(days: int = 7) -> str:
    """
    Pickup report: reservations created in the last N days for future stay dates.
    This is the core 'what changed recently?' question.

    Args:
        days: look-back window in days (default: 7)
    """
    rows = _q("""
        SELECT
            TO_CHAR(stay_date, 'YYYY-MM') AS stay_month,
            COUNT(DISTINCT reservation_id) AS new_reservations,
            SUM(number_of_spaces) AS room_nights_picked_up,
            SUM(daily_total_revenue_before_tax) AS revenue_picked_up,
            ROUND(
                SUM(daily_total_revenue_before_tax) / NULLIF(SUM(number_of_spaces), 0),
                2
            ) AS adr
        FROM reservations_hackathon
        WHERE
            reservation_status != 'Cancelled'
            AND create_datetime >= NOW() - (%(days)s || ' days')::interval
            AND stay_date >= CURRENT_DATE
        GROUP BY TO_CHAR(stay_date, 'YYYY-MM')
        ORDER BY stay_month
    """, {"days": days})

    # Also get cancellations in the same window
    canc_rows = _q("""
        SELECT COUNT(DISTINCT reservation_id) AS cancelled
        FROM reservations_hackathon
        WHERE
            reservation_status = 'Cancelled'
            AND cancellation_datetime >= NOW() - (%(days)s || ' days')::interval
    """, {"days": days})

    lines = [f"Pickup report — last {days} days (new bookings for future stays):"]

    if not rows:
        lines.append("  No new bookings picked up in this window.")
    else:
        lines.append(
            f"{'Stay Month':<12} {'New Res':>10} {'Room Nights':>12} "
            f"{'Revenue':>12} {'ADR':>8}"
        )
        lines.append("-" * 58)
        total_rn = total_rev = total_res = 0
        for r in rows:
            lines.append(
                f"{r['stay_month']:<12} {int(r['new_reservations']):>10} "
                f"{int(r['room_nights_picked_up'] or 0):>12,} "
                f"{float(r['revenue_picked_up'] or 0):>12,.2f} "
                f"{float(r['adr'] or 0):>8.2f}"
            )
            total_rn += int(r['room_nights_picked_up'] or 0)
            total_rev += float(r['revenue_picked_up'] or 0)
            total_res += int(r['new_reservations'])
        lines.append("-" * 58)
        lines.append(
            f"{'TOTAL':<12} {total_res:>10} {total_rn:>12,} {total_rev:>12,.2f}"
        )

    cancelled_count = int(canc_rows[0]['cancelled']) if canc_rows else 0
    lines.append(
        f"\nCancellations in same {days}-day window: {cancelled_count}"
    )

    return "\n".join(lines)


# ── Tool 7: Group business ───────────────────────────────────────────────────

@tool
def get_group_business(month: Optional[str] = None) -> str:
    """
    Group business analysis: blocks, event demand, MICE segments.
    Shows group vs transient split.

    Args:
        month: filter to a specific stay month (default: all future)
    """
    date_filter = ""
    if month:
        date_filter = f"AND TO_CHAR(r.stay_date, 'YYYY-MM') = '{month}'"

    rows = _q(f"""
        SELECT
            CASE
                WHEN m.macro_group IN ('MICE', 'Leisure Group') THEN 'Group'
                ELSE 'Transient'
            END AS business_type,
            m.macro_group,
            r.market_code,
            m.market_name,
            COUNT(DISTINCT r.reservation_id) AS reservations,
            SUM(r.number_of_spaces) AS room_nights,
            SUM(r.daily_total_revenue_before_tax) AS revenue,
            ROUND(
                SUM(r.daily_total_revenue_before_tax) / NULLIF(SUM(r.number_of_spaces), 0),
                2
            ) AS adr
        FROM reservations_hackathon r
        JOIN market_code_lookup m ON r.market_code = m.market_code
        WHERE r.reservation_status != 'Cancelled'
        {date_filter}
        GROUP BY business_type, m.macro_group, r.market_code, m.market_name
        ORDER BY business_type, room_nights DESC
    """)

    if not rows:
        return "No data found."

    period = f" for {month}" if month else " (all future stays)"
    lines = [f"Group vs Transient breakdown{period}:"]

    # Summary totals
    group_rn = sum(int(r['room_nights'] or 0) for r in rows if r['business_type'] == 'Group')
    trans_rn = sum(int(r['room_nights'] or 0) for r in rows if r['business_type'] == 'Transient')
    total_rn = group_rn + trans_rn
    if total_rn > 0:
        lines.append(
            f"  Group: {group_rn:,} room nights ({100*group_rn/total_rn:.1f}%) | "
            f"Transient: {trans_rn:,} ({100*trans_rn/total_rn:.1f}%)"
        )
        lines.append("")

    lines.append(
        f"{'Type':<12} {'Segment':<30} {'Res':>6} {'RN':>8} {'ADR':>8} {'Revenue':>12}"
    )
    lines.append("-" * 80)
    for r in rows:
        lines.append(
            f"{r['business_type']:<12} {r['market_name']:<30} "
            f"{int(r['reservations']):>6} {int(r['room_nights'] or 0):>8,} "
            f"{float(r['adr'] or 0):>8.2f} {float(r['revenue'] or 0):>12,.2f}"
        )

    return "\n".join(lines)


# ── Tool 8: Top companies ────────────────────────────────────────────────────

@tool
def get_top_companies(limit: int = 10) -> str:
    """
    Top corporate accounts by revenue on the books.
    Useful for understanding corporate concentration risk.

    Args:
        limit: number of companies to show (default: 10)
    """
    rows = _q("""
        SELECT
            COALESCE(company_name, '(No company / leisure)') AS company,
            COUNT(DISTINCT reservation_id) AS reservations,
            SUM(number_of_spaces) AS room_nights,
            SUM(daily_total_revenue_before_tax) AS revenue,
            ROUND(
                SUM(daily_total_revenue_before_tax) / NULLIF(SUM(number_of_spaces), 0),
                2
            ) AS adr
        FROM reservations_hackathon
        WHERE
            reservation_status != 'Cancelled'
            AND company_name IS NOT NULL
        GROUP BY company_name
        ORDER BY revenue DESC
        LIMIT %(limit)s
    """, {"limit": limit})

    if not rows:
        return "No company data found."

    lines = [f"Top {limit} companies by revenue on the books:"]
    lines.append(
        f"{'Company':<35} {'Res':>5} {'RN':>8} {'ADR':>8} {'Revenue':>12}"
    )
    lines.append("-" * 72)
    for r in rows:
        lines.append(
            f"{r['company'][:35]:<35} {int(r['reservations']):>5} "
            f"{int(r['room_nights'] or 0):>8,} "
            f"{float(r['adr'] or 0):>8.2f} "
            f"{float(r['revenue'] or 0):>12,.2f}"
        )
    return "\n".join(lines)


# ── Tool 9: Concentration risk ───────────────────────────────────────────────

@tool
def get_concentration_risk() -> str:
    """
    Checks whether the hotel's revenue is dangerously concentrated in a few
    large reservations (group blocks). Returns the top bookings by revenue
    and what % of total OTB they represent.
    """
    top_rows = _q("""
        SELECT
            reservation_id,
            MIN(arrival_date)::text AS arrival,
            MAX(departure_date)::text AS departure,
            market_code,
            SUM(number_of_spaces) AS room_nights,
            SUM(daily_total_revenue_before_tax) AS revenue
        FROM reservations_hackathon
        WHERE reservation_status != 'Cancelled'
        GROUP BY reservation_id, market_code
        ORDER BY revenue DESC
        LIMIT 10
    """)

    total_row = _q("""
        SELECT SUM(daily_total_revenue_before_tax) AS total_revenue
        FROM reservations_hackathon
        WHERE reservation_status != 'Cancelled'
    """)
    total_rev = float(total_row[0]['total_revenue'] or 0) if total_row else 0

    top5_rev = sum(float(r['revenue'] or 0) for r in top_rows[:5])
    top5_pct = 100.0 * top5_rev / total_rev if total_rev else 0

    lines = ["Concentration risk — top 10 reservations by revenue:"]
    lines.append(
        f"Top 5 reservations account for {top5_pct:.1f}% of total OTB revenue"
    )
    if top5_pct > 30:
        lines.append(
            "⚠ HIGH CONCENTRATION: losing one of these blocks would "
            "materially hurt the month."
        )
    lines.append("")
    lines.append(
        f"{'Res ID':<10} {'Arrival':<12} {'Depart':<12} {'Market':<8} "
        f"{'RN':>6} {'Revenue':>12} {'Share %':>8}"
    )
    lines.append("-" * 72)
    for r in top_rows:
        share = 100.0 * float(r['revenue'] or 0) / total_rev if total_rev else 0
        lines.append(
            f"{r['reservation_id']:<10} {str(r['arrival']):<12} "
            f"{str(r['departure']):<12} {r['market_code']:<8} "
            f"{int(r['room_nights'] or 0):>6,} "
            f"{float(r['revenue'] or 0):>12,.2f} "
            f"{share:>7.1f}%"
        )
    return "\n".join(lines)


# ── Tool 10: Safe SQL escape hatch ───────────────────────────────────────────

@tool
def run_safe_sql(query: str) -> str:
    """
    Run a read-only SQL SELECT query against the hotel database.
    Use this for one-off analytical questions not covered by the other tools.
    ONLY SELECT statements are allowed — no INSERT, UPDATE, DELETE, DROP, etc.

    Tables available:
      - reservations_hackathon (main fact table — one row per reservation x stay_date)
      - room_type_lookup
      - market_code_lookup
      - channel_code_lookup

    IMPORTANT business rules to follow in your SQL:
      - Filter reservation_status != 'Cancelled' unless you specifically need cancellations
      - For room nights: SUM(number_of_spaces), not COUNT(*)
      - For revenue: use daily_total_revenue_before_tax for total, daily_room_revenue_before_tax for room only
      - Use stay_date for when guests stay, create_datetime for when they booked
    """
    # Block anything that isn't a SELECT
    stripped = query.strip().upper()
    if not stripped.startswith("SELECT"):
        return "ERROR: Only SELECT queries are allowed."
    for dangerous in ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"):
        if dangerous in stripped:
            return f"ERROR: {dangerous} statements are not allowed."

    try:
        rows = _q(query)
        if not rows:
            return "Query returned no results."
        # Format as a simple table
        headers = list(rows[0].keys())
        lines = [" | ".join(str(h) for h in headers)]
        lines.append("-" * len(lines[0]))
        for row in rows[:100]:  # cap at 100 rows
            lines.append(" | ".join(str(row[h]) for h in headers))
        if len(rows) > 100:
            lines.append(f"... ({len(rows) - 100} more rows truncated)")
        return "\n".join(lines)
    except Exception as e:
        return f"SQL error: {e}"


# ── Export all tools ─────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_revenue_by_month,
    get_segment_mix,
    get_channel_mix,
    get_room_type_performance,
    get_cancellations,
    get_pickup_last_n_days,
    get_group_business,
    get_top_companies,
    get_concentration_risk,
    run_safe_sql,
]
