"""
Lot and Phase Map schemas for API request/response validation
Supports lot management, polygon boundaries, and phase map digitization
"""
from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Any, Dict
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, constr, validator

# Pydantic v2/v1 compatibility for from_attributes/orm_mode
try:
    from pydantic import ConfigDict  # Pydantic v2
    _HAS_V2 = True
except Exception:  # Pydantic v1 fallback
    _HAS_V2 = False


# ========== ENUMS ==========

class LotStatus(str, Enum):
    """Lot availability status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    UNAVAILABLE = "unavailable"
    ON_HOLD = "on_hold"


class PhaseStatus(str, Enum):
    """Phase development status"""
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class DetectionMethod(str, Enum):
    """How lot boundary was detected"""
    MANUAL = "manual"
    YOLO = "yolo"
    LINE_DETECTION = "line_detection"


# ========== COORDINATE SCHEMA ==========

class Coordinate(BaseModel):
    """2D coordinate point for polygon boundaries"""
    x: float = Field(..., description="X coordinate in image space")
    y: float = Field(..., description="Y coordinate in image space")


# ========== LOT SCHEMAS ==========

class LotBase(BaseModel):
    """Base lot schema with common fields"""
    lot_number: constr(strip_whitespace=True, min_length=1, max_length=50)
    square_footage: Optional[int] = Field(None, gt=0, description="Lot size in square feet")
    price: Optional[Decimal] = Field(None, ge=0, description="Lot or home price")
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[Decimal] = Field(None, ge=0, le=20)
    stories: Optional[int] = Field(None, ge=1, le=10)
    garage_spaces: Optional[int] = Field(None, ge=0, le=10)
    model: Optional[constr(max_length=100)] = None
    notes: Optional[str] = None


class LotCreate(LotBase):
    """Schema for creating a new lot"""
    phase_id: int = Field(..., description="Phase ID this lot belongs to")
    community_id: str = Field(..., description="Community ID (CMY-xxx)")
    builder_id: Optional[str] = Field(None, description="Builder ID (BLD-xxx)")
    status: LotStatus = LotStatus.AVAILABLE
    boundary_coordinates: Optional[List[Coordinate]] = Field(
        None,
        description="Polygon boundary coordinates"
    )
    move_in_date: Optional[date] = None
    detection_method: Optional[DetectionMethod] = DetectionMethod.MANUAL
    detection_confidence: Optional[Decimal] = Field(None, ge=0, le=1)


class LotUpdate(BaseModel):
    """Schema for updating a lot (all fields optional)"""
    lot_number: Optional[constr(strip_whitespace=True, min_length=1, max_length=50)] = None
    builder_id: Optional[str] = None
    status: Optional[LotStatus] = None
    boundary_coordinates: Optional[List[Coordinate]] = None
    square_footage: Optional[int] = Field(None, gt=0)
    price: Optional[Decimal] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=20)
    bathrooms: Optional[Decimal] = Field(None, ge=0, le=20)
    stories: Optional[int] = Field(None, ge=1, le=10)
    garage_spaces: Optional[int] = Field(None, ge=0, le=10)
    model: Optional[constr(max_length=100)] = None
    move_in_date: Optional[date] = None
    notes: Optional[str] = None


class LotStatusUpdate(BaseModel):
    """Schema for updating lot status only"""
    status: LotStatus
    changed_by: Optional[str] = Field(None, description="User making the change")
    change_reason: Optional[str] = Field(None, description="Reason for status change")
    reserved_by: Optional[str] = Field(None, description="Name of reserver (for RESERVED status)")
    sold_to: Optional[str] = Field(None, description="Name of buyer (for SOLD status)")


class LotOut(LotBase):
    """Schema for lot response"""
    id: int
    phase_id: int
    community_id: str
    builder_id: Optional[str] = None
    property_id: Optional[int] = None
    status: LotStatus
    boundary_coordinates: Optional[List[Dict[str, Any]]] = None
    reserved_by: Optional[str] = None
    reserved_at: Optional[datetime] = None
    sold_to: Optional[str] = None
    sold_at: Optional[datetime] = None
    move_in_date: Optional[date] = None
    detection_method: Optional[str] = None
    detection_confidence: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class LotListOut(BaseModel):
    """Schema for list of lots with statistics"""
    items: List[LotOut]
    total: int
    statistics: Dict[str, int] = Field(
        default_factory=lambda: {
            "available": 0,
            "reserved": 0,
            "sold": 0,
            "unavailable": 0,
            "on_hold": 0
        }
    )


# ========== LOT STATUS HISTORY SCHEMAS ==========

class LotStatusHistoryOut(BaseModel):
    """Schema for lot status history response"""
    id: int
    lot_id: int
    old_status: Optional[LotStatus] = None
    new_status: LotStatus
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    changed_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


# ========== PHASE SCHEMAS ==========

class PhaseBase(BaseModel):
    """Base phase schema"""
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    description: Optional[str] = None


class PhaseCreate(PhaseBase):
    """Schema for creating a new phase"""
    community_id: str = Field(..., description="Community ID (CMY-xxx)")
    status: PhaseStatus = PhaseStatus.PLANNING
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None


class PhaseUpdate(BaseModel):
    """Schema for updating a phase (all fields optional)"""
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    description: Optional[str] = None
    status: Optional[PhaseStatus] = None
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None


class PhaseOut(PhaseBase):
    """Schema for phase response"""
    id: int
    community_id: str
    status: str  # Using string instead of enum for flexibility
    start_date: Optional[date] = None
    target_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    total_lots: int = 0
    site_plan_image_url: Optional[str] = None
    map_url: Optional[str] = None  # Legacy field
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True


class PhaseWithLotsOut(PhaseOut):
    """Phase response with associated lots"""
    lot_records: List[LotOut] = []


# ========== PHASE MAP UPLOAD SCHEMAS ==========

class PhaseMapUploadResponse(BaseModel):
    """Response after uploading a phase map"""
    phase_id: int
    site_plan_image_url: str
    image_width: int
    image_height: int
    file_type: str
    message: str = "Phase map uploaded successfully"


class AutoDetectLotsRequest(BaseModel):
    """Request to auto-detect lots from phase map"""
    phase_id: int
    detection_method: DetectionMethod = DetectionMethod.YOLO
    min_confidence: Optional[Decimal] = Field(0.7, ge=0, le=1, description="Minimum confidence threshold")
    auto_save: bool = Field(False, description="Automatically save detected lots")


class AutoDetectLotsResponse(BaseModel):
    """Response from auto-detection"""
    phase_id: int
    detection_method: str
    detected_count: int
    lots: List[LotOut] = []
    average_confidence: Optional[Decimal] = None
    message: str


# ========== BATCH OPERATIONS ==========

class BulkLotCreate(BaseModel):
    """Schema for bulk creating lots"""
    phase_id: int
    community_id: str
    lots: List[LotCreate]


class BulkLotStatusUpdate(BaseModel):
    """Schema for bulk updating lot statuses"""
    lot_ids: List[int]
    status_update: LotStatusUpdate


class BulkOperationResult(BaseModel):
    """Result of bulk operation"""
    success_count: int
    failed_count: int
    total: int
    succeeded_ids: List[int] = []
    failed_ids: List[int] = []
    errors: List[str] = []


# ========== STATISTICS & ANALYTICS ==========

class PhaseStatistics(BaseModel):
    """Phase-level statistics"""
    phase_id: int
    total_lots: int
    available_lots: int
    reserved_lots: int
    sold_lots: int
    unavailable_lots: int
    on_hold_lots: int
    average_price: Optional[Decimal] = None
    total_revenue: Optional[Decimal] = None
    completion_percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class LotFilters(BaseModel):
    """Filter parameters for lot queries"""
    status: Optional[LotStatus] = None
    builder_id: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    min_sqft: Optional[int] = Field(None, gt=0)
    max_sqft: Optional[int] = Field(None, gt=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[Decimal] = Field(None, ge=0)

    @validator('max_price')
    def validate_price_range(cls, max_price, values):
        """Ensure max_price >= min_price if both specified"""
        min_price = values.get('min_price')
        if min_price is not None and max_price is not None and max_price < min_price:
            raise ValueError('max_price must be greater than or equal to min_price')
        return max_price

    @validator('max_sqft')
    def validate_sqft_range(cls, max_sqft, values):
        """Ensure max_sqft >= min_sqft if both specified"""
        min_sqft = values.get('min_sqft')
        if min_sqft is not None and max_sqft is not None and max_sqft < min_sqft:
            raise ValueError('max_sqft must be greater than or equal to min_sqft')
        return max_sqft
