"""
Collection Job Executor

Routes collection jobs to appropriate collectors and manages execution.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from model.collection import CollectionJob
from .community_collector import CommunityCollector
from .builder_collector import BuilderCollector
from .sales_rep_manager import SalesRepManager
from .property_collector import PropertyCollector

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Executes collection jobs by routing to appropriate collectors.
    """

    def __init__(self, db: Session):
        self.db = db

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
        Execute pending jobs in priority order.

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
