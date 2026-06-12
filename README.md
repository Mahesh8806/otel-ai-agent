# Grand Harbour Hotel — Revenue Manager Agent

An AI-powered Revenue Manager built for the Otel AI Engineer Intern challenge.

Ask it questions like *"What's driving July?"* or *"Are we too dependent on OTA?"* and it answers like a real hotel revenue manager — pulling live data, interpreting it commercially, and giving a clear recommendation.

---

## What it does

- **ETL Pipeline** — scrapes 250 hotel reservations from a live client-rendered website using Playwright, transforms the data, and loads it into PostgreSQL
- **AI Agent** — a LangChain Deep Agent with 10 SQL-backed tools that reads the database and answers revenue questions
- **Streaming Chat UI** — shows the agent thinking in real time: which tools it called, which skills it loaded, and the final answer
- **Login system** — protected with username + password

---

## Project Structure

```
otel-ai-agent/
├── agent/
│   ├── agent.py          # Deep Agent setup
│   ├── api.py            # FastAPI backend (serves UI + /chat + /login)
│   ├── tools.py          # 10 SQL-backed revenue tools
│   ├── skills/           # Expert skill files loaded by the agent
│   │   ├── revenue_analysis.md
│   │   ├── segment_and_channel.md
│   │   ├── pickup_and_pace.md
│   │   ├── cancellations.md
│   │   └── group_business.md
│   └── requirements.txt
├── etl/
│   ├── main.py           # Orchestrates Extract → Transform → Load → Verify
│   ├── extract.py        # Playwright scraping
│   ├── transform.py      # Clean and type-cast raw data
│   ├── load.py           # PostgreSQL upserts + verify
│   └── models.py         # Shared constants
├── ui/
│   └── index.html        # Chat UI (served by FastAPI)
├── schema.sql            # PostgreSQL schema
├── requirements.txt      # Root-level dependencies for deployment
└── Procfile              # For Render/Railway deployment
```

---

## Run Locally

### 1. Prerequisites

- Python 3.11+
- Docker Desktop (for local PostgreSQL)
- An OpenAI API key

### 2. Start the database

```bash
docker-compose up -d
```

This starts PostgreSQL on port `5433`.

### 3. Create the schema

```bash
psql "postgresql://hackathon:hackathon@localhost:5433/hotel_hackathon" -f schema.sql
```

Or paste `schema.sql` into any PostgreSQL client.

### 4. Run the ETL

```bash
cd etl
pip install -r requirements.txt
playwright install chromium
```

Create `etl/.env`:
```
DATABASE_URL=postgresql://hackathon:hackathon@localhost:5433/hotel_hackathon
```

Run the pipeline:
```bash
python main.py
```

Takes ~5-8 minutes to scrape all 250 reservations. At the end, all 6 VERIFY checks should show `PASS`.

To verify without re-running the full ETL:
```bash
python main.py --verify
```

### 5. Start the agent

```bash
cd agent
pip install -r requirements.txt
```

Create `agent/.env`:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://hackathon:hackathon@localhost:5433/hotel_hackathon
LOGIN_USERNAME=otel.reviewer
LOGIN_PASSWORD=FindRevenue!
```

Start the server:
```bash
uvicorn api:app --reload
```

Open **http://localhost:8000** in your browser.

---

## Deploy

### Database — Neon (free)

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the connection string
3. Paste `schema.sql` into the Neon SQL Editor and run it
4. Update `etl/.env` with the Neon URL and run `python main.py`

### Backend — Render (free)

1. Push this repo to GitHub
2. Create a new Web Service at [render.com](https://render.com)
3. Connect your GitHub repo
4. Set:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn agent.api:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:

   | Key | Value |
   |---|---|
   | `OPENAI_API_KEY` | your OpenAI key |
   | `DATABASE_URL` | your Neon connection string |
   | `LOGIN_USERNAME` | `otel.reviewer` |
   | `LOGIN_PASSWORD` | `FindRevenue!` |

6. Deploy — your app will be live at `https://your-app.onrender.com`

**Keep it awake:** Set up a free monitor at [uptimerobot.com](https://uptimerobot.com) to ping `https://your-app.onrender.com/health` every 5 minutes so Render never sleeps.

---

## Agent Tools

| Tool | What it answers |
|---|---|
| `get_revenue_by_month` | OTB revenue, ADR, room nights by month |
| `get_segment_mix` | Market segment breakdown |
| `get_channel_mix` | OTA dependency, direct vs indirect |
| `get_room_type_performance` | ADR and revenue by room type |
| `get_cancellations` | Cancellation rate and revenue at risk |
| `get_pickup_last_n_days` | What changed in the last N days |
| `get_group_business` | Group vs transient analysis |
| `get_top_companies` | Top corporate accounts by revenue |
| `get_concentration_risk` | Revenue concentration risk |
| `run_safe_sql` | Custom analytical queries (SELECT only) |

---

## Example Questions

- What revenue is on the books by month?
- What is driving July?
- Are we too dependent on OTA?
- What changed in the last 7 days?
- How much group business do we have?
- Which room type has the highest ADR?
- How much business was cancelled?
- Is our revenue concentrated in a few large bookings?

---

## Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Playwright (sync) |
| Database | PostgreSQL (Neon hosted) |
| Agent | LangChain Deep Agents + GPT-4o |
| Backend | FastAPI + Server-Sent Events |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Render |
