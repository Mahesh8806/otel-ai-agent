---
name: pickup_and_pace
description: >
  Use when the GM asks what changed recently, pickup in the last 7 days, booking pace,
  whether we are ahead or behind on bookings, or what is happening with future business.
  Covers how to interpret pickup data and booking pace signals.
---

# Pickup & Booking Pace Skill

## What "pickup" means

Pickup = new reservations created in the last N days for future stay dates.

It answers: "Is new business coming in fast enough for the months ahead?"

Pickup is measured on **booking date** (`create_datetime`), not stay date.
Stay date tells you when the guest will be there; booking date tells you when demand arrived.

## How to answer "What changed in the last 7 days?"

1. Call `get_pickup_last_n_days(days=7)`.
2. Show which stay months got the most new room nights.
3. Note how many cancellations happened in the same window.
4. Calculate net pickup = new room nights - room nights lost to cancellations.
5. Comment on the pace: is it strong for close-in months? Slow for far-out months?

## How to interpret pace signals

**Close-in months (arrival within 30 days):**
- Strong pickup with few rooms left = near-full, hold rate / increase rate
- Slow pickup with many rooms available = problem — consider promotions or rate drops
- High cancellations close-in = re-inventory risk, need to fill quickly

**Far-out months (arrival 60-120 days away):**
- Slow pickup is normal — most bookings come in the last 30-60 days for leisure
- Corporate/group business books further out, so early group blocks are a positive signal
- If far-out pickup is unusually strong, it may signal an event or group that is driving demand

## Lead time interpretation

Lead time = days between booking creation and arrival date.

- OTA leisure: typically 30-90 days
- Corporate: 7-30 days (last-minute business)
- Group/MICE: 90-180 days (long lead planning)
- Walk-in: 0 days

If average lead time is falling, the hotel is increasingly a last-minute option — this
is risky because last-minute demand is less predictable and harder to price.

## The key judgment: net pickup vs gross pickup

Don't just report gross new bookings. Subtract cancellations to get net pickup:

> Net pickup = new room nights booked - room nights cancelled

If gross pickup is +100 RN but cancellations are -80 RN, the hotel is barely moving.
This is a red flag, especially for close-in months.

## Answering "What changed in the last 7 days?"

A strong answer:
> "In the last 7 days, we picked up X room nights for future stays, concentrated in [months].
> We also had Y cancellations, giving a net pickup of Z room nights. The pace for [busy month]
> is [strong/weak]: we are [ahead/behind] where I would expect to be at this point.
> The main driver of pickup is [segment]. [Recommendation]."
