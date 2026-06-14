#!/opt/anaconda3/bin/python
# =============================================================================
# Tesla & EV Competitor Brand Sentiment ETL Pipeline
# =============================================================================
# Developer   : Michael Chen
# Course      : MSBA - Applied Data Engineering
# Assignment  : Week 3 - ETL Pipeline & Data Quality Engineering
# Database    : Supabase (PostgreSQL via SQLAlchemy)
# Data Source : NewsAPI (newsapi.org)
# Description : Extracts Tesla and competitor EV brand news articles,
#               performs sentiment analysis using VADER, validates data
#               quality, and loads into Supabase PostgreSQL tables.
# =============================================================================

# =============================================================================
# IMPORTS
# =============================================================================
import os
import sys
import logging
import hashlib
from datetime import datetime, timezone

import pandas as pd
from newsapi import NewsApiClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError


# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# =============================================================================

NEWS_API_KEY = "38309e2f905848baacbe0d1741f8d318"

# Supabase connection parameters
DB_USERNAME = "postgres.ttntqvcomspvbkdumfvx"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Tesla2026sentiment")
DB_HOST     = "aws-1-us-east-1.pooler.supabase.com"
DB_PORT     = 6543
DB_NAME     = "postgres"

# Each brand maps to a list of search terms
BRAND_QUERIES = {
    "Tesla": [
        "Tesla electric car",
        "Elon Musk",
        "Tesla Model 3",
        "Tesla Model Y",
        "Tesla Cybertruck"
    ],
    "Hyundai": [
        "Hyundai Ioniq",
        "Hyundai Ioniq 5",
        "Hyundai EV"
    ],
    "Rivian": [
        "Rivian electric",
        "Rivian R1T",
        "Rivian R1S"
    ],
    "Ford EV": [
        "Ford Mustang Mach-E",
        "Ford electric vehicle"
    ],
    "BYD": [
        "BYD electric car",
        "BYD EV"
    ]
}

# VADER sentiment thresholds
POSITIVE_THRESHOLD =  0.05
NEGATIVE_THRESHOLD = -0.05

# Articles per query
PAGE_SIZE = 100


# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_pipeline.log", mode="a", encoding="utf-8")
    ]
)
log = logging.getLogger(__name__)


# =============================================================================
# DATABASE CONNECTION
# =============================================================================
def get_engine():
    # Using URL.create to safely handle passwords with special characters
    connection_url = URL.create(
        drivername = "postgresql+psycopg2",
        username   = DB_USERNAME,
        password   = DB_PASSWORD,
        host       = DB_HOST,
        port       = DB_PORT,
        database   = DB_NAME
    )
    return create_engine(connection_url)


# =============================================================================
# STAGE 1: EXTRACTION
# Pull raw articles from NewsAPI for all brands and query terms
# =============================================================================
def extract_articles(newsapi):
    log.info("=" * 60)
    log.info("STAGE 1: EXTRACTION")
    log.info("=" * 60)

    raw_articles = []

    for brand, queries in BRAND_QUERIES.items():
        log.info("Fetching articles for brand: " + brand)

        for query_type in queries:
            try:
                response = newsapi.get_everything(
                    q=query_type,
                    language="en",
                    sort_by="publishedAt",
                    page_size=PAGE_SIZE
                )

                # Validate API response structure
                if "articles" not in response:
                    log.warning("  Unexpected API response for: " + query_type)
                    continue

                articles = response["articles"]
                log.info("  [" + query_type + "] -> " + str(len(articles)) + " articles")

                for article in articles:
                    article["_brand"]      = brand
                    article["_query_type"] = query_type
                    raw_articles.append(article)

            except Exception as e:
                log.error("  ERROR fetching " + query_type + ": " + str(e))
                continue

    log.info("Extraction complete. Total raw articles: " + str(len(raw_articles)))
    return raw_articles


# =============================================================================
# STAGE 2: TRANSFORMATION & CLEANING
# - Normalizes and cleans all fields
# - Generates unique article_id from URL hash
# - Scores sentiment using VADER
# - Derives sentiment_label from compound score
# =============================================================================
def transform_articles(raw_articles):
    log.info("=" * 60)
    log.info("STAGE 2: TRANSFORMATION & CLEANING")
    log.info("=" * 60)

    analyzer = SentimentIntensityAnalyzer()
    rows = []

    for article in raw_articles:
        try:
            # Field extraction and normalization
            title       = (article.get("title")       or "").strip()
            description = (article.get("description") or "").strip()
            url         = (article.get("url")         or "").strip()
            author      = (article.get("author")      or "Unknown").strip()[:200]
            source      = (article.get("source", {}).get("name") or "Unknown").strip()[:200]
            published   = article.get("publishedAt")  or ""
            brand       = article.get("_brand",       "Unknown")
            query_type  = article.get("_query_type",  "Unknown")

            # Skip articles missing title or URL
            if not title or not url:
                continue

            # Skip removed or deleted articles
            if title.lower() == "[removed]" or description.lower() == "[removed]":
                continue

            # Parse published timestamp
            try:
                published_at = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                log.warning("  Could not parse date - skipping article")
                continue

            # Generate unique article_id from URL hash
            article_id = hashlib.md5(url.encode()).hexdigest()[:20]

            # Score sentiment using VADER on title + description
            text_to_score = title + " " + description
            scores        = analyzer.polarity_scores(text_to_score)

            compound = round(scores["compound"], 4)
            positive = round(scores["pos"],      4)
            negative = round(scores["neg"],      4)
            neutral  = round(scores["neu"],      4)

            # Derive sentiment label from compound score
            if compound >= POSITIVE_THRESHOLD:
                sentiment_label = "positive"
            elif compound <= NEGATIVE_THRESHOLD:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"

            rows.append({
                "article_id":      article_id,
                "brand":           brand,
                "query_type":      query_type,
                "source":          source,
                "author":          author,
                "title":           title,
                "description":     description,
                "url":             url,
                "published_at":    published_at,
                "collected_at":    datetime.now(timezone.utc),
                "compound":        compound,
                "positive_score":  positive,
                "negative_score":  negative,
                "neutral_score":   neutral,
                "sentiment_label": sentiment_label,
            })

        except Exception as e:
            log.warning("  Error transforming article: " + str(e))
            continue

    df = pd.DataFrame(rows)
    log.info("Transformation complete. Clean articles: " + str(len(df)))
    return df


# =============================================================================
# STAGE 3: DATA VALIDATION & QUALITY CHECKS
# - Row count check
# - Required columns check
# - Null checks on critical fields
# - Duplicate URL and article_id detection
# - Compound score range validation
# - Sentiment label validation
# - Brand coverage check
# - Date range sanity check
# =============================================================================
def validate_data(df):
    log.info("=" * 60)
    log.info("STAGE 3: DATA VALIDATION & QUALITY CHECKS")
    log.info("=" * 60)

    passed = True

    # Check 1: Row count
    row_count = len(df)
    if row_count == 0:
        log.error("  [FAIL] Row count: DataFrame is empty - nothing to load")
        return False
    log.info("  [PASS] Row count: " + str(row_count) + " rows")

    # Check 2: Required columns present
    required_columns = [
        "article_id", "brand", "query_type", "title",
        "url", "published_at", "compound", "sentiment_label"
    ]
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        log.error("  [FAIL] Schema check: Missing columns: " + str(missing_cols))
        passed = False
    else:
        log.info("  [PASS] Schema check: All required columns present")

    # Check 3: Null checks on critical fields
    for col in ["article_id", "brand", "title", "url", "published_at", "sentiment_label"]:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            log.warning("  [WARN] Nulls in " + col + ": " + str(null_count))
        else:
            log.info("  [PASS] No nulls in " + col)

    # Check 4: Duplicate URL detection - deduplicate if found
    dup_urls = df["url"].duplicated().sum()
    if dup_urls > 0:
        log.warning("  [WARN] " + str(dup_urls) + " duplicate URLs - removing")
        df.drop_duplicates(subset="url", keep="first", inplace=True)
        log.info("  Deduplicated. Remaining rows: " + str(len(df)))
    else:
        log.info("  [PASS] No duplicate URLs")

    # Check 5: Duplicate article_id detection
    dup_ids = df["article_id"].duplicated().sum()
    if dup_ids > 0:
        log.warning("  [WARN] " + str(dup_ids) + " duplicate article_ids")
    else:
        log.info("  [PASS] No duplicate article_ids")

    # Check 6: Compound score range validation (-1.0 to 1.0)
    out_of_range = df[(df["compound"] < -1.0) | (df["compound"] > 1.0)]
    if len(out_of_range) > 0:
        log.error("  [FAIL] " + str(len(out_of_range)) + " compound scores out of range")
        passed = False
    else:
        log.info("  [PASS] All compound scores within [-1.0, 1.0]")

    # Check 7: Sentiment label validation
    valid_labels = {"positive", "neutral", "negative"}
    invalid_labels = df[~df["sentiment_label"].isin(valid_labels)]
    if len(invalid_labels) > 0:
        log.error("  [FAIL] " + str(len(invalid_labels)) + " invalid sentiment labels")
        passed = False
    else:
        log.info("  [PASS] All sentiment labels valid")

    # Check 8: Brand coverage check
    expected_brands = set(BRAND_QUERIES.keys())
    actual_brands   = set(df["brand"].unique())
    missing_brands  = expected_brands - actual_brands
    if missing_brands:
        log.warning("  [WARN] Missing brands: " + str(missing_brands))
    else:
        log.info("  [PASS] All " + str(len(expected_brands)) + " brands present")

    # Check 9: Date range sanity check
    min_date = df["published_at"].min()
    max_date = df["published_at"].max()
    log.info("  [INFO] Date range: " + str(min_date.date()) + " to " + str(max_date.date()))

    # Summary
    if passed:
        log.info("Validation complete. ALL CHECKS PASSED")
    else:
        log.info("Validation complete. SOME CHECKS FAILED - review above")

    log.info("Sentiment breakdown:")
    for label, count in df["sentiment_label"].value_counts().items():
        pct = round(count / len(df) * 100, 1)
        log.info("  " + str(label) + ": " + str(count) + " (" + str(pct) + "%)")

    return passed


# =============================================================================
# STAGE 4: INCREMENTAL LOADING
# - Creates schema and table if they don't exist
# - Fetches existing URLs from DB
# - Inserts only new articles (URL is the dedup key)
# - Prevents duplicate loads on repeated pipeline runs
# =============================================================================
def load_to_supabase(df, engine):
    log.info("=" * 60)
    log.info("STAGE 4: DATABASE LOADING (INCREMENTAL)")
    log.info("=" * 60)

    try:
        with engine.connect() as conn:

            # Create schema if it doesn't exist
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS tesla_sentiment"))
            conn.commit()

            # Create articles table if it doesn't exist
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS tesla_sentiment.articles ("
                "    article_id      VARCHAR(20)   PRIMARY KEY,"
                "    brand           VARCHAR(50)   NOT NULL,"
                "    query_type      VARCHAR(100)  NOT NULL,"
                "    source          VARCHAR(200),"
                "    author          VARCHAR(200),"
                "    title           TEXT          NOT NULL,"
                "    description     TEXT,"
                "    url             TEXT          UNIQUE NOT NULL,"
                "    published_at    TIMESTAMPTZ   NOT NULL,"
                "    collected_at    TIMESTAMPTZ,"
                "    compound        NUMERIC(5,4),"
                "    positive_score  NUMERIC(5,4),"
                "    negative_score  NUMERIC(5,4),"
                "    neutral_score   NUMERIC(5,4),"
                "    sentiment_label VARCHAR(10)   NOT NULL"
                ")"
            ))
            conn.commit()
            log.info("  Table tesla_sentiment.articles confirmed")

            # Fetch existing URLs to find only new records
            existing_urls = pd.read_sql(
                "SELECT url FROM tesla_sentiment.articles", conn
            )["url"].tolist()
            log.info("  Existing articles in DB: " + str(len(existing_urls)))

            # Filter to only new articles
            new_df = df[~df["url"].isin(existing_urls)].copy()
            log.info("  New articles to insert: " + str(len(new_df)))

            if len(new_df) == 0:
                log.info("  No new articles - pipeline is up to date")
                return

            # Insert new articles in chunks of 100
            new_df.to_sql(
                name="articles",
                schema="tesla_sentiment",
                con=conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=100
            )
            conn.commit()

            # Verify total row count after insert
            result    = conn.execute(text("SELECT COUNT(*) FROM tesla_sentiment.articles"))
            total_rows = result.scalar()
            log.info("  Insert complete. Total rows in DB: " + str(total_rows))
            log.info("  New rows added this run: " + str(len(new_df)))

    except SQLAlchemyError as e:
        log.error("  DATABASE ERROR: " + str(e))
        raise


# =============================================================================
# STAGE 5: ANALYTICS PREPARATION
# Materializes two summary tables ready for Power BI or Plotly Dash:
# 1. brand_sentiment_summary - brand-level sentiment KPIs
# 2. daily_sentiment_trend   - daily average sentiment per brand
# =============================================================================
def prepare_analytics(df, engine):
    log.info("=" * 60)
    log.info("STAGE 5: ANALYTICS PREPARATION")
    log.info("=" * 60)

    try:
        with engine.connect() as conn:

            # Brand sentiment summary
            brand_summary = df.groupby("brand").agg(
                total_articles = ("article_id",      "count"),
                positive_count = ("sentiment_label", lambda x: (x == "positive").sum()),
                negative_count = ("sentiment_label", lambda x: (x == "negative").sum()),
                neutral_count  = ("sentiment_label", lambda x: (x == "neutral").sum()),
                avg_compound   = ("compound",        "mean"),
                avg_positive   = ("positive_score",  "mean"),
                avg_negative   = ("negative_score",  "mean"),
            ).reset_index()

            brand_summary["avg_compound"]  = brand_summary["avg_compound"].round(4)
            brand_summary["avg_positive"]  = brand_summary["avg_positive"].round(4)
            brand_summary["avg_negative"]  = brand_summary["avg_negative"].round(4)
            brand_summary["positive_pct"]  = (
                brand_summary["positive_count"] / brand_summary["total_articles"] * 100
            ).round(1)
            brand_summary["refreshed_at"]  = datetime.now(timezone.utc)

            brand_summary.to_sql(
                name="brand_sentiment_summary",
                schema="tesla_sentiment",
                con=conn,
                if_exists="replace",
                index=False
            )
            conn.commit()
            log.info("  brand_sentiment_summary: " + str(len(brand_summary)) + " rows written")

            # Daily sentiment trend
            df["date"] = df["published_at"].dt.date

            daily_trend = df.groupby(["brand", "date"]).agg(
                article_count  = ("article_id",      "count"),
                avg_compound   = ("compound",        "mean"),
                positive_count = ("sentiment_label", lambda x: (x == "positive").sum()),
                negative_count = ("sentiment_label", lambda x: (x == "negative").sum()),
            ).reset_index()

            daily_trend["avg_compound"] = daily_trend["avg_compound"].round(4)
            daily_trend["refreshed_at"] = datetime.now(timezone.utc)

            daily_trend.to_sql(
                name="daily_sentiment_trend",
                schema="tesla_sentiment",
                con=conn,
                if_exists="replace",
                index=False
            )
            conn.commit()
            log.info("  daily_sentiment_trend: " + str(len(daily_trend)) + " rows written")

            # Log brand summary to console
            log.info("  Brand Sentiment Summary:")
            for _, row in brand_summary.sort_values("avg_compound", ascending=False).iterrows():
                log.info(
                    "    " + str(row["brand"]) +
                    " | articles=" + str(row["total_articles"]) +
                    " | avg_sentiment=" + str(row["avg_compound"]) +
                    " | positive=" + str(row["positive_pct"]) + "%"
                )

    except SQLAlchemyError as e:
        log.error("  DATABASE ERROR during analytics prep: " + str(e))
        raise


# =============================================================================
# MAIN PIPELINE EXECUTION
# Orchestrates all 5 stages in sequence
# =============================================================================
def run_pipeline():
    log.info("=" * 60)
    log.info("TESLA EV BRAND SENTIMENT ETL PIPELINE - START")
    log.info("Run timestamp: " + datetime.now(timezone.utc).isoformat())
    log.info("=" * 60)

    start_time = datetime.now()

    try:
        # Initialize NewsAPI client
        log.info("Initializing clients...")
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        log.info("  NewsAPI client initialized")

        # Initialize Supabase engine
        engine = get_engine()
        log.info("  Supabase engine initialized")

        # Test DB connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("  Supabase connection test: OK")

        # Stage 1: Extract
        raw_articles = extract_articles(newsapi)

        # Stage 2: Transform
        df = transform_articles(raw_articles)

        # Stage 3: Validate
        validation_passed = validate_data(df)
        if not validation_passed:
            log.error("Validation failed - aborting pipeline")
            sys.exit(1)

        # Stage 4: Load
        load_to_supabase(df, engine)

        # Stage 5: Analytics prep
        prepare_analytics(df, engine)

        # Done
        elapsed = (datetime.now() - start_time).seconds
        log.info("=" * 60)
        log.info("PIPELINE COMPLETE - " + str(elapsed) + "s elapsed")
        log.info("Total articles processed: " + str(len(df)))
        log.info("=" * 60)

    except KeyboardInterrupt:
        log.warning("Pipeline interrupted by user")
        sys.exit(0)

    except Exception as e:
        log.error("PIPELINE FAILED: " + str(e))
        sys.exit(1)


# =============================================================================
# ENTRY POINT
# =============================================================================
run_pipeline()