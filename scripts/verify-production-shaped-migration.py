#!/usr/bin/env python3
"""Upgrade and reconcile an isolated production-shaped database safely."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_cmd(args: list[str], *, env: dict[str, str]) -> None:
    logger.info("Running: %s", " ".join(args))
    result = subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    if result.stdout:
        logger.info(result.stdout.rstrip())
    if result.stderr:
        logger.info(result.stderr.rstrip())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True, help="Database URL for rehearsal")
    args = parser.parse_args()

    env = dict(os.environ)
    env["DATABASE_URL"] = args.db_url
    env["DEBUG"] = "false"
    env["ENVIRONMENT"] = "test"
    python = sys.executable

    logger.info("1. Upgrading isolated rehearsal database to head")
    run_cmd([python, "-m", "alembic", "upgrade", "head"], env=env)

    logger.info("2. Verifying the single current revision")
    run_cmd([python, "-m", "alembic", "current", "--check-heads"], env=env)

    logger.info("3. Running post-migration reconciliation")
    run_cmd(
        [python, "scripts/reconcile_reliability.py", "--fail-on-anomaly"],
        env=env,
    )

    logger.info("Production-shaped migration test PASSED.")

if __name__ == "__main__":
    main()
