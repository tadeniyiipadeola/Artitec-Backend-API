"""
Lot and Phase Map Management Routes
Handles lot CRUD, phase map upload, and AI-powered lot detection
"""
from __future__ import annotations

from typing import List, Optional
from decimal import Decimal
import io

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.db import get_db
from config.security import get_current_user_optional
from model.user import Users

# Models
from model.profiles.community import Community as CommunityModel, CommunityPhase as PhaseModel
from model.profiles.lot import Lot as LotModel, LotStatusHistory, LotStatus

# Schemas
from schema.lot import (
    PhaseCreate,
    PhaseUpdate,
    PhaseOut,
    PhaseWithLotsOut,
    LotCreate,
    LotUpdate,
    LotOut,
    LotListOut,
    LotStatusUpdate,
    LotStatusHistoryOut,
    PhaseMapUploadResponse,
    AutoDetectLotsRequest,
    AutoDetectLotsResponse,
    PhaseStatistics,
    LotFilters,
    BulkLotCreate,
    BulkLotStatusUpdate,
    BulkOperationResult,
    DetectionMethod,
)

# Services
from src.storage_service import storage_service
from src.lot_detection import YOLOLotDetector, LineLotDetector, YOLO_AVAILABLE

router = APIRouter()


# ========== HELPER FUNCTIONS ==========

def _get_community_or_404(db: Session, community_id: str) -> CommunityModel:
    """Get community by ID or raise 404"""
    community = db.query(CommunityModel).filter(
        CommunityModel.community_id == community_id
    ).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return community


def _get_phase_or_404(db: Session, community_id: str, phase_id: int) -> PhaseModel:
    """Get phase by ID and community or raise 404"""
    phase = db.query(PhaseModel).filter(
        PhaseModel.id == phase_id,
        PhaseModel.community_id == community_id
    ).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    return phase


def _get_lot_or_404(db: Session, phase_id: int, lot_id: int) -> LotModel:
    """Get lot by ID and phase or raise 404"""
    lot = db.query(LotModel).filter(
        LotModel.id == lot_id,
        LotModel.phase_id == phase_id
    ).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    return lot


# ========== PHASE ENDPOINTS ==========

@router.get("/communities/{community_id}/phases", response_model=List[PhaseOut])
def get_phases(
    community_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Get all phases for a community
    """
    _get_community_or_404(db, community_id)

    phases = db.query(PhaseModel).filter(
        PhaseModel.community_id == community_id
    ).order_by(PhaseModel.created_at.desc()).all()

    return phases


@router.get("/communities/{community_id}/phases/{phase_id}", response_model=PhaseWithLotsOut)
def get_phase(
    community_id: str,
    phase_id: int,
    include_lots: bool = Query(True, description="Include lot data"),
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Get a single phase with optional lot data
    """
    phase = _get_phase_or_404(db, community_id, phase_id)
    return phase


@router.post("/communities/{community_id}/phases", response_model=PhaseOut, status_code=status.HTTP_201_CREATED)
def create_phase(
    community_id: str,
    phase: PhaseCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Create a new phase for a community
    """
    _get_community_or_404(db, community_id)

    # Create phase
    new_phase = PhaseModel(
        community_id=community_id,
        name=phase.name,
        description=phase.description,
        status=phase.status.value if phase.status else 'planning',
        start_date=phase.start_date,
        target_completion_date=phase.target_completion_date,
    )

    db.add(new_phase)
    db.commit()
    db.refresh(new_phase)

    return new_phase


@router.put("/communities/{community_id}/phases/{phase_id}", response_model=PhaseOut)
def update_phase(
    community_id: str,
    phase_id: int,
    phase_update: PhaseUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Update a phase
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    # Update fields
    update_data = phase_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(phase, field):
            if field == 'status' and value:
                setattr(phase, field, value.value)
            else:
                setattr(phase, field, value)

    db.commit()
    db.refresh(phase)

    return phase


@router.delete("/communities/{community_id}/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phase(
    community_id: str,
    phase_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Delete a phase (cascades to lots)
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    db.delete(phase)
    db.commit()

    return None


# ========== PHASE MAP UPLOAD & DETECTION ==========

@router.post("/communities/{community_id}/phases/{phase_id}/upload-map", response_model=PhaseMapUploadResponse)
async def upload_phase_map(
    community_id: str,
    phase_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Upload a phase map image to MinIO
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    # Validate file type
    allowed_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml', 'image/webp', 'application/pdf'}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: JPG, PNG, SVG, WEBP, PDF"
        )

    # Read file
    file_data = await file.read()

    # Upload to MinIO
    minio_path = f"phases/{community_id}/phase-{phase_id}-{file.filename}"

    try:
        # Wrap bytes in BytesIO for storage service
        file_obj = io.BytesIO(file_data)
        url = storage_service.upload_file(
            file_obj,
            minio_path,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Get image dimensions
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(file_data))
        width, height = img.size
    except:
        width, height = None, None

    # Update phase with image info
    phase.site_plan_image_url = url
    phase.original_file_path = minio_path
    phase.file_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
    phase.image_width = width
    phase.image_height = height

    db.commit()
    db.refresh(phase)

    return PhaseMapUploadResponse(
        phase_id=phase.id,
        site_plan_image_url=url,
        image_width=width or 0,
        image_height=height or 0,
        file_type=phase.file_type,
        message="Phase map uploaded successfully"
    )


@router.post("/communities/{community_id}/phases/{phase_id}/detect-lots", response_model=AutoDetectLotsResponse)
def auto_detect_lots(
    community_id: str,
    phase_id: int,
    request: AutoDetectLotsRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Auto-detect lots from phase map using AI
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    if not phase.site_plan_image_url:
        raise HTTPException(
            status_code=400,
            detail="No phase map uploaded. Please upload a phase map first."
        )

    # Choose detector
    if request.detection_method == DetectionMethod.YOLO:
        if not YOLO_AVAILABLE:
            raise HTTPException(
                status_code=400,
                detail="YOLO detection not available. Please install: pip install ultralytics"
            )
        detector = YOLOLotDetector()
    else:
        detector = LineLotDetector()

    # Run detection
    try:
        result = detector.detect_lots(
            phase.original_file_path,
            from_minio=True,
            confidence_threshold=float(request.min_confidence) if request.detection_method == DetectionMethod.YOLO else 0.75
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {str(e)}"
        )

    detected_lots = result['lots']

    # Auto-save if requested
    saved_lots = []
    if request.auto_save:
        for lot_data in detected_lots:
            new_lot = LotModel(
                phase_id=phase.id,
                community_id=community_id,
                lot_number=lot_data['lot_number'],
                boundary_coordinates=lot_data['polygon'],
                status=LotStatus.AVAILABLE,
                detection_method=lot_data['detection_method'],
                detection_confidence=Decimal(str(lot_data['confidence']))
            )
            db.add(new_lot)
            saved_lots.append(new_lot)

        # Update phase total_lots count
        phase.total_lots = len(saved_lots)

        db.commit()

        # Refresh lots
        for lot in saved_lots:
            db.refresh(lot)

    return AutoDetectLotsResponse(
        phase_id=phase.id,
        detection_method=request.detection_method.value,
        detected_count=len(detected_lots),
        lots=[LotOut.from_orm(lot) for lot in saved_lots] if request.auto_save else [],
        average_confidence=Decimal(str(result.get('average_confidence', 0))),
        message=f"Detected {len(detected_lots)} lots using {request.detection_method.value}" +
                (f", saved {len(saved_lots)} to database" if request.auto_save else "")
    )


# ========== LOT ENDPOINTS ==========

@router.get("/communities/{community_id}/phases/{phase_id}/lots", response_model=LotListOut)
def get_lots(
    community_id: str,
    phase_id: int,
    filters: LotFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Get all lots for a phase with optional filtering
    """
    _get_phase_or_404(db, community_id, phase_id)

    # Base query
    query = db.query(LotModel).filter(LotModel.phase_id == phase_id)

    # Apply filters
    if filters.status:
        query = query.filter(LotModel.status == filters.status)
    if filters.builder_id:
        query = query.filter(LotModel.builder_id == filters.builder_id)
    if filters.min_price:
        query = query.filter(LotModel.price >= filters.min_price)
    if filters.max_price:
        query = query.filter(LotModel.price <= filters.max_price)
    if filters.min_sqft:
        query = query.filter(LotModel.square_footage >= filters.min_sqft)
    if filters.max_sqft:
        query = query.filter(LotModel.square_footage <= filters.max_sqft)
    if filters.bedrooms:
        query = query.filter(LotModel.bedrooms == filters.bedrooms)
    if filters.bathrooms:
        query = query.filter(LotModel.bathrooms == filters.bathrooms)

    lots = query.order_by(LotModel.lot_number).all()

    # Calculate statistics
    stats = {
        'available': db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.AVAILABLE
        ).scalar() or 0,
        'reserved': db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.RESERVED
        ).scalar() or 0,
        'sold': db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.SOLD
        ).scalar() or 0,
        'unavailable': db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.UNAVAILABLE
        ).scalar() or 0,
        'on_hold': db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.ON_HOLD
        ).scalar() or 0,
    }

    return LotListOut(
        items=lots,
        total=len(lots),
        statistics=stats
    )


@router.post("/communities/{community_id}/phases/{phase_id}/lots", response_model=LotOut, status_code=status.HTTP_201_CREATED)
def create_lot(
    community_id: str,
    phase_id: int,
    lot: LotCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Create a new lot
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    # Check for duplicate lot number
    existing = db.query(LotModel).filter(
        LotModel.phase_id == phase_id,
        LotModel.lot_number == lot.lot_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Lot number {lot.lot_number} already exists in this phase"
        )

    # Create lot
    new_lot = LotModel(
        phase_id=phase_id,
        community_id=community_id,
        **lot.dict(exclude={'phase_id', 'community_id', 'boundary_coordinates'}),
        boundary_coordinates=[coord.dict() for coord in lot.boundary_coordinates] if lot.boundary_coordinates else None
    )

    db.add(new_lot)

    # Update phase total_lots
    phase.total_lots = (phase.total_lots or 0) + 1

    db.commit()
    db.refresh(new_lot)

    # Create status history entry
    history = LotStatusHistory(
        lot_id=new_lot.id,
        old_status=None,
        new_status=new_lot.status,
        changed_by=current_user.email if current_user else "system",
        change_reason="Initial lot creation"
    )
    db.add(history)
    db.commit()

    return new_lot


@router.put("/communities/{community_id}/phases/{phase_id}/lots/{lot_id}", response_model=LotOut)
def update_lot(
    community_id: str,
    phase_id: int,
    lot_id: int,
    lot_update: LotUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Update a lot
    """
    lot = _get_lot_or_404(db, phase_id, lot_id)
    old_status = lot.status

    # Update fields
    update_data = lot_update.dict(exclude_unset=True, exclude={'boundary_coordinates'})
    for field, value in update_data.items():
        if hasattr(lot, field):
            setattr(lot, field, value)

    # Handle boundary coordinates separately
    if lot_update.boundary_coordinates is not None:
        lot.boundary_coordinates = [coord.dict() for coord in lot_update.boundary_coordinates]

    db.commit()
    db.refresh(lot)

    # Create status history if status changed
    if lot_update.status and lot_update.status != old_status:
        history = LotStatusHistory(
            lot_id=lot.id,
            old_status=old_status,
            new_status=lot.status,
            changed_by=current_user.email if current_user else "system",
            change_reason="Lot updated"
        )
        db.add(history)
        db.commit()

    return lot


@router.patch("/communities/{community_id}/phases/{phase_id}/lots/{lot_id}/status", response_model=LotOut)
def update_lot_status(
    community_id: str,
    phase_id: int,
    lot_id: int,
    status_update: LotStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Update lot status only (with history tracking)
    """
    lot = _get_lot_or_404(db, phase_id, lot_id)
    old_status = lot.status

    # Update status
    lot.status = status_update.status

    # Update reservation/sale info based on status
    if status_update.status == LotStatus.RESERVED:
        lot.reserved_by = status_update.reserved_by
        lot.reserved_at = func.now()
    elif status_update.status == LotStatus.SOLD:
        lot.sold_to = status_update.sold_to
        lot.sold_at = func.now()

    db.commit()
    db.refresh(lot)

    # Create status history entry
    history = LotStatusHistory(
        lot_id=lot.id,
        old_status=old_status,
        new_status=status_update.status,
        changed_by=status_update.changed_by or (current_user.email if current_user else "system"),
        change_reason=status_update.change_reason
    )
    db.add(history)
    db.commit()

    return lot


@router.delete("/communities/{community_id}/phases/{phase_id}/lots/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(
    community_id: str,
    phase_id: int,
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Delete a lot
    """
    lot = _get_lot_or_404(db, phase_id, lot_id)
    phase = _get_phase_or_404(db, community_id, phase_id)

    db.delete(lot)

    # Update phase total_lots
    if phase.total_lots:
        phase.total_lots = max(0, phase.total_lots - 1)

    db.commit()

    return None


# ========== LOT STATUS HISTORY ==========

@router.get("/communities/{community_id}/phases/{phase_id}/lots/{lot_id}/history", response_model=List[LotStatusHistoryOut])
def get_lot_status_history(
    community_id: str,
    phase_id: int,
    lot_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Get status change history for a lot
    """
    _get_lot_or_404(db, phase_id, lot_id)

    history = db.query(LotStatusHistory).filter(
        LotStatusHistory.lot_id == lot_id
    ).order_by(LotStatusHistory.changed_at.desc()).all()

    return history


# ========== STATISTICS ==========

@router.get("/communities/{community_id}/phases/{phase_id}/statistics", response_model=PhaseStatistics)
def get_phase_statistics(
    community_id: str,
    phase_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Get detailed statistics for a phase
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    total_lots = db.query(func.count(LotModel.id)).filter(LotModel.phase_id == phase_id).scalar() or 0

    stats = PhaseStatistics(
        phase_id=phase.id,
        total_lots=total_lots,
        available_lots=db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.AVAILABLE
        ).scalar() or 0,
        reserved_lots=db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.RESERVED
        ).scalar() or 0,
        sold_lots=db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.SOLD
        ).scalar() or 0,
        unavailable_lots=db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.UNAVAILABLE
        ).scalar() or 0,
        on_hold_lots=db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.ON_HOLD
        ).scalar() or 0,
        average_price=db.query(func.avg(LotModel.price)).filter(
            LotModel.phase_id == phase_id, LotModel.price.isnot(None)
        ).scalar(),
        total_revenue=db.query(func.sum(LotModel.price)).filter(
            LotModel.phase_id == phase_id,
            LotModel.status == LotStatus.SOLD,
            LotModel.price.isnot(None)
        ).scalar(),
        completion_percentage=Decimal(str((stats_sold / total_lots * 100) if total_lots > 0 else 0))
        if (stats_sold := db.query(func.count(LotModel.id)).filter(
            LotModel.phase_id == phase_id, LotModel.status == LotStatus.SOLD
        ).scalar() or 0) else Decimal('0')
    )

    return stats


# ========== BATCH OPERATIONS ==========

@router.post("/communities/{community_id}/phases/{phase_id}/lots/batch", response_model=BulkOperationResult, status_code=status.HTTP_201_CREATED)
def bulk_create_lots(
    community_id: str,
    phase_id: int,
    bulk_create: BulkLotCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Bulk create multiple lots at once
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    created_lots = []
    failed_lots = []
    errors = []

    for lot_data in bulk_create.lots:
        try:
            # Check for duplicate lot number
            existing = db.query(LotModel).filter(
                LotModel.phase_id == phase_id,
                LotModel.lot_number == lot_data.lot_number
            ).first()

            if existing:
                failed_lots.append(lot_data.lot_number)
                errors.append(f"Lot {lot_data.lot_number} already exists")
                continue

            # Create lot
            new_lot = LotModel(
                phase_id=phase_id,
                community_id=community_id,
                **lot_data.dict(exclude={'phase_id', 'community_id', 'boundary_coordinates'}),
                boundary_coordinates=[coord.dict() for coord in lot_data.boundary_coordinates] if lot_data.boundary_coordinates else None
            )

            db.add(new_lot)
            created_lots.append(new_lot)

            # Create status history entry
            history = LotStatusHistory(
                lot_id=new_lot.id,
                old_status=None,
                new_status=new_lot.status,
                changed_by=current_user.email if current_user else "system",
                change_reason="Bulk lot creation"
            )
            db.add(history)

        except Exception as e:
            failed_lots.append(lot_data.lot_number)
            errors.append(f"Lot {lot_data.lot_number}: {str(e)}")

    # Update phase total_lots
    if created_lots:
        phase.total_lots = (phase.total_lots or 0) + len(created_lots)

    db.commit()

    # Refresh created lots
    for lot in created_lots:
        db.refresh(lot)

    return BulkOperationResult(
        success=len(created_lots),
        failed=len(failed_lots),
        total=len(bulk_create.lots),
        created_ids=[lot.id for lot in created_lots],
        errors=errors if errors else None,
        message=f"Created {len(created_lots)} lots, {len(failed_lots)} failed"
    )


@router.patch("/communities/{community_id}/phases/{phase_id}/lots/batch/status", response_model=BulkOperationResult)
def bulk_update_lot_status(
    community_id: str,
    phase_id: int,
    bulk_update: BulkLotStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Bulk update status for multiple lots
    """
    _get_phase_or_404(db, community_id, phase_id)

    updated_lots = []
    failed_lots = []
    errors = []

    for lot_id in bulk_update.lot_ids:
        try:
            lot = db.query(LotModel).filter(
                LotModel.id == lot_id,
                LotModel.phase_id == phase_id
            ).first()

            if not lot:
                failed_lots.append(lot_id)
                errors.append(f"Lot ID {lot_id} not found")
                continue

            old_status = lot.status

            # Update status
            lot.status = bulk_update.new_status

            # Update reservation/sale info based on status
            if bulk_update.new_status == LotStatus.RESERVED:
                lot.reserved_by = bulk_update.reserved_by
                lot.reserved_at = func.now()
            elif bulk_update.new_status == LotStatus.SOLD:
                lot.sold_to = bulk_update.sold_to
                lot.sold_at = func.now()

            # Create status history entry
            history = LotStatusHistory(
                lot_id=lot.id,
                old_status=old_status,
                new_status=bulk_update.new_status,
                changed_by=bulk_update.changed_by or (current_user.email if current_user else "system"),
                change_reason=bulk_update.change_reason or "Bulk status update"
            )
            db.add(history)

            updated_lots.append(lot.id)

        except Exception as e:
            failed_lots.append(lot_id)
            errors.append(f"Lot ID {lot_id}: {str(e)}")

    db.commit()

    return BulkOperationResult(
        success=len(updated_lots),
        failed=len(failed_lots),
        total=len(bulk_update.lot_ids),
        updated_ids=updated_lots,
        errors=errors if errors else None,
        message=f"Updated {len(updated_lots)} lots to {bulk_update.new_status.value}, {len(failed_lots)} failed"
    )


@router.delete("/communities/{community_id}/phases/{phase_id}/lots/batch", response_model=BulkOperationResult)
def bulk_delete_lots(
    community_id: str,
    phase_id: int,
    lot_ids: List[int] = Query(..., description="List of lot IDs to delete"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user_optional)
):
    """
    Bulk delete multiple lots
    """
    phase = _get_phase_or_404(db, community_id, phase_id)

    deleted_lots = []
    failed_lots = []
    errors = []

    for lot_id in lot_ids:
        try:
            lot = db.query(LotModel).filter(
                LotModel.id == lot_id,
                LotModel.phase_id == phase_id
            ).first()

            if not lot:
                failed_lots.append(lot_id)
                errors.append(f"Lot ID {lot_id} not found")
                continue

            db.delete(lot)
            deleted_lots.append(lot_id)

        except Exception as e:
            failed_lots.append(lot_id)
            errors.append(f"Lot ID {lot_id}: {str(e)}")

    # Update phase total_lots
    if deleted_lots:
        phase.total_lots = max(0, (phase.total_lots or 0) - len(deleted_lots))

    db.commit()

    return BulkOperationResult(
        success=len(deleted_lots),
        failed=len(failed_lots),
        total=len(lot_ids),
        deleted_ids=deleted_lots,
        errors=errors if errors else None,
        message=f"Deleted {len(deleted_lots)} lots, {len(failed_lots)} failed"
    )
