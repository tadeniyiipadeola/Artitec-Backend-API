"""
OCR Service for Lot Number Extraction
Extracts lot numbers from site plan images using Tesseract OCR
Supports multiple lot numbering patterns and confidence scoring
"""
import cv2
import numpy as np
import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import pytesseract
from pytesseract import Output


@dataclass
class OCRResult:
    """Result of OCR detection"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    normalized_text: str  # Cleaned/standardized version


@dataclass
class LotNumberResult:
    """Detected lot number with metadata"""
    lot_number: str
    confidence: float
    position: Tuple[int, int]  # (x, y) center point
    bbox: Tuple[int, int, int, int]
    pattern_type: str  # e.g., "numeric", "alpha-numeric", "custom"


class OCRService:
    """
    Service for extracting lot numbers from images using OCR

    Features:
    - Multiple lot number pattern recognition
    - Image preprocessing for better accuracy
    - Confidence filtering
    - Text validation and normalization
    - Supports custom patterns via regex
    """

    # Common lot number patterns
    DEFAULT_PATTERNS = [
        r'LOT[- ]?\d+',           # LOT-123, LOT 123, LOT123
        r'LOT[- ]?[A-Z]\d+',      # LOT-A12, LOT A12
        r'\d{1,4}',               # 123, 1234 (simple numbers)
        r'[A-Z]-?\d{1,4}',        # A-12, A12, B-123
        r'[A-Z]{1,2}\d{1,4}',     # A1, AB12
        r'\d{1,4}[A-Z]?',         # 123A, 456
    ]

    def __init__(
        self,
        min_confidence: float = 60.0,
        custom_patterns: Optional[List[str]] = None,
        preprocess: bool = True,
        psm_mode: int = 6,  # Page segmentation mode
    ):
        """
        Initialize OCR service

        Args:
            min_confidence: Minimum confidence score (0-100)
            custom_patterns: Additional regex patterns for lot numbers
            preprocess: Apply image preprocessing
            psm_mode: Tesseract page segmentation mode (default 6 = single block)
        """
        self.min_confidence = min_confidence
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        self.preprocess = preprocess
        self.psm_mode = psm_mode

        # Compile regex patterns
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def extract_lot_numbers(
        self,
        image: np.ndarray,
        roi: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[LotNumberResult]:
        """
        Extract lot numbers from image

        Args:
            image: Input image (BGR or grayscale)
            roi: Region of interest (x, y, width, height) to limit search area

        Returns:
            List of detected lot numbers with metadata
        """
        # Extract ROI if specified
        if roi:
            x, y, w, h = roi
            image = image[y:y+h, x:x+w]
            roi_offset = (x, y)
        else:
            roi_offset = (0, 0)

        # Preprocess image
        processed = self._preprocess_image(image) if self.preprocess else image

        # Perform OCR
        ocr_results = self._perform_ocr(processed)

        # Filter and validate lot numbers
        lot_numbers = self._extract_lot_numbers_from_ocr(ocr_results, roi_offset)

        return lot_numbers

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy

        Args:
            image: Input image

        Returns:
            Preprocessed image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Adaptive thresholding for better text detection
        # Try both threshold methods and pick better results
        thresh1 = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        thresh2 = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        # Use Gaussian threshold as default
        thresh = thresh1

        # Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(cleaned)

        return enhanced

    def _perform_ocr(self, image: np.ndarray) -> List[OCRResult]:
        """
        Perform OCR on preprocessed image

        Args:
            image: Preprocessed image

        Returns:
            List of OCR results
        """
        # Configure Tesseract
        config = f'--psm {self.psm_mode} --oem 3'  # LSTM OCR Engine Mode

        # Get detailed OCR data
        try:
            data = pytesseract.image_to_data(
                image,
                config=config,
                output_type=Output.DICT
            )
        except Exception as e:
            print(f"OCR Error: {e}")
            return []

        # Parse results
        results = []
        n_boxes = len(data['text'])

        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])

            # Skip empty or low confidence detections
            if not text or conf < self.min_confidence:
                continue

            # Get bounding box
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]

            # Normalize text
            normalized = self._normalize_text(text)

            results.append(OCRResult(
                text=text,
                confidence=conf,
                bbox=(x, y, w, h),
                normalized_text=normalized,
            ))

        return results

    def _normalize_text(self, text: str) -> str:
        """
        Normalize OCR text for better matching

        Args:
            text: Raw OCR text

        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())

        # Common OCR corrections
        corrections = {
            'O': '0',  # Letter O -> Zero
            'I': '1',  # Letter I -> One
            'l': '1',  # Lowercase L -> One
            'S': '5',  # Sometimes S -> 5
            'Z': '2',  # Sometimes Z -> 2
        }

        # Apply corrections only to numeric parts
        # This is a simple approach - more sophisticated logic could be added
        normalized = text.upper()

        return normalized

    def _extract_lot_numbers_from_ocr(
        self,
        ocr_results: List[OCRResult],
        roi_offset: Tuple[int, int],
    ) -> List[LotNumberResult]:
        """
        Extract lot numbers from OCR results using pattern matching

        Args:
            ocr_results: OCR detection results
            roi_offset: Offset to add to positions if ROI was used

        Returns:
            List of validated lot numbers
        """
        lot_numbers = []

        for result in ocr_results:
            # Try to match against lot number patterns
            matches = []
            for pattern in self.compiled_patterns:
                match = pattern.search(result.normalized_text)
                if match:
                    matches.append((match.group(), pattern.pattern))

            if not matches:
                continue

            # Use first match (most specific pattern)
            lot_text, pattern_type = matches[0]

            # Calculate center position
            x, y, w, h = result.bbox
            center_x = x + w // 2 + roi_offset[0]
            center_y = y + h // 2 + roi_offset[1]

            # Adjust bbox for ROI offset
            bbox = (
                x + roi_offset[0],
                y + roi_offset[1],
                w,
                h
            )

            # Determine pattern type
            if 'LOT' in pattern_type:
                ptype = 'lot-prefix'
            elif re.match(r'^\d+$', lot_text):
                ptype = 'numeric'
            elif re.match(r'^[A-Z]-?\d+$', lot_text):
                ptype = 'alpha-numeric'
            else:
                ptype = 'custom'

            lot_numbers.append(LotNumberResult(
                lot_number=lot_text,
                confidence=result.confidence,
                position=(center_x, center_y),
                bbox=bbox,
                pattern_type=ptype,
            ))

        # Remove duplicates (same lot number detected multiple times)
        lot_numbers = self._remove_duplicates(lot_numbers)

        # Sort by confidence
        lot_numbers.sort(key=lambda x: x.confidence, reverse=True)

        return lot_numbers

    def _remove_duplicates(
        self,
        lot_numbers: List[LotNumberResult],
        distance_threshold: int = 50,
    ) -> List[LotNumberResult]:
        """
        Remove duplicate lot numbers that are close to each other

        Args:
            lot_numbers: List of lot numbers
            distance_threshold: Maximum distance to consider as duplicate

        Returns:
            Deduplicated list
        """
        if not lot_numbers:
            return []

        unique = []
        used = set()

        for i, lot1 in enumerate(lot_numbers):
            if i in used:
                continue

            # Check for duplicates
            duplicates = [lot1]
            for j, lot2 in enumerate(lot_numbers):
                if j <= i or j in used:
                    continue

                # Check if same lot number and close position
                if lot1.lot_number == lot2.lot_number:
                    x1, y1 = lot1.position
                    x2, y2 = lot2.position
                    dist = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                    if dist < distance_threshold:
                        duplicates.append(lot2)
                        used.add(j)

            # Keep the one with highest confidence
            best = max(duplicates, key=lambda x: x.confidence)
            unique.append(best)
            used.add(i)

        return unique

    def visualize_results(
        self,
        image: np.ndarray,
        results: List[LotNumberResult],
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Visualize OCR results on image

        Args:
            image: Input image
            results: OCR results to visualize
            show_confidence: Show confidence scores

        Returns:
            Image with annotations
        """
        output = image.copy()

        for result in results:
            x, y, w, h = result.bbox

            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)

            # Draw lot number
            text = result.lot_number
            if show_confidence:
                text += f" ({result.confidence:.1f}%)"

            # Position text above box
            text_y = max(y - 10, 20)
            cv2.putText(
                output,
                text,
                (x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

            # Draw center point
            cx, cy = result.position
            cv2.circle(output, (cx, cy), 4, (255, 0, 0), -1)

        return output


# Helper function for easy usage
def extract_lot_numbers_from_image(
    image_path: str,
    min_confidence: float = 60.0,
    custom_patterns: Optional[List[str]] = None,
) -> List[LotNumberResult]:
    """
    Convenience function to extract lot numbers from image file

    Args:
        image_path: Path to image
        min_confidence: Minimum OCR confidence
        custom_patterns: Additional regex patterns

    Returns:
        List of detected lot numbers
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    service = OCRService(
        min_confidence=min_confidence,
        custom_patterns=custom_patterns,
    )
    results = service.extract_lot_numbers(image)

    return results


# Tesseract configuration helper
def configure_tesseract(tesseract_cmd: Optional[str] = None):
    """
    Configure Tesseract executable path

    Args:
        tesseract_cmd: Path to tesseract executable
                      (e.g., '/usr/local/bin/tesseract' on macOS/Linux
                       or 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe' on Windows)
    """
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        # Try to auto-detect
        import shutil
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            print("Warning: Tesseract not found in PATH. Please install or configure manually.")
