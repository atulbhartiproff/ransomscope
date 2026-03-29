"""
Main evaluation pipeline for ransomware detection model.

This script orchestrates the complete evaluation workflow:
1. Loads the trained model from detection_analysis/model/
2. Loads the dataset from data/processed_sequences.csv
3. Splits the dataset (80/20 train/test)
4. Measures training time and inference time
5. Computes comprehensive evaluation metrics
6. Generates visualizations
7. Produces nicely formatted reports

Usage:
    python evaluation/run_evaluation.py

Output:
    - evaluation/results/confusion_matrix.png
    - evaluation/results/roc_curve.png
    - evaluation/results/precision_recall.png
    - evaluation/results/metrics_bar.png
    - evaluation/results/timing.png
    - Console output with formatted metrics and timing reports
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import config

# Import evaluation modules
from evaluation.metrics import compute_all_metrics, format_metrics_report
from evaluation.timing import measure_training_time, measure_inference_time, format_timing_report
from evaluation.plots import (
    plot_confusion_matrix,
    plot_roc_curve,
    plot_precision_recall,
    plot_metrics_bar,
    plot_timing
)


def load_dataset(dataset_path: str = "ransomescope_dataset.csv") -> tuple:
    """
    Load the dataset from CSV file.
    
    Expected CSV format:
        - Primary format: first column is label (used by train.py)
        - Alternative format: column named 'label' or 'target'
        - All remaining columns are features
    
    Args:
        dataset_path: Path to the CSV file relative to project root
    
    Returns:
        Tuple of (X, y) where X is features and y is labels
    
    Raises:
        FileNotFoundError: If dataset file doesn't exist
    """
    
    # Construct full path
    full_path = project_root / dataset_path
    
    print(f"Loading dataset from: {full_path}")
    
    # Check if file exists
    if not full_path.exists():
        raise FileNotFoundError(f"Dataset not found at {full_path}")
    
    # Load CSV file
    df = pd.read_csv(full_path)
    print(f"✓ Dataset loaded: {df.shape[0]} samples, {df.shape[1]} columns")
    
    # Separate features and labels.
    # Training script uses label in the first column, so we default to that.
    label_col = None
    lower_cols = [str(c).strip().lower() for c in df.columns]
    for name in ("label", "target", "y"):
        if name in lower_cols:
            label_col = lower_cols.index(name)
            break

    if label_col is None:
        label_col = 0

    y = df.iloc[:, label_col].values.astype(int)
    X = df.drop(df.columns[label_col], axis=1).values
    
    print(f"  Features shape: {X.shape}")
    print(f"  Labels shape: {y.shape}")
    print(f"  Label distribution: {np.bincount(y.astype(int))}")
    
    return X, y


def load_model(model_path: str = "ransomescope_lstm.pt"):
    """
    Load the trained model from file.
    
    Expects a PyTorch state_dict file saved during training.
    
    Args:
        model_path: Path to the model file relative to project root
    
    Returns:
        Loaded model object
    
    Raises:
        FileNotFoundError: If model file doesn't exist
    """
    
    # Construct full path
    full_path = project_root / model_path
    
    print(f"\nLoading model from: {full_path}")
    
    # Check if file exists
    if not full_path.exists():
        raise FileNotFoundError(f"Model not found at {full_path}")
    
    # Build model architecture then load weights (state_dict)
    from detection_analysis.model import RansomScopeLSTM

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RansomScopeLSTM().to(device)

    state = torch.load(full_path, map_location=device)
    model.load_state_dict(state)
    model.eval()  # Set to evaluation mode
    
    print(f"✓ Model loaded successfully")
    print(f"  Model type: {type(model).__name__}")
    print(f"  Device: {device}")
    
    return model


def prepare_data(X: np.ndarray, y: np.ndarray, test_size: float = 0.2, random_state: int = 42) -> tuple:
    """
    Split and prepare the dataset for evaluation.
    
    Args:
        X: Feature matrix
        y: Label vector
        test_size: Proportion of data to use for testing (default: 0.2)
        random_state: Random seed for reproducibility
    
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    
    print("\nPreparing dataset...")
    
    # Use stratified split only when at least two classes are present.
    unique_classes = np.unique(y)
    stratify_arg = y if len(unique_classes) > 1 else None
    if stratify_arg is None:
        print("⚠ Only one class found in labels; using non-stratified split.")

    # Split dataset into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_arg
    )
    
    print(f"✓ Dataset split complete:")
    print(f"  Training set: {X_train.shape[0]} samples ({(1-test_size)*100:.0f}%)")
    print(f"  Test set: {X_test.shape[0]} samples ({test_size*100:.0f}%)")
    
    # Optional: Normalize features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"✓ Features normalized using StandardScaler")
    
    return X_train_scaled, X_test_scaled, y_train, y_test


def create_sk_compatible_model(torch_model):
    """
    Create a scikit-learn compatible wrapper for the PyTorch model.
    
    This provides predict() and predict_proba() methods required by
    evaluation functions.
    
    Args:
        torch_model: PyTorch model object
    
    Returns:
        Wrapper class with sklearn interface
    """
    
    class SKCompatibleModel:
        """Wrapper to make PyTorch model compatible with sklearn interface."""
        
        def __init__(self, torch_model):
            self.model = torch_model
            self.model.eval()

        def _prepare_input(self, X):
            """Convert flattened vectors into LSTM-ready 3D tensor."""
            arr = np.asarray(X, dtype=np.float32)

            # If already shaped as (batch, seq_len, feat_dim), keep as-is.
            if arr.ndim == 3:
                return torch.from_numpy(arr).to(next(self.model.parameters()).device)

            if arr.ndim != 2:
                raise ValueError(f"Expected 2D or 3D input, got shape {arr.shape}")

            seq_len = config.SEQUENCE_LENGTH
            feat_dim = config.FEATURE_DIM
            expected_flat = seq_len * feat_dim

            if arr.shape[1] != expected_flat:
                raise ValueError(
                    f"Expected {expected_flat} flattened features "
                    f"({seq_len}x{feat_dim}), got {arr.shape[1]}"
                )

            arr = arr.reshape(arr.shape[0], seq_len, feat_dim)
            return torch.from_numpy(arr).to(next(self.model.parameters()).device)
        
        def predict(self, X):
            """Generate binary predictions."""
            X_tensor = self._prepare_input(X)
            with torch.no_grad():
                outputs = self.model(X_tensor)
            
            # Convert to probabilities and get class predictions
            if isinstance(outputs, tuple):
                probs = torch.sigmoid(outputs[0])
            else:
                probs = torch.sigmoid(outputs)
            
            predictions = (probs > 0.5).cpu().numpy().astype(int).flatten()
            return predictions
        
        def predict_proba(self, X):
            """Generate probability predictions."""
            X_tensor = self._prepare_input(X)
            with torch.no_grad():
                outputs = self.model(X_tensor)
            
            # Convert to probabilities
            if isinstance(outputs, tuple):
                probs = torch.sigmoid(outputs[0])
            else:
                probs = torch.sigmoid(outputs)
            
            probs = probs.cpu().numpy().flatten()
            
            # Return probabilities for both classes [P(0), P(1)]
            neg_probs = 1 - probs
            return np.column_stack([neg_probs, probs])
        
        def fit(self, X, y):
            """Dummy fit method for compatibility. Model is already trained."""
            return self
    
    return SKCompatibleModel(torch_model)


def run_evaluation():
    """
    Main evaluation pipeline.
    
    Orchestrates the complete evaluation workflow including:
    - Data loading
    - Model loading
    - Training/inference timing
    - Metric computation
    - Visualization generation
    - Report printing
    """
    
    print("\n" + "="*70)
    print("RANSOMWARE DETECTION - MODEL EVALUATION PIPELINE")
    print("="*70)
    
    try:
        # Step 1: Load dataset
        print("\n[1/6] LOADING DATASET")
        print("-" * 70)
        X, y = load_dataset()
        
        # Step 2: Load model
        print("\n[2/6] LOADING MODEL")
        print("-" * 70)
        torch_model = load_model()
        model = create_sk_compatible_model(torch_model)
        
        # Step 3: Prepare data
        print("\n[3/6] PREPARING DATA")
        print("-" * 70)
        X_train, X_test, y_train, y_test = prepare_data(X, y)
        
        # Step 4: Measure training time (model is already trained, but we measure fit time)
        print("\n[4/6] MEASURING PERFORMANCE")
        print("-" * 70)
        print("\nTraining time measurement:")
        train_time = measure_training_time(model, X_train, y_train)
        print(f"✓ Training completed in {train_time:.2f} seconds")
        
        print("\nInference time measurement:")
        inference_time_per_sample = measure_inference_time(model, X_test, samples_only=True)
        print(f"✓ Inference time: {inference_time_per_sample:.4f} ms per sample")
        print(f"  Throughput: {1000.0/inference_time_per_sample:.2f} samples/second")
        
        # Step 5: Generate predictions and compute metrics
        print("\n[5/6] COMPUTING METRICS")
        print("-" * 70)
        
        # Make predictions
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]  # Get probability for positive class
        
        # Compute all metrics
        metrics = compute_all_metrics(y_test, y_pred, y_proba)
        
        print("✓ Metrics computed successfully:")
        print(f"  - Accuracy: {metrics['accuracy']:.4f}")
        print(f"  - Precision: {metrics['precision']:.4f}")
        print(f"  - Recall: {metrics['recall']:.4f}")
        print(f"  - F1 Score: {metrics['f1']:.4f}")
        if 'roc_auc' in metrics and metrics['roc_auc'] is not None:
            print(f"  - ROC AUC: {metrics['roc_auc']:.4f}")
        
        # Step 6: Generate visualizations
        print("\n[6/6] GENERATING VISUALIZATIONS")
        print("-" * 70)
        
        # Ensure results directory exists
        results_dir = project_root / "evaluation" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate plots
        print("\nGenerating plots...")
        
        print("  - Confusion matrix... ", end="", flush=True)
        plot_confusion_matrix(
            metrics['confusion_matrix'],
            save_path=str(results_dir / "confusion_matrix.png")
        )
        print("✓")
        
        print("  - ROC curve... ", end="", flush=True)
        plot_roc_curve(
            y_test, y_proba,
            save_path=str(results_dir / "roc_curve.png")
        )
        print("✓")
        
        print("  - Precision-Recall curve... ", end="", flush=True)
        plot_precision_recall(
            y_test, y_proba,
            save_path=str(results_dir / "precision_recall.png")
        )
        print("✓")
        
        print("  - Metrics bar chart... ", end="", flush=True)
        # Create dictionary of numeric metrics for plotting
        plot_metrics = {
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1'],
            'fpr': metrics['fpr'],
            'fnr': metrics['fnr']
        }
        if 'roc_auc' in metrics and metrics['roc_auc'] is not None:
            plot_metrics['roc_auc'] = metrics['roc_auc']
        
        plot_metrics_bar(
            plot_metrics,
            save_path=str(results_dir / "metrics_bar.png")
        )
        print("✓")
        
        print("  - Timing chart... ", end="", flush=True)
        plot_timing(
            train_time, inference_time_per_sample,
            save_path=str(results_dir / "timing.png")
        )
        print("✓")
        
        # === FINAL REPORTS ===
        print("\n" + "="*70)
        
        # Metrics report
        metrics_report = format_metrics_report(metrics)
        print(metrics_report)
        
        # Timing report
        timing_report = format_timing_report(
            train_time, 
            inference_time_per_sample,
            n_test_samples=len(X_test)
        )
        print(timing_report)
        
        # Summary
        print("\n" + "="*70)
        print("EVALUATION COMPLETE")
        print("="*70)
        print(f"\nResults saved to: {results_dir}")
        print("\nGenerated files:")
        print("  - confusion_matrix.png")
        print("  - roc_curve.png")
        print("  - precision_recall.png")
        print("  - metrics_bar.png")
        print("  - timing.png")
        print("\n" + "="*70 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nPlease ensure the following files exist:")
        print("  - data/processed_sequences.csv")
        print("  - detection_analysis/model/lstm_model.pt")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_evaluation()
