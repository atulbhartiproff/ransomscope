"""
Metrics module for evaluating ransomware detection model performance.

This module provides functions to compute various classification metrics including
accuracy, precision, recall, F1 score, ROC AUC, confusion matrix, and false positive rate.
All functions use scikit-learn for computation.
"""

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from typing import Dict, Tuple, Union
import numpy as np


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray = None
) -> Dict[str, Union[float, np.ndarray]]:
    """
    Compute all classification metrics for model evaluation.
    
    Args:
        y_true: True binary labels (0 or 1)
        y_pred: Predicted binary labels (0 or 1)
        y_proba: Predicted probabilities for positive class [0, 1]. Optional.
                 Required for ROC AUC computation.
    
    Returns:
        Dictionary containing all computed metrics:
        - accuracy: Overall correctness of predictions
        - precision: True positives / (true positives + false positives)
        - recall: True positives / (true positives + false negatives)
        - f1: Harmonic mean of precision and recall
        - roc_auc: Area under ROC curve (if y_proba provided)
        - confusion_matrix: 2D array [[TN, FP], [FN, TP]]
        - fpr: False positive rate
    
    Raises:
        ValueError: If y_true and y_pred have different lengths or if y_proba
                   is provided but has incorrect shape
    """
    
    # Validate inputs
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    
    if y_proba is not None and len(y_true) != len(y_proba):
        raise ValueError("y_proba must have the same length as y_true")
    
    # Initialize metrics dictionary
    metrics = {}
    
    # Compute binary classification metrics
    metrics['accuracy'] = float(accuracy_score(y_true, y_pred))
    metrics['precision'] = float(precision_score(y_true, y_pred, zero_division=0))
    metrics['recall'] = float(recall_score(y_true, y_pred, zero_division=0))
    metrics['f1'] = float(f1_score(y_true, y_pred, zero_division=0))
    
    # Compute confusion matrix as fixed binary 2x2 matrix.
    # This prevents shape issues when y_true/y_pred contain only one class.
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    metrics['confusion_matrix'] = cm
    
    # Compute false positive rate manually from confusion matrix
    # FPR = FP / (FP + TN)
    tn, fp, fn, tp = cm.ravel()
    metrics['fpr'] = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    metrics['fnr'] = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    
    # Compute ROC AUC if probabilities are provided
    if y_proba is not None:
        try:
            metrics['roc_auc'] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            # Handle case where ROC AUC cannot be computed
            metrics['roc_auc'] = None
    
    return metrics


def compute_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute accuracy: (TP + TN) / (TP + TN + FP + FN)
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        Accuracy score as float between 0 and 1
    """
    return float(accuracy_score(y_true, y_pred))


def compute_precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute precision: TP / (TP + FP)
    
    Measures the proportion of positive predictions that were correct.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        Precision score as float between 0 and 1
    """
    return float(precision_score(y_true, y_pred, zero_division=0))


def compute_recall(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute recall (sensitivity/TPR): TP / (TP + FN)
    
    Measures the proportion of actual positives that were correctly identified.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        Recall score as float between 0 and 1
    """
    return float(recall_score(y_true, y_pred, zero_division=0))


def compute_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute F1 score: 2 * (precision * recall) / (precision + recall)
    
    Harmonic mean of precision and recall. Useful when you care about both
    false positives and false negatives.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        F1 score as float between 0 and 1
    """
    return float(f1_score(y_true, y_pred, zero_division=0))


def compute_roc_auc(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """
    Compute ROC AUC (Area Under the Receiver Operating Characteristic Curve)
    
    Measures the model's ability to distinguish between classes across all thresholds.
    Value of 1.0 indicates perfect classifier, 0.5 indicates random classifier.
    
    Args:
        y_true: True binary labels
        y_proba: Predicted probabilities for positive class
    
    Returns:
        ROC AUC score as float between 0 and 1
    
    Raises:
        ValueError: If y_proba cannot generate valid ROC curve
    """
    return float(roc_auc_score(y_true, y_proba))


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> np.ndarray:
    """
    Compute confusion matrix.
    
    Matrix format:
        [[TN, FP],
         [FN, TP]]
    where:
        - TN (True Negatives): Correctly predicted negative class
        - FP (False Positives): Incorrectly predicted positive class
        - FN (False Negatives): Incorrectly predicted negative class
        - TP (True Positives): Correctly predicted positive class
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        2x2 confusion matrix as numpy array
    """
    return confusion_matrix(y_true, y_pred, labels=[0, 1])


def compute_false_positive_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute False Positive Rate (FPR): FP / (FP + TN)
    
    Measures the proportion of negative instances that were incorrectly
    classified as positive.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        False positive rate as float between 0 and 1
    """
    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    # Calculate FPR
    if (fp + tn) == 0:
        return 0.0
    
    fpr = fp / (fp + tn)
    return float(fpr)


def compute_false_negative_rate(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute False Negative Rate (FNR): FN / (FN + TP)
    
    Measures the proportion of positive instances that were incorrectly
    classified as negative.
    
    Args:
        y_true: True binary labels
        y_pred: Predicted binary labels
    
    Returns:
        False negative rate as float between 0 and 1
    """
    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    # Calculate FNR
    if (fn + tp) == 0:
        return 0.0
    
    fnr = fn / (fn + tp)
    return float(fnr)


def format_metrics_report(metrics: Dict[str, Union[float, np.ndarray]]) -> str:
    """
    Format metrics dictionary into a readable report string.
    
    Args:
        metrics: Dictionary returned from compute_all_metrics()
    
    Returns:
        Formatted string report of all metrics
    """
    # Build report string
    report = "\n" + "=" * 60 + "\n"
    report += "MODEL EVALUATION METRICS REPORT\n"
    report += "=" * 60 + "\n"
    
    # Single-value metrics
    report += f"\nAccuracy:        {metrics.get('accuracy', 'N/A'):.4f}\n"
    report += f"Precision:       {metrics.get('precision', 'N/A'):.4f}\n"
    report += f"Recall:          {metrics.get('recall', 'N/A'):.4f}\n"
    report += f"F1 Score:        {metrics.get('f1', 'N/A'):.4f}\n"
    
    if 'roc_auc' in metrics and metrics['roc_auc'] is not None:
        report += f"ROC AUC:         {metrics['roc_auc']:.4f}\n"
    
    report += f"\nFalse Positive Rate: {metrics.get('fpr', 'N/A'):.4f}\n"
    report += f"False Negative Rate: {metrics.get('fnr', 'N/A'):.4f}\n"
    
    # Confusion matrix
    if 'confusion_matrix' in metrics:
        cm = metrics['confusion_matrix']
        tn, fp, fn, tp = cm.ravel()
        report += "\nConfusion Matrix:\n"
        report += f"  True Negatives:  {tn}\n"
        report += f"  False Positives: {fp}\n"
        report += f"  False Negatives: {fn}\n"
        report += f"  True Positives:  {tp}\n"
    
    report += "=" * 60 + "\n"
    
    return report
