"""
Admin Collection Routes

API endpoints for managing data collection jobs.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from config.db import get_db
from model.collection import CollectionJob, CollectionChange, EntityMatch
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


class CollectionChangeResponse(BaseModel):
    """Response with change details."""
    id: int
    job_id: str
    entity_type: str
    entity_id: Optional[int]
    is_new_entity: bool
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    change_type: str
    status: str
    confidence: float
    source_url: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


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
        # Route to appropriate job creator
        if request.entity_type == "community":
            job = create_community_collection_job(
                db=db,
                community_id=request.entity_id,
                community_name=request.search_query,
                location=request.location,
                # initiated_by=current_user.user_id
            )
        elif request.entity_type == "builder":
            job = create_builder_collection_job(
                db=db,
                builder_id=request.entity_id,
                builder_name=request.search_query,
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


@router.post("/jobs/execute-pending")
async def execute_pending_jobs(
    limit: int = Query(10, le=50, description="Max jobs to execute"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Execute pending jobs in priority order.

    Processes multiple pending jobs in batch.
    """
    try:
        executor = JobExecutor(db)
        executor.execute_pending_jobs(limit=limit)

        return {"message": f"Executed up to {limit} pending jobs"}

    except Exception as e:
        logger.error(f"Failed to execute pending jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Change Review Endpoints
# ===================================================================

@router.get("/changes", response_model=List[CollectionChangeResponse])
async def list_changes(
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    is_new_entity: Optional[bool] = Query(None, description="Filter by new entity flag"),
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

    changes = query.order_by(
        CollectionChange.created_at.desc()
    ).limit(limit).offset(offset).all()

    return [CollectionChangeResponse.from_orm(change) for change in changes]


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

    db.commit()

    logger.info(f"Change {change_id} {request.action}d by admin")

    return {"message": f"Change {request.action}d successfully"}


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
