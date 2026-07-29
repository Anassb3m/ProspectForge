#!/usr/bin/env python3
"""Verify migrations against production-shaped DB."""

import argparse

import logging
import subprocess
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_cmd(cmd: str):
    logger.info(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
    logger.info(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True, help="Database URL for rehearsal")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = args.db_url

    logger.info("1. Running Reconcile Reliability (Pre-Migration)...")
    run_cmd(".venv/bin/python scripts/reconcile_reliability.py --fail-on-anomaly")

    logger.info("2. Testing Downgrade by 1 revision...")
    run_cmd(".venv/bin/alembic downgrade -1")

    logger.info("3. Testing Upgrade to head...")
    run_cmd(".venv/bin/alembic upgrade head")

    logger.info("4. Running Reconcile Reliability (Post-Migration)...")
    run_cmd(".venv/bin/python scripts/reconcile_reliability.py --fail-on-anomaly")

    logger.info("Production-shaped migration test PASSED.")

if __name__ == "__main__":
    main()
