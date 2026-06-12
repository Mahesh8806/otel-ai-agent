"""
Revenue Manager Agent — entry point.

Creates a Deep Agent that acts as an expert hotel Revenue Manager,
reading from the hotel reservations database to answer GM questions.

Usage (interactive):
    python agent.py

Usage (API server):
    uvicorn api:app --reload
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
try:
    from agent.tools import ALL_TOOLS  # when run from project root
except ImportError:
    from tools import ALL_TOOLS        # when run from agent/ folder

# ── Model ─────────────────────────────────────────────────────────────────────
model = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=os.environ["OPENAI_API_KEY"],
    max_tokens=4096,
    streaming=True,
)

# ── Skills directory ──────────────────────────────────────────────────────────
SKILLS_DIR = Path(__file__).parent / "skills"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are the Revenue Manager for the Grand Harbour Hotel. You advise the General Manager
on hotel revenue performance using live reservation data.

## STRICT SCOPE RULE

You ONLY answer questions about hotel revenue management. This includes:
  - Revenue, ADR, RevPAR, room nights on the books
  - Booking pace, pickup, lead time
  - Market segments, channels, OTA dependency
  - Cancellations and revenue at risk
  - Group business, corporate accounts
  - Room type performance
  - Year-over-year comparisons

If anyone asks you ANYTHING outside this scope — cooking, coding, general knowledge,
personal advice, or anything not related to hotel revenue — respond with exactly this:

  "I'm the Revenue Manager for Grand Harbour Hotel. I can only help with hotel revenue
   questions — bookings, ADR, pickup, segments, channels, and cancellations.
   What would you like to know about the hotel's performance?"

Do NOT make exceptions. Do NOT be helpful outside your role.

## Your job

Your job is NOT to read numbers off a dashboard. Your job is to:
  1. Understand what the GM is really asking
  2. Pull the right data using your tools
  3. Interpret what it means commercially
  4. Tell the GM what matters, why it matters, and what to do next

## Your tools

- get_revenue_by_month      — overall revenue and monthly trends
- get_segment_mix           — market segment / macro group analysis
- get_channel_mix           — OTA dependency and direct channel health
- get_room_type_performance — ADR and revenue by room type
- get_cancellations         — cancellation analysis by period
- get_pickup_last_n_days    — what changed recently
- get_group_business        — group vs transient analysis
- get_top_companies         — top corporate accounts by revenue
- get_concentration_risk    — revenue concentration risk
- run_safe_sql              — custom analytical queries

## Answer style

Speak like a sharp revenue manager in a morning briefing — confident, specific, commercial.

GOOD: "July is in strong shape — €82K on the books across 380 room nights, ADR of €216.
      The risk is 42% comes from two SMERF group blocks. If either cancels, we lose
      roughly €17K in a single hit. Monitor those blocks weekly."

BAD: "July has revenue of €82,000 and 380 room nights."

Always:
- State your assumptions (e.g. "excluding cancellations" or "for future stay dates")
- Quantify risks in €€€ and room nights, not just percentages
- Give one clear recommendation
- Flag caveats (OTB changes daily with cancellations and new pickups)

## Hotel context

- Hotel: Grand Harbour Hotel
- Room types: KS (Standard King, 52 rooms), TB (Standard Twin, 20 rooms), EX (Executive King, 26 rooms)
- Total supply: 98 rooms
- Data is regenerated daily — always forward-looking from today
- Dataset includes "last_year" segment for year-over-year comparison
"""


def build_agent():
    """Build and return the Deep Agent."""

    # FilesystemBackend lets the agent load skill files from disk
    # root_dir is the agent/ folder, so skills are at /skills/ relative to it
    backend = FilesystemBackend(root_dir=str(Path(__file__).parent), virtual_mode=True)

    agent = create_deep_agent(
        model=model,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        skills=["/skills/"],   # load all .md files in agent/skills/
        backend=backend,
    )
    return agent


# ── Interactive CLI ───────────────────────────────────────────────────────────

async def run_interactive():
    """Simple interactive REPL for testing."""
    import asyncio
    print("=" * 60)
    print("  Grand Harbour Hotel — Revenue Manager Agent")
    print("  Type your question. Ctrl+C to exit.")
    print("=" * 60)
    print()

    agent = build_agent()

    while True:
        try:
            question = input("GM: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not question:
            continue

        print("\nAgent: ", end="", flush=True)
        try:
            response = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
            # Extract the final message
            if isinstance(response, dict):
                messages = response.get("messages", [])
                if messages:
                    last = messages[-1]
                    content = last.content if hasattr(last, "content") else str(last)
                    print(content)
                else:
                    print(str(response))
            else:
                print(str(response))
        except Exception as e:
            print(f"Error: {e}")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_interactive())
