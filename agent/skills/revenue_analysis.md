---
name: revenue_analysis
description: >
  Use when the GM asks about revenue on the books, monthly revenue, what is driving
  a specific month, OTB totals, or revenue trends. Covers how to read, interpret,
  and contextualise hotel revenue numbers — not just report them.
---

# Revenue Analysis Skill

## What "on the books" means

Revenue on the books (OTB) is the revenue attached to future reservations that currently
exist in the system. It is NOT what the hotel will actually make — cancellations will
reduce it, and new bookings will add to it before the stay date arrives.

Always state this caveat when reporting OTB numbers.

## How to answer "What revenue is on the books?"

1. Call `get_revenue_by_month` with `revenue_type='total'`.
2. Show the month-by-month table.
3. Highlight the highest and lowest months.
4. Comment on the shape: is it front-loaded? Back-loaded? Flat?
5. Mention which months are still far out (more bookings likely to come) vs. close-in
   (OTB is close to final).

## How to answer "What is driving [month]?"

This is the most common GM question. A weak answer names a number. A strong answer
explains the commercial story behind the number.

Steps:
1. Call `get_revenue_by_month` to size the month.
2. Call `get_segment_mix(month='YYYY-MM')` to see what segments are driving it.
3. Call `get_room_type_performance(month='YYYY-MM')` to see if it's ADR or volume driven.
4. Call `get_group_business(month='YYYY-MM')` to check group contribution.
5. Synthesise: is the month strong because of group blocks? High ADR on Executive rooms?
   OTA volume? A mix?

Key judgments to make:
- A month with high revenue but driven by OTA at a low ADR is fragile — commissions erode
  the net, and last-minute OTA bookings can cancel freely.
- A month with strong corporate/direct business at high ADR is more valuable even if
  room nights are lower.
- A month heavily reliant on one or two group blocks is risky — losing one block hurts badly.

## Revenue fields — use the right one

- `daily_room_revenue_before_tax`: room rate only. Use when discussing ADR or room pricing.
- `daily_total_revenue_before_tax`: room + packages/breakfast. Use for total commercial value.
- For GM briefings, default to `total` revenue — it reflects true commercial value.

## ADR interpretation

ADR = Average Daily Rate = revenue per occupied room per night.

A high ADR with low room nights = pricing power but low volume. Could mean the hotel is
capturing quality but leaving rooms unsold. Ask: is this close-in and rooms are filling?
Or is it a chronic undersell problem?

A low ADR with high room nights = high occupancy but poor rate. Could mean too much
promotional / OTA business at discounted rates. Commissions make this worse.

The sweet spot is high ADR + high room nights = strong RevPAR.

## Answering style

Don't just read back the table. Say something like:

> "July is shaping up well — €X on the books across Y room nights. The story here is [Z].
> The risk is [W]. My recommendation: [action]."
