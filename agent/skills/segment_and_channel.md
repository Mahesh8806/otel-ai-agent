---
name: segment_and_channel
description: >
  Use when the GM asks about OTA dependency, channel mix, segment mix, whether we are
  too dependent on one channel or segment, direct vs indirect split, or corporate vs leisure.
  Covers how to interpret segment and channel concentration and what to do about it.
---

# Segment & Channel Analysis Skill

## The segments in this dataset

| Code  | Name                      | Macro Group   | What it means commercially                                    |
|-------|---------------------------|---------------|----------------------------------------------------------------|
| OTA   | Online Travel Agency      | Retail        | Booking.com, Expedia. High volume, 15-20% commission cost.    |
| BAR   | Best Available Retail     | Retail        | Direct flexible rate. Low cost of sale. Cancellable.           |
| PROM  | Promotional Retail        | Retail        | Direct promo/member rates. Lower rate but also lower cost.     |
| FIT   | Free Independent Traveller| Leisure       | Independent leisure, often direct or via travel agent.         |
| CSR   | Corporate Negotiated      | Corporate     | Named account, negotiated rate. Loyal, reliable, low cancel.   |
| CNR   | Corporate Room Nights     | Corporate     | Corporate via agency. Slightly higher distribution cost.       |
| CNI   | Conference/Incentive Group| MICE          | Group blocks for meetings. High room nights, contracted.       |
| CGR   | Corporate Group           | MICE          | Corporate group blocks. Like CNI but smaller/internal.         |
| EVEN  | Event Demand              | MICE          | Demand tied to a citywide event. Often rate-driven.            |
| SMERF | SMERF Group              | Leisure Group | Social/military/religious/fraternal groups. Price sensitive.   |

## Are we too dependent on OTA?

This is one of the most common GM questions. Here is how to answer it well:

1. Call `get_channel_mix()` to get the WEB (OTA) share of room nights.
2. Call `get_segment_mix(group_by='macro_group')` to see Retail vs Corporate vs MICE.
3. Call `get_segment_mix()` to see the OTA market code specifically.

**Thresholds to use as judgment:**
- OTA room night share > 40%: elevated. Commission drag is real. Flag it.
- OTA room night share > 55%: high risk. The hotel is heavily intermediary-dependent.
- OTA share falling YoY: positive trend (if you have STLY data to compare).

**What high OTA dependency means:**
- Higher distribution costs (15-20% commission per booking)
- Less loyalty — OTA guests book the cheapest option next time, not the hotel
- Rate visibility on OTA platforms makes it hard to yield-manage without being visible
- Cancellation risk is higher — OTA bookings often have free cancellation policies

**What to recommend when OTA is too high:**
- Push direct booking incentives (loyalty points, F&B discounts, guaranteed best rate)
- Grow corporate accounts — they have lower acquisition cost and higher loyalty
- Invest in direct web channel (SEO, meta-search direct bidding)
- Review whether BAR/PROM rates are being undercut by OTA rates (rate parity issue)

## Direct vs Indirect

| Channel Group | Codes     | Cost of Sale  | Quality           |
|---------------|-----------|---------------|-------------------|
| Digital (OTA) | WEB       | High (15-20%) | Variable          |
| Direct        | REC       | Low (~3-5%)   | Higher loyalty    |
| Offline       | EMA, WAL  | Medium        | Often contracted  |

Direct (REC) is the most valuable channel for the hotel. Walk-in (WAL) can be high-rate
if occupancy is already high (gate rate).

## Segment concentration risk

If one or two MICE segments (CNI, CGR, EVEN, SMERF) account for > 40% of room nights,
losing a single group block would materially hurt occupancy. Flag this.

Corporate (CSR/CNR) is the most stable segment — low cancel rate, predictable.
Group (MICE) is high volume but binary: they show up or they cancel the whole block.

## Answering "Are we too dependent on OTA?"

A strong answer:
> "OTA accounts for X% of room nights on the books. This is [above/below] the 40% caution
> threshold. The commercial implication is approximately €Y in commission cost.
> To reduce this, the priority should be [specific action]. Our direct channel (REC) is
> currently at Z% — growing this to W% would save approximately €[amount] in distribution
> cost and improve guest retention."
