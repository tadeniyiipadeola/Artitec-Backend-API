# ML/AI Features API Documentation

## Overview
This document provides comprehensive documentation for all Machine Learning and AI-powered lot detection features integrated into the Artitec platform.

**Base URL**: `http://localhost:8000` (development) or your production URL

**Authentication**: Most endpoints require JWT Bearer token authentication.

---

## Table of Contents
1. [Phase Maps API](#phase-maps-api)
2. [ML Detection API](#ml-detection-api)
3. [ML Training & Feedback API](#ml-training--feedback-api)
4. [Batch Lot Operations](#batch-lot-operations)

---

## Phase Maps API

Base path: `/v1/phase-maps`

### 1. Upload Phase Map

Upload a site plan image for a community phase.

**Endpoint**: `POST /v1/phase-maps/{phase_id}/upload-map`

**Authentication**: Required

**Parameters**:
- `phase_id` (path, integer): The community phase ID

**Form Data**:
```
file: <binary file> (required)
  - Supported formats: JPG, JPEG, PNG, PDF, TIFF, TIF
  - Max size: Recommended <50MB

replace_existing: boolean (optional, default: false)
  - If true, replaces existing site plan
```

**Response**: `200 OK`
```json
{
  "success": true,
  "phase_id": 123,
  "file_path": "phases/CMY-123/phase-5-sitemap.jpg",
  "file_url": "https://storage.example.com/phases/CMY-123/phase-5-sitemap.jpg",
  "dimensions": {
    "width": 2400,
    "height": 1600
  },
  "file_type": "jpg"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/v1/phase-maps/5/upload-map" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/sitemap.jpg" \
  -F "replace_existing=true"
```

---

### 2. Auto-Detect Lots

Automatically detect lots on an uploaded site plan using ML/AI.

**Endpoint**: `POST /v1/phase-maps/{phase_id}/auto-detect`

**Authentication**: Required

**Parameters**:
- `phase_id` (path, integer): The community phase ID

**Form Data**:
```
detection_method: string (optional, default: "auto")
  - Options: "auto", "yolo", "ocr", "boundary", "line"
  - "auto": Combines OCR + boundary detection
  - "yolo": Deep learning segmentation (95%+ accuracy)
  - "ocr": Tesseract text recognition
  - "boundary": Canny edge + contour detection
  - "line": Hough Transform line detection

use_ocr: boolean (optional, default: true)
  - Whether to extract lot numbers using OCR

min_area: integer (optional, default: 1000)
  - Minimum lot area in pixels

confidence_threshold: float (optional, default: 0.25)
  - Confidence threshold for YOLO (0.0-1.0)

save_to_database: boolean (optional, default: true)
  - If true, saves detected lots to database
  - If true, clears existing lots for this phase first
```

**Response**: `200 OK`
```json
{
  "phase_id": 123,
  "lots_detected": 42,
  "detection_method": "yolo",
  "saved_to_database": true,
  "lots": [
    {
      "lot_number": "1",
      "coordinates": [[100, 200], [300, 200], [300, 400], [100, 400]],
      "area": 40000.5,
      "centroid": [200, 300],
      "confidence": 0.95,
      "detection_method": "yolo"
    }
  ],
  "statistics": {
    "total_detections": 42,
    "average_confidence": 0.89,
    "image_dimensions": {"width": 2400, "height": 1600}
  }
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/v1/phase-maps/5/auto-detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "detection_method=yolo" \
  -F "confidence_threshold=0.3" \
  -F "save_to_database=true"
```

---

### 3. Auto-Detect with Grid Layout

Detect lots using a grid-based approach (for regularly-spaced lots).

**Endpoint**: `POST /v1/phase-maps/{phase_id}/auto-detect-grid`

**Authentication**: Required

**Parameters**:
- `phase_id` (path, integer): The community phase ID

**Form Data**:
```
rows: integer (required)
  - Number of rows in the grid

columns: integer (required)
  - Number of columns in the grid

start_x: integer (optional, default: 100)
  - Starting X coordinate (pixels)

start_y: integer (optional, default: 100)
  - Starting Y coordinate (pixels)

lot_width: integer (optional, default: 200)
  - Width of each lot (pixels)

lot_height: integer (optional, default: 300)
  - Height of each lot (pixels)

spacing_x: integer (optional, default: 20)
  - Horizontal spacing between lots

spacing_y: integer (optional, default: 20)
  - Vertical spacing between lots

save_to_database: boolean (optional, default: true)
```

**Response**: `200 OK`
```json
{
  "phase_id": 123,
  "lots_created": 48,
  "grid_layout": {
    "rows": 6,
    "columns": 8,
    "total_lots": 48
  },
  "lots": [...]
}
```

---

### 4. Batch Auto-Detect

Process multiple phases for lot detection in parallel.

**Endpoint**: `POST /v1/phase-maps/batch/auto-detect`

**Authentication**: Required

**Request Body**:
```json
{
  "phase_ids": [1, 2, 3, 4, 5],
  "detection_method": "yolo",
  "confidence_threshold": 0.25,
  "save_to_database": true,
  "parallel": true
}
```

**Response**: `200 OK`
```json
{
  "total_phases": 5,
  "successful": 4,
  "failed": 1,
  "results": [
    {
      "phase_id": 1,
      "status": "success",
      "lots_detected": 42
    },
    {
      "phase_id": 2,
      "status": "failed",
      "error": "No site plan uploaded"
    }
  ]
}
```

---

### 5. Export Phase Map

Export detected lots in various formats.

**Endpoint**: `GET /v1/phase-maps/{phase_id}/export`

**Authentication**: Required

**Query Parameters**:
```
format: string (optional, default: "geojson")
  - Options: "geojson", "shapefile", "csv", "json"

include_metadata: boolean (optional, default: true)
  - Include detection metadata
```

**Response**: Depends on format
- `geojson`: GeoJSON FeatureCollection
- `csv`: CSV file download
- `json`: JSON array

**Example**:
```bash
curl -X GET "http://localhost:8000/v1/phase-maps/5/export?format=geojson" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6. Get Phase Statistics

Get detection statistics for a phase.

**Endpoint**: `GET /v1/phase-maps/{phase_id}/statistics`

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "phase_id": 123,
  "total_lots": 42,
  "detection_method": "yolo",
  "average_confidence": 0.89,
  "status_breakdown": {
    "available": 30,
    "reserved": 8,
    "sold": 4
  },
  "area_statistics": {
    "min_area": 32000.0,
    "max_area": 48000.0,
    "average_area": 40000.5
  },
  "last_detection": "2025-12-23T03:00:00Z"
}
```

---

## ML Detection API

Base path: `/v1/ml`

### 1. OCR Extract

Extract text (lot numbers) from an image.

**Endpoint**: `POST /v1/ml/ocr/extract`

**Authentication**: Required

**Form Data**:
```
file: <binary file> (required)
  - Image file containing text

language: string (optional, default: "eng")
  - OCR language code

confidence_threshold: float (optional, default: 0.5)
```

**Response**: `200 OK`
```json
{
  "text_regions": [
    {
      "text": "LOT 1",
      "confidence": 0.95,
      "bbox": [100, 200, 150, 230]
    }
  ],
  "total_found": 42
}
```

---

### 2. OCR Visualize

Extract text and return annotated image.

**Endpoint**: `POST /v1/ml/ocr/visualize`

**Authentication**: Required

**Form Data**: Same as OCR Extract

**Response**: `200 OK` (image/png)
- Returns PNG image with detected text highlighted

---

### 3. Boundary Detection

Detect lot boundaries using edge detection.

**Endpoint**: `POST /v1/ml/boundary/detect`

**Authentication**: Required

**Form Data**:
```
file: <binary file> (required)

min_area: integer (optional, default: 1000)
max_area: integer (optional, default: 50000)
canny_low: integer (optional, default: 50)
canny_high: integer (optional, default: 150)
```

**Response**: `200 OK`
```json
{
  "boundaries_detected": 42,
  "boundaries": [
    {
      "coordinates": [[x1, y1], [x2, y2], ...],
      "area": 40000.5,
      "num_sides": 4
    }
  ]
}
```

---

### 4. Line Detection

Detect lines using Hough Transform.

**Endpoint**: `POST /v1/ml/line/detect`

**Authentication**: Required

**Form Data**:
```
file: <binary file> (required)

threshold: integer (optional, default: 100)
min_line_length: integer (optional, default: 50)
max_line_gap: integer (optional, default: 10)
```

**Response**: `200 OK`
```json
{
  "lines_detected": 120,
  "lines": [
    {
      "start": [x1, y1],
      "end": [x2, y2],
      "length": 250.5,
      "angle": 45.0
    }
  ]
}
```

---

### 5. Auto-Detect (ML Combined)

Combined OCR + Boundary detection.

**Endpoint**: `POST /v1/ml/auto-detect`

**Authentication**: Required

**Form Data**:
```
file: <binary file> (required)

use_ocr: boolean (optional, default: true)
min_area: integer (optional, default: 1000)
confidence_threshold: float (optional, default: 0.5)
```

**Response**: `200 OK`
```json
{
  "lots_detected": 42,
  "detection_method": "auto",
  "lots": [
    {
      "lot_number": "1",
      "coordinates": [[x1, y1], [x2, y2], ...],
      "area": 40000.5,
      "confidence": 0.89
    }
  ]
}
```

---

### 6. Auto-Detect Visualize

Combined detection with annotated image output.

**Endpoint**: `POST /v1/ml/auto-detect/visualize`

**Authentication**: Required

**Form Data**: Same as Auto-Detect

**Response**: `200 OK` (image/png)
- Returns PNG image with detected lots highlighted and labeled

---

## ML Training & Feedback API

Base path: `/v1/ml`

### 1. Submit Training Feedback

Submit user corrections to improve ML model.

**Endpoint**: `POST /v1/ml/feedback`

**Authentication**: Required

**Request Body**:
```json
{
  "phase_id": 123,
  "corrections": [
    {
      "lot_id": 456,
      "correct_coordinates": [[x1, y1], [x2, y2], ...],
      "correct_lot_number": "1A",
      "feedback_type": "boundary_correction"
    }
  ],
  "detection_method": "yolo",
  "user_id": "user@example.com"
}
```

**Response**: `200 OK`
```json
{
  "feedback_saved": true,
  "corrections_count": 1,
  "model_updated": false,
  "message": "Feedback saved. Model will retrain when 10+ samples available."
}
```

---

### 2. Train Supervised ML Model

Manually trigger model retraining.

**Endpoint**: `POST /v1/ml/supervised/train`

**Authentication**: Required (Admin only)

**Query Parameters**:
```
min_samples: integer (optional, default: 10)
  - Minimum training samples required
```

**Response**: `200 OK`
```json
{
  "training_started": true,
  "samples_used": 42,
  "model_accuracy": 0.95,
  "model_path": "/models/supervised_ml_20251223.pkl"
}
```

---

### 3. Get ML Model Statistics

Get current ML model performance stats.

**Endpoint**: `GET /v1/ml/supervised/stats`

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "model_version": "20251223",
  "accuracy": 0.95,
  "training_samples": 420,
  "last_trained": "2025-12-23T03:00:00Z",
  "predictions_made": 1200,
  "feedback_received": 42
}
```

---

### 4. Train Few-Shot Model

Train a few-shot learning model from examples.

**Endpoint**: `POST /v1/ml/few-shot/train`

**Authentication**: Required

**Request Body**:
```json
{
  "pattern_name": "standard_lot",
  "example_lots": [
    {
      "image_region": "base64_encoded_image",
      "coordinates": [[x1, y1], [x2, y2], ...]
    }
  ],
  "phase_id": 123
}
```

**Response**: `200 OK`
```json
{
  "pattern_saved": true,
  "pattern_name": "standard_lot",
  "examples_count": 3,
  "features_extracted": true
}
```

---

### 5. Detect Using Few-Shot

Detect lots similar to learned examples.

**Endpoint**: `POST /v1/ml/few-shot/{phase_id}/detect`

**Authentication**: Required

**Query Parameters**:
```
pattern_name: string (optional, default: "default")
similarity_threshold: float (optional, default: 0.8)
```

**Response**: `200 OK`
```json
{
  "lots_detected": 38,
  "pattern_used": "standard_lot",
  "average_similarity": 0.92,
  "lots": [...]
}
```

---

### 6. Get Few-Shot Patterns

List all saved few-shot patterns.

**Endpoint**: `GET /v1/ml/few-shot/{phase_id}/patterns`

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "patterns": [
    {
      "name": "standard_lot",
      "examples_count": 3,
      "created_at": "2025-12-23T03:00:00Z"
    }
  ]
}
```

---

### 7. Delete Few-Shot Pattern

Delete a saved pattern.

**Endpoint**: `DELETE /v1/ml/few-shot/{phase_id}/patterns/{pattern_name}`

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "deleted": true,
  "pattern_name": "standard_lot"
}
```

---

### 8. Train YOLO Model

Train a custom YOLO model (advanced).

**Endpoint**: `POST /v1/ml/yolo/train`

**Authentication**: Required (Admin only)

**Request Body**:
```json
{
  "dataset_yaml": "/path/to/dataset.yaml",
  "epochs": 100,
  "image_size": 1024,
  "batch_size": 8
}
```

**Response**: `200 OK`
```json
{
  "training_started": true,
  "job_id": "train_20251223_001",
  "epochs": 100,
  "estimated_time_minutes": 120
}
```

---

### 9. Get Overall ML Statistics

Get statistics across all ML detection methods.

**Endpoint**: `GET /v1/ml/stats/overall`

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "total_phases_processed": 120,
  "total_lots_detected": 5040,
  "detection_methods": {
    "yolo": 3000,
    "auto": 1500,
    "ocr": 540
  },
  "average_accuracy": 0.91,
  "total_feedback_submissions": 240
}
```

---

## Batch Lot Operations

Base path: `/v1/communities/{community_id}/phases/{phase_id}/lots`

### 1. Bulk Create Lots

Create multiple lots at once.

**Endpoint**: `POST /v1/communities/{community_id}/phases/{phase_id}/lots/batch`

**Authentication**: Required

**Request Body**:
```json
{
  "lots": [
    {
      "lot_number": "1",
      "boundary_coordinates": [[x1, y1], [x2, y2], ...],
      "status": "available",
      "detection_method": "yolo",
      "detection_confidence": 0.95,
      "area_sqft": 5000.0,
      "frontage_ft": 50.0,
      "depth_ft": 100.0
    }
  ]
}
```

**Response**: `200 OK`
```json
{
  "success": 40,
  "failed": 2,
  "errors": [
    {
      "lot_number": "42",
      "error": "Duplicate lot number"
    }
  ],
  "created_lots": [...]
}
```

---

### 2. Bulk Update Lot Status

Update status for multiple lots.

**Endpoint**: `PATCH /v1/communities/{community_id}/phases/{phase_id}/lots/batch/status`

**Authentication**: Required

**Request Body**:
```json
{
  "lot_ids": [1, 2, 3, 4, 5],
  "new_status": "reserved",
  "reason": "Bulk reservation for premium lots"
}
```

**Response**: `200 OK`
```json
{
  "updated": 5,
  "failed": 0,
  "lots": [...]
}
```

---

### 3. Bulk Delete Lots

Delete multiple lots at once.

**Endpoint**: `DELETE /v1/communities/{community_id}/phases/{phase_id}/lots/batch`

**Authentication**: Required (Admin only)

**Request Body**:
```json
{
  "lot_ids": [1, 2, 3, 4, 5]
}
```

**Response**: `200 OK`
```json
{
  "deleted": 5,
  "failed": 0
}
```

---

## Error Responses

All endpoints may return standard error responses:

### 400 Bad Request
```json
{
  "code": "validation_error",
  "message": "Invalid request",
  "errors": [...]
}
```

### 401 Unauthorized
```json
{
  "code": "unauthorized",
  "message": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "code": "not_found",
  "message": "Phase not found"
}
```

### 500 Internal Server Error
```json
{
  "code": "internal_error",
  "message": "An unexpected error occurred"
}
```

---

## Detection Methods Comparison

| Method | Accuracy | Speed | Best For | Requires |
|--------|----------|-------|----------|----------|
| **YOLO** | 95%+ | Fast | Complex layouts, high accuracy | Trained model |
| **Auto** | 85-90% | Fast | Standard layouts | None |
| **OCR** | 70-80% | Medium | Text extraction | Clear labels |
| **Boundary** | 75-85% | Fast | Simple polygons | Clean edges |
| **Line** | 60-70% | Very Fast | Grid layouts | Regular patterns |
| **Supervised ML** | 90%+ | Fast | Custom patterns | Training data |
| **Few-Shot** | 85-90% | Medium | Limited examples | 2-3 examples |

---

## Best Practices

1. **Start with YOLO** for best accuracy on complex site plans
2. **Use Auto-Detect** as a fallback for standard layouts
3. **Submit Feedback** to continuously improve ML models
4. **Verify Detections** before bulk operations
5. **Use Batch Operations** for efficiency when processing multiple lots
6. **Export Data** regularly for backup and analysis
7. **Monitor Statistics** to track detection quality over time

---

## Support & Resources

- **OpenAPI Documentation**: `http://localhost:8000/docs`
- **Redoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

**Last Updated**: December 23, 2025
**API Version**: 1.0.0
