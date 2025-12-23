"""
ML Training and Feedback Routes
Handles supervised ML training, user feedback, and few-shot learning
"""
from typing import List, Dict, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from config.db import get_db
from config.security import get_current_user_optional
from model.user import Users
from model.profiles.community import CommunityPhase
from model.profiles.lot import Lot as LotModel, LotStatus

# ML Services (optional - only available if services are implemented)
try:
    from services.supervised_ml import SupervisedMLService
    from services.few_shot import FewShotService
    ML_SERVICES_AVAILABLE = True
except ImportError:
    ML_SERVICES_AVAILABLE = False
    SupervisedMLService = None  # type: ignore
    FewShotService = None  # type: ignore

router = APIRouter()


# ========== SCHEMAS ==========

class LotCorrection(BaseModel):
    """User correction for a detected lot"""
    lot_id: int
    is_correct: bool
    corrected_coordinates: Optional[List[Dict[str, int]]] = None


class TrainingFeedback(BaseModel):
    """Training feedback from user corrections"""
    phase_id: int
    corrections: List[LotCorrection]
    deleted_lot_ids: List[int] = []
    detection_method: str  # "supervised_ml", "few_shot", "yolo", etc.


class ExampleLot(BaseModel):
    """Example lot for few-shot learning"""
    coordinates: List[Dict[str, int]]  # Array of {x, y} points
    lot_number: Optional[str] = None


class FewShotTrainingRequest(BaseModel):
    """Request to train few-shot model with examples"""
    phase_id: int
    examples: List[ExampleLot]
    pattern_name: str = "default"
    min_similarity: float = 0.85


class MLDetectionRequest(BaseModel):
    """Request for ML-based detection"""
    phase_id: int
    confidence_threshold: float = 0.6
    save_to_database: bool = False
    clear_existing_lots: bool = False


# ========== SUPERVISED ML ENDPOINTS ==========

@router.post("/supervised/detect")
async def detect_lots_supervised_ml(
    request: MLDetectionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Detect lots using supervised ML model with road and line detection

    The model learns from user corrections and improves over time.
    Requires training data from user feedback to work effectively.
    """
    # Get phase
    phase = db.query(CommunityPhase).filter(
        CommunityPhase.id == request.phase_id
    ).first()

    if not phase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phase {request.phase_id} not found"
        )

    if not phase.site_plan_image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No site plan uploaded for this phase"
        )

    if not ML_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supervised ML service not yet implemented"
        )

    try:
        # Initialize ML detector
        ml_service = SupervisedMLService()

        # Download image from MinIO
        from src.storage_service import storage_service
        image_bytes = storage_service.download_file(phase.original_file_path)

        # Convert bytes to numpy array
        import io
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        image = np.array(img)

        # Run ML detection
        result = ml_service.detect_lots(
            image,
            confidence_threshold=request.confidence_threshold
        )

        detected_lots = result.lots

        # Optionally save to database
        saved_lots = []
        if request.save_to_database:
            # Clear existing lots if requested
            if request.clear_existing_lots:
                db.query(LotModel).filter(LotModel.phase_id == request.phase_id).delete()

            # Create lots
            for idx, lot_data in enumerate(detected_lots):
                new_lot = LotModel(
                    phase_id=request.phase_id,
                    community_id=phase.community_id,
                    lot_number=lot_data.lot_number or f"ML-{idx + 1}",
                    status=LotStatus.AVAILABLE,
                    boundary_coordinates=[{"x": coord[0], "y": coord[1]} for coord in lot_data.coordinates],
                    detection_method="supervised_ml",
                    detection_confidence=Decimal(str(lot_data.confidence)),
                    notes=f"Supervised ML detection (confidence: {lot_data.confidence:.2%})"
                )
                db.add(new_lot)
                saved_lots.append(new_lot)

            # Update phase total_lots
            phase.total_lots = len(saved_lots)
            db.commit()

            # Refresh lots
            for lot in saved_lots:
                db.refresh(lot)

        # Get model stats
        model_stats = ml_service.get_model_stats()

        return {
            "phase_id": request.phase_id,
            "detected_lots": [
                {
                    "lot_number": lot.lot_number,
                    "coordinates": lot.coordinates,
                    "confidence": float(lot.confidence),
                    "area": float(lot.area),
                }
                for lot in detected_lots
            ],
            "saved_lots": [
                {
                    "id": lot.id,
                    "lot_number": lot.lot_number,
                    "confidence": float(lot.detection_confidence)
                }
                for lot in saved_lots
            ] if request.save_to_database else [],
            "total_detected": len(detected_lots),
            "total_saved": len(saved_lots),
            "model_stats": model_stats,
            "metadata": {
                "road_coverage": result.road_mask_coverage,
                "lines_detected": result.lines_detected,
                "model_trained": result.model_trained,
                "total_training_samples": result.total_training_samples
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML detection failed: {str(e)}"
        )


@router.post("/feedback")
async def submit_training_feedback(
    feedback: TrainingFeedback,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Submit user corrections as training data for ML models

    This endpoint allows models to learn from user corrections,
    implementing supervised learning that improves over time.

    The model automatically retrains when enough samples are collected.
    """
    # Get phase
    phase = db.query(CommunityPhase).filter(
        CommunityPhase.id == feedback.phase_id
    ).first()

    if not phase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phase {feedback.phase_id} not found"
        )

    try:
        # Process corrections based on detection method
        if feedback.detection_method == "supervised_ml":
            if not ML_SERVICES_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Supervised ML service not yet implemented"
                )
            ml_service = SupervisedMLService()

            # Download image from MinIO
            from src.storage_service import storage_service
            image_bytes = storage_service.download_file(phase.original_file_path)

            # Convert to numpy array
            import io
            import numpy as np
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            image = np.array(img)

            # Prepare correct lots (user-confirmed or corrected)
            correct_lots = []
            for correction in feedback.corrections:
                if correction.is_correct:
                    lot = db.query(LotModel).filter(LotModel.id == correction.lot_id).first()
                    if lot:
                        coords = correction.corrected_coordinates if correction.corrected_coordinates else lot.boundary_coordinates
                        correct_lots.append({
                            'coordinates': [(c['x'], c['y']) for c in coords],
                            'lot_number': lot.lot_number,
                            'lot_id': lot.id
                        })

            # Prepare detected lots (all lots from this phase detected by ML)
            detected_lots = []
            all_lots = db.query(LotModel).filter(
                LotModel.phase_id == feedback.phase_id,
                LotModel.detection_method == "supervised_ml"
            ).all()

            for lot in all_lots:
                detected_lots.append({
                    'coordinates': [(c['x'], c['y']) for c in lot.boundary_coordinates],
                    'lot_number': lot.lot_number,
                    'confidence': float(lot.detection_confidence) if lot.detection_confidence else 0.5
                })

            # Add training sample
            ml_service.add_training_sample(image, correct_lots, detected_lots)

            # Get updated stats
            model_stats = ml_service.get_model_stats()

            # Check if we should retrain
            should_retrain = model_stats['total_training_samples'] >= 10

            if should_retrain:
                ml_service.train_model()
                model_stats = ml_service.get_model_stats()

            # Update corrected lots in database
            for correction in feedback.corrections:
                if correction.corrected_coordinates:
                    lot = db.query(LotModel).filter(LotModel.id == correction.lot_id).first()
                    if lot:
                        lot.boundary_coordinates = correction.corrected_coordinates

            # Delete rejected lots
            for lot_id in feedback.deleted_lot_ids:
                lot = db.query(LotModel).filter(LotModel.id == lot_id).first()
                if lot:
                    db.delete(lot)

            db.commit()

            return {
                "status": "success",
                "message": f"Training feedback recorded. {len(correct_lots)} corrections added.",
                "model_stats": model_stats,
                "model_retrained": should_retrain,
                "corrections_applied": len(correct_lots),
                "lots_deleted": len(feedback.deleted_lot_ids)
            }

        else:
            # For other detection methods, just update the lots
            for correction in feedback.corrections:
                if correction.corrected_coordinates:
                    lot = db.query(LotModel).filter(LotModel.id == correction.lot_id).first()
                    if lot:
                        lot.boundary_coordinates = correction.corrected_coordinates

            for lot_id in feedback.deleted_lot_ids:
                lot = db.query(LotModel).filter(LotModel.id == lot_id).first()
                if lot:
                    db.delete(lot)

            db.commit()

            return {
                "status": "success",
                "message": "Corrections applied (no model retraining for this detection method)",
                "corrections_applied": len([c for c in feedback.corrections if c.corrected_coordinates]),
                "lots_deleted": len(feedback.deleted_lot_ids)
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process training feedback: {str(e)}"
        )


@router.post("/supervised/train")
async def train_supervised_model(
    min_samples: int = 10,
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Manually trigger supervised ML model retraining

    Requires at least min_samples training examples from user feedback.
    """
    if not ML_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supervised ML service not yet implemented"
        )

    try:
        ml_service = SupervisedMLService()
        ml_service.train_model(min_samples=min_samples)

        model_stats = ml_service.get_model_stats()

        return {
            "status": "success",
            "message": "Supervised ML model retrained successfully",
            "model_stats": model_stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )


@router.get("/supervised/stats")
async def get_supervised_model_stats():
    """Get current supervised ML model statistics"""
    if not ML_SERVICES_AVAILABLE:
        return {
            "status": "service_unavailable",
            "message": "Supervised ML service not yet implemented",
            "stats": None
        }

    try:
        ml_service = SupervisedMLService()
        stats = ml_service.get_model_stats()

        return {
            "status": "success",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model stats: {str(e)}"
        )


# ========== FEW-SHOT LEARNING ENDPOINTS ==========

@router.post("/few-shot/train")
async def train_few_shot_model(
    request: FewShotTrainingRequest,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Train few-shot model from 2-3 example lots

    Create the first few lots manually, and the system will learn
    the pattern from those examples to detect similar lots.
    """
    # Validate we have at least 2 examples
    if len(request.examples) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 example lots for few-shot learning"
        )

    # Get phase
    phase = db.query(CommunityPhase).filter(
        CommunityPhase.id == request.phase_id
    ).first()

    if not phase:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Phase {request.phase_id} not found"
        )

    if not phase.site_plan_image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No site plan uploaded for this phase"
        )

    if not ML_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Few-shot learning service not yet implemented"
        )

    try:
        # Initialize few-shot detector
        few_shot_service = FewShotService()

        # Download image from MinIO
        from src.storage_service import storage_service
        image_bytes = storage_service.download_file(phase.original_file_path)

        # Convert to numpy array
        import io
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        image = np.array(img)

        # Convert examples to service format
        example_lots = [
            {
                'coordinates': [(c['x'], c['y']) for c in example.coordinates],
                'lot_number': example.lot_number
            }
            for example in request.examples
        ]

        # Learn from examples
        pattern_stats = few_shot_service.learn_from_examples(
            image,
            example_lots,
            pattern_name=request.pattern_name
        )

        return {
            "status": "success",
            "message": f"Few-shot model trained with {len(request.examples)} examples",
            "pattern": pattern_stats,
            "pattern_name": request.pattern_name
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Few-shot training failed: {str(e)}"
        )


@router.post("/few-shot/detect")
async def detect_lots_few_shot(
    phase_id: int,
    pattern_name: str = "default",
    similarity_threshold: float = 0.85,
    max_lots: Optional[int] = None,
    save_to_database: bool = False,
    clear_existing_lots: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Detect lots similar to learned examples using few-shot learning

    After training with 2-3 example lots, this endpoint detects all
    other lots that match the pattern learned from those examples.
    """
    # Get phase
    phase = db.query(CommunityPhase).filter(
        CommunityPhase.id == phase_id
    ).first()

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

    if not ML_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Few-shot learning service not yet implemented"
        )

    try:
        # Initialize few-shot detector
        few_shot_service = FewShotService()

        # Download image from MinIO
        from src.storage_service import storage_service
        image_bytes = storage_service.download_file(phase.original_file_path)

        # Convert to numpy array
        import io
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        image = np.array(img)

        # Detect similar lots
        result = few_shot_service.detect_similar_lots(
            image,
            pattern_name=pattern_name,
            similarity_threshold=similarity_threshold,
            max_lots=max_lots
        )

        detected_lots = result.lots

        # Optionally save to database
        saved_lots = []
        if save_to_database:
            # Clear existing lots if requested
            if clear_existing_lots:
                db.query(LotModel).filter(LotModel.phase_id == phase_id).delete()

            # Create lots
            for idx, lot_data in enumerate(detected_lots):
                new_lot = LotModel(
                    phase_id=phase_id,
                    community_id=phase.community_id,
                    lot_number=lot_data.lot_number or f"FS-{idx + 1}",
                    status=LotStatus.AVAILABLE,
                    boundary_coordinates=[{"x": coord[0], "y": coord[1]} for coord in lot_data.coordinates],
                    detection_method="few_shot",
                    detection_confidence=Decimal(str(lot_data.similarity)),
                    notes=f"Few-shot detection (similarity: {lot_data.similarity:.2%}, pattern: {pattern_name})"
                )
                db.add(new_lot)
                saved_lots.append(new_lot)

            # Update phase total_lots
            phase.total_lots = len(saved_lots)
            db.commit()

            # Refresh lots
            for lot in saved_lots:
                db.refresh(lot)

        return {
            "status": "success",
            "phase_id": phase_id,
            "detected_lots": [
                {
                    "lot_number": lot.lot_number,
                    "coordinates": lot.coordinates,
                    "similarity": float(lot.similarity),
                }
                for lot in detected_lots
            ],
            "saved_lots": [
                {
                    "id": lot.id,
                    "lot_number": lot.lot_number,
                    "similarity": float(lot.detection_confidence)
                }
                for lot in saved_lots
            ] if save_to_database else [],
            "total_detected": len(detected_lots),
            "total_saved": len(saved_lots),
            "metadata": {
                "pattern_name": result.pattern_name,
                "similarity_threshold": result.similarity_threshold,
                "total_candidates": result.total_candidates,
                "avg_similarity": result.avg_similarity
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Few-shot detection failed: {str(e)}"
        )


@router.get("/few-shot/patterns")
async def get_few_shot_patterns():
    """Get all saved few-shot patterns"""
    if not ML_SERVICES_AVAILABLE:
        return {
            "status": "service_unavailable",
            "message": "Few-shot learning service not yet implemented",
            "patterns": []
        }

    try:
        few_shot_service = FewShotService()
        patterns = few_shot_service.get_patterns()

        return {
            "status": "success",
            "patterns": patterns
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patterns: {str(e)}"
        )


@router.delete("/few-shot/patterns/{pattern_name}")
async def delete_few_shot_pattern(pattern_name: str):
    """Delete a few-shot pattern"""
    if not ML_SERVICES_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Few-shot learning service not yet implemented"
        )

    try:
        few_shot_service = FewShotService()
        few_shot_service.delete_pattern(pattern_name)

        return {
            "status": "success",
            "message": f"Pattern '{pattern_name}' deleted"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pattern: {str(e)}"
        )


# ========== YOLO TRAINING ENDPOINTS ==========

@router.post("/yolo/train")
async def train_yolo_model(
    dataset_yaml: str,
    epochs: int = 100,
    image_size: int = 1024,
    batch_size: int = 8,
    patience: int = 20,
    current_user: Optional[Users] = Depends(get_current_user_optional)
):
    """
    Train YOLO model on custom dataset

    Requires YOLO dataset in YAML format with training/validation splits.
    """
    try:
        from services.yolo_detector import YOLODetector

        detector = YOLODetector()
        results = detector.train_on_dataset(
            dataset_yaml=dataset_yaml,
            epochs=epochs,
            image_size=image_size,
            batch_size=batch_size,
            patience=patience
        )

        return {
            "status": "success",
            "message": "YOLO model training started",
            "training_config": {
                "dataset": dataset_yaml,
                "epochs": epochs,
                "image_size": image_size,
                "batch_size": batch_size,
                "patience": patience
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YOLO training failed: {str(e)}"
        )


# ========== GENERAL STATISTICS ==========

@router.get("/stats/overall")
async def get_overall_ml_stats(db: Session = Depends(get_db)):
    """
    Get overall ML detection statistics across all phases
    """
    try:
        # Count lots by detection method
        detection_methods = db.query(
            LotModel.detection_method,
            func.count(LotModel.id).label('count')
        ).group_by(LotModel.detection_method).all()

        # Average confidence by method
        avg_confidence = db.query(
            LotModel.detection_method,
            func.avg(LotModel.detection_confidence).label('avg_confidence')
        ).filter(
            LotModel.detection_confidence.isnot(None)
        ).group_by(LotModel.detection_method).all()

        # Get supervised ML stats
        if ML_SERVICES_AVAILABLE:
            try:
                ml_service = SupervisedMLService()
                ml_stats = ml_service.get_model_stats()
            except:
                ml_stats = None
        else:
            ml_stats = None

        # Get few-shot patterns
        if ML_SERVICES_AVAILABLE:
            try:
                few_shot_service = FewShotService()
                few_shot_patterns = few_shot_service.get_patterns()
            except:
                few_shot_patterns = []
        else:
            few_shot_patterns = []

        return {
            "status": "success",
            "detection_methods": {
                method: count for method, count in detection_methods if method
            },
            "average_confidence": {
                method: float(avg_conf) if avg_conf else 0.0
                for method, avg_conf in avg_confidence if method
            },
            "supervised_ml": ml_stats,
            "few_shot": {
                "patterns_count": len(few_shot_patterns),
                "patterns": few_shot_patterns
            },
            "total_ai_detected_lots": db.query(func.count(LotModel.id)).filter(
                LotModel.detection_method.in_(['yolo', 'supervised_ml', 'few_shot', 'auto_detect'])
            ).scalar() or 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ML stats: {str(e)}"
        )
