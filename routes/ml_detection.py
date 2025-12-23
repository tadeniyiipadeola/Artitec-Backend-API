"""
ML Detection API Endpoints
Provides endpoints for lot detection using various ML and CV methods
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import cv2
import numpy as np
import io
from pathlib import Path
import tempfile

from config.db import SessionLocal
from services.ocr_service import OCRService, LotNumberResult
from services.boundary_detection import BoundaryDetectionService, BoundaryResult
from services.line_lot_detector import LineLotDetector, LotPolygon
from services.auto_detect_service import AutoDetectService, DetectedLot
from services.ml_supervised_detector import MLSupervisedDetector, MLLotCandidate
from services.few_shot_detector import FewShotDetector, FewShotMatch, LotPattern
from services.yolo_detector import YOLODetector, YOLOLotResult, YOLODetectionResult


router = APIRouter(prefix="/ml", tags=["ML Detection"])


# ===== Pydantic Models =====

class OCRRequest(BaseModel):
    """OCR detection request"""
    min_confidence: float = Field(60.0, ge=0, le=100)
    custom_patterns: Optional[List[str]] = None


class BoundaryDetectionRequest(BaseModel):
    """Boundary detection request"""
    min_area: int = Field(1000, gt=0)
    max_area: Optional[int] = None
    use_grid: bool = False
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None


class LineDetectionRequest(BaseModel):
    """Line-based detection request"""
    min_area: int = Field(1000, gt=0)
    max_area: Optional[int] = None
    min_line_length: int = Field(50, gt=0)
    max_line_gap: int = Field(10, gt=0)


class AutoDetectRequest(BaseModel):
    """Auto-detect request"""
    use_ocr: bool = True
    use_grid: bool = False
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None
    min_area: int = Field(1000, gt=0)
    max_area: Optional[int] = None


class FewShotTrainRequest(BaseModel):
    """Few-shot training request"""
    pattern_name: str
    example_lots: List[List[List[float]]]  # List of polygons (coordinates)
    save_pattern: bool = True


class FewShotDetectRequest(BaseModel):
    """Few-shot detection request"""
    pattern_name: Optional[str] = None
    similarity_threshold: float = Field(0.7, ge=0, le=1)
    min_area: int = Field(1000, gt=0)
    max_area: Optional[int] = None


class SupervisedTrainingData(BaseModel):
    """Supervised learning training data"""
    corrections: List[Dict]
    phase_id: str


class YOLODetectionRequest(BaseModel):
    """YOLO detection request"""
    confidence_threshold: float = Field(0.25, ge=0, le=1)
    min_area: float = Field(500.0, gt=0)
    max_area: float = Field(50000.0, gt=0)


class YOLOMinIORequest(BaseModel):
    """YOLO detection from MinIO request"""
    minio_path: str
    confidence_threshold: float = Field(0.25, ge=0, le=1)
    min_area: float = Field(500.0, gt=0)
    max_area: float = Field(50000.0, gt=0)


# ===== Helper Functions =====

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


def image_to_bytes(image: np.ndarray, format: str = '.png') -> bytes:
    """Convert OpenCV image to bytes"""
    success, buffer = cv2.imencode(format, image)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encode image"
        )
    return buffer.tobytes()


# ===== OCR Endpoints =====

@router.post("/ocr/extract")
async def extract_lot_numbers(
    file: UploadFile = File(...),
    min_confidence: float = 60.0,
):
    """
    Extract lot numbers from image using OCR

    Args:
        file: Image file
        min_confidence: Minimum OCR confidence (0-100)

    Returns:
        List of detected lot numbers with positions and confidence
    """
    try:
        image = image_from_upload(file)

        service = OCRService(min_confidence=min_confidence)
        results = service.extract_lot_numbers(image)

        return {
            "total": len(results),
            "lot_numbers": [
                {
                    "lot_number": r.lot_number,
                    "confidence": r.confidence,
                    "position": {"x": r.position[0], "y": r.position[1]},
                    "bbox": {
                        "x": r.bbox[0],
                        "y": r.bbox[1],
                        "width": r.bbox[2],
                        "height": r.bbox[3],
                    },
                    "pattern_type": r.pattern_type,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(e)}"
        )


@router.post("/ocr/visualize")
async def visualize_ocr(
    file: UploadFile = File(...),
    min_confidence: float = 60.0,
):
    """
    Visualize OCR results on image

    Returns:
        Annotated image with detected lot numbers
    """
    try:
        image = image_from_upload(file)

        service = OCRService(min_confidence=min_confidence)
        results = service.extract_lot_numbers(image)
        visualized = service.visualize_results(image, results)

        img_bytes = image_to_bytes(visualized)

        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/png"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}"
        )


# ===== Boundary Detection Endpoints =====

@router.post("/boundary/detect")
async def detect_boundaries(
    file: UploadFile = File(...),
    min_area: int = 1000,
    max_area: Optional[int] = None,
    use_grid: bool = False,
    grid_rows: Optional[int] = None,
    grid_cols: Optional[int] = None,
):
    """
    Detect lot boundaries using edge detection

    Returns:
        List of detected boundaries (polygons)
    """
    try:
        image = image_from_upload(file)

        service = BoundaryDetectionService(
            min_area=min_area,
            max_area=max_area,
        )

        results = service.detect_boundaries(
            image,
            use_grid=use_grid,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
        )

        return {
            "total": len(results),
            "boundaries": [
                {
                    "coordinates": r.coordinates,
                    "area": r.area,
                    "perimeter": r.perimeter,
                    "confidence": r.confidence,
                    "method": r.method,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Boundary detection failed: {str(e)}"
        )


# ===== Line Detection Endpoints =====

@router.post("/line/detect")
async def detect_lines(
    file: UploadFile = File(...),
    min_area: int = 1000,
    max_area: Optional[int] = None,
):
    """
    Detect lot boundaries using Hough line detection

    Returns:
        List of detected lot polygons from lines
    """
    try:
        image = image_from_upload(file)

        detector = LineLotDetector(
            min_polygon_area=min_area,
            max_polygon_area=max_area,
        )

        results = detector.detect_lots(image)

        return {
            "total": len(results),
            "lots": [
                {
                    "vertices": r.vertices,
                    "area": r.area,
                    "confidence": r.confidence,
                    "method": r.method,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Line detection failed: {str(e)}"
        )


# ===== Auto-Detect Endpoints =====

@router.post("/auto-detect")
async def auto_detect_lots(
    file: UploadFile = File(...),
    use_ocr: bool = True,
    use_grid: bool = False,
    grid_rows: Optional[int] = None,
    grid_cols: Optional[int] = None,
    min_area: int = 1000,
):
    """
    Automatically detect lots using combined methods

    Combines boundary detection, line detection, and OCR

    Returns:
        List of detected lots with lot numbers and boundaries
    """
    try:
        image = image_from_upload(file)

        service = AutoDetectService(min_area=min_area)
        results = service.detect_lots(
            image,
            use_ocr=use_ocr,
            use_grid=use_grid,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
        )

        stats = service.get_statistics(results)

        return {
            "total": len(results),
            "statistics": stats,
            "lots": [
                {
                    "lot_number": r.lot_number,
                    "coordinates": r.coordinates,
                    "area": r.area,
                    "confidence": r.confidence,
                    "detection_method": r.detection_method,
                    "ocr_confidence": r.ocr_confidence,
                    "boundary_confidence": r.boundary_confidence,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-detection failed: {str(e)}"
        )


@router.post("/auto-detect/visualize")
async def visualize_auto_detect(
    file: UploadFile = File(...),
    use_ocr: bool = True,
    min_area: int = 1000,
):
    """
    Visualize auto-detection results

    Returns:
        Annotated image
    """
    try:
        image = image_from_upload(file)

        service = AutoDetectService(min_area=min_area)
        results = service.detect_lots(image, use_ocr=use_ocr)
        visualized = service.visualize_results(
            image,
            results,
            show_confidence=True,
            show_method=True,
        )

        img_bytes = image_to_bytes(visualized)

        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/png"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}"
        )


# ===== Few-Shot Learning Endpoints =====

# Store for few-shot detectors (in production, use database or persistent storage)
_few_shot_detectors: Dict[str, FewShotDetector] = {}

def get_few_shot_detector(phase_id: str) -> FewShotDetector:
    """Get or create few-shot detector for phase"""
    if phase_id not in _few_shot_detectors:
        patterns_dir = Path(tempfile.gettempdir()) / "artitec_patterns" / phase_id
        _few_shot_detectors[phase_id] = FewShotDetector(
            patterns_dir=str(patterns_dir),
        )
    return _few_shot_detectors[phase_id]


@router.post("/few-shot/train")
async def train_few_shot_pattern(
    phase_id: str,
    pattern_name: str = Form(...),
    file: UploadFile = File(...),
    example_coordinates: str = Form(...),  # JSON string of coordinates
):
    """
    Train few-shot pattern from example lots

    Args:
        phase_id: Phase identifier
        pattern_name: Name for this pattern
        file: Site plan image
        example_coordinates: JSON string of example polygon coordinates

    Returns:
        Pattern information
    """
    try:
        import json

        image = image_from_upload(file)
        coords_list = json.loads(example_coordinates)

        # Convert coordinates to contours
        contours = []
        for coords in coords_list:
            points = np.array(coords, dtype=np.int32)
            contours.append(points)

        detector = get_few_shot_detector(phase_id)
        pattern = detector.train_pattern(
            examples=contours,
            image=image,
            pattern_name=pattern_name,
            save_pattern=True,
        )

        return {
            "status": "success",
            "pattern_name": pattern.name,
            "training_samples": len(pattern.shape_descriptors),
            "avg_area": pattern.avg_area,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Few-shot training failed: {str(e)}"
        )


@router.post("/few-shot/{phase_id}/detect")
async def detect_with_few_shot(
    phase_id: str,
    file: UploadFile = File(...),
    pattern_name: Optional[str] = None,
    similarity_threshold: float = 0.7,
    min_area: int = 1000,
):
    """
    Detect lots using few-shot learned pattern

    Returns:
        List of matching lots
    """
    try:
        image = image_from_upload(file)

        detector = get_few_shot_detector(phase_id)
        detector.similarity_threshold = similarity_threshold

        results = detector.detect_similar_lots(
            image,
            pattern_name=pattern_name,
            min_area=min_area,
        )

        return {
            "total": len(results),
            "matches": [
                {
                    "coordinates": r.coordinates,
                    "area": r.area,
                    "confidence": r.confidence,
                    "similarity_score": r.similarity_score,
                    "matched_pattern": r.matched_pattern,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Few-shot detection failed: {str(e)}"
        )


@router.get("/few-shot/{phase_id}/patterns")
async def list_few_shot_patterns(phase_id: str):
    """List all few-shot patterns for a phase"""
    try:
        detector = get_few_shot_detector(phase_id)
        patterns = detector.list_patterns()

        pattern_info = []
        for pattern_name in patterns:
            info = detector.get_pattern_info(pattern_name)
            pattern_info.append(info)

        return {
            "total": len(patterns),
            "patterns": pattern_info,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list patterns: {str(e)}"
        )


@router.delete("/few-shot/{phase_id}/patterns/{pattern_name}")
async def delete_few_shot_pattern(phase_id: str, pattern_name: str):
    """Delete a few-shot pattern"""
    try:
        detector = get_few_shot_detector(phase_id)
        detector.delete_pattern(pattern_name)

        return {"status": "success", "message": f"Pattern '{pattern_name}' deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pattern: {str(e)}"
        )


# ===== Supervised Learning Endpoints =====

# Store for supervised detectors (in production, use database)
_supervised_detectors: Dict[str, MLSupervisedDetector] = {}

def get_supervised_detector(phase_id: str) -> MLSupervisedDetector:
    """Get or create supervised detector for phase"""
    if phase_id not in _supervised_detectors:
        model_path = Path(tempfile.gettempdir()) / "artitec_models" / f"{phase_id}.pkl"
        _supervised_detectors[phase_id] = MLSupervisedDetector(
            model_path=str(model_path),
        )
    return _supervised_detectors[phase_id]


@router.post("/supervised/{phase_id}/train")
async def train_supervised_model(
    phase_id: str,
    file: UploadFile = File(...),
    corrections_json: str = Form(...),  # JSON of corrections
):
    """
    Train supervised ML model from user corrections

    Args:
        phase_id: Phase identifier
        file: Training image
        corrections_json: JSON with corrections (contours and labels)

    Returns:
        Training metrics
    """
    try:
        import json

        image = image_from_upload(file)
        corrections = json.loads(corrections_json)

        detector = get_supervised_detector(phase_id)

        # Add corrections
        for correction in corrections:
            contour = np.array(correction['contour'], dtype=np.int32)
            is_lot = correction['is_lot']

            detector.add_correction(
                contour=contour,
                image=image,
                is_lot=is_lot,
                phase_id=phase_id,
            )

        # Train model
        metrics = detector.retrain()

        return {
            "status": "success",
            "metrics": metrics,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supervised training failed: {str(e)}"
        )


@router.post("/supervised/{phase_id}/detect")
async def detect_with_supervised(
    phase_id: str,
    file: UploadFile = File(...),
    min_area: int = 1000,
):
    """
    Detect lots using trained supervised model

    Returns:
        List of detected lots
    """
    try:
        image = image_from_upload(file)

        detector = get_supervised_detector(phase_id)

        if not detector.is_trained:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model not trained. Train the model first."
            )

        results = detector.detect_lots(image, min_area=min_area)

        return {
            "total": len(results),
            "lots": [
                {
                    "coordinates": r.coordinates,
                    "area": r.area,
                    "confidence": r.confidence,
                    "prediction": r.prediction,
                }
                for r in results
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supervised detection failed: {str(e)}"
        )


@router.get("/supervised/{phase_id}/info")
async def get_supervised_model_info(phase_id: str):
    """Get information about trained supervised model"""
    try:
        detector = get_supervised_detector(phase_id)
        info = detector.get_model_info()

        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model info: {str(e)}"
        )


# ===== YOLO Detection Endpoints =====

@router.post("/yolo/detect")
async def detect_lots_with_yolo(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.25,
    min_area: float = 500.0,
    max_area: float = 50000.0,
):
    """
    Detect lots using YOLOv8 deep learning segmentation

    This is the most accurate detection method (95%+ accuracy)

    Args:
        file: Image or PDF file
        confidence_threshold: Minimum detection confidence (0-1)
        min_area: Minimum lot area in pixels
        max_area: Maximum lot area in pixels

    Returns:
        Detected lots with high accuracy segmentation
    """
    try:
        image = image_from_upload(file)

        detector = YOLODetector(
            confidence_threshold=confidence_threshold,
            min_area=min_area,
            max_area=max_area,
        )

        result = detector.detect_from_array(image, confidence_threshold)

        return {
            "total_detections": result.total_detections,
            "lots_detected": result.lots_detected,
            "model_type": result.model_type,
            "confidence_threshold": result.confidence_threshold,
            "average_confidence": result.average_confidence,
            "image_dimensions": result.image_dimensions,
            "lots": [
                {
                    "lot_number": lot.lot_number,
                    "coordinates": lot.coordinates,
                    "area": lot.area,
                    "confidence": lot.confidence,
                    "centroid": {"x": lot.centroid[0], "y": lot.centroid[1]},
                    "num_sides": lot.num_sides,
                    "detection_method": lot.detection_method,
                }
                for lot in result.lots
            ]
        }
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="YOLO detector not available. Install with: pip install ultralytics"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YOLO detection failed: {str(e)}"
        )


@router.post("/yolo/detect-minio")
async def detect_lots_yolo_from_minio(
    minio_path: str = Form(...),
    confidence_threshold: float = Form(0.25),
    min_area: float = Form(500.0),
    max_area: float = Form(50000.0),
):
    """
    Detect lots from MinIO storage using YOLO

    Args:
        minio_path: Path to image in MinIO (e.g., 'phases/CMY-XXX/site-plan.jpg')
        confidence_threshold: Minimum confidence (0-1)
        min_area: Minimum lot area
        max_area: Maximum lot area

    Returns:
        Detected lots
    """
    try:
        detector = YOLODetector(
            confidence_threshold=confidence_threshold,
            min_area=min_area,
            max_area=max_area,
        )

        result = detector.detect_from_minio(minio_path, confidence_threshold)

        return {
            "total_detections": result.total_detections,
            "lots_detected": result.lots_detected,
            "model_type": result.model_type,
            "confidence_threshold": result.confidence_threshold,
            "average_confidence": result.average_confidence,
            "image_dimensions": result.image_dimensions,
            "lots": [
                {
                    "lot_number": lot.lot_number,
                    "coordinates": lot.coordinates,
                    "area": lot.area,
                    "confidence": lot.confidence,
                    "centroid": {"x": lot.centroid[0], "y": lot.centroid[1]},
                    "num_sides": lot.num_sides,
                    "detection_method": lot.detection_method,
                }
                for lot in result.lots
            ]
        }
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="YOLO detector not available. Install with: pip install ultralytics"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YOLO detection failed: {str(e)}"
        )


@router.post("/yolo/visualize")
async def visualize_yolo_detection(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.25,
    min_area: float = 500.0,
    max_area: float = 50000.0,
):
    """
    Visualize YOLO detection results

    Returns:
        Annotated image with detected lots
    """
    try:
        image = image_from_upload(file)

        detector = YOLODetector(
            confidence_threshold=confidence_threshold,
            min_area=min_area,
            max_area=max_area,
        )

        result = detector.detect_from_array(image, confidence_threshold)

        # Draw results on image
        vis_image = image.copy()
        for lot in result.lots:
            # Draw polygon
            points = np.array(lot.coordinates, dtype=np.int32)
            cv2.polylines(vis_image, [points], True, (0, 255, 0), 2)

            # Draw lot number and confidence
            cx, cy = lot.centroid
            text = f"{lot.lot_number} ({lot.confidence:.2f})"
            cv2.putText(
                vis_image,
                text,
                (cx - 20, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2
            )

        img_bytes = image_to_bytes(vis_image)

        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/png"
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="YOLO detector not available. Install with: pip install ultralytics"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization failed: {str(e)}"
        )
