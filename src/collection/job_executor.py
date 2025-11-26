"""
Collection Job Executor

Routes collection jobs to appropriate collectors and manages execution.
"""
import logging
import time
import threading
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DB_URL
from config.collection_config import CollectionConfig
from model.collection import CollectionJob
from .community_collector import CommunityCollector
from .builder_collector import BuilderCollector
from .sales_rep_manager import SalesRepManager
from .property_collector import PropertyCollector

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Executes collection jobs by routing to appropriate collectors.

    Supports concurrent execution with configurable limits per entity type.
    """

    def __init__(self, db: Session):
        self.db = db
        # Track running jobs by entity type
        self.running_jobs: Dict[str, List[str]] = {
            'community': [],
            'builder': [],
            'property': [],
            'sales_rep': []
        }
        self.lock = threading.Lock()

    def execute_job(self, job_id: str):
        """
        Execute a collection job.

        Args:
            job_id: The collection job ID to execute

        Raises:
            ValueError: If job not found or invalid entity type
        """
        # Load job
        job = self.db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        logger.info(
            f"Executing job {job_id}: "
            f"entity_type={job.entity_type}, job_type={job.job_type}"
        )

        # Route to appropriate collector
        if job.entity_type == "community":
            collector = CommunityCollector(self.db, job_id)
        elif job.entity_type == "builder":
            collector = BuilderCollector(self.db, job_id)
        elif job.entity_type == "sales_rep":
            collector = SalesRepManager(self.db, job_id)
        elif job.entity_type == "property":
            collector = PropertyCollector(self.db, job_id)
        else:
            raise ValueError(f"Unknown entity type: {job.entity_type}")

        # Execute collection
        try:
            collector.run()
            logger.info(f"Job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            raise

    def execute_pending_jobs(self, limit: int = 10):
        """
        Execute pending jobs in priority order (sequential, not concurrent).

        Args:
            limit: Maximum number of jobs to execute
        """
        # Get pending jobs ordered by priority (highest first)
        pending_jobs = self.db.query(CollectionJob).filter(
            CollectionJob.status == "pending"
        ).order_by(
            CollectionJob.priority.desc(),
            CollectionJob.created_at.asc()
        ).limit(limit).all()

        logger.info(f"Found {len(pending_jobs)} pending jobs to execute")

        for job in pending_jobs:
            try:
                self.execute_job(job.job_id)
            except Exception as e:
                logger.error(
                    f"Failed to execute job {job.job_id}: {str(e)}",
                    exc_info=True
                )
                # Continue with next job
                continue

    def _get_running_job_count(self, entity_type: str) -> int:
        """Get number of currently running jobs for entity type."""
        with self.lock:
            return len(self.running_jobs.get(entity_type, []))

    def _get_total_running_jobs(self) -> int:
        """Get total number of running jobs across all types."""
        with self.lock:
            return sum(len(jobs) for jobs in self.running_jobs.values())

    def _add_running_job(self, entity_type: str, job_id: str):
        """Add job to running jobs tracker."""
        with self.lock:
            if entity_type in self.running_jobs:
                self.running_jobs[entity_type].append(job_id)

    def _remove_running_job(self, entity_type: str, job_id: str):
        """Remove job from running jobs tracker."""
        with self.lock:
            if entity_type in self.running_jobs and job_id in self.running_jobs[entity_type]:
                self.running_jobs[entity_type].remove(job_id)

    def _can_start_job(self, entity_type: str) -> bool:
        """
        Check if we can start a new job for this entity type.

        Respects both per-type and global concurrency limits.
        """
        # Check global limit
        if self._get_total_running_jobs() >= CollectionConfig.MAX_TOTAL_CONCURRENT_JOBS:
            return False

        # Check per-type limit
        max_concurrent = CollectionConfig.get_max_concurrent_jobs(entity_type)
        current_count = self._get_running_job_count(entity_type)

        return current_count < max_concurrent

    def execute_job_in_background(self, job_id: str, entity_type: str):
        """
        Execute a job in a background thread.

        Args:
            job_id: Job ID to execute
            entity_type: Entity type for concurrency tracking
        """
        def background_task():
            # Create new DB session for this thread
            engine = create_engine(DB_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            bg_db = SessionLocal()

            try:
                # Track this job as running
                self._add_running_job(entity_type, job_id)
                logger.info(f"🔵 Starting job {job_id} ({entity_type}) - "
                           f"Running: {self._get_running_job_count(entity_type)}/{CollectionConfig.get_max_concurrent_jobs(entity_type)}")

                # Create executor with background DB session
                executor = JobExecutor(bg_db)
                executor.execute_job(job_id)

                logger.info(f"✅ Job {job_id} completed successfully")
            except Exception as e:
                error_message = str(e)
                logger.error(f"❌ Job {job_id} failed: {error_message}", exc_info=True)

                # Mark job as failed
                try:
                    failed_job = bg_db.query(CollectionJob).filter(
                        CollectionJob.job_id == job_id
                    ).first()

                    if failed_job and failed_job.status == "running":
                        failed_job.status = "failed"
                        failed_job.error_message = f"Execution failed: {error_message}"
                        failed_job.completed_at = datetime.utcnow()
                        bg_db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update job status: {db_err}")
                    bg_db.rollback()
            finally:
                # Remove from running tracker
                self._remove_running_job(entity_type, job_id)
                bg_db.close()
                logger.info(f"🏁 Job {job_id} finished - "
                           f"Running: {self._get_running_job_count(entity_type)}/{CollectionConfig.get_max_concurrent_jobs(entity_type)}")

        # Start background thread
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()

    def execute_pending_jobs_concurrent(
        self,
        max_iterations: int = 100,
        poll_interval: int = None
    ):
        """
        Execute pending jobs with concurrency control.

        Continuously polls for pending jobs and executes them in parallel
        while respecting concurrency limits.

        Args:
            max_iterations: Maximum polling iterations (0 = infinite)
            poll_interval: Seconds between polls (default from config)
        """
        if poll_interval is None:
            poll_interval = CollectionConfig.EXECUTOR_POLL_INTERVAL

        iteration = 0

        logger.info(f"🚀 Starting concurrent job executor")
        logger.info(f"📊 Concurrency limits: "
                   f"community={CollectionConfig.MAX_CONCURRENT_COMMUNITY_JOBS}, "
                   f"builder={CollectionConfig.MAX_CONCURRENT_BUILDER_JOBS}, "
                   f"property={CollectionConfig.MAX_CONCURRENT_PROPERTY_JOBS}, "
                   f"sales_rep={CollectionConfig.MAX_CONCURRENT_SALES_REP_JOBS}, "
                   f"total={CollectionConfig.MAX_TOTAL_CONCURRENT_JOBS}")

        while max_iterations == 0 or iteration < max_iterations:
            iteration += 1

            try:
                # Get pending jobs grouped by entity type
                for entity_type in ['community', 'builder', 'property', 'sales_rep']:
                    # Check if we can start more jobs of this type
                    if not self._can_start_job(entity_type):
                        continue

                    # Calculate how many more jobs we can start
                    max_concurrent = CollectionConfig.get_max_concurrent_jobs(entity_type)
                    current_running = self._get_running_job_count(entity_type)
                    available_slots = max_concurrent - current_running

                    # Also respect global limit
                    global_available = CollectionConfig.MAX_TOTAL_CONCURRENT_JOBS - self._get_total_running_jobs()
                    available_slots = min(available_slots, global_available)

                    if available_slots <= 0:
                        continue

                    # Get pending jobs for this entity type
                    pending_jobs = self.db.query(CollectionJob).filter(
                        CollectionJob.status == "pending",
                        CollectionJob.entity_type == entity_type
                    ).order_by(
                        CollectionJob.priority.desc(),
                        CollectionJob.created_at.asc()
                    ).limit(available_slots).all()

                    # Start jobs
                    for job in pending_jobs:
                        # Double-check we can still start (another thread might have started one)
                        if not self._can_start_job(entity_type):
                            break

                        # Mark as running immediately
                        job.status = "running"
                        job.started_at = datetime.utcnow()
                        self.db.commit()

                        # Execute in background
                        self.execute_job_in_background(job.job_id, entity_type)

                        logger.info(f"⏳ Started {entity_type} job: {job.job_id}")

                # Sleep before next poll
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error in executor loop: {str(e)}", exc_info=True)
                time.sleep(poll_interval)

        logger.info(f"🛑 Job executor stopped after {iteration} iterations")


def create_community_collection_job(
    db: Session,
    community_id: Optional[int] = None,
    community_name: Optional[str] = None,
    location: Optional[str] = None,
    initiated_by: Optional[str] = None
) -> CollectionJob:
    """
    Create a community collection job.

    Args:
        db: Database session
        community_id: Existing community ID (for updates)
        community_name: Community name (for discovery)
        location: Location string
        initiated_by: User ID who initiated the job

    Returns:
        Created CollectionJob
    """
    job = CollectionJob(
        entity_type="community",
        entity_id=community_id,
        job_type="update" if community_id else "discovery",
        status="pending",
        priority=7,
        search_query=community_name,
        search_filters={"location": location} if location else None,
        initiated_by=initiated_by
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Created community collection job: {job.job_id}")
    return job


def create_builder_collection_job(
    db: Session,
    builder_id: Optional[int] = None,
    builder_name: Optional[str] = None,
    community_id: Optional[int] = None,
    location: Optional[str] = None,
    initiated_by: Optional[str] = None
) -> CollectionJob:
    """
    Create a builder collection job.

    Args:
        db: Database session
        builder_id: Existing builder ID (for updates)
        builder_name: Builder name (for discovery)
        community_id: Associated community ID
        location: Location string
        initiated_by: User ID who initiated the job

    Returns:
        Created CollectionJob
    """
    job = CollectionJob(
        entity_type="builder",
        entity_id=builder_id,
        job_type="update" if builder_id else "discovery",
        parent_entity_type="community" if community_id else None,
        parent_entity_id=community_id,
        status="pending",
        priority=5,
        search_query=builder_name,
        search_filters={
            "community_id": community_id,
            "location": location
        } if (community_id or location) else None,
        initiated_by=initiated_by
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Created builder collection job: {job.job_id}")
    return job


def create_property_inventory_job(
    db: Session,
    builder_id: int,
    community_id: int,
    location: Optional[str] = None,
    initiated_by: Optional[str] = None
) -> CollectionJob:
    """
    Create a property inventory collection job.

    Args:
        db: Database session
        builder_id: Builder ID
        community_id: Community ID
        location: Location string
        initiated_by: User ID who initiated the job

    Returns:
        Created CollectionJob
    """
    job = CollectionJob(
        entity_type="property",
        entity_id=None,
        job_type="inventory",
        parent_entity_type="builder",
        parent_entity_id=builder_id,
        status="pending",
        priority=3,
        search_filters={
            "builder_id": builder_id,
            "community_id": community_id,
            "location": location
        },
        initiated_by=initiated_by
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info(f"Created property inventory job: {job.job_id}")
    return job
