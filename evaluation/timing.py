"""
Timing module for measuring model training and inference performance.

This module provides functions to measure the time required for model training
and inference. Measurements use time.perf_counter() for high precision timing.
"""

import time
from typing import Tuple, Union
import numpy as np


def measure_training_time(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray
) -> float:
    """
    Measure the time required to train a model.
    
    The model must have a fit() method (compatible with scikit-learn interface).
    
    Args:
        model: Trained model object with fit() method
        X_train: Training feature matrix (n_samples, n_features)
        y_train: Training labels
    
    Returns:
        Training time in seconds as float
    
    Example:
        >>> from sklearn.linear_model import LogisticRegression
        >>> model = LogisticRegression()
        >>> train_time = measure_training_time(model, X_train, y_train)
        >>> print(f"Training took {train_time:.2f} seconds")
    """
    
    # Record start time with high precision
    start_time = time.perf_counter()
    
    # Train the model
    model.fit(X_train, y_train)
    
    # Record end time
    end_time = time.perf_counter()
    
    # Calculate elapsed time in seconds
    elapsed_time = end_time - start_time
    
    return float(elapsed_time)


def measure_inference_time(
    model,
    X_test: np.ndarray,
    samples_only: bool = False
) -> Union[float, Tuple[float, float]]:
    """
    Measure the time required for model inference on test data.
    
    The model must have a predict() method (compatible with scikit-learn interface).
    
    Args:
        model: Trained model object with predict() method
        X_test: Test feature matrix (n_samples, n_features)
        samples_only: If True, return only milliseconds per sample.
                     If False, return tuple of (total_ms, per_sample_ms)
    
    Returns:
        If samples_only=True: Milliseconds per sample as float
        If samples_only=False: Tuple of (total_time_ms, per_sample_ms) as floats
    
    Example:
        >>> from sklearn.linear_model import LogisticRegression
        >>> model = LogisticRegression()
        >>> per_sample_ms = measure_inference_time(model, X_test, samples_only=True)
        >>> print(f"Inference: {per_sample_ms:.2f} ms per sample")
        
        >>> total_ms, per_sample_ms = measure_inference_time(model, X_test, samples_only=False)
        >>> print(f"Total: {total_ms:.2f} ms, Per sample: {per_sample_ms:.4f} ms")
    """
    
    # Get number of test samples
    n_samples = X_test.shape[0]
    
    # Record start time with high precision
    start_time = time.perf_counter()
    
    # Run inference
    predictions = model.predict(X_test)
    
    # Record end time
    end_time = time.perf_counter()
    
    # Calculate elapsed time in milliseconds
    elapsed_time_seconds = end_time - start_time
    total_time_ms = elapsed_time_seconds * 1000.0
    
    # Calculate per-sample inference time in milliseconds
    per_sample_ms = total_time_ms / n_samples if n_samples > 0 else 0.0
    
    if samples_only:
        return float(per_sample_ms)
    else:
        return (float(total_time_ms), float(per_sample_ms))


def measure_prediction_speed(
    model,
    X_test: np.ndarray,
    n_iterations: int = 1
) -> float:
    """
    Measure average prediction speed over multiple iterations.
    
    Useful for getting more stable timing measurements on fast models.
    
    Args:
        model: Trained model object with predict() method
        X_test: Test feature matrix
        n_iterations: Number of times to run inference (default: 1)
    
    Returns:
        Average milliseconds per sample across all iterations
    
    Example:
        >>> avg_time = measure_prediction_speed(model, X_test, n_iterations=10)
        >>> print(f"Average inference: {avg_time:.4f} ms per sample")
    """
    
    if n_iterations < 1:
        raise ValueError("n_iterations must be at least 1")
    
    total_per_sample_ms = 0.0
    
    # Run inference multiple times
    for _ in range(n_iterations):
        per_sample_ms = measure_inference_time(model, X_test, samples_only=True)
        total_per_sample_ms += per_sample_ms
    
    # Calculate average
    average_per_sample_ms = total_per_sample_ms / n_iterations
    
    return float(average_per_sample_ms)


def measure_prediction_with_probability(
    model,
    X_test: np.ndarray
) -> Tuple[float, float]:
    """
    Measure inference time when probabilities are needed.
    
    Some models may have different performance for predict() vs predict_proba().
    
    Args:
        model: Trained model object with predict_proba() method
        X_test: Test feature matrix
    
    Returns:
        Tuple of (total_time_ms, per_sample_ms) for probability predictions
    
    Example:
        >>> total_ms, per_sample_ms = measure_prediction_with_probability(model, X_test)
        >>> print(f"Probability inference: {per_sample_ms:.4f} ms per sample")
    """
    
    n_samples = X_test.shape[0]
    
    # Record start time
    start_time = time.perf_counter()
    
    # Get probabilities
    probabilities = model.predict_proba(X_test)
    
    # Record end time
    end_time = time.perf_counter()
    
    # Calculate times in milliseconds
    elapsed_time_seconds = end_time - start_time
    total_time_ms = elapsed_time_seconds * 1000.0
    per_sample_ms = total_time_ms / n_samples if n_samples > 0 else 0.0
    
    return (float(total_time_ms), float(per_sample_ms))


def format_timing_report(
    train_time_seconds: float,
    inference_time_ms: float,
    n_test_samples: int = None
) -> str:
    """
    Format timing measurements into a readable report string.
    
    Args:
        train_time_seconds: Training time in seconds
        inference_time_ms: Inference time in milliseconds per sample
        n_test_samples: Optional number of test samples for reference
    
    Returns:
        Formatted timing report string
    
    Example:
        >>> report = format_timing_report(45.5, 0.25, n_test_samples=1000)
        >>> print(report)
    """
    
    report = "\n" + "=" * 60 + "\n"
    report += "TIMING PERFORMANCE REPORT\n"
    report += "=" * 60 + "\n"
    
    # Training time information
    report += f"\nTraining Time:     {train_time_seconds:.2f} seconds\n"
    
    # Convert to human-readable format
    if train_time_seconds >= 60:
        minutes = int(train_time_seconds // 60)
        seconds = train_time_seconds % 60
        report += f"                   ({minutes}m {seconds:.1f}s)\n"
    
    # Inference time information
    report += f"\nInference Time:    {inference_time_ms:.4f} ms per sample\n"
    
    # Calculate throughput (samples per second)
    if inference_time_ms > 0:
        samples_per_second = 1000.0 / inference_time_ms
        report += f"Throughput:        {samples_per_second:.2f} samples/second\n"
    
    # Add test set size if provided
    if n_test_samples is not None:
        total_inference_ms = (inference_time_ms * n_test_samples) / 1000.0
        report += f"\nTotal inference time for {n_test_samples} samples: {total_inference_ms:.2f} seconds\n"
    
    report += "=" * 60 + "\n"
    
    return report
