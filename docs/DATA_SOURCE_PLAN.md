# Data Source Plan

**Project:** EV Sentiment Intelligence  
**Developer:** Michael Chen  
**Course:** MSBA Applied Data Engineering — University of Louisville

---

## 1. Data Source Overview

This project uses NewsAPI as its primary data source to extract real-time English-language news articles about Tesla and four major EV competitors. Articles are collected, cleaned, scored for sentiment using VADER NLP, and loaded into a Supabase PostgreSQL database for analysis and visualization.

| Attribute | Details |
|-----------|---------|
| Source Name | NewsAPI (newsapi.org) |
| Source Type | REST API — real-time news aggregation |
| Access Method | Python newsapi-python client library |
| Authentication | API key (stored in .env file, never committed to GitHub) |
| Data Format | JSON response — parsed into Pandas DataFrame |
| Language | English only (language='en' parameter) |
| Sort Order | publishedAt — most recent articles first |
| Articles/Query | Up to 100 per request (free tier maximum) |
| Date Range | Last 30 days (free tier limitation) |
| Update Frequency | Daily — automated via tesla_scheduler.py at 06:00 AM |

---

## 2. Why NewsAPI?

NewsAPI was selected as the data source for the following reasons:

- **Instant access** — no approval process required unlike Reddit (PRAW) or Twitter/X APIs
- **Free tier** — 100 requests/day and 30 days of historical data at no cost
- **Broad coverage** — aggregates articles from thousands of English-language news sources globally
- **Structured response** — returns consistent JSON with title, description, source, author, and publishedAt fields
- **EV coverage** — automotive and technology news is well-represented in NewsAPI's source network
- **Python client** — official newsapi-python library simplifies authentication and pagination

### Alternative Sources Considered

| Source | Reason Not Selected |
|--------|---------------------|
| Reddit (PRAW) | API approval pending at project start; slower approval process |
| Twitter/X API | Free tier too restrictive; paid tier required for meaningful volume |
| Google News | No official API; scraping violates terms of service |
| Bloomberg/Reuters | Requires paid enterprise subscription |

---

## 3. Search Queries & Brand Mapping

Thirteen search queries are used across five EV brands. Each query targets a specific brand term or product to maximize relevant article coverage.

| Brand | Query Terms | Rationale |
|-------|-------------|-----------|
| Tesla | Tesla electric car, Elon Musk, Tesla Model 3, Tesla Model Y, Tesla Cybertruck | Covers brand, CEO, and top 3 models — highest coverage volume |
| Hyundai | Hyundai Ioniq, Hyundai Ioniq 5, Hyundai EV | Targets flagship EV line and general EV coverage |
| Rivian | Rivian electric, Rivian R1T, Rivian R1S | Covers brand and both primary truck/SUV models |
| Ford EV | Ford Mustang Mach-E, Ford electric vehicle | Targets specific model and general EV coverage |
| BYD | BYD electric car, BYD EV | Two broad queries needed due to lower English-language coverage volume |

---

## 4. Data Fields Extracted

The following fields are extracted from each NewsAPI article response and loaded into the `articles` table in Supabase:

| Field | Source | Type | Description |
|-------|--------|------|-------------|
| article_id | Derived (MD5 hash of URL) | VARCHAR(20) | Unique identifier — deterministic hash ensures deduplication across runs |
| brand | Pipeline-assigned | VARCHAR(50) | EV brand the article was collected for (Tesla, Rivian, etc.) |
| query_type | Pipeline-assigned | VARCHAR(100) | Exact search query that returned this article |
| title | API: title | TEXT | Article headline — primary text used for VADER sentiment scoring |
| description | API: description | TEXT | Article summary — combined with title for sentiment scoring |
| url | API: url | TEXT UNIQUE | Full article URL — used as deduplication key |
| source | API: source.name | VARCHAR(200) | Name of the news publication |
| author | API: author | VARCHAR(200) | Article author name (truncated to 200 chars) |
| published_at | API: publishedAt | TIMESTAMPTZ | Publication timestamp — parsed from ISO 8601 format |
| collected_at | Pipeline-assigned | TIMESTAMPTZ | Timestamp when the ETL pipeline collected this article |
| compound | VADER output | NUMERIC(5,4) | Overall sentiment score from -1.0 (negative) to +1.0 (positive) |
| positive_score | VADER output | NUMERIC(5,4) | Proportion of text with positive sentiment (0.0 to 1.0) |
| negative_score | VADER output | NUMERIC(5,4) | Proportion of text with negative sentiment (0.0 to 1.0) |
| neutral_score | VADER output | NUMERIC(5,4) | Proportion of text with neutral sentiment (0.0 to 1.0) |
| sentiment_label | Derived from compound | VARCHAR(10) | Positive (>=0.05), Negative (<=-0.05), or Neutral |

---

## 5. Sentiment Scoring Methodology

### VADER (Valence Aware Dictionary and sEntiment Reasoner)

VADER is a lexicon and rule-based sentiment analysis tool specifically designed for social media and news text. It is particularly well-suited for this project because:

- Handles news headlines well — short, punchy text without requiring large training datasets
- No model training required — works out of the box with domain-specific vocabulary
- Fast — scores thousands of articles in seconds
- Outputs four scores — compound, positive, negative, and neutral — providing rich sentiment dimensions

### Scoring Logic

Each article's title and description are concatenated and passed to VADER's `polarity_scores()` function. The compound score determines the sentiment label:

| Compound Score | Sentiment Label | Interpretation |
|----------------|-----------------|----------------|
| 0.05 or higher | Positive | Article conveys a favorable tone toward the brand |
| -0.05 to 0.05 | Neutral | Article is factual or mixed in tone |
| -0.05 or lower | Negative | Article conveys an unfavorable tone toward the brand |

---

## 6. Data Quality & Limitations

### Known Limitations

- **30-day rolling window** — NewsAPI free tier only returns articles from the last 30 days; historical data requires a paid plan
- **100 articles per query** — the free tier caps each API call at 100 results regardless of how many articles exist
- **Off-topic articles** — broad queries like "Elon Musk" can return articles about SpaceX or other ventures unrelated to Tesla
- **English only** — non-English coverage of BYD and Hyundai is excluded, which underrepresents their global media presence
- **Duplicate articles** — the same article may appear in multiple query results; URL-based deduplication resolves this

### Mitigations Applied

- **Keyword relevance filter** — articles whose titles contain no EV-related terms are excluded from the dashboard
- **URL deduplication** — MD5 hash of the URL serves as a unique key; duplicates are detected and removed in Stage 3 validation
- **Daily scheduler** — `tesla_scheduler.py` runs the ETL automatically every day to accumulate 30+ days of history over time
- **9-point validation framework** — automated quality checks catch nulls, schema violations, and out-of-range scores before any data reaches Supabase

---

## 7. Data Volume Summary

| Brand | Query Count | Max Articles/Run | Actual Avg Articles | DB Total |
|-------|-------------|------------------|---------------------|----------|
| Tesla | 5 | 500 | ~383 | 383 |
| Hyundai | 3 | 300 | ~135 | 135 |
| BYD | 2 | 200 | ~111 | 111 |
| Rivian | 3 | 300 | ~65 | 65 |
| Ford EV | 2 | 200 | ~97 | 97 |
| **Total** | **13** | **1,300** | **~791** | **762+** |

> **Note:** Actual article counts are lower than the theoretical maximum due to limited news coverage for smaller brands, deduplication of articles appearing in multiple queries, and keyword relevance filtering removing off-topic results.
