# =============================================================================
# Tesla ETL Daily Scheduler
# =============================================================================
# Developer   : Michael Chen
# Description : Automatically runs the ETL pipeline every 24 hours
#               to keep your Supabase database fresh with new articles.
# =============================================================================
# To run: /opt/anaconda3/bin/python tesla_scheduler.py
# To stop: Ctrl + C
# =============================================================================

import schedule
import time
import subprocess
import logging
import sys
import os
from datetime import datetime

# Path to ETL script — must be in the same folder as this file
ETL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesla_etl_final.py")
PYTHON     = sys.executable
RUN_AT     = "06:00"  # Daily run time — change if needed

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scheduler.log", mode="a", encoding="utf-8")
    ]
)
log = logging.getLogger(__name__)

def run_etl():
    log.info("=" * 50)
    log.info("Starting ETL run at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 50)
    try:
        result = subprocess.run(
            [PYTHON, ETL_SCRIPT],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            log.info("ETL completed successfully!")
            for line in result.stdout.strip().split("\n")[-5:]:
                log.info("  " + line)
        else:
            log.error("ETL failed: " + (result.stderr[-300:] if result.stderr else "unknown error"))
    except subprocess.TimeoutExpired:
        log.error("ETL timed out after 5 minutes")
    except Exception as e:
        log.error("Scheduler error: " + str(e))

if __name__ == "__main__":
    log.info("Scheduler started — running ETL daily at " + RUN_AT)
    log.info("ETL script: " + ETL_SCRIPT)
    log.info("Press Ctrl+C to stop")
    log.info("-" * 50)

    # Run immediately on startup
    run_etl()

    # Schedule daily
    schedule.every().day.at(RUN_AT).do(run_etl)

    while True:
        schedule.run_pending()
        time.sleep(60)
