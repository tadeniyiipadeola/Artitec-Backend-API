"""
Admin Collection Routes

API endpoints for managing data collection jobs.
"""
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from config.db import get_db
from model.collection import CollectionJob, CollectionChange, EntityMatch, CollectionJobLog
from src.collection.job_executor import (
    JobExecutor,
    create_community_collection_job,
    create_builder_collection_job,
    create_property_inventory_job
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["Admin - Data Collection"])


# ===================================================================
# Pydantic Schemas
# ===================================================================

class CollectionJobCreate(BaseModel):
    """Request to create a collection job."""
    entity_type: str = Field(..., description="community, builder, property, sales_rep")
    entity_id: Optional[int] = Field(None, description="ID of existing entity (for updates)")
    job_type: str = Field(..., description="update, discovery, inventory")
    search_query: Optional[str] = Field(None, description="Search query")
    location: Optional[str] = Field(None, description="Location context")
    community_id: Optional[int] = Field(None, description="Associated community ID")
    builder_id: Optional[int] = Field(None, description="Associated builder ID")
    priority: int = Field(5, description="Job priority (1-10, higher = more urgent)")


class CollectionJobResponse(BaseModel):
    """Response with job details."""
    job_id: str
    entity_type: str
    entity_id: Optional[int]
    job_type: str
    status: str
    priority: int
    search_query: Optional[str]
    items_found: int
    changes_detected: int
    new_entities_found: int
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle datetime serialization."""
        data = {
            'job_id': obj.job_id,
            'entity_type': obj.entity_type,
            'entity_id': obj.entity_id,
            'job_type': obj.job_type,
            'status': obj.status,
            'priority': obj.priority,
            'search_query': obj.search_query,
            'items_found': obj.items_found or 0,
            'changes_detected': obj.changes_detected or 0,
            'new_entities_found': obj.new_entities_found or 0,
            'error_message': obj.error_message,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'started_at': obj.started_at.isoformat() if obj.started_at else None,
            'completed_at': obj.completed_at.isoformat() if obj.completed_at else None,
        }
        return cls(**data)


class CollectionChangeResponse(BaseModel):
    """Response with change details."""
    id: int
    job_id: str
    entity_type: str
    entity_id: Optional[int]
    entity_name: Optional[str] = None  # Entity name for field-level changes OR parent entity for awards/credentials
    parent_entity_type: Optional[str] = None  # Type of parent entity (for awards/credentials)
    parent_entity_id: Optional[int] = None  # ID of parent entity (for awards/credentials)
    associated_communities: Optional[list] = None  # List of community names builder is associated with
    is_new_entity: bool
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    change_type: str
    status: str
    confidence: float
    source_url: Optional[str]
    proposed_entity_data: Optional[dict]  # Add proposed entity data for new entities
    reviewed_by: Optional[str]
    reviewed_by_name: Optional[str]  # Full name of reviewer
    reviewed_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_db(cls, obj, db):
        """Custom from_orm to handle datetime serialization and fetch entity name."""
        entity_name = None
        parent_entity_type = None
        parent_entity_id = None
        associated_communities = None
        reviewed_by_name = None

        # Fetch reviewer name if reviewed_by is set
        if obj.reviewed_by:
            try:
                from model.user import Users
                reviewer = db.query(Users).filter(Users.user_id == obj.reviewed_by).first()
                if reviewer:
                    reviewed_by_name = f"{reviewer.first_name} {reviewer.last_name}"
            except Exception as e:
                logger.warning(f"Failed to fetch reviewer name for user_id {obj.reviewed_by}: {e}")

        # Handle awards and credentials - fetch parent entity info
        if obj.entity_type in ("award", "credential") and obj.is_new_entity and obj.proposed_entity_data:
            try:
                # Check for builder_id or community_id in proposed_entity_data
                builder_id = obj.proposed_entity_data.get("builder_id")
                community_id = obj.proposed_entity_data.get("community_id")

                if builder_id:
                    from model.profiles.builder import BuilderProfile
                    builder = db.query(BuilderProfile).filter(BuilderProfile.id == builder_id).first()
                    if builder:
                        entity_name = builder.name
                        parent_entity_type = "builder"
                        parent_entity_id = builder_id
                elif community_id:
                    from model.profiles.community import Community
                    community = db.query(Community).filter(Community.id == community_id).first()
                    if community:
                        entity_name = community.name
                        parent_entity_type = "community"
                        parent_entity_id = community_id
            except Exception as e:
                logger.warning(f"Failed to fetch parent entity for {obj.entity_type}: {e}")

        # Handle field-level changes - fetch entity name and communities for builders
        elif not obj.is_new_entity and obj.entity_id:
            try:
                if obj.entity_type == "community":
                    from model.profiles.community import Community
                    entity = db.query(Community).filter(Community.id == obj.entity_id).first()
                    if entity:
                        entity_name = entity.name
                elif obj.entity_type == "builder":
                    from model.profiles.builder import BuilderProfile
                    from sqlalchemy import text
                    entity = db.query(BuilderProfile).filter(BuilderProfile.id == obj.entity_id).first()
                    if entity:
                        entity_name = entity.name
                        # Fetch associated communities for this builder
                        try:
                            community_result = db.execute(text("""
                                SELECT c.name
                                FROM builder_communities bc
                                JOIN communities c ON bc.community_id = c.id
                                WHERE bc.builder_id = :builder_id
                                ORDER BY c.name
                                LIMIT 10
                            """), {"builder_id": obj.entity_id}).fetchall()
                            if community_result:
                                associated_communities = [row[0] for row in community_result]
                        except Exception as comm_err:
                            logger.warning(f"Failed to fetch communities for builder {obj.entity_id}: {comm_err}")
                elif obj.entity_type == "property":
                    from model.profiles.property import Property
                    entity = db.query(Property).filter(Property.id == obj.entity_id).first()
                    if entity:
                        entity_name = entity.title or entity.address
            except Exception as e:
                logger.warning(f"Failed to fetch entity name for {obj.entity_type} {obj.entity_id}: {e}")

        data = {
            'id': obj.id,
            'job_id': obj.job_id,
            'entity_type': obj.entity_type,
            'entity_id': obj.entity_id,
            'entity_name': entity_name,
            'parent_entity_type': parent_entity_type,
            'parent_entity_id': parent_entity_id,
            'associated_communities': associated_communities,
            'is_new_entity': obj.is_new_entity,
            'field_name': obj.field_name,
            'old_value': obj.old_value,
            'new_value': obj.new_value,
            'change_type': obj.change_type,
            'status': obj.status,
            'confidence': obj.confidence,
            'source_url': obj.source_url,
            'proposed_entity_data': obj.proposed_entity_data,
            'reviewed_by': obj.reviewed_by,
            'reviewed_by_name': reviewed_by_name,
            'reviewed_at': obj.reviewed_at.isoformat() if obj.reviewed_at else None,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
        }
        return cls(**data)


class ChangeReviewRequest(BaseModel):
    """Request to review a change."""
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = Field(None, description="Review notes")


class BulkChangeReviewRequest(BaseModel):
    """Request to review multiple changes."""
    change_ids: List[int] = Field(..., description="List of change IDs")
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = Field(None, description="Review notes")


class CollectionJobListResponse(BaseModel):
    """Paginated response for job list."""
    jobs: List[CollectionJobResponse]
    total: int
    page: int
    page_size: int


class CollectionStatsResponse(BaseModel):
    """Statistics about collection jobs."""
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    success_rate: float
    average_duration: int
    total_entities_collected: int
    total_changes_detected: int


# ===================================================================
# Job Management Endpoints
# ===================================================================

@router.post("/jobs", response_model=CollectionJobResponse)
async def create_collection_job(
    request: CollectionJobCreate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)  # TODO: Add auth
):
    """
    Create a new collection job.

    Creates a job to collect data for a specific entity type.
    """
    try:
        # Validate request based on job type
        if request.job_type == "discovery":
            # For discovery jobs:
            # - search_query is optional (blank = search all in location)
            # - location is required when search_query is blank
            if not request.search_query and not request.location:
                raise HTTPException(
                    status_code=400,
                    detail="Either search_query or location is required for discovery jobs"
                )
        elif request.job_type == "update":
            # For update jobs, entity_id is required
            if not request.entity_id:
                raise HTTPException(
                    status_code=400,
                    detail="entity_id is required for update jobs"
                )

        # Route to appropriate job creator
        if request.entity_type == "community":
            job = create_community_collection_job(
                db=db,
                community_id=request.entity_id,
                community_name=request.search_query or None,  # None if blank
                location=request.location,
                # initiated_by=current_user.user_id
            )
        elif request.entity_type == "builder":
            job = create_builder_collection_job(
                db=db,
                builder_id=request.entity_id,
                builder_name=request.search_query or None,  # None if blank
                community_id=request.community_id,
                location=request.location,
                # initiated_by=current_user.user_id
            )
        elif request.entity_type == "property":
            if not request.builder_id or not request.community_id:
                raise HTTPException(
                    status_code=400,
                    detail="builder_id and community_id required for property collection"
                )
            job = create_property_inventory_job(
                db=db,
                builder_id=request.builder_id,
                community_id=request.community_id,
                location=request.location,
                # initiated_by=current_user.user_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported entity type: {request.entity_type}"
            )

        return CollectionJobResponse.from_orm(job)

    except Exception as e:
        logger.error(f"Failed to create collection job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=CollectionJobListResponse)
async def list_collection_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    List collection jobs.

    Returns paginated list of collection jobs.
    """
    query = db.query(CollectionJob)

    if status:
        query = query.filter(CollectionJob.status == status)
    if entity_type:
        query = query.filter(CollectionJob.entity_type == entity_type)

    # Get total count
    total = query.count()

    # Calculate offset
    offset = (page - 1) * page_size

    # Get paginated results
    jobs = query.order_by(
        CollectionJob.created_at.desc()
    ).limit(page_size).offset(offset).all()

    return CollectionJobListResponse(
        jobs=[CollectionJobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=CollectionStatsResponse)
async def get_collection_stats(
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get collection statistics.

    Returns overall statistics about collection jobs.
    """
    from sqlalchemy import func, case
    from datetime import datetime

    # Count jobs by status
    total_jobs = db.query(func.count(CollectionJob.job_id)).scalar() or 0
    pending_jobs = db.query(func.count(CollectionJob.job_id)).filter(
        CollectionJob.status == "pending"
    ).scalar() or 0
    running_jobs = db.query(func.count(CollectionJob.job_id)).filter(
        CollectionJob.status == "running"
    ).scalar() or 0
    completed_jobs = db.query(func.count(CollectionJob.job_id)).filter(
        CollectionJob.status == "completed"
    ).scalar() or 0
    failed_jobs = db.query(func.count(CollectionJob.job_id)).filter(
        CollectionJob.status == "failed"
    ).scalar() or 0

    # Calculate success rate
    success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    # Calculate average duration (in seconds) for completed jobs
    completed_query = db.query(CollectionJob).filter(
        CollectionJob.status == "completed",
        CollectionJob.started_at.isnot(None),
        CollectionJob.completed_at.isnot(None)
    ).all()

    total_duration = 0
    for job in completed_query:
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            total_duration += duration

    average_duration = int(total_duration / len(completed_query)) if completed_query else 0

    # Get total entities and changes
    total_entities = db.query(func.sum(CollectionJob.new_entities_found)).scalar() or 0
    total_changes = db.query(func.sum(CollectionJob.changes_detected)).scalar() or 0

    return CollectionStatsResponse(
        total_jobs=total_jobs,
        pending_jobs=pending_jobs,
        running_jobs=running_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        success_rate=round(success_rate, 2),
        average_duration=average_duration,
        total_entities_collected=total_entities,
        total_changes_detected=total_changes
    )


@router.get("/jobs/{job_id}", response_model=CollectionJobResponse)
async def get_collection_job(
    job_id: str,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """Get details of a specific collection job."""
    job = db.query(CollectionJob).filter(
        CollectionJob.job_id == job_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return CollectionJobResponse.from_orm(job)


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    limit: int = Query(100, le=500, description="Max number of logs to return"),
    offset: int = Query(0, description="Offset for pagination"),
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, SUCCESS, WARNING, ERROR)"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get execution logs for a collection job.

    Returns detailed real-time logs from job execution stored in the database.
    Logs are written by collectors during execution and can be polled for live updates.
    """
    # Verify job exists
    job = db.query(CollectionJob).filter(
        CollectionJob.job_id == job_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Query logs from database
    query = db.query(CollectionJobLog).filter(
        CollectionJobLog.job_id == job_id
    )

    # Apply filters
    if level:
        query = query.filter(CollectionJobLog.level == level.upper())
    if stage:
        query = query.filter(CollectionJobLog.stage == stage)

    # Get total count before pagination
    total_logs = query.count()

    # Get logs ordered by timestamp (newest first for live updates, or oldest first for full history)
    logs = query.order_by(
        CollectionJobLog.timestamp.asc()  # Chronological order
    ).limit(limit).offset(offset).all()

    # Format logs for response
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "level": log.level,
            "message": log.message,
            "stage": log.stage,
            "log_data": log.log_data  # Additional structured data
        })

    return {
        "job_id": job_id,
        "logs": formatted_logs,
        "total_logs": total_logs,
        "limit": limit,
        "offset": offset
    }


@router.get("/jobs/{job_id}/changes", response_model=List[CollectionChangeResponse])
async def get_job_changes(
    job_id: str,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get all changes detected by a specific collection job.

    Returns changes (new entities, updates) found during this job's execution.
    """
    # Verify job exists
    job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all changes for this job
    changes = db.query(CollectionChange).filter(
        CollectionChange.job_id == job_id
    ).order_by(CollectionChange.created_at.desc()).all()

    logger.info(f"Found {len(changes)} changes for job {job_id}")

    return [CollectionChangeResponse.from_orm_with_db(change, db) for change in changes]


@router.post("/jobs/{job_id}/execute")
async def execute_collection_job(
    job_id: str,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Execute a collection job immediately.

    Runs the collection job synchronously and returns the result.
    """
    try:
        executor = JobExecutor(db)
        executor.execute_job(job_id)

        # Reload job to get updated status
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        return CollectionJobResponse.from_orm(job)

    except Exception as e:
        logger.error(f"Failed to execute job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/start", response_model=CollectionJobResponse)
async def start_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Start a pending collection job immediately.

    This endpoint allows you to manually start a specific pending job.
    The job will run in the background and you can poll for status updates.

    Only works for jobs with status 'pending'. Returns 400 if job is already running or completed.
    """
    try:
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Check job status
        if job.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start job with status '{job.status}'. Only pending jobs can be started."
            )

        # Mark as running immediately
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"⏳ Starting job {job_id} in background")

        # Execute job in background thread
        def execute_job_background():
            """Execute job in background with proper error handling"""
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config.settings import DB_URL

            # Create new DB session for background thread
            engine = create_engine(DB_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            bg_db = SessionLocal()

            try:
                executor = JobExecutor(bg_db)
                logger.info(f"🔵 Executing job {job_id} in background")
                executor.execute_job(job_id)
                logger.info(f"✅ Job {job_id} completed successfully")
            except Exception as e:
                error_message = str(e)
                logger.error(f"❌ Job {job_id} failed: {error_message}", exc_info=True)

                # Mark job as failed in database
                try:
                    failed_job = bg_db.query(CollectionJob).filter(
                        CollectionJob.job_id == job_id
                    ).first()

                    if failed_job and failed_job.status == "running":
                        failed_job.status = "failed"
                        failed_job.error_message = f"Execution failed: {error_message}"
                        failed_job.completed_at = datetime.utcnow()
                        bg_db.commit()
                        logger.info(f"🔧 Marked job {job_id} as failed in database")
                except Exception as db_err:
                    logger.error(f"Failed to update job status for {job_id}: {db_err}")
                    bg_db.rollback()
            finally:
                bg_db.close()
                logger.info(f"🏁 Background thread finished for job {job_id}")

        # Use threading to execute in background
        import threading
        thread = threading.Thread(target=execute_job_background)
        thread.daemon = True
        thread.start()

        # Refresh job to get updated data
        db.refresh(job)

        return CollectionJobResponse.from_orm(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Cancel and delete a collection job.

    Deletes the job and all associated changes. Works for any job status except 'running'.
    """
    try:
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Don't allow deleting currently running jobs (could cause issues)
        if job.status == "running":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete running job. Wait for it to complete or fail first."
            )

        # Delete associated changes first (foreign key constraint)
        changes_deleted = db.query(CollectionChange).filter(
            CollectionChange.job_id == job_id
        ).delete()

        # Delete the job
        db.delete(job)
        db.commit()

        logger.info(f"Job {job_id} deleted successfully (status was '{job.status}', deleted {changes_deleted} associated changes)")
        return {"success": True, "message": f"Job {job_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/retry", response_model=CollectionJobResponse)
async def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Retry a failed or cancelled collection job.

    Resets the job status to 'pending' so it can be re-executed.
    """
    try:
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Only allow retrying failed or cancelled jobs
        if job.status not in ("failed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job with status '{job.status}'. Only failed or cancelled jobs can be retried."
            )

        # Reset job status
        job.status = "pending"
        job.error_message = None
        job.started_at = None
        job.completed_at = None

        db.commit()
        db.refresh(job)

        logger.info(f"Job {job_id} reset to pending for retry")
        return CollectionJobResponse.from_orm(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/reset-stuck")
async def reset_stuck_jobs(
    timeout_minutes: int = Query(30, description="Consider jobs stuck after this many minutes"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Reset jobs that have been running for too long (stuck jobs).

    Finds all jobs in 'running' status that started more than timeout_minutes ago
    and resets them to 'failed' with an error message.
    """
    try:
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        # Find stuck jobs
        stuck_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "running",
            CollectionJob.started_at < cutoff_time
        ).all()

        if not stuck_jobs:
            return {
                "success": True,
                "reset_count": 0,
                "message": f"No jobs have been running for more than {timeout_minutes} minutes"
            }

        reset_count = 0
        job_ids = []

        for job in stuck_jobs:
            job.status = "failed"
            job.error_message = f"Job timed out after running for more than {timeout_minutes} minutes. Background execution may have failed."
            job.completed_at = datetime.utcnow()
            job_ids.append(job.job_id)
            reset_count += 1

        db.commit()

        logger.info(f"Reset {reset_count} stuck jobs: {', '.join(job_ids)}")

        return {
            "success": True,
            "reset_count": reset_count,
            "job_ids": job_ids,
            "message": f"Reset {reset_count} stuck job(s) that were running for more than {timeout_minutes} minutes"
        }

    except Exception as e:
        logger.error(f"Failed to reset stuck jobs: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Change Review Endpoints
# ===================================================================

@router.get("/changes", response_model=List[CollectionChangeResponse])
async def list_changes(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    is_new_entity: Optional[bool] = Query(None, description="Filter by new entity flag"),
    reviewed_by: Optional[str] = Query(None, description="Filter by reviewer user_id"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    List detected changes for review.

    Returns paginated list of changes that need admin review.
    """
    query = db.query(CollectionChange)

    if status:
        query = query.filter(CollectionChange.status == status)
    if entity_type:
        query = query.filter(CollectionChange.entity_type == entity_type)
    if is_new_entity is not None:
        query = query.filter(CollectionChange.is_new_entity == is_new_entity)
    if reviewed_by:
        query = query.filter(CollectionChange.reviewed_by == reviewed_by)

    changes = query.order_by(
        CollectionChange.created_at.desc()
    ).limit(limit).offset(offset).all()

    return [CollectionChangeResponse.from_orm_with_db(change, db) for change in changes]


def _cascade_reject_community_changes(
    db: Session,
    community_id: Optional[int],
    community_job_id: Optional[str],
    reviewed_by: Optional[str]
) -> int:
    """
    Cascade rejection to all pending changes associated with a community.

    When a community change is rejected:
    1. Find all pending builder changes in that community
    2. Find all pending property changes in that community
    3. Auto-reject those changes with cascading note
    4. Cancel pending jobs spawned from the community job

    Args:
        db: Database session
        community_id: Community entity ID (if existing community)
        community_job_id: Job ID that created the community (for new communities)
        reviewed_by: User ID who triggered the cascade

    Returns:
        Number of cascaded rejections
    """
    cascaded_count = 0

    # Case 1: Existing community - reject by entity_id relationship
    if community_id:
        # Find all pending builder changes where builder is in this community
        # We need to check builder_communities table to find associated builders
        from model.profiles.builder import Builder, builder_communities
        from model.profiles.property import Property

        # Get all builders in this community
        builder_ids = db.query(builder_communities.c.builder_id).filter(
            builder_communities.c.community_id == community_id
        ).all()
        builder_ids = [b[0] for b in builder_ids]

        # Reject pending builder changes for builders in this community
        if builder_ids:
            pending_builder_changes = db.query(CollectionChange).filter(
                CollectionChange.entity_type == "builder",
                CollectionChange.entity_id.in_(builder_ids),
                CollectionChange.status == "pending"
            ).all()

            for change in pending_builder_changes:
                change.status = "rejected"
                change.reviewed_by = reviewed_by
                change.reviewed_at = datetime.utcnow()
                change.review_notes = f"Auto-rejected: Associated community (ID: {community_id}) was denied"
                cascaded_count += 1
                logger.info(f"Cascaded rejection to builder change {change.id} (builder {change.entity_id})")

        # Get all properties in this community
        property_ids = db.query(Property.id).filter(
            Property.community_id == community_id
        ).all()
        property_ids = [p[0] for p in property_ids]

        # Reject pending property changes for properties in this community
        if property_ids:
            pending_property_changes = db.query(CollectionChange).filter(
                CollectionChange.entity_type == "property",
                CollectionChange.entity_id.in_(property_ids),
                CollectionChange.status == "pending"
            ).all()

            for change in pending_property_changes:
                change.status = "rejected"
                change.reviewed_by = reviewed_by
                change.reviewed_at = datetime.utcnow()
                change.review_notes = f"Auto-rejected: Associated community (ID: {community_id}) was denied"
                cascaded_count += 1
                logger.info(f"Cascaded rejection to property change {change.id} (property {change.entity_id})")

    # Case 2: New community - reject by job hierarchy
    if community_job_id:
        # Find all changes from jobs that have this community job as parent
        pending_child_changes = db.query(CollectionChange).join(
            CollectionJob, CollectionChange.job_id == CollectionJob.job_id
        ).filter(
            CollectionJob.parent_entity_type == "community",
            CollectionJob.job_id != community_job_id,  # Don't reject the community change itself
            CollectionChange.status == "pending"
        ).all()

        # We need to check if the parent job matches our community job
        # Get the community job to check its entity_id or as a direct parent
        for change in pending_child_changes:
            child_job = db.query(CollectionJob).filter(
                CollectionJob.job_id == change.job_id
            ).first()

            # Check if this job's parent is our rejected community job
            if child_job:
                # For new communities, check if parent job matches
                parent_job = db.query(CollectionJob).filter(
                    CollectionJob.job_id == community_job_id
                ).first()

                if parent_job and child_job.parent_entity_type == "community":
                    # Check if they're related through job hierarchy
                    # This is a simplified check - for new entities we match by parent entity type
                    if change.entity_type in ["builder", "property"]:
                        change.status = "rejected"
                        change.reviewed_by = reviewed_by
                        change.reviewed_at = datetime.utcnow()
                        change.review_notes = f"Auto-rejected: Parent community from job {community_job_id} was denied"
                        cascaded_count += 1
                        logger.info(f"Cascaded rejection to {change.entity_type} change {change.id} from job {change.job_id}")

        # Cancel pending jobs that have this community job as parent
        pending_child_jobs = db.query(CollectionJob).filter(
            CollectionJob.parent_entity_type == "community",
            CollectionJob.status == "pending"
        ).all()

        for job in pending_child_jobs:
            # For new communities, we'd need a parent_job_id field to make this more precise
            # For now, we'll be conservative and not auto-cancel jobs without clear parent linkage
            logger.info(f"Found potential child job {job.job_id} but need parent_job_id for safe cancellation")

    if cascaded_count > 0:
        db.commit()
        logger.info(f"Cascaded {cascaded_count} rejections from community denial (community_id={community_id}, job_id={community_job_id})")

    return cascaded_count


@router.post("/changes/{change_id}/review")
async def review_change(
    change_id: int,
    request: ChangeReviewRequest,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Review a detected change.

    Admin can approve or reject the change.
    If approved and is_new_entity=True, creates the entity in the database.
    If rejecting a community, cascades rejection to associated builders/properties.
    """
    change = db.query(CollectionChange).filter(
        CollectionChange.id == change_id
    ).first()

    if not change:
        raise HTTPException(status_code=404, detail="Change not found")

    if request.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    # Update change status
    change.status = "approved" if request.action == "approve" else "rejected"
    # change.reviewed_by = current_user.user_id
    change.reviewed_at = datetime.utcnow()
    change.review_notes = request.notes

    # If rejecting a community, cascade the rejection to associated builders/properties
    cascaded_count = 0
    if request.action == "reject" and change.entity_type == "community":
        cascaded_count = _cascade_reject_community_changes(
            db=db,
            community_id=change.entity_id,  # Will be None for new communities
            community_job_id=change.job_id,  # Job that found this community
            reviewed_by=change.reviewed_by  # Pass through the reviewer
        )
        logger.info(f"Rejected community change {change_id}, cascaded {cascaded_count} related changes")

    # If approved and is a new entity, create it
    if request.action == "approve" and change.is_new_entity and change.proposed_entity_data:
        try:
            if change.entity_type == "community":
                from model.profiles.community import Community
                from src.collection.duplicate_detection import find_duplicate_community
                import uuid

                data = change.proposed_entity_data

                # FINAL SAFETY CHECK: Check for duplicates before creating
                duplicate_id, match_confidence, match_method = find_duplicate_community(
                    db=db,
                    name=data.get("name"),
                    city=data.get("city"),
                    state=data.get("state"),
                    website=data.get("website"),
                    address=data.get("location")
                )

                if duplicate_id:
                    # Duplicate found - reject the change and log warning
                    change.status = "rejected"
                    change.review_notes = f"Duplicate detected during approval: matched existing community ID {duplicate_id} (confidence: {match_confidence:.2f}, method: {match_method}). {request.notes or ''}"
                    db.commit()

                    logger.warning(
                        f"Blocked duplicate community creation during approval - Change {change_id} matched existing ID {duplicate_id} "
                        f"(confidence: {match_confidence:.2f}, method: {match_method})"
                    )

                    raise HTTPException(
                        status_code=409,
                        detail=f"Duplicate community detected: matches existing community ID {duplicate_id} with {match_confidence:.0%} confidence via {match_method}"
                    )

                community = Community(
                    community_id=f"CMY-{uuid.uuid4().hex[:8].upper()}",
                    name=data.get("name"),
                    city=data.get("city"),
                    state=data.get("state"),
                    postal_code=data.get("zip_code"),
                    address=data.get("location"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    about=data.get("description"),
                    homes=data.get("homes", 0),
                    residents=data.get("total_residents", 0) if data.get("total_residents") else 0,
                    founded_year=data.get("year_established"),
                    total_acres=data.get("total_acres"),
                    development_stage=data.get("development_stage"),
                    community_dues=str(data.get("hoa_fee")) if data.get("hoa_fee") else None,
                    monthly_fee=str(data.get("monthly_fee")) if data.get("monthly_fee") else None,
                    tax_rate=data.get("tax_rate"),
                    community_website_url=data.get("website"),
                    is_verified=False  # Collected communities start as unverified
                )
                db.add(community)

                # Update the change with the new entity_id
                db.flush()  # Get the ID
                change.entity_id = community.id

                logger.info(f"Created new community {community.community_id} from change {change_id}")

            elif change.entity_type == "builder":
                from model.profiles.builder import BuilderProfile, builder_communities, BuilderAward, BuilderCredential
                from src.collection.duplicate_detection import find_duplicate_builder
                import uuid
                import re

                data = change.proposed_entity_data

                # Get community_id from proposed data (this is the DB ID, not community_id string)
                community_id = data.get("community_id")

                # Extract city and state from headquarters_address if not provided separately
                city = data.get("city")
                state = data.get("state")
                postal_code = data.get("zip_code")

                if not city or not state:
                    address = data.get("address") or data.get("headquarters_address") or ""
                    # Try to parse city, state from address (e.g., "Houston, TX 77001")
                    match = re.search(r',\s*([A-Za-z\s]+),?\s*([A-Z]{2})\s*(\d{5})?', address)
                    if match:
                        if not city:
                            city = match.group(1).strip()
                        if not state:
                            state = match.group(2).strip()
                        if not postal_code and match.group(3):
                            postal_code = match.group(3).strip()

                # FINAL SAFETY CHECK: Check for duplicates before creating
                duplicate_id, match_confidence, match_method = find_duplicate_builder(
                    db=db,
                    name=data.get("name"),
                    city=city,
                    state=state,
                    website=data.get("website_url") or data.get("website"),
                    phone=data.get("phone"),
                    email=data.get("email")
                )

                if duplicate_id:
                    # Duplicate found - reject the change and log warning
                    change.status = "rejected"
                    change.review_notes = f"Duplicate detected during approval: matched existing builder ID {duplicate_id} (confidence: {match_confidence:.2f}, method: {match_method}). {request.notes or ''}"
                    db.commit()

                    logger.warning(
                        f"Blocked duplicate builder creation during approval - Change {change_id} matched existing ID {duplicate_id} "
                        f"(confidence: {match_confidence:.2f}, method: {match_method})"
                    )

                    raise HTTPException(
                        status_code=409,
                        detail=f"Duplicate builder detected: matches existing builder ID {duplicate_id} with {match_confidence:.0%} confidence via {match_method}"
                    )

                # Generate unique builder_id
                timestamp = int(time.time())
                random_suffix = uuid.uuid4().hex[:6].upper()
                builder_id_str = f"BLD-{timestamp}-{random_suffix}"

                # Create builder with default admin user
                builder = BuilderProfile(
                    builder_id=builder_id_str,
                    user_id="USR-1763443503-N3UTFX",  # Default admin user
                    name=data.get("name"),
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    headquarters_address=data.get("address") or data.get("headquarters_address"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    website=data.get("website_url") or data.get("website"),
                    founded_year=data.get("year_founded") or data.get("founded_year"),
                    description=data.get("description"),
                    rating=data.get("rating"),
                    employee_count=data.get("employee_count"),
                    price_range_min=data.get("price_range_min"),
                    price_range_max=data.get("price_range_max"),
                    review_count=data.get("review_count"),
                    verified=0  # Start as unverified
                )
                db.add(builder)
                db.flush()  # Get the builder ID

                change.entity_id = builder.id

                # Create awards if provided
                awards = data.get("awards", [])
                if awards and isinstance(awards, list):
                    for award_data in awards:
                        if isinstance(award_data, dict):
                            award = BuilderAward(
                                builder_id=builder.id,
                                title=award_data.get("title") or award_data.get("name"),
                                awarded_by=award_data.get("awarded_by") or award_data.get("issuer"),
                                year=award_data.get("year")
                            )
                            db.add(award)
                    logger.info(f"Created {len(awards)} awards for builder {builder.builder_id}")

                # Create credentials (certifications/licenses) if provided
                certifications = data.get("certifications", [])
                if certifications and isinstance(certifications, list):
                    for cert_data in certifications:
                        if isinstance(cert_data, dict):
                            credential = BuilderCredential(
                                builder_id=builder.id,
                                name=cert_data.get("name") or cert_data.get("title"),
                                credential_type="certification"
                            )
                            db.add(credential)
                        elif isinstance(cert_data, str):
                            # Handle simple string certifications
                            credential = BuilderCredential(
                                builder_id=builder.id,
                                name=cert_data,
                                credential_type="certification"
                            )
                            db.add(credential)
                    logger.info(f"Created {len(certifications)} credentials for builder {builder.builder_id}")

                # Link builder to community if community_id provided
                if community_id:
                    try:
                        stmt = builder_communities.insert().values(
                            builder_id=builder.id,
                            community_id=community_id
                        )
                        db.execute(stmt)
                        logger.info(f"Linked builder {builder.builder_id} to community ID {community_id}")
                    except Exception as e:
                        logger.warning(f"Failed to link builder to community {community_id}: {e}")

                logger.info(f"Created new builder {builder.builder_id} from change {change_id}")

            # Add support for other entity types here (property, etc.)

        except Exception as e:
            logger.error(f"Failed to create entity from change {change_id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create entity: {str(e)}")

    db.commit()

    logger.info(f"Change {change_id} {request.action}d by admin")

    # Build response message
    message = f"Change {request.action}d successfully"
    if cascaded_count > 0:
        message += f" (cascaded to {cascaded_count} related change{'s' if cascaded_count != 1 else ''})"

    return {"message": message, "cascaded_changes": cascaded_count if cascaded_count > 0 else None}


@router.post("/changes/review-bulk")
async def review_changes_bulk(
    request: BulkChangeReviewRequest,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Review multiple changes at once.

    Allows bulk approve or reject of changes.
    """
    if request.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    changes = db.query(CollectionChange).filter(
        CollectionChange.id.in_(request.change_ids)
    ).all()

    if not changes:
        raise HTTPException(status_code=404, detail="No changes found")

    # Update all changes
    from datetime import datetime
    for change in changes:
        change.status = "approved" if request.action == "approve" else "rejected"
        # change.reviewed_by = current_user.user_id
        change.reviewed_at = datetime.utcnow()
        change.review_notes = request.notes

    db.commit()

    logger.info(
        f"{len(changes)} changes {request.action}d by admin"
    )

    return {
        "message": f"{len(changes)} changes {request.action}d successfully",
        "count": len(changes)
    }


@router.get("/changes/stats")
async def get_change_stats(
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get statistics about pending changes.

    Returns counts by status and entity type.
    """
    from sqlalchemy import func

    stats = db.query(
        CollectionChange.status,
        CollectionChange.entity_type,
        func.count(CollectionChange.id).label("count")
    ).group_by(
        CollectionChange.status,
        CollectionChange.entity_type
    ).all()

    # Format response
    result = {
        "by_status": {},
        "by_entity_type": {},
        "total_pending": 0
    }

    for status, entity_type, count in stats:
        if status not in result["by_status"]:
            result["by_status"][status] = 0
        result["by_status"][status] += count

        if entity_type not in result["by_entity_type"]:
            result["by_entity_type"][entity_type] = 0
        result["by_entity_type"][entity_type] += count

        if status == "pending":
            result["total_pending"] += count

    return result


@router.post("/jobs/execute-pending")
async def execute_pending_jobs(
    limit: int = Query(1, ge=1, le=1, description="Max number of jobs to execute (set to 1 for sequential execution)"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Execute pending collection jobs asynchronously (one at a time).

    Starts ONE pending job in the background and returns immediately.
    Jobs execute in priority order (highest priority first).
    Use GET /jobs/{job_id} to check status.

    NOTE: Only one job runs at a time to prevent resource conflicts.
    """
    try:
        # Check if any job is currently running
        running_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "running"
        ).count()

        if running_jobs > 0:
            return {
                "total_pending": db.query(CollectionJob).filter(
                    CollectionJob.status == "pending"
                ).count(),
                "started": 0,
                "job_ids": [],
                "message": f"Cannot start new job: {running_jobs} job(s) already running. Only one job can run at a time."
            }

        # Get next pending job (only one)
        pending_jobs = db.query(CollectionJob).filter(
            CollectionJob.status == "pending"
        ).order_by(
            CollectionJob.priority.desc(),
            CollectionJob.created_at.asc()
        ).limit(1).all()

        if not pending_jobs:
            return {
                "total_pending": 0,
                "started": 0,
                "job_ids": [],
                "message": "No pending jobs to execute"
            }

        job_ids = []

        # Start single job in background
        for job in pending_jobs:
            job_id = job.job_id
            job_ids.append(job_id)

            # Mark as running immediately
            job.status = "running"
            job.started_at = datetime.utcnow()

            logger.info(f"⏳ Starting background execution for job {job_id} (sequential mode)")

        db.commit()

        # Execute jobs in background (after response is sent)
        def execute_jobs_background():
            """Execute jobs in background thread with proper error handling"""
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config.settings import DB_URL

            # Create new DB session for background thread
            engine = create_engine(DB_URL, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            bg_db = SessionLocal()

            try:
                executor = JobExecutor(bg_db)
                for job_id in job_ids:
                    job_failed = False
                    error_message = None

                    try:
                        logger.info(f"🔵 Executing job {job_id} in background")
                        executor.execute_job(job_id)
                        logger.info(f"✅ Job {job_id} completed successfully")
                    except Exception as e:
                        job_failed = True
                        error_message = str(e)
                        logger.error(f"❌ Background job {job_id} failed: {error_message}", exc_info=True)

                        # Mark job as failed in database
                        try:
                            failed_job = bg_db.query(CollectionJob).filter(
                                CollectionJob.job_id == job_id
                            ).first()

                            if failed_job and failed_job.status == "running":
                                failed_job.status = "failed"
                                failed_job.error_message = f"Background execution failed: {error_message}"
                                failed_job.completed_at = datetime.utcnow()
                                bg_db.commit()
                                logger.info(f"🔧 Marked job {job_id} as failed in database")
                        except Exception as db_err:
                            logger.error(f"Failed to update job status for {job_id}: {db_err}")
                            bg_db.rollback()
            except Exception as thread_err:
                logger.error(f"❌ Background thread crashed: {str(thread_err)}", exc_info=True)
            finally:
                bg_db.close()
                logger.info(f"🏁 Background thread finished processing {len(job_ids)} job(s)")

        # Use threading to execute in background
        import threading
        thread = threading.Thread(target=execute_jobs_background)
        thread.daemon = True
        thread.start()

        total_pending = db.query(CollectionJob).filter(
            CollectionJob.status == "pending"
        ).count()

        return {
            "total_pending": total_pending,
            "started": len(job_ids),
            "job_ids": job_ids,
            "message": f"Started job {job_ids[0]} in background (sequential mode: 1 job at a time). {total_pending} job(s) remaining in queue. Poll /jobs/{{job_id}} for status."
        }

    except Exception as e:
        logger.error(f"Failed to start pending jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ================================================================
# Data Coverage & Backfill Endpoints
# ================================================================

@router.get("/coverage/community-builders")
async def get_community_builder_coverage(
    db: Session = Depends(get_db)
):
    """
    Get community-builder data coverage statistics.

    Returns information about how many communities have builders linked.
    """
    try:
        from sqlalchemy import text

        # Total communities
        total_result = db.execute(text("SELECT COUNT(*) FROM communities")).scalar()
        total_communities = total_result or 0

        # Communities with builders
        with_builders_result = db.execute(text("""
            SELECT COUNT(DISTINCT community_id)
            FROM builder_communities
        """)).scalar()
        communities_with_builders = with_builders_result or 0

        # Communities without builders
        communities_without_builders = total_communities - communities_with_builders

        # Coverage percentage
        coverage_pct = (communities_with_builders / total_communities * 100) if total_communities > 0 else 0

        # Total associations
        associations_result = db.execute(text("SELECT COUNT(*) FROM builder_communities")).scalar()
        total_associations = associations_result or 0

        # Average builders per community (for communities that have builders)
        avg_builders = (total_associations / communities_with_builders) if communities_with_builders > 0 else 0

        # Get communities without builders (limited to 20)
        missing_result = db.execute(text("""
            SELECT c.id, c.name, c.city, c.state
            FROM communities c
            LEFT JOIN builder_communities bc ON c.id = bc.community_id
            WHERE bc.community_id IS NULL
            ORDER BY c.name
            LIMIT 20
        """))

        communities_missing = [
            {
                "id": row.id,
                "name": row.name,
                "city": row.city,
                "state": row.state,
                "location": f"{row.city}, {row.state}" if row.city and row.state else None
            }
            for row in missing_result.fetchall()
        ]

        return {
            "total_communities": total_communities,
            "communities_with_builders": communities_with_builders,
            "communities_without_builders": communities_without_builders,
            "coverage_percentage": round(coverage_pct, 1),
            "total_builder_associations": total_associations,
            "average_builders_per_community": round(avg_builders, 2),
            "communities_missing_builders": communities_missing
        }

    except Exception as e:
        logger.error(f"Failed to get coverage stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill/community-builders")
async def backfill_community_builders(
    priority: int = Query(7, description="Priority for created jobs (1-10)", ge=1, le=10),
    dry_run: bool = Query(True, description="Preview without creating jobs"),
    db: Session = Depends(get_db)
):
    """
    Create builder discovery jobs for communities without builders.

    This endpoint implements the backfill functionality to fill data gaps
    in the cascading collection workflow (communities → builders → properties).
    """
    try:
        from sqlalchemy import text

        # Get communities without builders
        result = db.execute(text("""
            SELECT c.id, c.name, c.city, c.state, c.community_id
            FROM communities c
            LEFT JOIN builder_communities bc ON c.id = bc.community_id
            WHERE bc.community_id IS NULL
            ORDER BY c.name
        """))

        communities_without_builders = result.fetchall()

        if not communities_without_builders:
            return {
                "message": "All communities already have builders linked",
                "communities_found": 0,
                "jobs_created": 0,
                "dry_run": dry_run
            }

        jobs_preview = []
        jobs_created = []

        for row in communities_without_builders:
            location = f"{row.city}, {row.state}" if row.city and row.state else None
            search_query = f"{row.name} builders"
            if location:
                search_query += f" {location}"

            job_data = {
                "community_id": row.id,
                "community_name": row.name,
                "location": location,
                "search_query": search_query,
                "priority": priority
            }

            jobs_preview.append(job_data)

            if not dry_run:
                # Create the actual job
                job = CollectionJob(
                    entity_type="builder",
                    entity_id=None,
                    job_type="discovery",
                    parent_entity_type="community",
                    parent_entity_id=row.id,
                    status="pending",
                    priority=priority,
                    search_query=search_query,
                    search_filters={
                        "community_id": row.id,
                        "community_name": row.name,
                        "location": location
                    },
                    initiated_by="system_backfill"
                )
                db.add(job)
                jobs_created.append({
                    "job_id": job.job_id,
                    "community_name": row.name,
                    "community_id": row.id
                })

        if not dry_run:
            db.commit()
            logger.info(f"Created {len(jobs_created)} backfill jobs for communities without builders")

        return {
            "message": f"{'Preview:' if dry_run else 'Created'} {len(jobs_preview)} builder discovery job(s)",
            "communities_found": len(communities_without_builders),
            "jobs_created": len(jobs_created) if not dry_run else 0,
            "dry_run": dry_run,
            "jobs_preview": jobs_preview if dry_run else None,
            "jobs": jobs_created if not dry_run else None,
            "priority": priority
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to backfill community builders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
