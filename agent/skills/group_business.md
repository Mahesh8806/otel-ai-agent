---
name: group_business
description: >
  Use when the GM asks about group business, group blocks, how much group we have,
  group vs transient split, MICE contribution, corporate groups, or event demand.
---

# Group Business Skill

## What counts as "group" in this dataset

Group segments (macro groups: MICE and Leisure Group):
- **CNI** — Conference/Incentive Group (meetings, conferences)
- **CGR** — Corporate Group (internal corporate retreats/events)
- **EVEN** — Event Demand (citywide events, sports events linked to hotel)
- **SMERF** — Social/Military/Educational/Religious/Fraternal groups

Transient segments (everything else):
- OTA, BAR, PROM, FIT, CSR, CNR

The `is_block` flag also indicates group-style bookings regardless of segment.

## How to answer "How much group business do we have?"

1. Call `get_group_business()` or `get_group_business(month='YYYY-MM')`.
2. Report the group vs transient split in room nights and revenue.
3. Identify the dominant group segments.
4. Call `get_concentration_risk()` — group business is the biggest source of
   concentration risk (one block = many rooms).

## The group business trade-off

**Why group is good:**
- Fills many rooms in one transaction — reduces complexity
- Usually books far in advance (good for pace certainty)
- Predictable dates and room night commitment
- Can anchor the hotel's occupancy base for a month

**Why group is risky:**
- A single group cancellation can destroy a month's occupancy
- Group rates are typically below transient BAR — you sacrifice rate for volume
- Group business "displaces" transient demand — the rooms blocked for group can't be
  sold individually, even if transient rates would be higher
- SMERF groups are particularly price-sensitive and cancel at higher rates

## Displacement thinking (key concept)

If a group wants 20 rooms for a July weekend at €140/night (below BAR of €180), the hotel
must decide: is it better to take the group at €140 and guarantee 20 rooms, or hold the
rooms for transient at €180 (but risk some rooms going unsold)?

A good revenue manager calculates the "displacement cost" = lost revenue if we take the group
instead of holding for transient. If occupancy is already projected high, reject the group
or negotiate a higher group rate.

## Answering "How much group business do we have?"

A strong answer:
> "Group business accounts for X% of room nights on the books (Y room nights).
> The dominant group segments are [CNI/SMERF/EVEN]. The largest single group block is
> [reservation ID or month], representing Z room nights. 
> At X% group mix, [we have a healthy base / we are over-reliant on group with concentration risk].
> [Recommendation based on the specific numbers]."
