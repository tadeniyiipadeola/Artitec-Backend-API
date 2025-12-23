"""
ML Supervised Learning Detector
Learns from user corrections to improve lot detection accuracy
Uses RandomForest classifier with feature extraction
"""
import cv2
import numpy as np
import pickle
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, asdict
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from scipy.spatial import distance


@dataclass
class TrainingExample:
    """Single training example for ML model"""
    features: np.ndarray
    label: int  # 1 = valid lot, 0 = not a lot
    phase_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class MLLotCandidate:
    """Lot candidate with ML features"""
    coordinates: List[Tuple[int, int]]
    area: float
    confidence: float
    features: np.ndarray
    prediction: int  # 1 = lot, 0 = not lot


class MLSupervisedDetector:
    """
    Machine Learning based lot detector using supervised learning

    Features:
    - Learns from user corrections
    - RandomForest classification
    - Feature extraction (shape, size, edge density, etc.)
    - Model persistence (save/load)
    - Confidence scoring
    - Incremental learning support
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_estimators: int = 100,
        min_samples: int = 10,
    ):
        """
        Initialize ML detector

        Args:
            model_path: Path to saved model file (None = create new)
            n_estimators: Number of trees in random forest
            min_samples: Minimum samples required to train
        """
        self.model_path = model_path
        self.n_estimators = n_estimators
        self.min_samples = min_samples

        # ML components
        self.classifier = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_data = []

        # Load existing model if path provided
        if model_path and Path(model_path).exists():
            self.load_model(model_path)

    def extract_features(
        self,
        contour: np.ndarray,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Extract features from a contour for ML classification

        Features extracted:
        - Area
        - Perimeter
        - Aspect ratio
        - Extent (area / bounding box area)
        - Solidity (area / convex hull area)
        - Number of vertices
        - Circularity
        - Edge density inside contour
        - Mean intensity
        - Standard deviation of intensity

        Args:
            contour: OpenCV contour
            image: Source image

        Returns:
            Feature vector (numpy array)
        """
        features = []

        # Basic shape features
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        # Bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = float(w) / h if h > 0 else 0

        # Extent
        rect_area = w * h
        extent = area / rect_area if rect_area > 0 else 0

        # Solidity
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0

        # Polygon approximation
        epsilon = 0.02 * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        num_vertices = len(approx)

        # Circularity (4π * area / perimeter²)
        circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0

        # Create mask for contour
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # Edge density inside contour
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = cv2.countNonZero(cv2.bitwise_and(edges, edges, mask=mask))
        edge_density = edge_pixels / area if area > 0 else 0

        # Intensity statistics
        masked_pixels = gray[mask > 0]
        mean_intensity = np.mean(masked_pixels) if len(masked_pixels) > 0 else 0
        std_intensity = np.std(masked_pixels) if len(masked_pixels) > 0 else 0

        # Compile features
        features = [
            area,
            perimeter,
            aspect_ratio,
            extent,
            solidity,
            num_vertices,
            circularity,
            edge_density,
            mean_intensity,
            std_intensity,
        ]

        return np.array(features, dtype=np.float32)

    def train(
        self,
        training_examples: List[TrainingExample],
        save_model: bool = True,
    ) -> Dict:
        """
        Train the ML model on training examples

        Args:
            training_examples: List of training examples
            save_model: Save trained model to disk

        Returns:
            Training metrics
        """
        if len(training_examples) < self.min_samples:
            raise ValueError(
                f"Insufficient training data. Need at least {self.min_samples} samples, "
                f"got {len(training_examples)}"
            )

        # Prepare training data
        X = np.array([ex.features for ex in training_examples])
        y = np.array([ex.label for ex in training_examples])

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train classifier
        self.classifier = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
        )
        self.classifier.fit(X_scaled, y)

        self.is_trained = True
        self.training_data = training_examples

        # Calculate metrics
        train_accuracy = self.classifier.score(X_scaled, y)

        # Feature importance
        feature_names = [
            'area', 'perimeter', 'aspect_ratio', 'extent', 'solidity',
            'num_vertices', 'circularity', 'edge_density',
            'mean_intensity', 'std_intensity'
        ]
        importance = dict(zip(feature_names, self.classifier.feature_importances_))

        # Save model
        if save_model and self.model_path:
            self.save_model(self.model_path)

        return {
            'training_samples': len(training_examples),
            'train_accuracy': train_accuracy,
            'feature_importance': importance,
        }

    def predict(
        self,
        contours: List[np.ndarray],
        image: np.ndarray,
    ) -> List[MLLotCandidate]:
        """
        Predict which contours are valid lots

        Args:
            contours: List of OpenCV contours
            image: Source image

        Returns:
            List of lot candidates with predictions
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first or load a trained model.")

        candidates = []

        for contour in contours:
            # Extract features
            features = self.extract_features(contour, image)

            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))

            # Predict
            prediction = self.classifier.predict(features_scaled)[0]
            confidence = self.classifier.predict_proba(features_scaled)[0][prediction]

            # Get coordinates
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            coordinates = [(int(p[0][0]), int(p[0][1])) for p in approx]

            # Calculate area
            area = cv2.contourArea(contour)

            candidates.append(MLLotCandidate(
                coordinates=coordinates,
                area=area,
                confidence=float(confidence),
                features=features,
                prediction=int(prediction),
            ))

        # Filter only predicted lots (prediction == 1)
        lots = [c for c in candidates if c.prediction == 1]

        # Sort by confidence
        lots.sort(key=lambda x: x.confidence, reverse=True)

        return lots

    def detect_lots(
        self,
        image: np.ndarray,
        min_area: int = 1000,
        max_area: Optional[int] = None,
    ) -> List[MLLotCandidate]:
        """
        Detect lots in image using trained ML model

        Args:
            image: Input image
            min_area: Minimum contour area
            max_area: Maximum contour area

        Returns:
            List of detected lots
        """
        # Preprocess image
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        # Filter by area
        filtered_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            if max_area and area > max_area:
                continue
            filtered_contours.append(contour)

        # Predict using ML model
        lots = self.predict(filtered_contours, image)

        return lots

    def add_correction(
        self,
        contour: np.ndarray,
        image: np.ndarray,
        is_lot: bool,
        phase_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Add user correction to training data

        Args:
            contour: Contour that was corrected
            image: Source image
            is_lot: True if this is a valid lot, False otherwise
            phase_id: Optional phase identifier
            metadata: Optional metadata
        """
        features = self.extract_features(contour, image)
        label = 1 if is_lot else 0

        example = TrainingExample(
            features=features,
            label=label,
            phase_id=phase_id,
            metadata=metadata,
        )

        self.training_data.append(example)

    def retrain(self) -> Dict:
        """
        Retrain model with accumulated training data

        Returns:
            Training metrics
        """
        return self.train(self.training_data, save_model=True)

    def save_model(self, path: str):
        """
        Save trained model to disk

        Args:
            path: File path to save model
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        model_data = {
            'classifier': self.classifier,
            'scaler': self.scaler,
            'training_data': self.training_data,
            'n_estimators': self.n_estimators,
            'min_samples': self.min_samples,
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, path: str):
        """
        Load trained model from disk

        Args:
            path: File path to load model from
        """
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        self.classifier = model_data['classifier']
        self.scaler = model_data['scaler']
        self.training_data = model_data.get('training_data', [])
        self.n_estimators = model_data.get('n_estimators', 100)
        self.min_samples = model_data.get('min_samples', 10)
        self.is_trained = True

    def get_model_info(self) -> Dict:
        """
        Get information about the trained model

        Returns:
            Model information dictionary
        """
        if not self.is_trained:
            return {
                'is_trained': False,
                'training_samples': len(self.training_data),
            }

        return {
            'is_trained': True,
            'training_samples': len(self.training_data),
            'n_estimators': self.n_estimators,
            'feature_names': [
                'area', 'perimeter', 'aspect_ratio', 'extent', 'solidity',
                'num_vertices', 'circularity', 'edge_density',
                'mean_intensity', 'std_intensity'
            ],
            'model_path': self.model_path,
        }

    def visualize_results(
        self,
        image: np.ndarray,
        lots: List[MLLotCandidate],
        show_confidence: bool = True,
    ) -> np.ndarray:
        """
        Visualize ML detection results

        Args:
            image: Input image
            lots: Detected lots
            show_confidence: Show confidence scores

        Returns:
            Image with visualizations
        """
        output = image.copy()

        for lot in lots:
            # Convert coordinates
            points = np.array(lot.coordinates, dtype=np.int32)
            points = points.reshape((-1, 1, 2))

            # Color based on confidence
            if lot.confidence > 0.8:
                color = (0, 255, 0)  # Green
            elif lot.confidence > 0.6:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 165, 255)  # Orange

            # Draw polygon
            cv2.polylines(output, [points], isClosed=True, color=color, thickness=2)

            # Calculate centroid
            M = cv2.moments(points)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                # Draw confidence
                if show_confidence:
                    text = f"{lot.confidence:.2f}"
                    cv2.putText(
                        output,
                        text,
                        (cx - 20, cy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

        return output


# Helper function
def train_from_corrections(
    corrections: List[Dict],
    image_path: str,
    model_save_path: str,
) -> Dict:
    """
    Train ML model from user corrections

    Args:
        corrections: List of correction dicts with 'contour', 'is_lot'
        image_path: Path to training image
        model_save_path: Where to save trained model

    Returns:
        Training metrics
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    detector = MLSupervisedDetector(model_path=model_save_path)

    # Add corrections
    for correction in corrections:
        detector.add_correction(
            contour=correction['contour'],
            image=image,
            is_lot=correction['is_lot'],
        )

    # Train
    metrics = detector.retrain()

    return metrics
