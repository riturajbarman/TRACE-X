import numpy as np
from sklearn.ensemble import IsolationForest

from app.domain.anomaly.features import FEATURE_NAMES

class AnomalyModel:
    """
    Wrapper for Isolation Forest to detect anomalies in event feature vectors.
    """
    
    VERSION = "1.0.0"
    
    def __init__(self, random_state: int = 42, contamination: float = "auto"):
        self.model = IsolationForest(
            random_state=random_state,
            contamination=contamination
        )
        self.is_fitted = False
        # Store training feature means to help build explanations later
        self.feature_means = None
        
    def fit(self, X: np.ndarray):
        """Train the baseline model on a set of feature vectors."""
        if len(X) == 0:
            return
            
        self.model.fit(X)
        # Calculate mean for each feature column for later explanation generation
        self.feature_means = np.mean(X, axis=0)
        self.is_fitted = True
        
    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Predict anomalies.
        Returns:
            is_anomaly: boolean array (True if anomaly, False if normal)
            scores: float array of anomaly scores (higher is more anomalous)
        """
        if not self.is_fitted or len(X) == 0:
            return np.array([]), np.array([])
            
        # IsolationForest returns -1 for outliers and 1 for inliers.
        preds = self.model.predict(X)
        is_anomaly = preds == -1
        
        # score_samples returns opposite of anomaly score (lower values are more anomalous)
        # We invert it so higher score = more anomalous. 
        # Normalize to a 0-100 range loosely based on training data.
        raw_scores = -self.model.score_samples(X)
        # Scale score: typical values are between 0.3 and 0.8
        scores = np.clip((raw_scores - 0.3) / 0.5 * 100, 0, 100)
        
        return is_anomaly, scores
        
    def explain(self, x: np.ndarray, top_n: int = 3) -> str:
        """
        Provide a deterministic explanation of why this vector was flagged.
        We simply find the features that deviate most from the training mean.
        """
        if not self.is_fitted or self.feature_means is None:
            return "No explanation available"
            
        # Calculate absolute difference from mean, normalized roughly by mean (avoid div 0)
        diff = np.abs(x - self.feature_means)
        norm_diff = diff / (np.abs(self.feature_means) + 1e-5)
        
        # Get indices of top_n largest deviations
        top_indices = np.argsort(norm_diff)[-top_n:][::-1]
        
        explanation_parts = []
        for idx in top_indices:
            # Only include if there's actually a meaningful deviation
            if norm_diff[idx] > 0.1:
                feat_name = FEATURE_NAMES[idx]
                val = x[idx]
                mean_val = self.feature_means[idx]
                explanation_parts.append(f"{feat_name} (val: {val:.2f}, baseline mean: {mean_val:.2f})")
                
        if explanation_parts:
            return "Anomalous features: " + "; ".join(explanation_parts)
        return "Anomaly detected, but no single feature deviated significantly"
