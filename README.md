# EV Sentiment Intelligence 🚗⚡

> Real-time brand sentiment tracking dashboard for Tesla and top EV competitors — powered by NewsAPI, VADER NLP, Supabase, and Plotly Dash.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Dash](https://img.shields.io/badge/Dash-2.0-lightblue) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-green) ![NewsAPI](https://img.shields.io/badge/Data-NewsAPI-orange)

---

## Project Overview

EV Sentiment Intelligence is an end-to-end data engineering project that:

- **Extracts** real-time news articles from NewsAPI across 5 EV brands
- **Scores** each article using VADER sentiment analysis (positive / neutral / negative)
- **Loads** data incrementally into a Supabase PostgreSQL database
- **Visualizes** insights through an interactive Plotly Dash dashboard

**Brands tracked:** Tesla · Rivian · Ford EV · Hyundai · BYD

---

## Business Insights

- **Tesla** generates the most media coverage but ranks lowest in average sentiment — brand fatigue and Elon Musk controversy drag coverage quality down
- **Ford EV and Rivian** consistently score the highest sentiment despite lower article volume — niche EV positioning generates more enthusiastic coverage
- **Tesla Cybertruck** is the only topic with a negative average sentiment score (-0.127), reflecting ongoing recall and quality perception issues
- **Elon Musk** as a search term scores lower than the Tesla brand overall — his public persona negatively impacts brand health
- **BYD** shows lower English-language coverage than US-based brands despite being Tesla's largest global competitor

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | NewsAPI |
| NLP | VADER Sentiment Analysis |
| ETL | Python, Pandas, SQLAlchemy |
| Database | Supabase (PostgreSQL) |
| Dashboard | Plotly Dash |
| Scheduler | Python `schedule` library |

---

## Setup & Installation

### 1. Clone the repo
```bash
git clone https://github.com/mc1025/ev-sentiment-intelligence.git
cd ev-sentiment-intelligence
```

### 2. Install dependencies
```bash
/opt/anaconda3/bin/pip install dash plotly pandas sqlalchemy psycopg2-binary newsapi-python vaderSentiment schedule python-dotenv
```

### 3. Create a `.env` file
```bash
touch .env
```

Add your credentials:
```
NEWS_API_KEY=your_newsapi_key_here
DB_PASSWORD=your_supabase_password_here
```

Get a free NewsAPI key at [newsapi.org](https://newsapi.org)

Get a free Supabase account at [supabase.com](https://supabase.com)

### 4. Run the ETL pipeline
```bash
/opt/anaconda3/bin/python tesla_etl_final.py
```

### 5. Run the dashboard
```bash
/opt/anaconda3/bin/python tesla_dashboard.py
```

Then open **http://127.0.0.1:8050** in your browser.

### 6. (Optional) Run the daily scheduler
Keep data fresh automatically — runs ETL every day at 6:00 AM:
```bash
/opt/anaconda3/bin/python tesla_scheduler.py
```

---

## File Structure

```
ev-sentiment-intelligence/
├── tesla_dashboard.py      # Plotly Dash dashboard application
├── tesla_etl_final.py      # ETL pipeline (extract, transform, load)
├── tesla_scheduler.py      # Daily ETL scheduler
├── .env                    # Local credentials (not committed to GitHub)
├── .gitignore
└── README.md
```

---

## Dashboard Features

### Filters
- **Brand pills** — click to toggle brands on/off with company logos
- **Sentiment filter** — filter by positive, neutral, or negative
- **Date presets** — Last 7 / 14 / 30 days or All time
- **Custom date picker** — select any date range
- **Tesla events toggle** — show/hide event markers on trend chart

### Charts
- 📈 **Daily Sentiment Trend** — line chart with Tesla event overlays
- 📊 **Brand Avg Sentiment** — ranked horizontal bar chart
- 🥧 **Sentiment Mix** — stacked bar showing sentiment breakdown per brand
- 📦 **Article Volume** — total article count per brand
- 🔍 **Sentiment by Topic** — compound score per search query

### KPI Cards
- Total articles · Positive % · Negative % · Avg Score · Top Brand

---

## ETL Pipeline Stages

| Stage | Description |
|-------|-------------|
| 1. Extract | NewsAPI pulls up to 100 articles per query across 13 search terms |
| 2. Transform | Cleans nulls, parses timestamps, scores sentiment with VADER |
| 3. Validate | 9 data quality checks — nulls, duplicates, score ranges, brand coverage |
| 4. Load | Incremental insert — URL as dedup key, only new articles inserted |
| 5. Prepare | Materializes summary tables for dashboard performance |

---

## Database Schema

All tables in `tesla_sentiment` schema on Supabase PostgreSQL:

| Table | Description |
|-------|-------------|
| `articles` | Raw articles with VADER sentiment scores |
| `tesla_events` | Manually curated Tesla event timeline |
| `brand_sentiment_summary` | Pre-aggregated brand KPIs |
| `daily_sentiment_trend` | Daily avg sentiment per brand |
| `competitors` | Lookup table for competitor brands |

---

## Developer

**Michael Chen** — MSBA Student, University of Louisville

GitHub: [github.com/mc1025](https://github.com/mc1025)
