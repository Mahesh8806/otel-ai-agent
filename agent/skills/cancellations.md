---
name: cancellations
description: >
  Use when the GM asks about cancellations, how much business was cancelled, cancel rate,
  revenue at risk from cancellations, or which segments cancel the most.
---

# Cancellation Analysis Skill

## How to answer "How much business was cancelled?"

1. Call `get_cancellations()` for an overview.
2. Call `get_cancellations(breakdown_by='market_code')` to see which segments cancel most.
3. Optionally filter by arrival month if the question is period-specific.

## What to look for

**Cancel rate benchmarks (rule of thumb):**
- < 10%: healthy, within normal range
- 10-20%: moderate — monitor but not alarming
- > 20%: elevated — investigate which segments are driving it

**Which segments cancel most:**
- OTA has the highest cancel rate (free cancellation is standard on most OTA rates)
- BAR (flexible direct rates) also cancels freely
- Corporate (CSR/CNR) has very low cancel rates — these are loyal, committed guests
- Group (MICE) cancels less often but when they do, the impact is large (many rooms at once)

## Revenue at risk vs revenue lost

Important distinction:
- **Revenue lost** = cancelled reservations for past stay dates (already gone)
- **Revenue at risk** = cancelled reservations for future stay dates
  — but the rooms can be re-sold, so this is re-inventory opportunity, not guaranteed loss

Always clarify which you are talking about.

## What to recommend when cancel rate is high

1. Check if high cancellations are concentrated in OTA — if so, encourage more non-refundable
   rate variants (ADV, NONREF rate plans) to lock in revenue.
2. If cancellations are close-in (< 14 days), aggressive re-pricing or OTA visibility may help
   re-sell the rooms.
3. If cancellations are in group blocks, the hotel needs to urgently find replacement business.
4. Track pace of cancellations: are they accelerating or stable?

## Answering "How much business was cancelled in [month]?"

A strong answer:
> "In [month], X reservations were cancelled representing Y room nights and €Z in revenue.
> The overall cancel rate was W%. The biggest driver was [segment], which accounted for P%
> of all cancellations. [Those rooms are/are not] close-in, so [re-selling them is
> straightforward/will require rate action]."
