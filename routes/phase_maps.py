"""
Phase Map Detection API Endpoints
Provides ML/AI lot detection endpoints for phase site plans
Integrates with existing community phase endpoints
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form, status, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import cv2
import numpy as np
import io
from pathlib import Path
import tempfile
from datetime import datetime

from config.db import SessionLocal
from model.profiles.community import CommunityPhase, Community
from model.profiles.lot import Lot, LotStatus
from services.auto_detect_service import AutoDetectService
from services.yolo_detector import YOLODetector
from services.ocr_service import OCRService
from services.batch_processor import BatchProcessor, DetectionMethod
from src.storage_service import storage_service


router = APIRouter(tags=["Phase Maps"])


# ===== Pydantic Models =====

class UploadPhaseMapRequest(BaseModel):
    """Upload phase map request"""
    phase_id: int
    replace_existing: bool = False


class AutoDetectRequest(BaseModel):
    """Auto-detect lots request"""
    phase_id: int
    detection_method: str = Field("auto", description="auto, yolo, ocr, boundary, line")
    use_ocr: bool = True
    min_area: int = Field(1000, gt=0)
    confidence_threshold: float = Field(0.25, ge=0, le=1)
    save_to_database: bool = True


class AutoDetectGridRequest(BaseModel):
    """Auto-detect with grid layout"""
    phase_id: int
    grid_rows: int = Field(..., gt=0)
    grid_cols: int = Field(..., gt=0)
    detection_method: str = "auto"
    save_to_database: bool = True


class BatchAutoDetectRequest(BaseModel):
    """Batch auto-detect request"""
    phase_ids: List[int]
    detection_method: str = "auto"
    min_area: int = 1000
    confidence_threshold: float = 0.25


class LotDetectionResult(BaseModel):
    """Single lot detection result"""
    lot_number: str
    coordinates: List[List[float]]
    area: float
    confidence: float
    detection_method: str


class PhaseMapDetectionResponse(BaseModel):
    """Phase map detection response"""
    phase_id: int
    total_lots_detected: int
    lots: List[LotDetectionResult]
    detection_method: str
    processing_time: float
    image_dimensions: Dict[str, int]


# ===== Helper Functions =====

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def image_from_upload(file: UploadFile) -> np.ndarray:
    """Convert uploaded file to OpenCV image"""
    contents = file.file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode image"
        )

    return image


# ===== Phase Map Upload Endpoint =====

@router.post("/{phase_id}/upload-map")
async def upload_phase_map(
    phase_id: int,
    file: UploadFile = File(...),
    replace_existing: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    Upload site plan map for a phase

    Stores the image in MinIO and updates the phase record
    """
    try:
        # Verify phase exists
        phase = db.query(CommunityPhase).filter(CommunityPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phase {phase_id} not found"
            )

        # Check if map already exists and replace_existing is False
        if phase.site_plan_image_url and not replace_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Site plan already exists. Set replace_existing=true to replace."
            )

        # Validate file type
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_ext}"
            )

        # Read file contents
        file_contents = await file.read()

        # Create storage path
        storage_path = f"phases/{phase.community_id}/phase-{phase_id}-{file.filename}"

        # Upload to MinIO
        file_obj = io.BytesIO(file_contents)
        public_url = storage_service.upload_file(
            file_obj,
            storage_path,
            content_type=file.content_type or 'application/octet-stream'
        )

        # Get image dimensions if it's an image
        image_width = None
        image_height = None
        if file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            nparr = np.frombuffer(file_contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                image_height, image_width = img.shape[:2]

        # Update phase record
        phase.site_plan_image_url = public_url
        phase.original_file_path = storage_path
        phase.file_type = file_ext.lstrip('.')
        phase.image_width = image_width
        phase.image_height = image_height
        phase.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(phase)

        return {
            "status": "success",
            "message": "Site plan uploaded successfully",
            "phase_id": phase_id,
            "site_plan_url": public_url,
            "image_dimensions": {
                "width": image_width,
                "height": image_height
            } if image_width and image_height else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload site plan: {str(e)}"
        )


# ===== Auto-Detection Endpoints =====

@router.post("/{phase_id}/auto-detect", response_model=PhaseMapDetectionResponse)
async def auto_detect_lots(
    phase_id: int,
    detection_method: str = Form("auto"),
    use_ocr: bool = Form(True),
    min_area: int = Form(1000),
    confidence_threshold: float = Form(0.25),
    save_to_database: bool = Form(True),
    db: Session = Depends(get_db),
):
    """
    Auto-detect lots on phase map using ML/AI

    Supports multiple detection methods:
    - auto: Combined OCR + boundary detection
    - yolo: Deep learning segmentation (highest accuracy)
    - ocr: OCR-based lot number detection
    - boundary: Edge detection
    - line: Hough line detection
    """
    start_time = datetime.now()

    try:
        # Get phase with site plan
        phase = db.query(CommunityPhase).filter(CommunityPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phase {phase_id} not found"
            )

        if not phase.site_plan_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No site plan uploaded for this phase"
            )

        # Download image from MinIO
        image_data = storage_service.download_file(phase.original_file_path or phase.site_plan_image_url.split('/')[-1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not decode site plan image"
            )

        # Run detection based on method
        detected_lots = []

        if detection_method == "yolo":
            detector = YOLODetector(
                confidence_threshold=confidence_threshold,
                min_area=min_area,
            )
            result = detector.detect_from_array(image, confidence_threshold)
            detected_lots = result.lots

        elif detection_method == "auto":
            service = AutoDetectService(min_area=min_area)
            results = service.detect_lots(image, use_ocr=use_ocr)
            detected_lots = results

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported detection method: {detection_method}"
            )

        # Save to database if requested
        if save_to_database and detected_lots:
            # Clear existing lots for this phase
            db.query(Lot).filter(Lot.phase_id == phase_id).delete()

            # Create new lots
            for lot in detected_lots:
                new_lot = Lot(
                    phase_id=phase_id,
                    community_id=phase.community_id,
                    lot_number=lot.lot_number if hasattr(lot, 'lot_number') else str(getattr(lot, 'lot_number', '')),
                    boundary_coordinates=[{"x": coord[0], "y": coord[1]} for coord in lot.coordinates] if hasattr(lot, 'coordinates') else None,
                    status=LotStatus.AVAILABLE,
                    detection_method=detection_method,
                    detection_confidence=float(lot.confidence) if hasattr(lot, 'confidence') else None,
                )
                db.add(new_lot)

            # Update phase total_lots
            phase.total_lots = len(detected_lots)

            db.commit()

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Build response
        height, width = image.shape[:2]

        return PhaseMapDetectionResponse(
            phase_id=phase_id,
            total_lots_detected=len(detected_lots),
            lots=[
                LotDetectionResult(
                    lot_number=lot.lot_number if hasattr(lot, 'lot_number') else '',
                    coordinates=[[float(c[0]), float(c[1])] for c in lot.coordinates] if hasattr(lot, 'coordinates') else [],
                    area=float(lot.area) if hasattr(lot, 'area') else 0.0,
                    confidence=float(lot.confidence) if hasattr(lot, 'confidence') else 0.0,
                    detection_method=detection_method,
                )
                for lot in detected_lots
            ],
            detection_method=detection_method,
            processing_time=processing_time,
            image_dimensions={"width": width, "height": height},
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )


@router.post("/{phase_id}/auto-detect-grid")
async def auto_detect_with_grid(
    phase_id: int,
    grid_rows: int = Form(...),
    grid_cols: int = Form(...),
    detection_method: str = Form("auto"),
    save_to_database: bool = Form(True),
    db: Session = Depends(get_db),
):
    """
    Auto-detect lots with grid layout assumption

    Useful for uniformly laid out phases where lots are in a regular grid
    """
    try:
        # Get phase
        phase = db.query(CommunityPhase).filter(CommunityPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phase {phase_id} not found"
            )

        if not phase.site_plan_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No site plan uploaded for this phase"
            )

        # Download and decode image
        image_data = storage_service.download_file(phase.original_file_path or phase.site_plan_image_url.split('/')[-1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not decode site plan image"
            )

        # Use auto-detect with grid
        service = AutoDetectService()
        results = service.detect_lots(
            image,
            use_grid=True,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
        )

        # Save to database if requested
        if save_to_database and results:
            # Clear existing lots
            db.query(Lot).filter(Lot.phase_id == phase_id).delete()

            # Create new lots
            for lot in results:
                new_lot = Lot(
                    phase_id=phase_id,
                    community_id=phase.community_id,
                    lot_number=lot.lot_number,
                    boundary_coordinates=[{"x": coord[0], "y": coord[1]} for coord in lot.coordinates],
                    status=LotStatus.AVAILABLE,
                    detection_method="grid",
                    detection_confidence=lot.confidence,
                )
                db.add(new_lot)

            phase.total_lots = len(results)
            db.commit()

        return {
            "status": "success",
            "phase_id": phase_id,
            "total_lots_detected": len(results),
            "grid_layout": {"rows": grid_rows, "cols": grid_cols},
            "saved_to_database": save_to_database,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grid detection failed: {str(e)}"
        )


@router.post("/batch/auto-detect")
async def batch_auto_detect(
    phase_ids: List[int] = Form(...),
    detection_method: str = Form("auto"),
    min_area: int = Form(1000),
    confidence_threshold: float = Form(0.25),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Batch auto-detect lots across multiple phases

    Returns job ID for tracking progress
    """
    try:
        # Verify all phases exist and have site plans
        phases = db.query(CommunityPhase).filter(CommunityPhase.id.in_(phase_ids)).all()

        if len(phases) != len(phase_ids):
            found_ids = {p.id for p in phases}
            missing = set(phase_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phases not found: {missing}"
            )

        phases_without_maps = [p.id for p in phases if not p.site_plan_image_url]
        if phases_without_maps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phases without site plans: {phases_without_maps}"
            )

        # Create batch job
        # Note: This is a simplified implementation
        # In production, you'd use Celery or similar task queue

        results = []
        for phase in phases:
            try:
                # Download image
                image_data = storage_service.download_file(phase.original_file_path or phase.site_plan_image_url.split('/')[-1])
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if image is None:
                    results.append({
                        "phase_id": phase.id,
                        "status": "failed",
                        "error": "Could not decode image"
                    })
                    continue

                # Run detection
                if detection_method == "yolo":
                    detector = YOLODetector(
                        confidence_threshold=confidence_threshold,
                        min_area=min_area,
                    )
                    result = detector.detect_from_array(image, confidence_threshold)
                    detected_lots = result.lots
                else:
                    service = AutoDetectService(min_area=min_area)
                    detected_lots = service.detect_lots(image, use_ocr=True)

                results.append({
                    "phase_id": phase.id,
                    "status": "success",
                    "lots_detected": len(detected_lots)
                })

            except Exception as e:
                results.append({
                    "phase_id": phase.id,
                    "status": "failed",
                    "error": str(e)
                })

        return {
            "status": "completed",
            "total_phases": len(phase_ids),
            "results": results,
            "detection_method": detection_method,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch detection failed: {str(e)}"
        )


# ===== Export Endpoint =====

@router.get("/{phase_id}/export")
async def export_phase_map(
    phase_id: int,
    format: str = "json",
    db: Session = Depends(get_db),
):
    """
    Export phase map with lot data

    Formats: json, csv, geojson
    """
    try:
        # Get phase with lots
        phase = db.query(CommunityPhase).filter(CommunityPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phase {phase_id} not found"
            )

        # Get all lots for this phase
        lots = db.query(Lot).filter(Lot.phase_id == phase_id).all()

        if format == "json":
            export_data = {
                "phase": {
                    "id": phase.id,
                    "name": phase.name,
                    "community_id": phase.community_id,
                    "status": phase.status,
                    "total_lots": phase.total_lots,
                    "site_plan_url": phase.site_plan_image_url,
                    "image_dimensions": {
                        "width": phase.image_width,
                        "height": phase.image_height
                    } if phase.image_width and phase.image_height else None,
                },
                "lots": [
                    {
                        "id": lot.id,
                        "lot_number": lot.lot_number,
                        "status": lot.status.value,
                        "boundary_coordinates": lot.boundary_coordinates,
                        "square_footage": lot.square_footage,
                        "price": float(lot.price) if lot.price else None,
                        "detection_method": lot.detection_method,
                        "detection_confidence": float(lot.detection_confidence) if lot.detection_confidence else None,
                    }
                    for lot in lots
                ],
                "export_timestamp": datetime.utcnow().isoformat(),
            }

            return JSONResponse(content=export_data)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


# ===== Statistics Endpoint =====

@router.get("/{phase_id}/statistics")
async def get_phase_map_statistics(
    phase_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed statistics for a phase map

    Includes lot counts by status, detection methods, etc.
    """
    try:
        # Get phase
        phase = db.query(CommunityPhase).filter(CommunityPhase.id == phase_id).first()
        if not phase:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Phase {phase_id} not found"
            )

        # Get lots with aggregations
        lots = db.query(Lot).filter(Lot.phase_id == phase_id).all()

        # Calculate statistics
        stats = {
            "phase_id": phase_id,
            "phase_name": phase.name,
            "total_lots": len(lots),
            "by_status": {},
            "by_detection_method": {},
            "avg_detection_confidence": 0.0,
            "has_site_plan": bool(phase.site_plan_image_url),
            "image_dimensions": {
                "width": phase.image_width,
                "height": phase.image_height
            } if phase.image_width and phase.image_height else None,
        }

        # Count by status
        for lot in lots:
            status_key = lot.status.value
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1

            # Count by detection method
            if lot.detection_method:
                stats["by_detection_method"][lot.detection_method] = \
                    stats["by_detection_method"].get(lot.detection_method, 0) + 1

        # Calculate average confidence
        confidences = [float(lot.detection_confidence) for lot in lots if lot.detection_confidence]
        if confidences:
            stats["avg_detection_confidence"] = sum(confidences) / len(confidences)

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )
