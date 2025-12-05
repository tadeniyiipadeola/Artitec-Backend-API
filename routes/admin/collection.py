"""
Admin Collection Routes

API endpoints for managing data collection jobs.
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from config.db import get_db
from model.collection import CollectionJob, CollectionChange, EntityMatch, CollectionJobLog
from model.property.property import Property
from src.collection.job_executor import (
    JobExecutor,
    create_community_collection_job,
    create_builder_collection_job,
    create_property_inventory_job,
    create_bulk_property_discovery_jobs,
    create_bulk_builder_update_jobs
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["Admin - Data Collection"])


# ===================================================================
# Helper Functions
# ===================================================================

def enrich_job_with_property_data(job, db: Session):
    """Enrich job object with property details if entity_type is property."""
    if job.entity_type == "property":
        # First try to get property data if entity_id is set (completed jobs)
        if job.entity_id:
            property_obj = db.query(Property).filter(Property.id == job.entity_id).first()
            if property_obj:
                job.property_title = property_obj.title
                job.property_description = property_obj.description
                job.property_community_id = property_obj.community_id
                job.property_builder_id = property_obj.builder_id
                job.property_move_in_date = property_obj.move_in_date
                job.property_builder_plan_name = property_obj.builder_plan_name
                return job

        # If no entity_id, try to get builder/community info from search_filters
        if job.search_filters:
            import json
            try:
                filters = json.loads(job.search_filters) if isinstance(job.search_filters, str) else job.search_filters
                builder_id = filters.get('builder_id')
                community_id = filters.get('community_id')

                # Get builder name
                if builder_id:
                    from model.profiles.builder import BuilderProfile
                    builder = db.query(BuilderProfile).filter(BuilderProfile.id == builder_id).first()
                    if builder:
                        job.property_builder_id = builder_id
                        job.property_builder_name = builder.name

                # Get community name - use as the main title
                if community_id:
                    from model.profiles.community import Community
                    # community_id can be either integer (DB ID) or string (public CMY-XXX ID)
                    if isinstance(community_id, int):
                        community = db.query(Community).filter(Community.id == community_id).first()
                    else:
                        community = db.query(Community).filter(Community.community_id == community_id).first()
                    if community:
                        job.property_community_id = community_id
                        job.property_community_name = community.name
                        job.property_title = community.name

                        # Add community location to location field
                        location_parts = [community.city, community.state]
                        location_str = ", ".join([p for p in location_parts if p])
                        if location_str:
                            job.location = location_str
            except Exception as e:
                # If JSON parsing fails or query fails, log and skip enrichment
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to enrich property job {job.job_id}: {e}", exc_info=True)
    return job


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
    search_filters: Optional[dict] = None
    items_found: int
    changes_detected: int
    approved_changes: int
    new_entities_found: int
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    # Property details (for property jobs)
    property_title: Optional[str] = None
    property_description: Optional[str] = None
    property_community_id: Optional[int] = None
    property_community_name: Optional[str] = None
    property_builder_id: Optional[int] = None
    property_builder_name: Optional[str] = None
    property_move_in_date: Optional[str] = None
    property_builder_plan_name: Optional[str] = None

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
            'search_filters': obj.search_filters,
            'items_found': obj.items_found or 0,
            'changes_detected': obj.changes_detected or 0,
            'approved_changes': obj.approved_changes or 0,
            'new_entities_found': obj.new_entities_found or 0,
            'error_message': obj.error_message,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'started_at': obj.started_at.isoformat() if obj.started_at else None,
            'completed_at': obj.completed_at.isoformat() if obj.completed_at else None,
            'property_title': getattr(obj, 'property_title', None),
            'property_description': getattr(obj, 'property_description', None),
            'property_community_id': getattr(obj, 'property_community_id', None),
            'property_community_name': getattr(obj, 'property_community_name', None),
            'property_builder_id': getattr(obj, 'property_builder_id', None),
            'property_builder_name': getattr(obj, 'property_builder_name', None),
            'property_move_in_date': getattr(obj, 'property_move_in_date', None),
            'property_builder_plan_name': getattr(obj, 'property_builder_plan_name', None),
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
    property_bedrooms: Optional[int] = None  # For property entities - bedroom count
    property_bathrooms: Optional[float] = None  # For property entities - bathroom count
    entity_community_id: Optional[str] = None  # Current community_id of the entity (for orphaned detection)
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
        property_bedrooms = None
        property_bathrooms = None
        entity_community_id = None

        # Fetch reviewer name if reviewed_by is set
        if obj.reviewed_by:
            try:
                from model.user import Users
                reviewer = db.query(Users).filter(Users.user_id == obj.reviewed_by).first()
                if reviewer:
                    reviewed_by_name = f"{reviewer.first_name} {reviewer.last_name}"
            except Exception as e:
                logger.warning(f"Failed to fetch reviewer name for user_id {obj.reviewed_by}: {e}")

        # Handle new properties - extract title, bedrooms, and bathrooms from proposed_entity_data
        if obj.entity_type == "property" and obj.is_new_entity and obj.proposed_entity_data:
            try:
                entity_name = obj.proposed_entity_data.get("title") or obj.proposed_entity_data.get("address1") or "Unknown Property"
                property_bedrooms = obj.proposed_entity_data.get("bedrooms")
                property_bathrooms = obj.proposed_entity_data.get("bathrooms")
            except Exception as e:
                logger.warning(f"Failed to extract property display info: {e}")

        # Handle awards and credentials - fetch parent entity info
        elif obj.entity_type in ("award", "credential") and obj.is_new_entity and obj.proposed_entity_data:
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
                    # community_id can be either integer (DB ID) or string (public CMY-XXX ID)
                    if isinstance(community_id, int):
                        community = db.query(Community).filter(Community.id == community_id).first()
                    else:
                        community = db.query(Community).filter(Community.community_id == community_id).first()
                    if community:
                        entity_name = community.name
                        parent_entity_type = "community"
                        parent_entity_id = community_id
            except Exception as e:
                logger.warning(f"Failed to fetch parent entity for {obj.entity_type}: {e}")

        # Handle field-level changes - fetch entity name, community_id, and communities for builders
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
                        # Store the community_id for orphaned detection
                        entity_community_id = entity.community_id
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
                    from model.property.property import Property
                    entity = db.query(Property).filter(Property.id == obj.entity_id).first()
                    if entity:
                        entity_name = entity.title or entity.address1
                        # Store the community_id for orphaned detection
                        entity_community_id = entity.community_id
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
            'property_bedrooms': property_bedrooms,
            'property_bathrooms': property_bathrooms,
            'entity_community_id': entity_community_id,
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
        if request.job_type == "discovery" and request.entity_type != "property":
            # For discovery jobs (except property jobs which use existing communities):
            # - search_query is optional (blank = search all in location)
            # - location is required when search_query is blank
            if not request.search_query and not request.location:
                raise HTTPException(
                    status_code=400,
                    detail="Either search_query or location is required for discovery jobs"
                )
        elif request.job_type == "update":
            # For update jobs, entity_id is required UNLESS it's a bulk builder update
            # (builder entity type with no entity_id and no search_query = bulk update)
            is_bulk_builder_update = (request.entity_type == "builder" and
                                     not request.entity_id and
                                     not request.search_query)

            if not request.entity_id and not is_bulk_builder_update:
                raise HTTPException(
                    status_code=400,
                    detail="entity_id is required for update jobs (or omit both entity_id and search_query for builder bulk update)"
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
            # For update job type without specific builder (bulk update mode)
            if request.job_type == "update" and not request.entity_id and not request.search_query:
                # Bulk builder update: Create update jobs for all existing builders
                result = create_bulk_builder_update_jobs(
                    db=db,
                    priority=request.priority or 5,
                    # initiated_by=current_user.user_id
                )

                # Return summary response instead of single job
                return {
                    "message": f"Created {result['jobs_created']} builder update jobs",
                    "jobs_created": result['jobs_created'],
                    "builders_processed": result['builders_processed'],
                    "job_ids": result['job_ids'][:10]  # Return first 10 job IDs
                }

            # Single builder job (discovery or specific update)
            job = create_builder_collection_job(
                db=db,
                builder_id=request.entity_id,
                builder_name=request.search_query or None,  # None if blank
                community_id=request.community_id,
                location=request.location,
                # initiated_by=current_user.user_id
            )
        elif request.entity_type == "property":
            # For discovery jobs without specific IDs, create bulk jobs for all communities
            if request.job_type == "discovery" and not request.builder_id and not request.community_id:
                # Bulk property discovery: Create jobs for all builder-community pairs
                result = create_bulk_property_discovery_jobs(
                    db=db,
                    priority=request.priority or 5,
                    # initiated_by=current_user.user_id
                )

                # Return summary response instead of single job
                return {
                    "message": f"Created {result['jobs_created']} property inventory jobs",
                    "jobs_created": result['jobs_created'],
                    "communities_processed": result['communities_processed'],
                    "builder_community_pairs": result['builder_community_pairs'],
                    "job_ids": result['job_ids'][:10]  # Return first 10 job IDs
                }

            # For non-discovery property jobs, require builder_id and community_id
            if request.job_type != "discovery":
                if not request.builder_id or not request.community_id:
                    raise HTTPException(
                        status_code=400,
                        detail="builder_id and community_id required for property inventory/update jobs"
                    )

            # Single property inventory job (specific builder + community)
            job = create_property_inventory_job(
                db=db,
                builder_id=request.builder_id,
                community_id=request.community_id,
                location=request.location,
                priority=request.priority or 3,
                #initiated_by=current_user.user_id
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

    # Enrich jobs with property data where applicable
    enriched_jobs = [enrich_job_with_property_data(job, db) for job in jobs]

    return CollectionJobListResponse(
        jobs=[CollectionJobResponse.from_orm(job) for job in enriched_jobs],
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

    # Enrich with property data if applicable
    job = enrich_job_with_property_data(job, db)

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


@router.post("/jobs/{job_id}/approve-all")
async def approve_all_job_changes(
    job_id: str,
    notes: str = Query(None, description="Optional notes for the bulk approval"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Approve all pending changes detected by a specific job.

    This endpoint allows admin to bulk-approve all changes from a job,
    which is useful after reviewing the job details and deciding all changes are valid.
    """
    try:
        # Verify job exists
        job = db.query(CollectionJob).filter(
            CollectionJob.job_id == job_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Get all pending changes for this job
        pending_changes = db.query(CollectionChange).filter(
            CollectionChange.job_id == job_id,
            CollectionChange.status == "pending"
        ).all()

        if not pending_changes:
            return {
                "message": "No pending changes found for this job",
                "job_id": job_id,
                "approved_count": 0,
                "failed_count": 0,
                "errors": []
            }

        approved_count = 0
        failed_count = 0
        errors = []

        logger.info(f"Bulk approving {len(pending_changes)} pending changes for job {job_id}")

        # Process each change by calling the review endpoint for each
        for change in pending_changes:
            try:
                # Create review request
                review_request = ChangeReviewRequest(
                    action="approve",
                    notes=notes or f"Bulk approved from job {job_id}"
                )

                # Call the existing review_change function directly
                await review_change(
                    change_id=change.id,
                    request=review_request,
                    db=db
                )

                approved_count += 1

            except HTTPException as http_exc:
                # Handle HTTP exceptions (like 409 Conflict for duplicates)
                failed_count += 1
                error_msg = f"Change {change.id} ({change.entity_type}): {http_exc.detail}"
                errors.append(error_msg)
                logger.warning(f"Failed to approve change {change.id}: {http_exc.detail}")
                # Continue with other changes
                continue
            except Exception as e:
                failed_count += 1
                error_msg = f"Change {change.id} ({change.entity_type}): {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to approve change {change.id}: {str(e)}", exc_info=True)
                # Continue with other changes
                continue

        # Update the job's approved_changes count
        if approved_count > 0:
            job.approved_changes = (job.approved_changes or 0) + approved_count
            db.commit()
            logger.info(f"Updated job {job_id} approved_changes count to {job.approved_changes}")

        # Note: review_change already commits each change, so no need for additional commit

        result = {
            "message": f"Bulk approval completed for job {job_id}",
            "job_id": job_id,
            "total_changes": len(pending_changes),
            "approved_count": approved_count,
            "failed_count": failed_count,
            "errors": errors if errors else None
        }

        logger.info(f"Bulk approval completed for job {job_id}: {approved_count} approved, {failed_count} failed")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk approve changes for job {job_id}: {str(e)}", exc_info=True)
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

                # Auto-create amenities if provided in collected data
                amenities_data = data.get("amenities", [])
                if amenities_data and isinstance(amenities_data, list):
                    from model.profiles.community import CommunityAmenity

                    amenities_created = 0
                    for amenity_name in amenities_data:
                        if amenity_name and isinstance(amenity_name, str):
                            amenity = CommunityAmenity(
                                community_id=community.id,
                                name=amenity_name.strip(),
                                gallery=[]  # Empty gallery initially
                            )
                            db.add(amenity)
                            amenities_created += 1

                    if amenities_created > 0:
                        logger.info(f"Auto-created {amenities_created} amenities for community {community.community_id}")

            elif change.entity_type == "builder":
                from model.profiles.builder import BuilderProfile, builder_communities, BuilderAward, BuilderCredential
                from model.profiles.community import Community
                from src.collection.duplicate_detection import find_duplicate_builder
                import re

                data = change.proposed_entity_data

                # Get community_id from proposed data (this is the public string ID like CMY-XXX, not the internal DB integer ID)
                community_id = data.get("community_id")

                # === ORPHANED BUILDER: TRIGGER COMMUNITY DISCOVERY ===
                if not community_id:
                    # Builder has no community link - trigger community discovery job
                    builder_name = data.get("name", "Unknown Builder")

                    # PRIORITY 1: Use community_name + community_city + community_state if available
                    community_name = data.get("community_name")
                    community_city = data.get("community_city")
                    community_state = data.get("community_state")

                    # PRIORITY 2: Fallback to builder's city/state
                    city = data.get("city")
                    state = data.get("state")

                    # PRIORITY 3: Extract from address
                    address = data.get("headquarters_address") or data.get("sales_office_address") or data.get("address")

                    logger.info(f"Orphaned builder detected: {builder_name}")
                    logger.info(f"  Community data: name={community_name}, city={community_city}, state={community_state}")
                    logger.info(f"  Builder location: city={city}, state={state}")

                    # Build search query from location data
                    search_query = None

                    # Best case: We have the community name and location
                    if community_name and community_city and community_state:
                        search_query = f"{community_name}, {community_city}, {community_state}"
                        logger.info(f"Using community data for search: {search_query}")
                    # Good case: We have builder's city/state
                    elif city and state:
                        search_query = f"{city}, {state}"
                        logger.info(f"Using builder location for search: {search_query}")
                    # Last resort: Try to extract from address
                    elif address:
                        import re
                        addr_match = re.search(r',\s*([A-Za-z\s]+),?\s*([A-Z]{2})', address)
                        if addr_match:
                            search_query = f"{addr_match.group(1).strip()}, {addr_match.group(2).strip()}"
                            logger.info(f"Extracted location from address: {search_query}")

                    if search_query:
                        # Create community discovery job
                        logger.info(f"Creating community discovery job for location: {search_query}")

                        # Create job directly
                        job_id_str = f"JOB-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

                        community_job = CollectionJob(
                            job_id=job_id_str,
                            entity_type="community",
                            job_type="discovery",
                            search_query=search_query,
                            priority=9,  # High priority since admin is waiting
                            status="pending"
                        )
                        db.add(community_job)
                        db.flush()

                        if community_job:
                            # Commit the job to database first
                            db.commit()

                            # Start the job immediately in background with a new DB session
                            import threading
                            from sqlalchemy.orm import sessionmaker
                            from config.settings import DB_URL
                            from sqlalchemy import create_engine

                            def run_job():
                                try:
                                    # Create a new database session for the background thread
                                    engine = create_engine(DB_URL)
                                    SessionLocal = sessionmaker(bind=engine)
                                    thread_db = SessionLocal()

                                    try:
                                        from src.collection.job_executor import JobExecutor
                                        executor = JobExecutor(thread_db)
                                        executor.execute_job(community_job.job_id)
                                    finally:
                                        thread_db.close()
                                        engine.dispose()
                                except Exception as e:
                                    logger.error(f"Community discovery job failed: {e}")

                            thread = threading.Thread(target=run_job, daemon=True)
                            thread.start()

                            logger.info(f"Started community discovery job {community_job.job_id} for orphaned builder")

                            # Return info to admin that job was created
                            return JSONResponse(
                                status_code=202,
                                content={
                                    "message": f"Community discovery job started for {builder_name}",
                                    "job_id": community_job.job_id,
                                    "search_query": search_query,
                                    "community_name": community_name,
                                    "instruction": "Please wait for the community discovery job to complete, then retry approving this builder."
                                }
                            )
                        else:
                            logger.warning(f"Failed to create community discovery job for orphaned builder")
                    else:
                        logger.warning(f"Cannot create community discovery job: insufficient location data for {builder_name}")
                        # Let it continue - builder will be created without community link

                # AUTO-APPROVE PARENT COMMUNITY if needed (confidence >= 0.75)
                if community_id:
                    # Check if community exists in database
                    # community_id can be either integer (DB ID) or string (public CMY-XXX ID)
                    if isinstance(community_id, int):
                        community = db.query(Community).filter(Community.id == community_id).first()
                    else:
                        community = db.query(Community).filter(Community.community_id == community_id).first()

                    if not community:
                        # Community doesn't exist yet - check if there's a pending change to approve
                        logger.info(f"Builder references community ID {community_id} which doesn't exist yet - checking for pending community change")

                        # Find the pending community change
                        community_change = db.query(CollectionChange).filter(
                            CollectionChange.entity_type == "community",
                            CollectionChange.entity_id == community_id,
                            CollectionChange.status == "pending",
                            CollectionChange.is_new_entity == True
                        ).first()

                        if community_change:
                            # Check confidence score
                            community_data = community_change.proposed_entity_data or {}
                            confidence = community_data.get("confidence", 0.0)

                            # Handle both nested and flat confidence formats
                            if isinstance(confidence, dict):
                                confidence = confidence.get("overall", 0.0)

                            if confidence >= 0.75:
                                logger.info(f"Auto-approving parent community (change {community_change.id}) with confidence {confidence:.2%}")

                                # Auto-approve the community change
                                try:
                                    # Create the community (reusing existing community creation logic)
                                    timestamp = int(time.time())
                                    random_suffix = uuid.uuid4().hex[:6].upper()
                                    community_id_str = f"CMY-{timestamp}-{random_suffix}"

                                    community = Community(
                                        community_id=community_id_str,
                                        name=community_data.get("name"),
                                        city=community_data.get("city"),
                                        state=community_data.get("state"),
                                        zip_code=community_data.get("zip_code"),
                                        description=community_data.get("description"),
                                        builder_name=community_data.get("builder"),
                                        price_range=community_data.get("price_range"),
                                        home_styles=community_data.get("home_styles", []),
                                        total_homes=community_data.get("total_homes"),
                                        available_homes=community_data.get("available_homes"),
                                        website_url=community_data.get("website_url") or community_data.get("website"),
                                        sales_office_phone=community_data.get("sales_office_phone") or community_data.get("phone"),
                                        sales_office_address=community_data.get("sales_office_address"),
                                        hoa_fee=community_data.get("hoa_fee"),
                                        schools=community_data.get("schools", {}),
                                        data_source=community_data.get("data_source", "collected"),
                                        data_confidence=confidence
                                    )
                                    db.add(community)
                                    db.flush()

                                    # Update the change record
                                    community_change.status = "approved"
                                    community_change.entity_id = community.id
                                    community_change.reviewed_by = request.user_id
                                    community_change.reviewed_at = func.current_timestamp()
                                    community_change.review_notes = f"Auto-approved (confidence: {confidence:.2%}) as dependency for builder approval"

                                    # Auto-create amenities if provided
                                    amenities_data = community_data.get("amenities", [])
                                    if amenities_data and isinstance(amenities_data, list):
                                        from model.profiles.community import CommunityAmenity

                                        amenities_created = 0
                                        for amenity_name in amenities_data:
                                            if amenity_name and isinstance(amenity_name, str):
                                                amenity = CommunityAmenity(
                                                    community_id=community.id,
                                                    name=amenity_name.strip(),
                                                    gallery=[]
                                                )
                                                db.add(amenity)
                                                amenities_created += 1

                                        if amenities_created > 0:
                                            logger.info(f"Auto-created {amenities_created} amenities for auto-approved community {community.community_id}")

                                    db.flush()
                                    logger.info(f"Auto-approved and created community {community.community_id} (ID: {community.id}) for builder")

                                    # Update community_id to use the newly created community
                                    community_id = community.id

                                except Exception as e:
                                    logger.error(f"Failed to auto-approve parent community: {e}")
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Failed to auto-approve parent community (confidence {confidence:.2%}): {str(e)}"
                                    )
                            else:
                                # Confidence too low for auto-approval
                                logger.warning(f"Cannot approve builder: parent community (change {community_change.id}) has confidence {confidence:.2%} < 75% threshold")
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Cannot approve builder: parent community has insufficient confidence ({confidence:.2%} < 75%). Please manually review and approve the community first."
                                )
                        else:
                            # No pending change found
                            logger.warning(f"Cannot approve builder: community ID {community_id} not found and no pending change exists")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Cannot approve builder: parent community (ID {community_id}) does not exist. Please approve the community first."
                            )

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
                # Pass community_id to check if builder already exists in THIS community
                duplicate_id, match_confidence, match_method = find_duplicate_builder(
                    db=db,
                    name=data.get("name"),
                    city=city,
                    state=state,
                    website=data.get("website_url") or data.get("website"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    community_id=community_id  # Only reject if duplicate in same community
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
                    title=data.get("title"),  # Office type (Sales Office, etc.)
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    headquarters_address=data.get("address") or data.get("headquarters_address"),
                    sales_office_address=data.get("sales_office_address"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    website=data.get("website_url") or data.get("website"),
                    founded_year=data.get("year_founded") or data.get("founded_year"),
                    about=data.get("description"),
                    rating=data.get("rating"),
                    employee_count=data.get("employee_count"),
                    service_areas=data.get("service_areas"),
                    specialties=data.get("specialties"),
                    price_range_min=data.get("price_range_min"),
                    price_range_max=data.get("price_range_max"),
                    review_count=data.get("review_count"),
                    community_name=data.get("community_name"),  # Primary community name from collection
                    data_source=data.get("data_source", "collected"),
                    data_confidence=data.get("data_confidence", 0.8),
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
                        # Insert into builder_communities join table
                        stmt = builder_communities.insert().values(
                            builder_id=builder.id,
                            community_id=community_id
                        )
                        db.execute(stmt)

                        # Also update legacy community_id field with public community_id string
                        # community_id can be either integer (DB ID) or string (public CMY-XXX ID)
                        if isinstance(community_id, int):
                            community = db.query(Community).filter(Community.id == community_id).first()
                        else:
                            community = db.query(Community).filter(Community.community_id == community_id).first()
                        if community:
                            builder.community_id = community.community_id
                            db.flush()
                            logger.info(f"Linked builder {builder.builder_id} to community {community.community_id} (ID: {community_id})")
                        else:
                            logger.warning(f"Community ID {community_id} not found for legacy field update")
                    except Exception as e:
                        logger.warning(f"Failed to link builder to community {community_id}: {e}")

                logger.info(f"Created new builder {builder.builder_id} from change {change_id}")

            elif change.entity_type == "property":
                from model.property.property import Property

                data = change.proposed_entity_data

                # CRITICAL VALIDATION: Ensure builder_id and community_id are provided
                builder_id = data.get("builder_id")
                community_id = data.get("community_id")

                if not builder_id or not community_id:
                    # Reject the change - missing required relationships
                    change.status = "rejected"
                    change.review_notes = f"Property missing required relationships: builder_id={builder_id}, community_id={community_id}. Properties MUST have both builder and community associations. {request.notes or ''}"
                    db.commit()

                    logger.error(
                        f"Blocked property creation during approval - Change {change_id} missing required foreign keys "
                        f"(builder_id: {builder_id}, community_id: {community_id})"
                    )

                    raise HTTPException(
                        status_code=400,
                        detail=f"Property validation failed: must have both builder_id and community_id"
                    )

                # Verify builder and community exist in database
                from model.profiles.builder import BuilderProfile
                from model.profiles.community import Community

                builder = db.query(BuilderProfile).filter(BuilderProfile.id == builder_id).first()
                # community_id can be either integer (DB ID) or string (public CMY-XXX ID)
                if isinstance(community_id, int):
                    community = db.query(Community).filter(Community.id == community_id).first()
                else:
                    community = db.query(Community).filter(Community.community_id == community_id).first()

                if not builder:
                    change.status = "rejected"
                    change.review_notes = f"Builder ID {builder_id} not found in database. {request.notes or ''}"
                    db.commit()

                    raise HTTPException(
                        status_code=404,
                        detail=f"Builder ID {builder_id} does not exist"
                    )

                if not community:
                    change.status = "rejected"
                    change.review_notes = f"Community ID {community_id} not found in database. {request.notes or ''}"
                    db.commit()

                    raise HTTPException(
                        status_code=404,
                        detail=f"Community ID {community_id} does not exist"
                    )

                # VALIDATION: Ensure minimum required fields for manual approval
                price = data.get("price") or 0
                bedrooms = data.get("bedrooms") or 0
                bathrooms = data.get("bathrooms") or 0

                if price <= 0:
                    change.status = "rejected"
                    change.review_notes = f"Invalid price ({price}). Price must be greater than 0. {request.notes or ''}"
                    db.commit()

                    raise HTTPException(
                        status_code=400,
                        detail=f"Property validation failed: price must be > 0 (got {price})"
                    )

                if bedrooms < 1:
                    change.status = "rejected"
                    change.review_notes = f"Invalid bedrooms ({bedrooms}). Must have at least 1 bedroom. {request.notes or ''}"
                    db.commit()

                    raise HTTPException(
                        status_code=400,
                        detail=f"Property validation failed: must have at least 1 bedroom (got {bedrooms})"
                    )

                if bathrooms < 1:
                    change.status = "rejected"
                    change.review_notes = f"Invalid bathrooms ({bathrooms}). Must have at least 1 bathroom. {request.notes or ''}"
                    db.commit()

                    raise HTTPException(
                        status_code=400,
                        detail=f"Property validation failed: must have at least 1 bathroom (got {bathrooms})"
                    )

                # Create the property with validated relationships
                property = Property(
                    # REQUIRED foreign keys - enforced at approval
                    builder_id=builder_id,
                    builder_id_string=data.get("builder_id_string"),
                    community_id=community_id,
                    community_id_string=data.get("community_id_string"),

                    # Basic info
                    title=data.get("title", "Untitled Property"),
                    description=data.get("description"),

                    # Address
                    address1=data.get("address1") or "Address TBD",
                    city=data.get("city", ""),
                    state=data.get("state", ""),
                    postal_code=data.get("postal_code", ""),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),

                    # Required fields with defaults
                    price=price,
                    bedrooms=data.get("bedrooms") or 0,
                    bathrooms=data.get("bathrooms") or 0,

                    # Specifications
                    sqft=data.get("sqft"),
                    lot_sqft=data.get("lot_sqft"),
                    year_built=data.get("year_built"),
                    property_type=data.get("property_type"),
                    listing_status=data.get("listing_status", "available"),
                    stories=data.get("stories"),
                    garage_spaces=data.get("garage_spaces"),

                    # Lot details
                    lot_number=data.get("lot_number"),
                    corner_lot=data.get("corner_lot", False),
                    cul_de_sac=data.get("cul_de_sac", False),
                    lot_backing=data.get("lot_backing"),

                    # Schools
                    school_district=data.get("school_district"),
                    elementary_school=data.get("elementary_school"),
                    middle_school=data.get("middle_school"),
                    high_school=data.get("high_school"),
                    school_ratings=data.get("school_ratings"),

                    # Builder-specific
                    model_home=data.get("model_home", False),
                    quick_move_in=data.get("quick_move_in", False),
                    construction_stage=data.get("construction_stage"),
                    estimated_completion=data.get("estimated_completion"),
                    builder_plan_name=data.get("builder_plan_name"),

                    # Pricing
                    price_per_sqft=data.get("price_per_sqft"),
                    days_on_market=data.get("days_on_market"),
                    builder_incentives=data.get("builder_incentives"),
                    upgrades_included=data.get("upgrades_included"),
                    upgrades_value=data.get("upgrades_value"),

                    # Media
                    virtual_tour_url=data.get("virtual_tour_url"),
                    floor_plan_url=data.get("floor_plan_url"),
                    media_urls=data.get("media_urls", []),

                    # Collection metadata
                    source_url=data.get("source_url"),
                    data_confidence=data.get("confidence", 0.8),

                    # Approval metadata - manually approved
                    approved_at=datetime.utcnow(),
                    approved_by_user_id=None  # TODO: Enable when current_user is available
                )

                db.add(property)

                # Update the change with the new entity_id
                db.flush()  # Get the ID
                change.entity_id = property.id

                logger.info(
                    f"Created new property {property.id} from change {change_id} "
                    f"(builder_id: {builder_id}, community_id: {community_id}, address: {property.address1})"
                )

            # Add support for other entity types here

        except Exception as e:
            logger.error(f"Failed to create entity from change {change_id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create entity: {str(e)}")

    # Handle updates to EXISTING entities (bulk updates with proposed_entity_data)
    elif request.action == "approve" and not change.is_new_entity and change.proposed_entity_data and change.entity_id:
        try:
            proposed_data = change.proposed_entity_data

            if change.entity_type == "builder":
                # Fetch existing builder
                builder = db.query(BuilderProfile).filter(BuilderProfile.builder_id == change.entity_id).first()

                if not builder:
                    raise HTTPException(status_code=404, detail=f"Builder {change.entity_id} not found")

                # Update builder fields from proposed data
                if "name" in proposed_data:
                    builder.name = proposed_data["name"]
                if "phone" in proposed_data:
                    builder.phone = proposed_data["phone"]
                if "email" in proposed_data:
                    builder.email = proposed_data["email"]
                if "website" in proposed_data:
                    builder.website = proposed_data["website"]
                if "city" in proposed_data:
                    builder.city = proposed_data["city"]
                if "state" in proposed_data:
                    builder.state = proposed_data["state"]
                if "postal_code" in proposed_data:
                    builder.postal_code = proposed_data["postal_code"]
                if "headquarters_address" in proposed_data:
                    builder.headquarters_address = proposed_data["headquarters_address"]
                if "sales_office_address" in proposed_data:
                    builder.sales_office_address = proposed_data["sales_office_address"]
                if "about" in proposed_data:
                    builder.about = proposed_data["about"]
                if "community_id" in proposed_data:
                    builder.community_id = proposed_data["community_id"]
                if "community_name" in proposed_data:
                    builder.community_name = proposed_data["community_name"]

                # Update data collection metadata
                builder.last_data_sync = datetime.utcnow()
                builder.data_source = "collected"

                db.add(builder)
                logger.info(f"Updated existing builder {change.entity_id} from change {change_id}")

            elif change.entity_type == "property":
                # Fetch existing property
                property_obj = db.query(Property).filter(Property.property_id == change.entity_id).first()

                if not property_obj:
                    raise HTTPException(status_code=404, detail=f"Property {change.entity_id} not found")

                # Update property fields from proposed data
                if "address1" in proposed_data:
                    property_obj.address1 = proposed_data["address1"]
                if "address2" in proposed_data:
                    property_obj.address2 = proposed_data["address2"]
                if "city" in proposed_data:
                    property_obj.city = proposed_data["city"]
                if "state" in proposed_data:
                    property_obj.state = proposed_data["state"]
                if "postal_code" in proposed_data:
                    property_obj.postal_code = proposed_data["postal_code"]
                if "price" in proposed_data:
                    property_obj.price = proposed_data["price"]
                if "bedrooms" in proposed_data:
                    property_obj.bedrooms = proposed_data["bedrooms"]
                if "bathrooms" in proposed_data:
                    property_obj.bathrooms = proposed_data["bathrooms"]
                if "square_feet" in proposed_data:
                    property_obj.square_feet = proposed_data["square_feet"]
                if "description" in proposed_data:
                    property_obj.description = proposed_data["description"]
                if "community_id" in proposed_data:
                    property_obj.community_id = proposed_data["community_id"]
                if "community_name" in proposed_data:
                    property_obj.community_name = proposed_data["community_name"]

                # Update data collection metadata
                property_obj.last_data_sync = datetime.utcnow()
                property_obj.data_source = "collected"

                db.add(property_obj)
                logger.info(f"Updated existing property {change.entity_id} from change {change_id}")

            elif change.entity_type == "community":
                # Fetch existing community
                community = db.query(Community).filter(Community.community_id == change.entity_id).first()

                if not community:
                    raise HTTPException(status_code=404, detail=f"Community {change.entity_id} not found")

                # Update community fields from proposed data
                if "name" in proposed_data:
                    community.name = proposed_data["name"]
                if "description" in proposed_data:
                    community.description = proposed_data["description"]
                if "city" in proposed_data:
                    community.city = proposed_data["city"]
                if "state" in proposed_data:
                    community.state = proposed_data["state"]
                if "postal_code" in proposed_data:
                    community.postal_code = proposed_data["postal_code"]
                if "address" in proposed_data:
                    community.address = proposed_data["address"]
                if "website" in proposed_data:
                    community.website = proposed_data["website"]
                if "phone" in proposed_data:
                    community.phone = proposed_data["phone"]
                if "amenities" in proposed_data:
                    community.amenities = proposed_data["amenities"]

                # Update data collection metadata
                community.last_data_sync = datetime.utcnow()
                community.data_source = "collected"

                db.add(community)
                logger.info(f"Updated existing community {change.entity_id} from change {change_id}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update entity from change {change_id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update entity: {str(e)}")

    # Handle field-level updates to EXISTING entities
    elif request.action == "approve" and not change.is_new_entity and change.field_name and change.entity_id:
        try:
            if change.entity_type == "builder":
                from model.profiles.builder import BuilderProfile

                # Fetch existing builder by internal ID
                builder = db.query(BuilderProfile).filter(BuilderProfile.id == change.entity_id).first()

                if not builder:
                    raise HTTPException(status_code=404, detail=f"Builder {change.entity_id} not found")

                # Apply the field-level change
                if hasattr(builder, change.field_name):
                    setattr(builder, change.field_name, change.new_value)

                    # Update data collection metadata (unless we're updating these fields themselves)
                    if change.field_name not in ['last_data_sync', 'data_source', 'data_confidence']:
                        builder.last_data_sync = datetime.utcnow()
                        if change.field_name != 'data_source':
                            builder.data_source = "collected"

                    db.add(builder)
                    logger.info(f"Updated builder {change.entity_id} field '{change.field_name}' from '{change.old_value}' to '{change.new_value}'")
                else:
                    logger.warning(f"Builder field '{change.field_name}' does not exist, skipping update")

            elif change.entity_type == "property":
                # Fetch existing property by internal ID
                property_obj = db.query(Property).filter(Property.id == change.entity_id).first()

                if not property_obj:
                    raise HTTPException(status_code=404, detail=f"Property {change.entity_id} not found")

                # Apply the field-level change
                if hasattr(property_obj, change.field_name):
                    setattr(property_obj, change.field_name, change.new_value)

                    # Update data collection metadata
                    if change.field_name not in ['last_data_sync', 'data_source', 'data_confidence']:
                        property_obj.last_data_sync = datetime.utcnow()
                        if change.field_name != 'data_source':
                            property_obj.data_source = "collected"

                    db.add(property_obj)
                    logger.info(f"Updated property {change.entity_id} field '{change.field_name}' from '{change.old_value}' to '{change.new_value}'")
                else:
                    logger.warning(f"Property field '{change.field_name}' does not exist, skipping update")

            elif change.entity_type == "community":
                from model.profiles.community import Community

                # Fetch existing community by internal ID
                community = db.query(Community).filter(Community.id == change.entity_id).first()

                if not community:
                    raise HTTPException(status_code=404, detail=f"Community {change.entity_id} not found")

                # Apply the field-level change
                if hasattr(community, change.field_name):
                    setattr(community, change.field_name, change.new_value)

                    # Update data collection metadata
                    if change.field_name not in ['last_data_sync', 'data_source', 'data_confidence']:
                        community.last_data_sync = datetime.utcnow()
                        if change.field_name != 'data_source':
                            community.data_source = "collected"

                    db.add(community)
                    logger.info(f"Updated community {change.entity_id} field '{change.field_name}' from '{change.old_value}' to '{change.new_value}'")
                else:
                    logger.warning(f"Community field '{change.field_name}' does not exist, skipping update")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to apply field change {change_id}: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to apply field change: {str(e)}")

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

        # Get communities without builders (limited to 20) with property counts
        missing_result = db.execute(text("""
            SELECT c.id, c.name, c.city, c.state,
                   COUNT(p.id) as property_count
            FROM communities c
            LEFT JOIN builder_communities bc ON c.id = bc.community_id
            LEFT JOIN properties p ON c.id = p.community_id
            WHERE bc.community_id IS NULL
            GROUP BY c.id, c.name, c.city, c.state
            ORDER BY c.name
            LIMIT 20
        """))

        communities_missing = [
            {
                "id": row.id,
                "name": row.name,
                "city": row.city,
                "state": row.state,
                "location": f"{row.city}, {row.state}" if row.city and row.state else None,
                "property_count": row.property_count
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
    dry_run: bool = Query(False, description="Preview without creating jobs (default: False)"),
    max_communities: int = Query(10, description="Maximum number of communities to process", ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Create builder discovery jobs for communities without builders.

    This endpoint implements the backfill functionality to fill data gaps
    in the cascading collection workflow (communities → builders → properties).

    **NEW BEHAVIOR:**
    - Calls Claude AI to find actual builders operating in each community
    - Creates individual jobs for each builder (not one job per community)
    - Reuses the same logic as normal community discovery flow

    **Usage:**
    - Default behavior creates jobs immediately (dry_run=false)
    - Set dry_run=true to preview what would be created
    - Use max_communities to limit batch size (default: 10 to avoid high API costs)

    **Process:**
    1. Finds communities with NO builders linked
    2. For each community, calls Claude to find builders
    3. Creates pending jobs for each builder found
    4. Jobs must be executed separately via /jobs/execute-pending
    5. Changes require manual review and approval
    """
    try:
        from sqlalchemy import text
        from anthropic import Anthropic
        from src.collection.prompts import generate_community_builders_prompt
        import os
        import json

        # Initialize Claude client
        anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Check for existing pending builder discovery jobs to avoid duplicates
        pending_jobs = db.query(CollectionJob).filter(
            CollectionJob.entity_type == "builder",
            CollectionJob.job_type == "discovery",
            CollectionJob.status == "pending"
        ).count()

        if pending_jobs > 0:
            logger.warning(f"Found {pending_jobs} existing pending builder discovery jobs")

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
                "pending_jobs_exist": pending_jobs,
                "dry_run": dry_run
            }

        # Limit to max_communities (note: this controls API calls, not total jobs)
        if len(communities_without_builders) > max_communities:
            logger.info(f"Limiting backfill to {max_communities} communities (found {len(communities_without_builders)} total)")
            communities_to_process = communities_without_builders[:max_communities]
            communities_skipped = len(communities_without_builders) - max_communities
        else:
            communities_to_process = communities_without_builders
            communities_skipped = 0

        jobs_preview = []
        jobs_created = []
        total_builders_found = 0
        communities_processed = 0
        communities_with_errors = 0

        # Process each community
        for row in communities_to_process:
            community_name = row.name
            location = f"{row.city}, {row.state}" if row.city and row.state else None

            logger.info(f"Backfill: Discovering builders for {community_name} ({location})")

            try:
                # Call Claude to find builders in this community
                prompt = generate_community_builders_prompt(community_name, location or "")

                message = anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=4000,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}]
                )

                # Parse Claude's response
                response_text = message.content[0].text

                # Extract JSON from response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    collected_data = json.loads(json_str)
                else:
                    logger.warning(f"No JSON found in Claude response for {community_name}")
                    collected_data = {"builders": []}

                builders = collected_data.get("builders", [])
                logger.info(f"Found {len(builders)} builders for {community_name}")

                # Create a job for each builder found
                for builder_data in builders:
                    builder_name = builder_data.get("name")
                    if not builder_name:
                        continue

                    total_builders_found += 1

                    job_data = {
                        "community_id": row.id,
                        "community_name": community_name,
                        "location": location,
                        "builder_name": builder_name,
                        "search_query": builder_name,  # Just the builder name, not "{community} builders"
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
                            search_query=builder_name,  # JUST THE NAME
                            search_filters={
                                "community_id": row.id,
                                "community_name": community_name,
                                "location": location
                            },
                            initiated_by="system_backfill"
                        )
                        db.add(job)
                        jobs_created.append({
                            "job_id": job.job_id,
                            "builder_name": builder_name,
                            "community_name": community_name,
                            "community_id": row.id
                        })

                # Successfully processed this community (whether builders found or not)
                communities_processed += 1

            except Exception as e:
                logger.error(f"Failed to process community {community_name}: {str(e)}", exc_info=True)
                communities_with_errors += 1
                continue

        if not dry_run:
            db.commit()
            logger.info(f"Created {len(jobs_created)} builder discovery jobs across {communities_processed} communities")

        # Calculate costs (now based on actual API calls + job execution)
        api_cost = communities_processed * 0.02  # Cost per Claude API call
        job_execution_cost = total_builders_found * 0.03  # Cost per builder job execution
        estimated_cost = api_cost + job_execution_cost
        estimated_time_minutes = total_builders_found * 0.75  # ~45 seconds per job

        response = {
            "message": f"{'Would create' if dry_run else 'Created'} {len(jobs_preview)} builder discovery job(s) across {communities_processed} communities",
            "communities_found": len(communities_without_builders),
            "communities_processed": communities_processed,
            "communities_with_errors": communities_with_errors,
            "builders_found": total_builders_found,
            "jobs_created": len(jobs_created) if not dry_run else 0,
            "communities_skipped": communities_skipped,
            "pending_jobs_exist": pending_jobs,
            "dry_run": dry_run,
            "priority": priority,
            "estimated_cost_usd": round(estimated_cost, 2),
            "estimated_time_minutes": round(estimated_time_minutes, 1)
        }

        # Include preview data in response
        if dry_run or not jobs_created:
            response["jobs_preview"] = jobs_preview[:20]  # Limit preview to first 20
            if len(jobs_preview) > 20:
                response["jobs_preview_truncated"] = f"Showing 20 of {len(jobs_preview)} jobs"
        else:
            response["jobs"] = jobs_created[:20]  # Limit to first 20 in response
            if len(jobs_created) > 20:
                response["jobs_truncated"] = f"Showing 20 of {len(jobs_created)} jobs"
            response["next_step"] = "Execute pending jobs via POST /v1/admin/collection/jobs/execute-pending"

        return response

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to backfill community builders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a single collection job by ID.

    **Warning**: This will permanently delete the job and its associated logs.
    """
    try:
        # Find the job
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Delete associated logs first
        db.query(CollectionJobLog).filter(CollectionJobLog.job_id == job_id).delete()

        # Delete the job
        db.delete(job)
        db.commit()

        logger.info(f"Deleted job {job_id}")

        return {
            "message": f"Successfully deleted job {job_id}",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs")
async def delete_jobs_bulk(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    delete_all: bool = Query(False, description="Delete all matching jobs (not just page)"),
    db: Session = Depends(get_db)
):
    """
    Bulk delete collection jobs matching the specified filters.

    This endpoint allows deleting all jobs that match the given criteria.
    Can filter by entity_type, job_type, and status.

    **Warning**: This will permanently delete jobs and their associated logs.
    Use with caution!
    """
    try:
        # Build the query with filters
        query = db.query(CollectionJob)

        if entity_type:
            query = query.filter(CollectionJob.entity_type == entity_type)

        if job_type:
            query = query.filter(CollectionJob.job_type == job_type)

        if status:
            query = query.filter(CollectionJob.status == status)

        # Count jobs that will be deleted
        total_count = query.count()

        if total_count == 0:
            return {
                "message": "No jobs found matching the specified filters",
                "deleted_count": 0,
                "filters": {
                    "entity_type": entity_type,
                    "job_type": job_type,
                    "status": status
                }
            }

        # Get job IDs for logging
        job_ids = [job.job_id for job in query.all()]

        # Delete associated logs first (due to foreign key constraints)
        for job_id in job_ids:
            db.query(CollectionJobLog).filter(CollectionJobLog.job_id == job_id).delete()

        # Delete the jobs
        deleted_count = query.delete(synchronize_session=False)

        db.commit()

        logger.info(f"Bulk deleted {deleted_count} jobs with filters: entity_type={entity_type}, job_type={job_type}, status={status}")

        return {
            "message": f"Successfully deleted {deleted_count} job(s)",
            "deleted_count": deleted_count,
            "filters": {
                "entity_type": entity_type,
                "job_type": job_type,
                "status": status
            },
            "job_ids": job_ids[:100]  # Return first 100 job IDs for reference
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to bulk delete jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Audit Log Endpoints
# ===================================================================

class AuditLogEntryResponse(BaseModel):
    """Response for a single audit log entry."""
    id: int
    timestamp: str
    action: str  # "approved", "rejected", "auto_approved", "auto_denied"
    entity_type: str  # "property", "builder", "community"
    entity_name: str
    property_address: Optional[str] = None
    property_bedrooms: Optional[int] = None
    property_bathrooms: Optional[float] = None
    property_price: Optional[float] = None
    reviewer_name: Optional[str] = None
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    confidence: float
    change_type: str  # "added", "modified", "removed"
    is_auto_action: bool
    source_url: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogStatsResponse(BaseModel):
    """Statistics for audit log."""
    total_actions: int
    auto_approved: int
    auto_denied: int
    manually_approved: int
    manually_rejected: int
    pending_review: int
    properties_added: int
    properties_updated: int
    last_7_days: int
    last_30_days: int


@router.get("/audit-logs", response_model=List[AuditLogEntryResponse])
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action (approved, rejected, auto_approved, auto_denied)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (property, builder, community)"),
    reviewer_id: Optional[str] = Query(None, description="Filter by reviewer user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get audit logs for property approval/denial activities.

    Returns a paginated list of all approval/denial actions taken on properties,
    including both manual and automatic decisions.
    """
    try:
        from datetime import timedelta

        # Query collection changes that have been reviewed
        query = db.query(CollectionChange).filter(
            CollectionChange.reviewed_at.isnot(None)
        )

        # Apply filters
        if action:
            if action == "auto_approved":
                query = query.filter(
                    CollectionChange.status == "approved",
                    CollectionChange.reviewed_by.is_(None)  # Auto-approved have no reviewer
                )
            elif action == "auto_denied":
                query = query.filter(
                    CollectionChange.status == "rejected",
                    CollectionChange.reviewed_by.is_(None)
                )
            elif action == "approved":
                query = query.filter(
                    CollectionChange.status == "approved",
                    CollectionChange.reviewed_by.isnot(None)  # Manual approval has reviewer
                )
            elif action == "rejected":
                query = query.filter(
                    CollectionChange.status == "rejected",
                    CollectionChange.reviewed_by.isnot(None)
                )

        if entity_type:
            query = query.filter(CollectionChange.entity_type == entity_type)

        if reviewer_id:
            query = query.filter(CollectionChange.reviewed_by == reviewer_id)

        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(CollectionChange.reviewed_at >= cutoff_date)

        # Order by most recent first
        query = query.order_by(CollectionChange.reviewed_at.desc())

        # Apply pagination
        changes = query.limit(limit).offset(offset).all()

        # Format response
        audit_entries = []
        for change in changes:
            # Determine action type
            if change.status == "approved":
                action_type = "auto_approved" if not change.reviewed_by else "approved"
            else:
                action_type = "auto_denied" if not change.reviewed_by else "rejected"

            # Get entity name
            entity_name = "Unknown"
            property_address = None
            property_bedrooms = None
            property_bathrooms = None
            property_price = None

            if change.is_new_entity and change.proposed_entity_data:
                data = change.proposed_entity_data
                if change.entity_type == "property":
                    entity_name = data.get("title") or data.get("address1") or "Untitled Property"
                    property_address = data.get("address1")
                    property_bedrooms = data.get("bedrooms")
                    property_bathrooms = data.get("bathrooms")
                    property_price = data.get("price")
                elif change.entity_type == "builder":
                    entity_name = data.get("name", "Unknown Builder")
                elif change.entity_type == "community":
                    entity_name = data.get("name", "Unknown Community")
            elif change.entity_id:
                # Fetch entity name from database
                try:
                    if change.entity_type == "property":
                        from model.property.property import Property
                        prop = db.query(Property).filter(Property.id == change.entity_id).first()
                        if prop:
                            entity_name = prop.title or prop.address1
                            property_address = prop.address1
                            property_bedrooms = prop.bedrooms
                            property_bathrooms = prop.bathrooms
                            property_price = float(prop.price) if prop.price else None
                    elif change.entity_type == "builder":
                        from model.profiles.builder import BuilderProfile
                        builder = db.query(BuilderProfile).filter(BuilderProfile.id == change.entity_id).first()
                        if builder:
                            entity_name = builder.name
                    elif change.entity_type == "community":
                        from model.profiles.community import Community
                        community = db.query(Community).filter(Community.id == change.entity_id).first()
                        if community:
                            entity_name = community.name
                except Exception as e:
                    logger.warning(f"Failed to fetch entity name for {change.entity_type} {change.entity_id}: {e}")

            # Get reviewer name
            reviewer_name = None
            if change.reviewed_by:
                try:
                    from model.user import Users
                    reviewer = db.query(Users).filter(Users.user_id == change.reviewed_by).first()
                    if reviewer:
                        reviewer_name = f"{reviewer.first_name} {reviewer.last_name}"
                except Exception as e:
                    logger.warning(f"Failed to fetch reviewer name for {change.reviewed_by}: {e}")

            audit_entries.append(AuditLogEntryResponse(
                id=change.id,
                timestamp=change.reviewed_at.isoformat() if change.reviewed_at else None,
                action=action_type,
                entity_type=change.entity_type,
                entity_name=entity_name,
                property_address=property_address,
                property_bedrooms=property_bedrooms,
                property_bathrooms=property_bathrooms,
                property_price=property_price,
                reviewer_name=reviewer_name,
                reviewer_id=change.reviewed_by,
                review_notes=change.review_notes,
                confidence=change.confidence,
                change_type=change.change_type,
                is_auto_action=not bool(change.reviewed_by),
                source_url=change.source_url
            ))

        return audit_entries

    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs/stats", response_model=AuditLogStatsResponse)
async def get_audit_log_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to calculate stats for"),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_admin_user)
):
    """
    Get statistics about property approval/denial activities.

    Returns counts of different types of actions taken.
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_7_days = datetime.utcnow() - timedelta(days=7)

        # Total actions
        total_actions = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.reviewed_at.isnot(None),
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Auto-approved (approved + no reviewer)
        auto_approved = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.status == "approved",
            CollectionChange.reviewed_by.is_(None),
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Auto-denied (rejected + no reviewer)
        auto_denied = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.status == "rejected",
            CollectionChange.reviewed_by.is_(None),
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Manually approved (approved + has reviewer)
        manually_approved = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.status == "approved",
            CollectionChange.reviewed_by.isnot(None),
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Manually rejected (rejected + has reviewer)
        manually_rejected = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.status == "rejected",
            CollectionChange.reviewed_by.isnot(None),
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Pending review
        pending_review = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.status == "pending"
        ).scalar() or 0

        # Properties added (new entities that were approved)
        properties_added = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.entity_type == "property",
            CollectionChange.is_new_entity == True,
            CollectionChange.status == "approved",
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Properties updated (field changes that were approved)
        properties_updated = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.entity_type == "property",
            CollectionChange.is_new_entity == False,
            CollectionChange.status == "approved",
            CollectionChange.reviewed_at >= cutoff_date
        ).scalar() or 0

        # Last 7 days activity
        last_7_days = db.query(func.count(CollectionChange.id)).filter(
            CollectionChange.reviewed_at.isnot(None),
            CollectionChange.reviewed_at >= cutoff_7_days
        ).scalar() or 0

        return AuditLogStatsResponse(
            total_actions=total_actions,
            auto_approved=auto_approved,
            auto_denied=auto_denied,
            manually_approved=manually_approved,
            manually_rejected=manually_rejected,
            pending_review=pending_review,
            properties_added=properties_added,
            properties_updated=properties_updated,
            last_7_days=last_7_days,
            last_30_days=total_actions
        )

    except Exception as e:
        logger.error(f"Failed to fetch audit log stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===================================================================
# Change Reversion
# ===================================================================

class RevertChangeRequest(BaseModel):
    """Request model for reverting an auto-applied change."""
    user_id: str = Field(..., description="User ID performing the reversion")
    reason: Optional[str] = Field(None, description="Optional reason for reverting")


@router.post("/changes/{change_id}/revert", summary="Revert an auto-applied change")
def revert_change(
    change_id: int,
    request: RevertChangeRequest,
    db: Session = Depends(get_db)
):
    """
    Revert an auto-applied change back to its original value.

    This endpoint allows reverting changes that were automatically applied
    by the collection system. It restores the old value and marks the change
    as reverted with full audit trail.

    Requirements:
    - Change must have auto_applied = True
    - Change must have status = 'applied'
    - Entity must still exist in database
    """
    try:
        # Get the change record
        change = db.query(CollectionChange).filter(CollectionChange.id == change_id).first()

        if not change:
            raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

        # Validate that this change can be reverted
        if not change.auto_applied:
            raise HTTPException(
                status_code=400,
                detail="Only auto-applied changes can be reverted. This change was manually reviewed."
            )

        if change.status != "applied":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot revert change with status '{change.status}'. Only applied changes can be reverted."
            )

        if change.reverted_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Change was already reverted at {change.reverted_at}"
            )

        # Get the entity to revert
        entity_model = None
        if change.entity_type == "community":
            from model.profiles.community import Community
            entity_model = Community
        elif change.entity_type == "builder":
            from model.profiles.builder import BuilderProfile
            entity_model = BuilderProfile
        elif change.entity_type == "property":
            from model.property.property import Property
            entity_model = Property
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported entity type: {change.entity_type}"
            )

        # Get the entity
        entity = db.query(entity_model).filter(entity_model.id == change.entity_id).first()
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"{change.entity_type.capitalize()} {change.entity_id} not found"
            )

        # Revert the change by setting the field back to old_value
        if change.field_name and hasattr(entity, change.field_name):
            setattr(entity, change.field_name, change.old_value)

            # Update the change record
            change.reverted_at = datetime.utcnow()
            change.reverted_by = request.user_id
            change.review_notes = (
                f"Reverted by {request.user_id}. "
                f"{request.reason if request.reason else 'No reason provided.'}"
            )

            db.commit()

            logger.info(
                f"Reverted change {change_id}: {change.entity_type}.{change.field_name} "
                f"from {change.new_value} back to {change.old_value} "
                f"(reverted by {request.user_id})"
            )

            return {
                "success": True,
                "change_id": change_id,
                "entity_type": change.entity_type,
                "entity_id": change.entity_id,
                "field_name": change.field_name,
                "restored_value": change.old_value,
                "reverted_at": change.reverted_at.isoformat(),
                "reverted_by": change.reverted_by,
                "message": f"Successfully reverted {change.field_name} to its original value"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Field {change.field_name} not found on {change.entity_type}"
            )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revert change {change_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
