"""
Job Executor Runner

Runs the concurrent job executor to process pending collection jobs.

Usage:
    python run_executor.py [--iterations N] [--poll-interval N]

Options:
    --iterations N      Maximum iterations (0 = run forever, default: 0)
    --poll-interval N   Seconds between polls (default: from config)
"""

import sys
import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DB_URL
from src.collection.job_executor import JobExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Run the job executor."""
    parser = argparse.ArgumentParser(description='Run the concurrent job executor')
    parser.add_argument(
        '--iterations',
        type=int,
        default=0,
        help='Maximum iterations (0 = run forever)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=None,
        help='Seconds between polls (default: from config)'
    )

    args = parser.parse_args()

    # Create database session
    engine = create_engine(DB_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()

    try:
        logger.info("=" * 80)
        logger.info("Starting Collection Job Executor")
        logger.info("=" * 80)

        if args.iterations == 0:
            logger.info("Running continuously (Ctrl+C to stop)")
        else:
            logger.info(f"Running for {args.iterations} iterations")

        if args.poll_interval:
            logger.info(f"Poll interval: {args.poll_interval} seconds")

        # Create and run executor
        executor = JobExecutor(db)
        executor.execute_pending_jobs_concurrent(
            max_iterations=args.iterations,
            poll_interval=args.poll_interval
        )

        logger.info("Executor finished")

    except KeyboardInterrupt:
        logger.info("\n🛑 Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Executor failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
